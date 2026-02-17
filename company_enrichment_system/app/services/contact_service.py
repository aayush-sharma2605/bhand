from __future__ import annotations

import asyncio

import httpx

from app.config import Settings
from app.models import ContactLookupResult
from app.services.rate_limiter import AsyncRateLimiter
from app.utils.validators import is_valid_email, is_valid_phone


class ContactService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.rate_limiter = AsyncRateLimiter(settings.rate_limit_per_second)

    async def lookup_contact(self, client: httpx.AsyncClient, company: str) -> ContactLookupResult:
        if not self.settings.google_places_api_key:
            return ContactLookupResult(source='not_configured')

        place = await self._search_place(client, company)
        if not place:
            return ContactLookupResult(source='google_places')

        phone = place.get('formatted_phone_number') or place.get('international_phone_number')
        email = place.get('email')

        phone_found = is_valid_phone(phone)
        email_found = is_valid_email(email)

        return ContactLookupResult(
            phone=phone if phone_found else None,
            email=email if email_found else None,
            phone_found=phone_found,
            email_found=email_found,
            source='google_places',
        )

    async def _search_place(self, client: httpx.AsyncClient, company: str) -> dict | None:
        await self.rate_limiter.wait()
        text_search_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
        try:
            search_resp = await client.get(
                text_search_url,
                params={'query': company, 'key': self.settings.google_places_api_key},
                timeout=self.settings.request_timeout_seconds,
            )
            search_resp.raise_for_status()
            search_json = search_resp.json()
            results = search_json.get('results', [])
            if not results:
                return None
            place_id = results[0].get('place_id')
            if not place_id:
                return None
        except (httpx.HTTPError, ValueError, KeyError, TypeError, asyncio.TimeoutError):
            return None

        await self.rate_limiter.wait()
        details_url = 'https://maps.googleapis.com/maps/api/place/details/json'
        try:
            details_resp = await client.get(
                details_url,
                params={
                    'place_id': place_id,
                    'fields': 'formatted_phone_number,international_phone_number,email',
                    'key': self.settings.google_places_api_key,
                },
                timeout=self.settings.request_timeout_seconds,
            )
            details_resp.raise_for_status()
            details_json = details_resp.json()
            return details_json.get('result')
        except (httpx.HTTPError, ValueError, KeyError, TypeError, asyncio.TimeoutError):
            return None
