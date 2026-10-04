import asyncio
import httpx
from app.main import app

async def run_verifier_tests():
    """
    Test suite for Module 2: Email Verification Engine.
    Tests all 4 cases:
      1. Malformed syntax
      2. Disposable burner address
      3. Non-existent domain
      4. Valid real-world domain with MX records (e.g., google.com)
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n--- Test 1: Invalid Syntax ---")
        res1 = await client.get("/api/v1/verify-email?email=not-an-email")
        data1 = res1.json()
        print(f"Input: 'not-an-email' -> Status: {data1['status']}, Score: {data1['deliverability_score']}, Reason: {data1['diagnostic_reason']}")
        assert data1["status"] == "invalid"
        assert data1["is_valid_syntax"] is False

        print("\n--- Test 2: Disposable Burner Email ---")
        res2 = await client.get("/api/v1/verify-email?email=someone@mailinator.com")
        data2 = res2.json()
        print(f"Input: 'someone@mailinator.com' -> Status: {data2['status']}, Score: {data2['deliverability_score']}, Disposable: {data2['is_disposable']}")
        assert data2["status"] == "invalid"
        assert data2["is_disposable"] is True

        print("\n--- Test 3: Non-existent Domain ---")
        res3 = await client.get("/api/v1/verify-email?email=recruiter@this-domain-does-not-exist-xyz123.com")
        data3 = res3.json()
        print(f"Input: '...fake domain...' -> Status: {data3['status']}, Has MX: {data3['has_mx_records']}, Score: {data3['deliverability_score']}")
        assert data3["status"] == "invalid"
        assert data3["has_mx_records"] is False

        print("\n--- Test 4: Real-World Domain (google.com) ---")
        res4 = await client.get("/api/v1/verify-email?email=test-user@google.com")
        data4 = res4.json()
        print(f"Input: 'test-user@google.com' -> Status: {data4['status']}, Score: {data4['deliverability_score']}")
        print(f"MX Servers Found: {data4['mx_servers']}")
        print(f"Diagnostic Reason: {data4['diagnostic_reason']}")
        assert data4["has_mx_records"] is True
        assert len(data4["mx_servers"]) > 0

    print("\n==========================================")
    print(">>> ALL VERIFICATION TESTS PASSED (4/4)! <<<")
    print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(run_verifier_tests())
