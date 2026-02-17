# company_enrichment_system

Production-ready FastAPI backend for enrichment of up to 20,000 companies from CSV/XLSX input.

## Why this architecture
- **Non-blocking ingest + processing**: `/upload` parses file, stores a job, and returns immediately while processing runs via `asyncio.create_task`.
- **Scalable batches**: worker processes records in configurable batches (`50-100`) with bounded concurrency (`Semaphore`) to keep memory stable.
- **Resilient network behavior**: async `httpx` calls, retry logic per company (`max 3`), configurable timeouts, and global rate limiter.
- **Official API usage only**: optional SerpApi/generic search API for website fallback and Google Places API for contacts when website is unavailable.
- **Operational visibility**: job metadata tracks status and counters (`total`, `processed`, `success_count`, `failure_count`, `error`).
- **Exportability**: job results stream back as CSV via `/download/{job_id}`.

## Project structure

```text
company_enrichment_system/
  app/
    main.py
    config.py
    models.py
    routers/
      jobs.py
    services/
      website_service.py
      contact_service.py
      rate_limiter.py
    jobs/
      job_manager.py
      processor.py
    utils/
      file_loader.py
      validators.py
  requirements.txt
  .env.example
```

## Run locally

```bash
cd company_enrichment_system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```


## API keys: what you need to insert
- `GOOGLE_PLACES_API_KEY` (**optional, but required for contact discovery**): used only when website is not found and you want phone/email lookup from Google Places.
- `SERPAPI_API_KEY` (**optional**): used for SerpApi-based official search fallback when domain guessing fails.
- `SEARCH_API_URL` + `SEARCH_API_KEY` (**optional pair**): generic official search fallback if you are not using SerpApi.

If search keys are empty, the system still runs: it will perform domain-guess website checks only.
If `GOOGLE_PLACES_API_KEY` is also empty, contact lookup is skipped.


## SerpApi usage
Yes, SerpApi can be used in this project. Set:
- `SERPAPI_API_KEY`
- `SERPAPI_URL` (default already points to `https://serpapi.com/search.json`)

The backend queries SerpApi only after domain guessing fails, then tries to pick likely official website URLs from organic results.


## API key kahan place karna hai
1. `company_enrichment_system/.env.example` ko copy karke `.env` banao:
   - `cp .env.example .env`
2. `.env` file me apne keys paste karo:
   - `SERPAPI_API_KEY=...`
   - `GOOGLE_PLACES_API_KEY=...`
   - (optional) `SEARCH_API_URL` + `SEARCH_API_KEY`
3. Server restart karo taaki new env values load ho jayein.

## 20 companies sample file
Project me ready file di gayi hai: `sample_companies_20.csv`
- Total: 20 companies
- First 10: popular companies (usually website mil jati hai)
- Next 10: synthetic/fake names (often website nahi milti)

## Output me website mili ya nahi kaise dekho
`/download/{job_id}` CSV me ye columns milenge:
- `website_found` -> `true/false`
- `website` -> agar website mili to URL, warna blank

Aap Excel/CSV me filter laga sakte ho:
- `website_found = true` => jinki website mili
- `website_found = false` => jinki website nahi mili

## API endpoints
- `POST /upload` — Upload `.csv` or `.xlsx`; first column is used for company names.
- `GET /job/{job_id}` — Inspect job status and counters.
- `GET /download/{job_id}` — Download job results as CSV.

## Output schema
Each row contains:

```json
{
  "company": "acme ltd",
  "website": "https://acmeltd.com",
  "website_found": true,
  "phone": "+14155550123",
  "phone_found": true,
  "email": "contact@acme.com",
  "email_found": true,
  "source": "domain_guess",
  "status": "SUCCESS"
}
```

## Notes
- CSV and XLSX extraction normalizes names (`strip + lowercase`) and removes duplicates while preserving order.
- Contact lookup runs **only** when website is not found.
- Google Places `email` availability depends on provider response; many records may not include it.
