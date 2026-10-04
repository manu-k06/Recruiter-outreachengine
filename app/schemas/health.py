from pydantic import BaseModel
from typing import Dict

class HealthResponse(BaseModel):
    """
    Standardized response format for server health.
    Guarantees consistent schema for monitoring tools and frontend status indicators.
    """
    status: str
    version: str
    services: Dict[str, str]
