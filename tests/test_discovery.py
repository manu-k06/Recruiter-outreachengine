import asyncio
import httpx
from unittest.mock import AsyncMock, patch
from app.main import app
from app.services.email_verifier import email_verifier_service

async def run_discovery_tests():
    """
    Test suite for Module 3: Recruiter Discovery & Lead Extraction.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n--- Test 1: Discover Recruiters for Stripe ---")
        payload = {
            "company": "Stripe",
            "role_keyword": "Technical Recruiter",
            "max_results": 2
        }
        verification = await email_verifier_service.verify("not-an-email")
        with patch("app.services.recruiter_discovery.recruiter_discovery_service.search_public_profiles", new=AsyncMock(return_value=[("Sam Smith", "Technical Recruiter")])), patch.object(email_verifier_service, "verify", new=AsyncMock(return_value=verification)):
            res = await client.post("/api/v1/discover-recruiters", json=payload)
        data = res.json()
        
        print(f"Company: {data['company']} | Domain: {data['company_domain']}")
        print(f"Total Leads Discovered: {data['total_found']}")
        
        assert res.status_code == 200
        assert data["company_domain"] == "stripe.com"
        assert len(data["leads"]) > 0

        for idx, lead in enumerate(data["leads"], 1):
            print(f"\nLead #{idx}:")
            print(f"  Name: {lead['full_name']} ({lead['first_name']} {lead['last_name']})")
            print(f"  Title: {lead['job_title']}")
            print(f"  Recommended Email: {lead['recommended_email']}")
            print(f"  Generated Variations: {lead['candidate_emails']}")
            print(f"  Deliverability Score: {lead['deliverability_score']}/100 ({lead['status']})")
            
            assert lead["recommended_email"] is None
            assert len(lead["candidate_emails"]) >= 2
            # Check domain matches
            assert all(email.endswith("@stripe.com") for email in lead["candidate_emails"])

    print("\n==========================================")
    print(">>> MODULE 3 DISCOVERY TESTS PASSED! <<<")
    print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(run_discovery_tests())
