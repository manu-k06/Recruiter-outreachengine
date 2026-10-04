from typing import List, Tuple
from app.schemas.pitch import CandidateProfile, GeneratePitchRequest, GeneratedPitchResponse

class PitchGeneratorService:
    """
    Intelligent Outreach Pitch Generator.
    Crafts ultra-concise, high-converting cold emails tailored specifically
    to the target company, recruiter role, and candidate profile.
    """

    def extract_first_name(self, full_name: str) -> str:
        """
        Extracts just the first name for a natural, respectful salutation.
        Example: 'Sarah Jenkins' -> 'Sarah'
        """
        parts = full_name.strip().split()
        return parts[0] if parts else "there"

    def craft_subject_line(self, candidate_name: str, target_role: str, company: str) -> str:
        """
        Generates clean, non-spammy subject lines that tech recruiters actually open.
        """
        return f"Quick note regarding {target_role} @ {company}"

    def generate_pitch(self, request: GeneratePitchRequest, recipient_email: str = None) -> GeneratedPitchResponse:
        """
        Assembles a personalized cold email following the 3-bullet executive rule:
        1. Context & Reason for reaching out
        2. Proof of Competence (Projects & Skills)
        3. Low-friction Call to Action (CTA)
        """
        recruiter_first = self.extract_first_name(request.recruiter_name)
        candidate = request.candidate
        company = request.company_name
        role = candidate.target_role
        
        # Take top 3 core skills
        top_skills = candidate.core_skills[:3]
        skills_str = ", ".join(top_skills)

        # Tone 1: Direct (Default, Highest response rate)
        if request.tone == "technical":
            body = (
                f"Hi {recruiter_first},\n\n"
                f"I've been following {company}'s engineering architecture and wanted to reach out directly regarding open {role} opportunities.\n\n"
                f"As a developer specialized in {skills_str}, I focus on high-throughput backend services and reactive interfaces. "
                f"Recently, I built {candidate.featured_project or 'production-grade distributed systems'}.\n\n"
                f"I'd love to learn if your team is currently looking for engineers with this background. "
                f"Would you be open to a brief 5-minute sync this week?\n\n"
                f"Best regards,\n"
                f"{candidate.candidate_name}"
            )
            cta = "Would you be open to a brief 5-minute sync this week?"

        elif request.tone == "conversational":
            body = (
                f"Hi {recruiter_first},\n\n"
                f"Hope your week is going great! I noticed you lead technical recruiting at {company}, "
                f"and I'm really inspired by the products your team is shipping.\n\n"
                f"I'm a {role} working primarily with {skills_str}. "
                f"A recent project of mine is {candidate.featured_project or 'modern full-stack web applications'}.\n\n"
                f"Are you currently the point of contact for engineering hiring, or would someone else on the talent team be better to reach out to?\n\n"
                f"Thanks so much for your time,\n"
                f"{candidate.candidate_name}"
            )
            cta = "Are you currently the point of contact for engineering hiring?"

        else: # "direct" (Default)
            body = (
                f"Hi {recruiter_first},\n\n"
                f"I'm reaching out directly regarding {role} opportunities at {company}.\n\n"
                f"A quick snapshot of my work:\n"
                f"• Stack: Proficient in {skills_str}\n"
                f"• Project: Developed {candidate.featured_project}\n"
                + (f"• Portfolio / Code: {candidate.portfolio_url}\n\n" if candidate.portfolio_url else "\n") +
                f"If you have a quick minute, I'd welcome the chance to connect. Are you the right person to speak with regarding this role?\n\n"
                f"Best,\n"
                f"{candidate.candidate_name}"
            )
            cta = "Are you the right person to speak with regarding this role?"

        # Calculate word count (kept short for 6-second scan rate)
        word_count = len(body.split())
        subject = self.craft_subject_line(candidate.candidate_name, role, company)

        return GeneratedPitchResponse(
            recipient_email=recipient_email,
            recipient_name=request.recruiter_name,
            company_name=company,
            subject_line=subject,
            body=body,
            word_count=word_count,
            matched_skills=top_skills,
            call_to_action=cta
        )

# Singleton instance
pitch_generator_service = PitchGeneratorService()
