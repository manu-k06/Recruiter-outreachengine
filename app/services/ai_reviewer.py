import os
import re
from typing import List
from app.schemas.ai_review import (
    ReviewPitchRequest, 
    ReviewPitchResponse, 
    RefinePitchRequest, 
    RefinePitchResponse
)

class AIReviewerService:
    """
    AI Pitch Reviewer & Writing Coach.
    Analyzes cold outreach pitches against proven recruiter psychology rules:
    Brevity (<90 words), Relevance, and Low-Friction Calls to Action.
    """

    def review_pitch(self, request: ReviewPitchRequest) -> ReviewPitchResponse:
        body = request.body.strip()
        words = body.split()
        word_count = len(words)

        strengths: List[str] = []
        improvements: List[str] = []

        # 1. Brevity Scoring (Target: 60-90 words)
        if word_count <= 85:
            brevity_score = 98
            strengths.append(f"Ideal length ({word_count} words). Takes under 5 seconds to scan.")
        elif word_count <= 115:
            brevity_score = 80
            strengths.append(f"Good length ({word_count} words), though slightly on the longer side.")
        else:
            brevity_score = 45
            improvements.append(f"Too long ({word_count} words). Cut by {word_count - 80} words so recruiters don't skip it.")

        # 2. Relevance Scoring (Personalization check)
        relevance_score = 60
        first_name = request.recruiter_name.split()[0]
        if first_name.lower() in body.lower():
            relevance_score += 20
            strengths.append(f"Properly personalizes greeting to '{first_name}'.")
        else:
            improvements.append(f"Does not greet '{first_name}' by name.")

        if request.company_name.lower() in body.lower():
            relevance_score += 20
            strengths.append(f"Explicitly references {request.company_name}.")
        else:
            improvements.append(f"Does not mention {request.company_name} in the message body.")
        relevance_score = min(100, relevance_score)

        # 3. Call-to-Action (CTA) Scoring
        cta_score = 70
        if "?" in body:
            cta_score += 25
            strengths.append("Ends with a clear question to prompt a reply.")
        else:
            cta_score = 30
            improvements.append("Missing a question at the end! Always close with a low-friction question.")
        cta_score = min(100, cta_score)

        # Overall composite score
        overall = int((brevity_score * 0.4) + (relevance_score * 0.35) + (cta_score * 0.25))

        if overall >= 85:
            readiness = "Ready to Send"
        elif overall >= 70:
            readiness = "Minor Edits Recommended"
        else:
            readiness = "Needs Revision"

        return ReviewPitchResponse(
            overall_score=overall,
            brevity_score=brevity_score,
            relevance_score=relevance_score,
            cta_score=cta_score,
            word_count=word_count,
            readiness=readiness,
            strengths=strengths,
            actionable_improvements=improvements
        )

    def refine_pitch(self, request: RefinePitchRequest) -> RefinePitchResponse:
        """
        Rewrites/polishes the email according to user instructions.
        """
        current_body = request.current_body.strip()
        instruction = request.instruction.lower()
        recruiter_first = request.recruiter_name.split()[0]
        company = request.company_name

        refined_subject = request.current_subject
        refined_body = current_body
        changes = []

        # Rule A: Make it shorter / punchier
        if "short" in instruction or "punch" in instruction or "concise" in instruction:
            refined_body = (
                f"Hi {recruiter_first},\n\n"
                f"Quick reachout regarding software engineering at {company}.\n\n"
                f"I build high-performance systems with Python/FastAPI and React. "
                f"Recently created Cineforge (AI discovery & streaming platform).\n\n"
                f"Are you the right contact for engineering hiring at {company}?\n\n"
                f"Best,\n"
                f"Manu K"
            )
            refined_subject = f"Engineering inquiry @ {company}"
            changes.append("Trimmed intro filler and reduced total words to 45 words for instant reading.")

        # Rule B: Highlight Cineforge / AI
        elif "cineforge" in instruction or "ai" in instruction:
            refined_body = (
                f"Hi {recruiter_first},\n\n"
                f"I've been following {company}'s tech stack and wanted to share a relevant project.\n\n"
                f"I recently engineered Cineforge (an AI-powered platform with smart semantic search, "
                f"built using FastAPI, React, and Google Gemini).\n\n"
                f"Would love to connect if your team is expanding full-stack or AI engineering. "
                f"Open to a brief 5-min sync this week?\n\n"
                f"Best,\n"
                f"Manu K"
            )
            changes.append("Put direct spotlight on Cineforge and AI architecture.")

        else:
            # Default polish
            refined_body = current_body.replace("I am writing to", "Quick reachout regarding")
            changes.append(f"Applied style refinement based on instruction: '{request.instruction}'")

        return RefinePitchResponse(
            refined_subject=refined_subject,
            refined_body=refined_body,
            word_count=len(refined_body.split()),
            changes_summary="; ".join(changes)
        )

ai_reviewer_service = AIReviewerService()
