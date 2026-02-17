from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import httpx

from app.config import Settings
from app.models import DomainLookupResult
from app.services.rate_limiter import AsyncRateLimiter


class WebsiteService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.rate_limiter = AsyncRateLimiter(settings.rate_limit_per_second)

    async def detect_website(self, client: httpx.AsyncClient, company: str) -> DomainLookupResult:
        base = company.replace(' ', '').replace('&', 'and')
        candidates = [
            f'https://{base}.com',
            f'https://{base}.in',
            f'https://{base}.co.in',
        ]

        for url in candidates:
            found = await self._check_url(client, url)
            if found:
                return DomainLookupResult(website_found=True, website_url=url, source='domain_guess')

        search_result = await self._search_official_api(client, company)
        if search_result:
            return DomainLookupResult(website_found=True, website_url=search_result, source='search_api')

        return DomainLookupResult(website_found=False)

    async def _check_url(self, client: httpx.AsyncClient, url: str) -> bool:
        await self.rate_limiter.wait()
        try:
            response = await client.get(url, timeout=self.settings.request_timeout_seconds, follow_redirects=True)
            return response.status_code < 400
        except (httpx.HTTPError, asyncio.TimeoutError):
            return False

    async def _search_official_api(self, client: httpx.AsyncClient, company: str) -> str | None:
        serp_candidate = await self._search_serpapi(client, company)
        if serp_candidate:
            return serp_candidate

        generic_candidate = await self._search_generic_official_api(client, company)
        return generic_candidate

    async def _search_serpapi(self, client: httpx.AsyncClient, company: str) -> str | None:
        if not self.settings.serpapi_api_key:
            return None

        await self.rate_limiter.wait()
        try:
            response = await client.get(
                self.settings.serpapi_url,
                params={
                    'engine': 'google',
                    'q': f'{company} official website',
                    'api_key': self.settings.serpapi_api_key,
                    'num': 5,
                },
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            organic_results = payload.get('organic_results', [])
            for entry in organic_results:
                link = entry.get('link')
                if isinstance(link, str) and self._looks_like_company_site(link, company):
                    return link
        except (httpx.HTTPError, ValueError, TypeError):
            return None

        return None

    async def _search_generic_official_api(self, client: httpx.AsyncClient, company: str) -> str | None:
        if not self.settings.search_api_url or not self.settings.search_api_key:
            return None

        await self.rate_limiter.wait()
        try:
            response = await client.get(
                self.settings.search_api_url,
                params={'q': company},
                headers={'Authorization': f'Bearer {self.settings.search_api_key}'},
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            candidate = payload.get('website')
            if isinstance(candidate, str) and candidate.startswith('http'):
                return candidate
        except (httpx.HTTPError, ValueError, TypeError):
            return None

        return None

    @staticmethod
    def _looks_like_company_site(url: str, company: str) -> bool:
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower().replace('www.', '')
            if not host:
                return False

            excluded_hosts = {
                'linkedin.com',
                'facebook.com',
                'instagram.com',
                'x.com',
                'twitter.com',
                'wikipedia.org',
                'justdial.com',
                'crunchbase.com',
            }
            if any(host.endswith(excluded) for excluded in excluded_hosts):
                return False

            tokens = [token for token in company.lower().replace('&', ' ').split() if len(token) > 2]
            if not tokens:
                return True

            return any(token in host for token in tokens)
        except Exception:
            return False
