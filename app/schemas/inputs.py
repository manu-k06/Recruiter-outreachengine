"""Shared input limits: reject blank values before they reach services."""
from typing import Annotated

from pydantic import StringConstraints

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
BodyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]
ResumeText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100000)]
DomainName = Annotated[str, StringConstraints(
    strip_whitespace=True, to_lower=True, max_length=253,
    pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$",
)]
