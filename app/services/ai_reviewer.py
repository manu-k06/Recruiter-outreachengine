import re

from app.schemas.ai_review import (
    ReviewPitchRequest, ReviewPitchResponse, RefinePitchRequest, RefinePitchResponse,
)


class AIReviewerService:
    """Basic writing heuristics, not a model or an authorization to send."""

    def review_pitch(self, request: ReviewPitchRequest) -> ReviewPitchResponse:
        body = request.body
        word_count = len(body.split())
        strengths, improvements = [], []

        if word_count < 20:
            brevity_score = 20
            improvements.append("Too little context to assess an outreach pitch; explain your relevant background and request.")
        elif word_count <= 85:
            brevity_score = 98
            strengths.append(f"Concise length ({word_count} words).")
        elif word_count <= 115:
            brevity_score = 80
            improvements.append("Consider shortening the message for easier reading.")
        else:
            brevity_score = 45
            improvements.append(f"Long message ({word_count} words); consider cutting unnecessary detail.")

        relevance_score = 60
        for label, value in (("recruiter", request.recruiter_name.split()[0]), ("company", request.company_name)):
            if re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", body, re.IGNORECASE):
                relevance_score += 20
                strengths.append(f"Mentions the {label}: {value}.")
            else:
                improvements.append(f"Does not mention the {label}: {value}.")

        # A question mark is only a weak signal; do not claim to understand the ask.
        cta_score = 95 if "?" in body else 30
        if "?" in body:
            strengths.append("Contains a question; manually confirm it is relevant and easy to answer.")
        else:
            improvements.append("Consider adding a clear closing question.")
        overall = int(brevity_score * .4 + relevance_score * .35 + cta_score * .25)
        if word_count < 20:
            overall = min(overall, 49)

        return ReviewPitchResponse(
            overall_score=overall, brevity_score=brevity_score,
            relevance_score=relevance_score, cta_score=cta_score,
            word_count=word_count,
            readiness="Needs Revision" if overall < 70 else "Manual Review Required",
            strengths=strengths, actionable_improvements=improvements,
            unchecked_guidelines=request.custom_guidelines or [],
            warnings=["Rule-based feedback only. Factual accuracy, subject quality and custom guidelines require manual review; this is not send approval."],
        )

    def refine_pitch(self, request: RefinePitchRequest) -> RefinePitchResponse:
        # Phrase edits keep identity, projects and other candidate facts.
        # Unsupported instructions remain explicit instead of claiming a rewrite.
        body = request.current_body
        instruction = request.instruction.lower()
        warnings = []
        changed = False
        if re.search(r"\b(short\w*|punch\w*|concise)\b", instruction):
            for phrase, replacement in (
                ("I am writing to inquire about", "I'm asking about"),
                ("I wanted to reach out to ask", "I'd like to ask"),
                ("at this point in time", "now"),
            ):
                body, count = re.subn(r"\b" + re.escape(phrase) + r"\b", replacement, body)
                changed = changed or count > 0
            warnings.append("Only supported filler phrases were shortened. Length targets, emphasis and any other instructions need manual review.")
        else:
            warnings.append("This instruction is not supported by the rule-based editor. The original text was preserved for manual editing.")

        return RefinePitchResponse(
            refined_subject=request.current_subject, refined_body=body,
            word_count=len(body.split()),
            changes_summary="Shortened supported filler phrases; candidate details were preserved." if changed else "No supported changes were made; original text preserved.",
            warnings=warnings,
        )


ai_reviewer_service = AIReviewerService()
