"""Run against a dedicated test database; CI supplies its own disposable service."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import unittest
from uuid import uuid4
from unittest.mock import patch

import psycopg

from app.core.postgres import PostgresStore
from app.core.storage import RecordConflictError, StorageUnavailableError
from app.schemas.outbox import OutboxItem, OutboxStatus
from app.schemas.pitch import CandidateProfile
from app.schemas.workflow import EditDraft


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to a dedicated PostgreSQL test database")
class PostgresTests(unittest.TestCase):
    def setUp(self):
        self.store = PostgresStore(os.environ["TEST_DATABASE_URL"])
        self.store.initialize()

    def draft(self):
        return OutboxItem(id=str(uuid4()), recipient_email="test@example.com", recipient_name="Test",
                          company_name="Example", subject_line="Test introduction", body="Test message",
                          status=OutboxStatus.DRAFT, created_at=datetime.now(timezone.utc))

    def test_persistence_and_atomic_history(self):
        profile = self.store.save_profile(CandidateProfile(candidate_name="Test", target_role="Engineer"))
        reopened = PostgresStore(os.environ["TEST_DATABASE_URL"])
        self.assertEqual(reopened.get_profile(profile.id), profile)
        self.assertEqual(len(reopened.history(profile.id)), 1)
        self.assertGreaterEqual(reopened.workspace_summary()["profiles"], 1)
        self.assertGreaterEqual(reopened.outbox_stats().daily_limit, 0)

    def test_concurrent_retry_and_stale_edit(self):
        draft = self.draft()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.store.save_workflow_draft(draft), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(self.store.history(draft.id)), 1)
        edit = EditDraft(expected_version=1, recipient_email="test@example.com", recipient_confirmed=True,
                         subject_line="Edited", body="Edited body")
        self.assertEqual(self.store.edit_draft(draft.id, edit).version, 2)
        with self.assertRaises(RecordConflictError):
            self.store.edit_draft(draft.id, edit)

    def test_failed_event_rolls_back_record(self):
        draft = self.draft()
        with patch.object(self.store, "_append_event", side_effect=psycopg.OperationalError("test failure")):
            with self.assertRaises(StorageUnavailableError):
                self.store.save_workflow_draft(draft)
        self.assertIsNone(self.store.get_outbox(draft.id))
