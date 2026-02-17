from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class CompanyResult(BaseModel):
    company: str
    website: str | None = None
    website_found: bool = False
    phone: str | None = None
    phone_found: bool = False
    email: str | None = None
    email_found: bool = False
    source: str | None = None
    status: str = 'SUCCESS'


class JobMetadata(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    total: int
    processed: int = 0
    success_count: int = 0
    failure_count: int = 0
    error: str | None = None


class JobRecord(BaseModel):
    metadata: JobMetadata
    results: list[CompanyResult] = Field(default_factory=list)


class UploadResponse(BaseModel):
    job_id: str
    total: int
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    total: int
    processed: int
    success_count: int
    failure_count: int
    error: str | None = None


class DomainLookupResult(BaseModel):
    website_found: bool
    website_url: str | None = None
    source: str | None = None


class ContactLookupResult(BaseModel):
    phone: str | None = None
    email: str | None = None
    phone_found: bool = False
    email_found: bool = False
    source: str | None = None


class SearchCandidate(BaseModel):
    website: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
