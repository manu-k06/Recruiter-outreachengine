import asyncio
import httpx
from app.main import app

async def run_ai_studio_tests():
    """
    Test suite for Markdown Resume Parsing and AI Reviewer Studio.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Test 1: Parse Markdown Resume
        print("\n--- Test 1: Parse Markdown Resume (.md) ---")
        with open("sample_resume.md", "r", encoding="utf-8") as f:
            resume_md = f.read()

        res_resume = await client.post("/api/v1/resume/parse-markdown", json={"markdown_content": resume_md})
        resume_data = res_resume.json()
        print(f"Candidate Name: {resume_data['name']}")
        print(f"Skills Extracted: {len(resume_data['skills'])} skills -> {resume_data['skills'][:6]}")
        print(f"Projects Extracted: {[p['title'] for p in resume_data['projects']]}")
        
        assert res_resume.status_code == 200
        assert "Manu" in resume_data["name"]
        assert any("Python" in s for s in resume_data["skills"])
        assert any("Cineforge" in p["title"] for p in resume_data["projects"])

        # Test 2: AI Review of a Cold Email
        print("\n--- Test 2: AI Pitch Review & Diagnostics ---")
        review_payload = {
            "recruiter_name": "Sarah Jenkins",
            "company_name": "Stripe",
            "subject_line": "Quick note regarding Full-Stack Engineer @ Stripe",
            "body": (
                "Hi Sarah,\n\n"
                "I'm reaching out directly regarding Full-Stack Engineer opportunities at Stripe.\n\n"
                "A quick snapshot of my work:\n"
                "• Stack: Proficient in Python, FastAPI, React\n"
                "• Project: Developed Cineforge (AI movie streaming and discovery platform)\n"
                "• Portfolio: https://cineforge-rose.vercel.app\n\n"
                "If you have a quick minute, I'd welcome the chance to connect. Are you the right person to speak with regarding this role?\n\n"
                "Best,\n"
                "Manu K"
            )
        }
        res_review = await client.post("/api/v1/ai/review", json=review_payload)
        review_data = res_review.json()
        print(f"Overall Score: {review_data['overall_score']}/100")
        print(f"Readiness Verdict: {review_data['readiness']}")
        print(f"Word Count: {review_data['word_count']} words")
        print("Strengths:", review_data["strengths"])
        
        assert res_review.status_code == 200
        assert review_data["overall_score"] >= 80

        # Test 3: AI Refinement / Rewrite
        print("\n--- Test 3: AI Refine / Rewrite with Custom Instruction ---")
        refine_payload = {
            "recruiter_name": "Sarah Jenkins",
            "company_name": "Stripe",
            "current_subject": "Quick note regarding Full-Stack Engineer @ Stripe",
            "current_body": review_payload["body"],
            "instruction": "Make it shorter and highlight Cineforge and AI"
        }
        res_refine = await client.post("/api/v1/ai/refine", json=refine_payload)
        refine_data = res_refine.json()
        print(f"Refined Word Count: {refine_data['word_count']} words")
        print(f"Changes Applied: {refine_data['changes_summary']}")
        print("\nRefined Email Body:")
        print("--------------------------------------------------")
        print(refine_data["refined_body"])
        print("--------------------------------------------------")

        assert res_refine.status_code == 200
        assert "Cineforge" in refine_data["refined_body"]

    print("\n==========================================")
    print(">>> AI STUDIO & RESUME TESTS PASSED! <<<")
    print("==========================================\n")

if __name__ == "__main__":
    asyncio.run(run_ai_studio_tests())
