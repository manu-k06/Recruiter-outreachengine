import re
from urllib.parse import urlsplit

from app.schemas.resume import ParsedResume, ProjectItem


class ResumeParserService:
    """Extract supported Markdown sections; never fill gaps with sample facts."""

    def parse_markdown(self, markdown_text: str) -> ParsedResume:
        lines = markdown_text.strip().splitlines()
        name = None
        github_url = None
        portfolio_url = None
        for line in lines:
            if name is None and line.strip().startswith("# "):
                name = line.strip()[2:].strip() or None
            urls = re.findall(r"https?://[^\s<>\)\]]+", line)
            for url in urls:
                url = url.rstrip(".,")
                host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
                if host == "github.com" and github_url is None:
                    github_url = url
                if portfolio_url is None and host not in {"github.com", "linkedin.com"} and re.search(r"\b(portfolio|website)\b", line, re.I):
                    portfolio_url = url
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", markdown_text)
        skills, projects = [], []
        section = None
        project = None
        description = []

        def finish_project():
            if project is not None:
                project.description = " ".join(description).strip()
                projects.append(project)

        for line in lines:
            text = line.strip()
            heading = re.match(r"^(#{1,3})\s+(.+)$", text)
            if heading and len(heading[1]) <= 2:
                finish_project()
                project, description = None, []
                title = heading[2].strip().lower()
                if title in {"skills", "technical skills"}:
                    section = "skills"
                elif title in {"projects", "featured projects", "selected projects"}:
                    section = "projects"
                else:
                    section = None
                continue
            if not text or text == "---":
                continue
            if section == "skills":
                cleaned = re.sub(r"^[-*•]\s*", "", text)
                cleaned = re.sub(r"^\*\*[^*]+\*\*\s*:?\s*", "", cleaned)
                for item in re.split(r"[,;|]", cleaned):
                    item = item.strip()
                    if item and item not in skills:
                        skills.append(item)
            elif section == "projects":
                # Metadata bullets belong to a project, not to new project headings.
                metadata = re.match(r"^[-*]\s+\*\*(Tech Stack|Live Platform|Repository|Link):?\*\*\s*:?\s*(.*)$", text, re.I)
                if metadata:
                    if project is not None:
                        label, value = metadata.groups()
                        if label.lower() == "tech stack":
                            project.tech_stack = [s.strip() for s in value.split(",") if s.strip()]
                        elif project.link is None:
                            match = re.search(r"https?://[^\s)]+", value)
                            if match:
                                project.link = match[0]
                    continue
                project_heading = re.match(r"^###\s+(.+)$", text) or re.match(r"^[-*]\s+\*\*([^*]+)\*\*[:\-]?\s*(.*)$", text)
                if project_heading:
                    finish_project()
                    project = ProjectItem(title=project_heading[1], description="")
                    description = [project_heading[2]] if len(project_heading.groups()) > 1 and project_heading[2] else []
                elif project is not None:
                    description.append(re.sub(r"^[-*]\s*", "", text))
        finish_project()

        warnings = ["Confirm the extracted profile before using it in a pitch. Target role is not inferred."]
        for value, warning in ((name, "No name heading was found."), (skills, "No skills were extracted from a Skills section."), (projects, "No projects were extracted from a Projects section.")):
            if not value:
                warnings.append(warning)
        return ParsedResume(
            name=name, target_role=None,
            email=email_match[0] if email_match else None,
            github_url=github_url, portfolio_url=portfolio_url,
            skills=skills, projects=projects, raw_markdown=markdown_text, warnings=warnings,
        )


resume_parser_service = ResumeParserService()
