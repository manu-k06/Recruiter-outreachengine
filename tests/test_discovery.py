import asyncio
import httpx
from app.main import app

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
            
            assert lead["recommended_email"] is not None
            assert len(lead["candidate_emails"]) >= 2
            # Check domain matches
            assert "stripe.com" in lead["recommended_email"]

    print("\n==========================================")
    print(">>> MODULE 3 DISCOVERY TESTS PASSED! <<<")
    print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(run_discovery_tests())
