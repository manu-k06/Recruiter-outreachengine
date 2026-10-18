from app.schemas.pitch import GeneratePitchRequest, GeneratedPitchResponse


class PitchGeneratorService:
    """Build templates using only the candidate facts provided in the request."""

    def extract_first_name(self, full_name: str) -> str:
        parts = full_name.strip().split()
        return parts[0] if parts else "there"

    def craft_subject_line(self, candidate_name: str, target_role: str, company: str) -> str:
        return f"Quick note regarding {target_role} @ {company}"

    def generate_pitch(self, request: GeneratePitchRequest, recipient_email: str = None) -> GeneratedPitchResponse:
        candidate = request.candidate
        top_skills = candidate.core_skills[:3]
        paragraphs = [f"Hi {self.extract_first_name(request.recruiter_name)},"]
        paragraphs.append(f"I'm reaching out about {candidate.target_role} opportunities at {request.company_name}.")

        # Optional facts are omitted, never replaced with example achievements.
        details = []
        if top_skills:
            details.append(f"Skills: {', '.join(top_skills)}")
        if candidate.featured_project:
            details.append(f"Project: {candidate.featured_project}")
        if candidate.portfolio_url:
            details.append(f"Portfolio / code: {candidate.portfolio_url}")

        if details:
            if request.tone == "direct":
                paragraphs.append("A quick snapshot of my work:\n" + "\n".join(f"• {detail}" for detail in details))
            elif request.tone == "technical":
                paragraphs.append("Relevant experience:\n" + "\n".join(details))
            else:
                paragraphs.append("Here's a little about my background:\n" + "\n".join(details))

        if request.tone == "technical":
            cta = "Would you be open to a brief conversation about the experience your team needs?"
        elif request.tone == "conversational":
            cta = "Are you the right person to ask about these opportunities, or could you point me to the right contact?"
        else:
            cta = "Are you the right person to speak with regarding this role?"
        paragraphs.extend([cta, f"Best,\n{candidate.candidate_name}"])
        body = "\n\n".join(paragraphs)
        return GeneratedPitchResponse(
            recipient_email=recipient_email,
            recipient_name=request.recruiter_name,
            company_name=request.company_name,
            subject_line=self.craft_subject_line(candidate.candidate_name, candidate.target_role, request.company_name),
            body=body,
            word_count=len(body.split()),
            matched_skills=top_skills,
            call_to_action=cta,
        )


pitch_generator_service = PitchGeneratorService()
