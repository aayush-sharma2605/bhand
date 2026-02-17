from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.jobs.job_manager import JobManager
from app.jobs.processor import JobProcessor
from app.models import JobStatusResponse, UploadResponse
from app.utils.file_loader import load_company_names

router = APIRouter()
job_manager = JobManager()


def get_job_processor(settings: Settings = Depends(get_settings)) -> JobProcessor:
    return JobProcessor(settings=settings, manager=job_manager)


@router.post('/upload', response_model=UploadResponse)
async def upload_file(file: UploadFile, processor: JobProcessor = Depends(get_job_processor)) -> UploadResponse:
    company_names = await load_company_names(file)
    metadata = await job_manager.create_job(company_names)
    asyncio.create_task(processor.start(metadata.job_id, company_names))
    return UploadResponse(job_id=metadata.job_id, total=metadata.total, status=metadata.status)


@router.get('/job/{job_id}', response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    m = job.metadata
    return JobStatusResponse(
        job_id=m.job_id,
        status=m.status,
        total=m.total,
        processed=m.processed,
        success_count=m.success_count,
        failure_count=m.failure_count,
        error=m.error,
    )


@router.get('/download/{job_id}')
async def download_results(job_id: str) -> StreamingResponse:
    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')

    csv_bytes = await job_manager.to_csv_bytes(job_id)
    filename = f'company_enrichment_{job_id}.csv'
    return StreamingResponse(
        iter([csv_bytes]),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )
