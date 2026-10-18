from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from app.schemas.inputs import ShortText, BodyText, DomainName


class PitchFromRecords(BaseModel):
    profile_id: UUID
    discovery_id: UUID
    lead_index: int = Field(ge=0)
    tone: Literal["direct", "technical", "conversational"] = "direct"


class SaveWorkflowDraft(PitchFromRecords):
    request_id: UUID
    recipient_email: EmailStr
    recipient_confirmed: Literal[True]
    subject_line: ShortText
    body: BodyText


class EditDraft(BaseModel):
    expected_version: int = Field(ge=1)
    recipient_email: EmailStr
    recipient_confirmed: Literal[True]
    subject_line: ShortText
    body: BodyText


class ManualContact(BaseModel):
    full_name: ShortText
    job_title: ShortText
    company: ShortText
    company_domain: DomainName
    email: EmailStr | None = None
    source_url: HttpUrl | None = None
