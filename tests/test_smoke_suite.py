"""Make the existing offline smoke scripts runnable by unittest discovery."""
from pathlib import Path
import runpy
import unittest


class OfflineSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def run_script(self, filename, function):
        scope = runpy.run_path(str(Path(__file__).with_name(filename)))
        await scope[function]()

    async def test_server(self):
        await self.run_script("test_server.py", "run_smoke_test")

    async def test_pitch(self):
        await self.run_script("test_pitch.py", "run_pitch_tests")

    async def test_outbox(self):
        await self.run_script("test_outbox.py", "run_outbox_tests")

    async def test_ai_studio(self):
        await self.run_script("test_ai_studio.py", "run_ai_studio_tests")

    async def test_discovery(self):
        await self.run_script("test_discovery.py", "run_discovery_tests")
