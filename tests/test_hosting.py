from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import httpx

from app.core.config import Settings
from app.main import create_application


class HostingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "test.sqlite3"

    def client(self, config):
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_application(self.path, config)), base_url="https://workspace.test")
        self.addAsyncCleanup(client.aclose)
        return client

    async def test_hosted_configuration_fails_closed(self):
        client = self.client(Settings(VERCEL=True))
        for path in ["/dashboard", "/docs", "/api/v1/profiles", "/api/v1/workspace"]:
            self.assertEqual((await client.get(path)).status_code, 503)
        self.assertEqual((await client.get("/api/v1/health")).status_code, 200)
        self.assertFalse(self.path.exists())

    async def test_authentication_and_cross_site_write_protection(self):
        client = self.client(Settings(WORKSPACE_PASSWORD="test-password-long-enough"))
        self.assertEqual((await client.get("/api/v1/profiles")).status_code, 401)
        self.assertEqual((await client.get("/docs", auth=("owner", "wrong"))).status_code, 401)
        client.auth = ("owner", "test-password-long-enough")
        response = await client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        root = await client.get("/", headers={"Accept": "text/html"})
        self.assertEqual(root.status_code, 307)
        self.assertEqual(root.headers["location"], "/dashboard")
        payload = {"candidate_name": "Jane", "target_role": "Engineer"}
        response = await client.post("/api/v1/profiles", json=payload, headers={"Origin": "https://other.test"})
        self.assertEqual(response.status_code, 403)
        response = await client.post("/api/v1/profiles", json=payload, headers={"Origin": "https://workspace.test"})
        self.assertEqual(response.status_code, 201)

    async def test_workspace_counts_real_saved_actions(self):
        client = self.client(Settings())
        await client.post("/api/v1/profiles", json={"candidate_name": "Jane", "target_role": "Engineer"})
        summary = (await client.get("/api/v1/workspace")).json()
        self.assertEqual(summary["profiles"], 1)
        self.assertEqual(summary["research"], 0)
        self.assertEqual(len(summary["activity"]), 7)
        self.assertEqual(sum(day["count"] for day in summary["activity"]), 1)

    async def test_postgres_is_selected_without_exposing_url(self):
        config = Settings(DATABASE_URL="postgresql://test:secret@localhost/outreach")
        app = create_application(config=config)
        self.assertEqual(app.state.store.__class__.__name__, "PostgresStore")
        self.assertNotIn("secret", repr(config))
