from __future__ import annotations

import asyncio
import io
import uuid
from typing import Iterable

import csv

from app.models import CompanyResult, JobMetadata, JobRecord, JobStatus


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, companies: list[str]) -> JobMetadata:
        metadata = JobMetadata(job_id=str(uuid.uuid4()), total=len(companies), status=JobStatus.PENDING)
        async with self._lock:
            self._jobs[metadata.job_id] = JobRecord(metadata=metadata)
        return metadata

    async def get_job(self, job_id: str) -> JobRecord | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def set_status(self, job_id: str, status: JobStatus, error: str | None = None) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.metadata.status = status
            job.metadata.error = error

    async def append_result(self, job_id: str, result: CompanyResult) -> None:
        async with self._lock:
            job = self._jobs[job_id]
            job.results.append(result)
            job.metadata.processed += 1
            if result.status == 'SUCCESS':
                job.metadata.success_count += 1
            else:
                job.metadata.failure_count += 1

    async def to_csv_bytes(self, job_id: str) -> bytes:
        async with self._lock:
            job = self._jobs[job_id]
            rows = list(job.results)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['company', 'website', 'website_found', 'phone', 'phone_found', 'email', 'email_found', 'source', 'status'])

        for item in rows:
            writer.writerow(
                [
                    item.company,
                    item.website,
                    item.website_found,
                    item.phone,
                    item.phone_found,
                    item.email,
                    item.email_found,
                    item.source,
                    item.status,
                ]
            )

        return output.getvalue().encode('utf-8')


def chunked(data: Iterable[str], size: int) -> Iterable[list[str]]:
    bucket: list[str] = []
    for entry in data:
        bucket.append(entry)
        if len(bucket) == size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket
