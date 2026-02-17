from __future__ import annotations

import asyncio

import httpx

from app.config import Settings
from app.jobs.job_manager import JobManager, chunked
from app.models import CompanyResult, JobStatus
from app.services.contact_service import ContactService
from app.services.website_service import WebsiteService


class JobProcessor:
    def __init__(self, settings: Settings, manager: JobManager) -> None:
        self.settings = settings
        self.manager = manager
        self.website_service = WebsiteService(settings)
        self.contact_service = ContactService(settings)
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)

    async def start(self, job_id: str, companies: list[str]) -> None:
        await self.manager.set_status(job_id, JobStatus.PROCESSING)
        try:
            async with httpx.AsyncClient() as client:
                for company_batch in chunked(companies, self.settings.batch_size):
                    tasks = [self._process_company(job_id, client, company) for company in company_batch]
                    await asyncio.gather(*tasks)

            await self.manager.set_status(job_id, JobStatus.COMPLETED)
        except Exception as exc:  # defensive terminal fallback for job lifecycle
            await self.manager.set_status(job_id, JobStatus.FAILED, error=str(exc))

    async def _process_company(self, job_id: str, client: httpx.AsyncClient, company: str) -> None:
        async with self._semaphore:
            for attempt in range(1, self.settings.max_retries + 1):
                try:
                    website_lookup = await self.website_service.detect_website(client, company)
                    result = CompanyResult(
                        company=company,
                        website=website_lookup.website_url,
                        website_found=website_lookup.website_found,
                        source=website_lookup.source,
                    )

                    if not website_lookup.website_found:
                        contact = await self.contact_service.lookup_contact(client, company)
                        result.phone = contact.phone
                        result.phone_found = contact.phone_found
                        result.email = contact.email
                        result.email_found = contact.email_found
                        result.source = contact.source

                    await self.manager.append_result(job_id, result)
                    return
                except Exception:  # recoverable per-item failures
                    if attempt >= self.settings.max_retries:
                        failed = CompanyResult(company=company, status='FAILED')
                        await self.manager.append_result(job_id, failed)
                        return
                    await asyncio.sleep(0.5 * attempt)
