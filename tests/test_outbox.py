"""Outbox smoke check: no mode can claim delivery without a provider."""
import asyncio
import httpx
from pathlib import Path
from tempfile import TemporaryDirectory
from app.main import create_application


async def run_outbox_tests():
    directory = TemporaryDirectory()
    app = create_application(Path(directory.name) / "test.sqlite3")
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = dict(recipient_email="sam@example.com", recipient_name="Sam", company_name="Example", subject_line="Hiring inquiry", body="Are you hiring?", mode="draft")
            draft = await client.post("/api/v1/outbox/queue", json=payload)
            assert draft.status_code == 200
            assert draft.json()["status"] == "draft"
            payload["mode"] = "simulate"
            simulation = await client.post("/api/v1/outbox/queue", json=payload)
            assert simulation.status_code == 200
            assert simulation.json()["status"] == "simulated"
            assert simulation.json()["sent_at"] is None
            payload["mode"] = "live_send"
            unavailable = await client.post("/api/v1/outbox/queue", json=payload)
            assert unavailable.status_code == 503
            stats = (await client.get("/api/v1/outbox/stats")).json()
            assert stats["sent_today"] == 0
            assert stats["total_sent"] == 0
            assert stats["total_simulated"] == 1
            assert len((await client.get("/api/v1/outbox/items")).json()) == 2
    finally:
        directory.cleanup()
    print("Outbox draft/simulation checks passed; no email sent.")


if __name__ == "__main__":
    asyncio.run(run_outbox_tests())
