"""Offline regression checks for truthful results and preserved candidate facts."""
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from app.main import app
from app.services.email_verifier import email_verifier_service
from app.services.outbox_dispatcher import outbox_dispatcher_service


class TrustworthyResultsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://testserver",
        )
        outbox_dispatcher_service._outbox.clear()

    async def asyncTearDown(self):
        await self.client.aclose()
        outbox_dispatcher_service._outbox.clear()

    def message(self, mode="draft"):
        return dict(recipient_email="sam@example.com", recipient_name="Sam",
                    company_name="Example", subject_line="Hiring inquiry",
                    body="Hello Sam, are you hiring accountants? Best, Jane", mode=mode)

    async def test_live_send_is_unavailable_and_does_not_create_sent_record(self):
        response = await self.client.post("/api/v1/outbox/queue", json=self.message("live_send"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual((await self.client.get("/api/v1/outbox/items")).json(), [])

    async def test_simulation_never_counts_as_sent(self):
        response = await self.client.post("/api/v1/outbox/queue", json=self.message("simulate"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "simulated")
        self.assertIsNone(response.json()["sent_at"])
        stats = (await self.client.get("/api/v1/outbox/stats")).json()
        self.assertEqual(stats["sent_today"], 0)
        self.assertEqual(stats["total_sent"], 0)
        self.assertEqual(stats["total_simulated"], 1)

    async def test_default_is_draft_and_invalid_recipient_is_rejected(self):
        payload = self.message()
        payload.pop("mode")
        response = await self.client.post("/api/v1/outbox/queue", json=payload)
        self.assertEqual(response.json()["status"], "draft")
        payload["recipient_email"] = "not-an-email"
        self.assertEqual((await self.client.post("/api/v1/outbox/queue", json=payload)).status_code, 422)

    async def test_no_search_results_means_no_leads_even_for_sample_companies(self):
        invalid = await email_verifier_service.verify("not-an-email")
        with patch("app.services.recruiter_discovery.recruiter_discovery_service.search_public_profiles", new=AsyncMock(return_value=[])), patch.object(email_verifier_service, "verify", new=AsyncMock(return_value=invalid)):
            for company in ("Stripe", "Nonexistent Audit Company"):
                response = await self.client.post("/api/v1/discover-recruiters", json={"company": company})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["leads"], [])
                self.assertTrue(response.json()["warnings"])

    async def test_invalid_or_uncertain_email_is_not_recommended(self):
        invalid = await email_verifier_service.verify("not-an-email")
        with patch("app.services.recruiter_discovery.recruiter_discovery_service.search_public_profiles", new=AsyncMock(return_value=[("Sam Smith", "Recruiter")])):
            for status in ("invalid", "risky", "valid"):
                from app.schemas.verifier import EmailStatus
                result = invalid.model_copy(update={"status": EmailStatus(status)})
                with patch.object(email_verifier_service, "verify", new=AsyncMock(return_value=result)):
                    response = await self.client.post("/api/v1/discover-recruiters", json={"company": "Example"})
                    lead = response.json()["leads"][0]
                    # Mailbox acceptance cannot establish that this address belongs to this person.
                    self.assertIsNone(lead["recommended_email"])

    async def test_resume_does_not_invent_missing_facts(self):
        response = await self.client.post("/api/v1/resume/parse-markdown", json={"markdown_content": "# Jane Doe\nAccountant\nhttps://github.com/jane"})
        data = response.json()
        self.assertEqual(data["name"], "Jane Doe")
        self.assertEqual(data["skills"], [])
        self.assertEqual(data["projects"], [])
        self.assertIsNone(data["target_role"])
        self.assertIsNone(data["portfolio_url"])
        self.assertTrue(data["warnings"])

    async def test_resume_keeps_full_explicit_portfolio_and_unknown_name(self):
        response = await self.client.post("/api/v1/resume/parse-markdown", json={"markdown_content": "Portfolio: [My work](https://jane.dev/work?view=all)\n## Skills\n- Accounting"})
        self.assertEqual(response.json()["portfolio_url"], "https://jane.dev/work?view=all")
        self.assertIsNone(response.json()["name"])

    async def test_refinement_preserves_identity_and_reports_unhandled_instructions(self):
        body = "Hi Sam,\n\nMy name is Jane. I am an accountant.\n\nBest,\nJane"
        for instruction in ("Make it shorter", "Highlight Cineforge and AI", "Translate into French"):
            response = await self.client.post("/api/v1/ai/refine", json={"recruiter_name": "Sam", "company_name": "Example", "current_subject": "Jane inquiry", "current_body": body, "instruction": instruction})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["refined_body"], body)
            self.assertTrue(response.json()["warnings"])

    async def test_review_is_a_heuristic_not_send_approval(self):
        response = await self.client.post("/api/v1/ai/review", json={"recruiter_name": "Sam", "company_name": "Example", "subject_line": "Inquiry", "body": "Sam Example?", "custom_guidelines": ["Must mention accounting"]})
        data = response.json()
        self.assertEqual(data["readiness"], "Needs Revision")
        self.assertLess(data["overall_score"], 70)
        self.assertEqual(data["review_method"], "heuristic")
        self.assertEqual(data["unchecked_guidelines"], ["Must mention accounting"])

    async def test_blank_names_and_empty_resume_return_validation_errors(self):
        response = await self.client.post("/api/v1/ai/review", json={"recruiter_name": "  ", "company_name": "Example", "subject_line": "Inquiry", "body": "Hello"})
        self.assertEqual(response.status_code, 422)
        response = await self.client.post("/api/v1/resume/parse-markdown", json={"markdown_content": " \n "})
        self.assertEqual(response.status_code, 422)
        with patch("app.services.recruiter_discovery.recruiter_discovery_service.search_public_profiles", new=AsyncMock(return_value=[])) as search:
            response = await self.client.get("/api/v1/discover-recruiters", params={"company": " "})
            search.assert_not_awaited()
        self.assertEqual(response.status_code, 422)

    async def test_pitch_requires_candidate_and_valid_tone(self):
        payload = dict(recruiter_name="Sam", recruiter_title="Recruiter", company_name="Example")
        self.assertEqual((await self.client.post("/api/v1/generate-pitch", json=payload)).status_code, 422)
        payload["candidate"] = {"candidate_name": "Jane", "target_role": "Accountant"}
        payload["tone"] = "nonsense"
        self.assertEqual((await self.client.post("/api/v1/generate-pitch", json=payload)).status_code, 422)

    async def test_all_pitch_tones_only_use_supplied_candidate_facts(self):
        for tone in ("direct", "technical", "conversational"):
            response = await self.client.post("/api/v1/generate-pitch", json={"recruiter_name": "Sam", "recruiter_title": "Recruiter", "company_name": "Example", "candidate": {"candidate_name": "Jane", "target_role": "Accountant"}, "tone": tone})
            self.assertEqual(response.status_code, 200)
            body = response.json()["body"]
            self.assertIn("Jane", body)
            for invented in ("Cineforge", "Python", "distributed systems", "reactive interfaces", "None", "I've been following", "you lead technical"):
                self.assertNotIn(invented, body)
            self.assertEqual(response.json()["matched_skills"], [])

    async def test_sample_projects_are_extracted_without_metadata_becoming_projects(self):
        markdown = (Path(__file__).resolve().parents[1] / "sample_resume.md").read_text(encoding="utf-8")
        response = await self.client.post("/api/v1/resume/parse-markdown", json={"markdown_content": markdown})
        data = response.json()
        self.assertEqual([p["title"] for p in data["projects"]], ["Cineforge", "Recruiter Outreach Engine"])
        self.assertEqual(data["projects"][0]["tech_stack"], ["React", "FastAPI", "Supabase", "Google Gemini AI"])
        self.assertIn("Python", data["skills"])
        self.assertNotIn("Bachelor", data["projects"][-1]["description"])

    async def test_shortening_changes_filler_without_changing_facts(self):
        body = "Hi Sam,\n\nI am writing to inquire about accounting roles. I built Ledger in Excel.\n\nBest,\nJane"
        response = await self.client.post("/api/v1/ai/refine", json=dict(current_subject="Jane inquiry", current_body=body, instruction="Make it shorter and translate to French", recruiter_name="Sam", company_name="Example"))
        data = response.json()
        self.assertIn("I'm asking about accounting roles.", data["refined_body"])
        self.assertIn("I built Ledger in Excel.", data["refined_body"])
        self.assertTrue(data["refined_body"].endswith("Jane"))
        self.assertEqual(data["refined_subject"], "Jane inquiry")
        self.assertTrue(data["warnings"])

    async def test_input_limits_and_domains_are_validated_before_network(self):
        with patch("app.services.recruiter_discovery.recruiter_discovery_service.search_public_profiles", new=AsyncMock(return_value=[])) as search:
            for domain in ("https://example.com", "example.com/path", "-bad.com", ""):
                response = await self.client.post("/api/v1/discover-recruiters", json={"company": "Example", "company_domain": domain})
                self.assertEqual(response.status_code, 422)
                response = await self.client.get("/api/v1/discover-recruiters", params={"company": "Example", "domain": domain})
                self.assertEqual(response.status_code, 422)
            search.assert_not_awaited()
        payload = self.message()
        for key, value in (("body", "x" * 20001), ("subject_line", " "), ("recipient_name", " ")):
            response = await self.client.post("/api/v1/outbox/queue", json={**payload, key: value})
            self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
