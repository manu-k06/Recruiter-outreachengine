from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from app.schemas.inputs import ResumeText

class ProjectItem(BaseModel):
    title: str = Field(..., description="Project name")
    tech_stack: List[str] = Field(default_factory=list, description="Technologies used")
    description: str = Field(..., description="Project overview or impact")
    link: Optional[str] = None

class ParsedResume(BaseModel):
    """
    Structured representation of a Markdown (.md) resume.
    """
    name: Optional[str] = Field(default=None, description="Candidate's name if explicitly extracted")
    target_role: Optional[str] = None
    email: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    skills: List[str] = Field(default_factory=list, description="Extracted technical skills")
    projects: List[ProjectItem] = Field(default_factory=list, description="Extracted featured projects")
    summary: Optional[str] = None
    raw_markdown: str = Field(..., description="The original raw markdown content")
    warnings: List[str] = Field(default_factory=list)

class ParseResumeRequest(BaseModel):
    markdown_content: ResumeText = Field(
        ..., 
        description="The raw Markdown (.md) resume text"
    )
