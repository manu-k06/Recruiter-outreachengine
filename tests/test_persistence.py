"""Exercise durable behavior with real SQLite files and no external services."""
import asyncio
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.core.storage import SQLiteStore, StorageUnavailableError
from app.main import create_application
from app.schemas.outbox import OutboxItem, OutboxStatus
from app.schemas.pitch import CandidateProfile
from app.services.email_verifier import email_verifier_service


class PersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "outreach.sqlite3"
        self.app = create_application(self.path)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def reopen(self):
        await self.client.aclose()
        self.app = create_application(self.path)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    def message(self, mode="draft"):
        return dict(recipient_email="sam@example.com", recipient_name="Sam", company_name="Example",
                    subject_line="Hiring inquiry", body="Hello Sam, are you hiring? Best, Jane", mode=mode)

    async def test_profiles_drafts_simulations_and_history_survive_reopen(self):
        profile = await self.client.post("/api/v1/profiles", json={"candidate_name": "Jane", "target_role": "Accountant", "core_skills": ["Excel"]})
        self.assertEqual(profile.status_code, 201)
        draft = (await self.client.post("/api/v1/outbox/queue", json=self.message())).json()
        simulation = (await self.client.post("/api/v1/outbox/queue", json=self.message("simulate"))).json()
        await self.reopen()
        self.assertEqual((await self.client.get(f"/api/v1/profiles/{profile.json()['id']}")).json(), profile.json())
        self.assertEqual((await self.client.get(f"/api/v1/outbox/items/{draft['id']}")).json(), draft)
        self.assertEqual((await self.client.get(f"/api/v1/outbox/items/{simulation['id']}")).json(), simulation)
        stats = (await self.client.get("/api/v1/outbox/stats")).json()
        self.assertEqual((stats["total_drafts"], stats["total_simulated"], stats["total_sent"]), (1, 1, 0))
        events = (await self.client.get("/api/v1/history")).json()
        self.assertEqual({e["action"] for e in events}, {"profile_saved", "outbox_draft", "outbox_simulated"})
        self.assertEqual(len(events), 3)

    async def test_discovery_snapshot_includes_request_and_verification(self):
        invalid = await email_verifier_service.verify("not-an-email")
        with patch("app.services.recruiter_discovery.recruiter_discovery_service.search_public_profiles", new=AsyncMock(return_value=[("Sam Smith", "Recruiter")])), patch.object(email_verifier_service, "verify", new=AsyncMock(return_value=invalid)):
            response = await self.client.post("/api/v1/discover-recruiters", json={"company": "Example", "company_domain": "example.com"})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        await self.reopen()
        saved = (await self.client.get(f"/api/v1/discoveries/{result['discovery_id']}")).json()
        self.assertEqual(saved["result"], result)
        self.assertEqual(saved["request"]["company_domain"], "example.com")
        self.assertEqual(saved["result"]["leads"][0]["verification"], invalid.model_dump(mode="json"))

    async def test_empty_discovery_is_saved_without_inventing_leads(self):
        with patch("app.services.recruiter_discovery.recruiter_discovery_service.search_public_profiles", new=AsyncMock(return_value=[])):
            response = await self.client.get("/api/v1/discover-recruiters", params={"company": "Example"})
        self.assertEqual(response.status_code, 200)
        await self.reopen()
        results = (await self.client.get("/api/v1/discoveries")).json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["result"]["leads"], [])
        self.assertTrue(results[0]["result"]["warnings"])

    async def test_pagination_filters_and_missing_ids(self):
        for _ in range(3):
            await self.client.post("/api/v1/outbox/queue", json=self.message())
        await self.client.post("/api/v1/outbox/queue", json=self.message("simulate"))
        first = (await self.client.get("/api/v1/outbox/items", params={"status": "draft", "limit": 2})).json()
        second = (await self.client.get("/api/v1/outbox/items", params={"status": "draft", "limit": 2, "offset": 2})).json()
        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 1)
        self.assertEqual(len({i["id"] for i in first + second}), 3)
        events = (await self.client.get("/api/v1/history", params={"record_id": second[0]["id"]})).json()
        self.assertEqual(len(events), 1)
        for route in ("profiles", "discoveries", "outbox/items"):
            self.assertEqual((await self.client.get(f"/api/v1/{route}/missing")).status_code, 404)
            self.assertEqual((await self.client.get(f"/api/v1/{route}", params={"limit": 101})).status_code, 422)

    async def test_failed_history_write_rolls_back_record_and_returns_503(self):
        with patch.object(self.app.state.store, "_append_event", side_effect=sqlite3.OperationalError("injected failure")):
            with self.assertLogs("app.main", level="ERROR"):
                response = await self.client.post("/api/v1/outbox/queue", json=self.message())
        self.assertEqual(response.status_code, 503)
        await self.reopen()
        self.assertEqual((await self.client.get("/api/v1/outbox/items")).json(), [])
        self.assertEqual((await self.client.get("/api/v1/history")).json(), [])

    async def test_live_send_and_invalid_profile_do_not_create_records(self):
        self.assertEqual((await self.client.post("/api/v1/outbox/queue", json=self.message("live_send"))).status_code, 503)
        self.assertEqual((await self.client.post("/api/v1/profiles", json={"candidate_name": " "})).status_code, 422)
        self.assertEqual((await self.client.get("/api/v1/history")).json(), [])

    async def test_parsing_does_not_implicitly_save_unconfirmed_profile(self):
        await self.client.post("/api/v1/resume/parse-markdown", json={"markdown_content": "# Jane"})
        self.assertEqual((await self.client.get("/api/v1/profiles")).json(), [])

    async def test_worker_instances_share_persisted_limit_and_utc_sent_count(self):
        first = SQLiteStore(self.path, daily_limit=3)
        first.initialize()
        now = datetime.now(timezone.utc)
        for sent_at in (now, now - timedelta(days=1)):
            first.save_outbox(OutboxItem(id=str(uuid4()), created_at=sent_at, sent_at=sent_at, status=OutboxStatus.SENT,
                                        **{k: v for k, v in self.message().items() if k != "mode"}))
        second = SQLiteStore(self.path, daily_limit=99)
        self.assertEqual(second.outbox_stats().daily_limit, 3)
        self.assertEqual(second.outbox_stats().sent_today, 1)
        self.assertEqual(second.outbox_stats().total_sent, 2)
        self.assertEqual(second.outbox_stats().remaining_today, 2)

    async def test_concurrent_initialization_and_writes_preserve_every_record(self):
        path = self.path
        def write(index):
            store = SQLiteStore(path)
            return store.save_profile(CandidateProfile(candidate_name=f"Candidate {index}", target_role="Engineer")).id
        def run_workers():
            with ThreadPoolExecutor(max_workers=4) as workers:
                return list(workers.map(write, range(16)))
        ids = await asyncio.to_thread(run_workers)
        reopened = SQLiteStore(path)
        self.assertEqual({p.id for p in reopened.list_profiles()}, set(ids))
        self.assertEqual(len(reopened.history()), 16)

    async def test_separate_python_process_reads_saved_profile(self):
        profile = self.app.state.store.save_profile(CandidateProfile(candidate_name="Jane", target_role="Accountant"))
        code = "import sys; from app.core.storage import SQLiteStore; print(SQLiteStore(sys.argv[1]).get_profile(sys.argv[2]).model_dump_json())"
        result = await asyncio.to_thread(subprocess.run, [sys.executable, "-c", code, str(self.path), profile.id],
                                         cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["candidate"]["candidate_name"], "Jane")

    async def test_schema_version_and_environment_configuration(self):
        self.app.state.store.initialize()
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
        with patch.dict("os.environ", {"DATABASE_PATH": str(self.path), "DAILY_SEND_LIMIT": "7"}):
            settings = Settings.from_environment()
            self.assertEqual(settings.DATABASE_PATH, self.path)
            self.assertEqual(settings.DAILY_SEND_LIMIT, 7)

    async def test_future_schema_and_unwritable_path_fail_without_fallback(self):
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("PRAGMA user_version = 99")
        with self.assertRaises(StorageUnavailableError):
            self.app.state.store.initialize()
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 99)
        bad = SQLiteStore(self.path / "not-a-directory.sqlite3")
        with self.assertRaises(StorageUnavailableError):
            bad.initialize()

    async def test_application_startup_initializes_storage(self):
        self.assertFalse(self.path.exists())
        async with self.app.router.lifespan_context(self.app):
            self.assertTrue(self.path.exists())
            self.assertEqual(self.app.state.store.list_profiles(), [])
