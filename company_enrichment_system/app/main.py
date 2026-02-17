from fastapi import FastAPI

from app.config import get_settings
from app.routers.jobs import router as jobs_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(jobs_router)


@app.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}
