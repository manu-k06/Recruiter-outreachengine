from pydantic import BaseModel
from typing import Optional
import os

class Settings(BaseModel):
    """
    Application Settings & Environment Configuration.
    Using Pydantic ensures environment variables are type-checked at startup.
    """
    PROJECT_NAME: str = "Recruiter Outreach Engine"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    
    # Mailer & Limits
    DAILY_SEND_LIMIT: int = 25
    MX_DNS_TIMEOUT_SECONDS: float = 3.0
    SMTP_TIMEOUT_SECONDS: float = 5.0

settings = Settings()
