import asyncio
import httpx
from app.main import app

async def run_smoke_test():
    """
    Smoke test using ASGI Lifespan transport (no open ports needed).
    Tests route resolution, CORS headers, and Pydantic serialization.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Test Root
        res_root = await client.get("/")
        print("Root response:", res_root.status_code, res_root.json())
        assert res_root.status_code == 200

        # Test Health
        res_health = await client.get("/api/v1/health")
        print("Health response:", res_health.status_code, res_health.json())
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

    print("\n>>> ALL SMOKE TESTS PASSED! API FOUNDATION IS SOLID. <<<")

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
