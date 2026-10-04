import asyncio
import httpx
from app.main import app

async def run_pitch_tests():
    """
    Test suite for Module 4: Tailored Pitch Generator.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\n--- Test 1: Direct Executive Pitch (Stripe Recruiter) ---")
        payload = {
            "recruiter_name": "Sarah Jenkins",
            "recruiter_title": "Lead Technical Recruiter",
            "company_name": "Stripe",
            "candidate": {
                "candidate_name": "Manu K",
                "target_role": "Full-Stack Engineer",
                "core_skills": ["Python", "FastAPI", "React", "Supabase"],
                "featured_project": "Cineforge (AI movie streaming and discovery platform)",
                "portfolio_url": "https://github.com/manu-k06"
            },
            "tone": "direct"
        }
        res = await client.post("/api/v1/generate-pitch", json=payload)
        data = res.json()
        
        print(f"Status Code: {res.status_code}")
        print(f"Subject: {data['subject_line']}")
        print(f"Word Count: {data['word_count']} words (Target: < 120 words)")
        print("\nGenerated Body Preview:")
        print("--------------------------------------------------")
        print(data["body"])
        print("--------------------------------------------------")
        
        assert res.status_code == 200
        assert "Sarah" in data["body"]
        assert "Stripe" in data["body"]
        assert "Cineforge" in data["body"]
        assert data["word_count"] < 120

        print("\n--- Test 2: Technical Architecture Tone ---")
        payload["tone"] = "technical"
        res2 = await client.post("/api/v1/generate-pitch", json=payload)
        data2 = res2.json()
        assert res2.status_code == 200
        assert "architecture" in data2["body"]
        print("Technical Tone Subject:", data2["subject_line"])

    print("\n==========================================")
    print(">>> MODULE 4 PITCH TESTS PASSED! <<<")
    print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(run_pitch_tests())
