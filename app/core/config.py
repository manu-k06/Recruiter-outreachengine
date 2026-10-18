from pydantic import BaseModel, Field, SecretStr
from pathlib import Path
import os

class Settings(BaseModel):
    """
    Application Settings & Environment Configuration.
    Using Pydantic ensures environment variables are type-checked at startup.
    """
    PROJECT_NAME: str = "Recruiter Outreach Engine"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    VERCEL: bool = False
    DATABASE_URL: SecretStr | None = None
    WORKSPACE_USERNAME: str = "owner"
    WORKSPACE_PASSWORD: SecretStr | None = None
    
    # Mailer & Limits
    DAILY_SEND_LIMIT: int = Field(default=25, ge=0)
    DATABASE_PATH: Path = Path(__file__).resolve().parents[2] / "data" / "outreach.sqlite3"
    MX_DNS_TIMEOUT_SECONDS: float = 3.0
    SMTP_TIMEOUT_SECONDS: float = 5.0

    @classmethod
    def from_environment(cls):
        # Explicit environment loading; no dependency or implicit .env lookup needed.
        return cls(**{name: os.environ[name] for name in cls.model_fields if name in os.environ})

settings = Settings.from_environment()
