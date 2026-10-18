from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
import sqlite3
import re

import httpx

from app.main import create_application


class DraftWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "workflow.sqlite3"
        self.app = create_application(self.path)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        profile = await self.client.post("/api/v1/profiles", json={"candidate_name": "Jane", "target_role": "Accountant", "core_skills": ["Excel"], "featured_project": "Ledger reporting"})
        contact = await self.client.post("/api/v1/workflow/contacts", json={"full_name": "Sam Smith", "job_title": "Recruiter", "company": "Example", "company_domain": "example.com", "email": "sam@example.com", "source_url": "https://example.com/team"})
        self.assertEqual(contact.status_code, 201)
        self.source = dict(profile_id=profile.json()["id"], discovery_id=contact.json()["id"], lead_index=0, tone="direct")

    async def draft_payload(self):
        response = await self.client.post("/api/v1/workflow/preview", json=self.source)
        self.assertEqual(response.status_code, 200)
        pitch = response.json()
        return {**self.source, "request_id": str(uuid4()), "recipient_email": "sam@example.com", "recipient_confirmed": True, "subject_line": pitch["subject_line"], "body": pitch["body"]}

    async def test_complete_workflow_preserves_sources_and_edits_across_restart(self):
        payload = await self.draft_payload()
        self.assertIn("Ledger reporting", payload["body"])
        self.assertIn("Jane", payload["body"])
        draft = (await self.client.post("/api/v1/workflow/drafts", json=payload)).json()
        self.assertEqual(draft["profile_id"], self.source["profile_id"])
        self.assertEqual(draft["discovery_id"], self.source["discovery_id"])
        self.assertEqual(draft["status"], "draft")
        edit = dict(expected_version=1, recipient_email="sam@example.com", recipient_confirmed=True, subject_line="A personal introduction", body="Hi Sam, I built Ledger in Excel. Best, Jane")
        response = await self.client.patch(f"/api/v1/outbox/items/{draft['id']}", json=edit)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], 2)
        self.assertIsNotNone(response.json()["updated_at"])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_application(self.path)), base_url="http://test") as reopened:
            saved = (await reopened.get(f"/api/v1/outbox/items/{draft['id']}")).json()
            self.assertEqual(saved["body"], edit["body"])
            self.assertEqual(saved["profile_id"], self.source["profile_id"])
            self.assertIsNone(saved["sent_at"])
            events = (await reopened.get("/api/v1/history", params={"record_id": draft["id"]})).json()
            self.assertEqual([event["action"] for event in events], ["draft_updated", "outbox_draft"])

    async def test_retry_is_idempotent_and_changed_payload_conflicts(self):
        payload = await self.draft_payload()
        first = await self.client.post("/api/v1/workflow/drafts", json=payload)
        second = await self.client.post("/api/v1/workflow/drafts", json=payload)
        self.assertEqual(first.json(), second.json())
        self.assertEqual((await self.client.get("/api/v1/outbox/stats")).json()["total_drafts"], 1)
        events = (await self.client.get("/api/v1/history", params={"record_id": first.json()["id"]})).json()
        self.assertEqual(len(events), 1)
        response = await self.client.post("/api/v1/workflow/drafts", json={**payload, "body": "A different body"})
        self.assertEqual(response.status_code, 409)

    async def test_stale_edits_are_rejected_without_losing_newer_text(self):
        draft = (await self.client.post("/api/v1/workflow/drafts", json=await self.draft_payload())).json()
        edit = dict(expected_version=1, recipient_email="sam@example.com", recipient_confirmed=True, subject_line="Updated subject", body="First editor's text")
        self.assertEqual((await self.client.patch(f"/api/v1/outbox/items/{draft['id']}", json=edit)).status_code, 200)
        self.assertEqual((await self.client.patch(f"/api/v1/outbox/items/{draft['id']}", json={**edit, "body": "Stale editor"})).status_code, 409)
        self.assertEqual((await self.client.get(f"/api/v1/outbox/items/{draft['id']}")).json()["body"], edit["body"])

    async def test_save_requires_explicit_recipient_review(self):
        payload = await self.draft_payload()
        payload.pop("recipient_confirmed")
        self.assertEqual((await self.client.post("/api/v1/workflow/drafts", json=payload)).status_code, 422)
        self.assertEqual((await self.client.post("/api/v1/workflow/drafts", json={**payload, "recipient_confirmed": False})).status_code, 422)
        self.assertEqual((await self.client.get("/api/v1/outbox/items")).json(), [])

    async def test_missing_sources_and_invalid_lead_fail_before_saving(self):
        payload = await self.draft_payload()
        for changed in ({"profile_id": str(uuid4())}, {"discovery_id": str(uuid4())}, {"lead_index": 42}):
            self.assertEqual((await self.client.post("/api/v1/workflow/drafts", json={**payload, **changed})).status_code, 404)
        self.assertEqual((await self.client.get("/api/v1/outbox/items")).json(), [])

    async def test_edit_rolls_back_if_history_fails(self):
        draft = (await self.client.post("/api/v1/workflow/drafts", json=await self.draft_payload())).json()
        edit = dict(expected_version=1, recipient_email="sam@example.com", recipient_confirmed=True, subject_line="New subject", body="Changed")
        with patch.object(self.app.state.store, "_append_event", side_effect=sqlite3.OperationalError("test failure")):
            with self.assertLogs("app.main", level="ERROR"):
                response = await self.client.patch(f"/api/v1/outbox/items/{draft['id']}", json=edit)
        self.assertEqual(response.status_code, 503)
        self.assertEqual((await self.client.get(f"/api/v1/outbox/items/{draft['id']}")).json(), draft)

    async def test_simulation_cannot_be_edited_as_draft(self):
        item = (await self.client.post("/api/v1/outbox/queue", json=dict(recipient_email="sam@example.com", recipient_name="Sam", company_name="Example", subject_line="Test", body="Test", mode="simulate"))).json()
        change = dict(expected_version=1, recipient_email="sam@example.com", recipient_confirmed=True, subject_line="Test", body="Edited")
        self.assertEqual((await self.client.patch(f"/api/v1/outbox/items/{item['id']}", json=change)).status_code, 409)

    async def test_manual_contact_is_stored_as_unverified(self):
        saved = (await self.client.get(f"/api/v1/discoveries/{self.source['discovery_id']}")).json()
        lead = saved["result"]["leads"][0]
        self.assertIsNone(lead["recommended_email"])
        self.assertEqual(lead["status"], "unverified")
        self.assertEqual(lead["profile_url"], "https://example.com/team")

    async def test_dashboard_and_assets_are_served(self):
        response = await self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<div id="root"></div>', response.text)
        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', response.text)
        self.assertTrue(assets)
        for asset in assets:
            self.assertEqual((await self.client.get(asset)).status_code, 200)
