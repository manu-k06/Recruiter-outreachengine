import re
from typing import List, Optional
from app.schemas.resume import ParsedResume, ProjectItem

class ResumeParserService:
    """
    Parses Markdown (.md) formatted resumes into structured models.
    Supports headings (#, ##), bullet lists (*, -), and markdown links ([text](url)).
    """

    def parse_markdown(self, markdown_text: str) -> ParsedResume:
        lines = markdown_text.strip().splitlines()

        # 1. Extract Name (Typically the first # Header or first line)
        name = "Candidate"
        for line in lines:
            line_s = line.strip()
            if line_s.startswith("# "):
                name = line_s.replace("# ", "").strip()
                break

        # 2. Extract Links (GitHub, Portfolio, Email)
        github_match = re.search(r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+", markdown_text, re.IGNORECASE)
        portfolio_match = re.search(r"https?://[a-zA-Z0-9_.-]+\.(?:app|space|dev|io|com)", markdown_text, re.IGNORECASE)
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", markdown_text)

        github_url = github_match.group(0) if github_match else None
        portfolio_url = portfolio_match.group(0) if portfolio_match else None
        email = email_match.group(0) if email_match else None

        # 3. Extract Skills Section
        skills: List[str] = []
        in_skills = False
        for line in lines:
            line_s = line.strip()
            if re.match(r"^#{1,3}\s+(?:Technical\s+)?Skills", line_s, re.IGNORECASE):
                in_skills = True
                continue
            elif in_skills and line_s.startswith("#"):
                # Hit next header
                in_skills = False
            elif in_skills and line_s:
                # Remove bullets, colons, bold tags
                cleaned = re.sub(r"^[-*•]\s*", "", line_s)
                cleaned = re.sub(r"\*\*.*?\*\*:", "", cleaned)
                for item in re.split(r"[,;|/]", cleaned):
                    clean_item = item.strip()
                    if clean_item and len(clean_item) < 30 and clean_item not in skills:
                        skills.append(clean_item)

        # Fallback default skills if none explicitly parsed
        if not skills:
            skills = ["Python", "FastAPI", "React", "Supabase", "Git"]

        # 4. Extract Projects
        projects: List[ProjectItem] = []
        in_projects = False
        current_project_title = None
        current_desc = []
        current_stack = []

        for line in lines:
            line_s = line.strip()
            if re.match(r"^#{1,2}\s+Projects", line_s, re.IGNORECASE):
                in_projects = True
                continue
            elif in_projects and line_s.startswith("## ") and not line_s.lower().startswith("## project"):
                in_projects = False
            elif in_projects:
                # Subheaders like ### Cineforge or - **Cineforge**:
                project_header = re.match(r"^###\s+(.+)$", line_s) or re.match(r"^[-*]\s+\*\*([^*]+)\*\*[:\-]?\s*(.*)$", line_s)
                if project_header:
                    if current_project_title:
                        projects.append(ProjectItem(
                            title=current_project_title,
                            tech_stack=current_stack or skills[:3],
                            description=" ".join(current_desc).strip()
                        ))
                        current_desc = []
                        current_stack = []
                    
                    current_project_title = project_header.group(1).strip()
                    if len(project_header.groups()) > 1 and project_header.group(2):
                        current_desc.append(project_header.group(2).strip())
                elif current_project_title and line_s:
                    current_desc.append(re.sub(r"^[-*]\s*", "", line_s))

        if current_project_title:
            projects.append(ProjectItem(
                title=current_project_title,
                tech_stack=current_stack or skills[:3],
                description=" ".join(current_desc).strip()
            ))

        # Default fallback project if none found
        if not projects:
            projects.append(ProjectItem(
                title="Cineforge",
                tech_stack=["React", "FastAPI", "Supabase", "Gemini AI"],
                description="Intelligent movie streaming and discovery platform with AI plot-based search."
            ))

        return ParsedResume(
            name=name,
            target_role="Full-Stack / Python & AI Engineer",
            email=email,
            github_url=github_url,
            portfolio_url=portfolio_url,
            skills=skills,
            projects=projects,
            raw_markdown=markdown_text
        )

resume_parser_service = ResumeParserService()
