# FinSight

FinSight is a source-linked Indian financial research prototype. This update adds a usable mutual-fund area and RBI macro records to the fresh repository.

## Added in this update

- Scheme search backed by MFapi.in’s documented search API, with source attribution and response caching.
- One-year NAV lookup and multi-scheme NAV comparison; comparisons show historical NAV change only, never a recommendation.
- Optional factsheet records for expense ratios, categories, and holdings overlap. NAV alone is not used to invent these fields.
- Seven source-linked RBI policy-rate/reserve-ratio observations dated 1 October 2026 and August 2026 official CPI/WPI inflation records, inserted automatically by migrations `0002` and `0006`.
- RBI macro CSV import for adding DBIE time series, with source URL and timezone-aware observation time retained.
- Admin pages for inspecting imported fund factsheets, NAV records, and macro observations.
- SQLite local default for simpler setup; MySQL can be configured through environment variables.

## Run the whole project with one command

Install Python 3.12 or newer and Node.js 20.9 or newer once. From the repository root in PowerShell, run:

```powershell
py -3.12 run_local.py
```

The launcher creates/uses `.venv`, installs packages only when the Python requirements or npm lock file changes, connects Django to the repository `data/` folder, builds a missing TCS/Infosys filing index if source PDFs are present, applies migrations (including the RBI/CPI/WPI starter records), checks Django, then starts the API and Next.js frontend and opens `http://127.0.0.1:3000`. Keep the terminal open; press `Ctrl+C` to stop both services. It uses local SQLite by default, preserving existing project data and avoiding accidental migrations against a configured production MySQL database. Existing retrieval indexes are reused.

The root `.env` is created from `.env.example` on first run. Add an OpenRouter, OpenAI, or Gemini key there only if you want generated RAG answers; without a key the app shows retrieved evidence with citations. OpenRouter tries `google/gemma-4-31b-it:free` first, then `openrouter/free` if the selected model is unavailable or rate-limited. Gemini defaults to `gemini-3.8-flash`. For a deployed app, set model-provider keys only in the Django backend host's secret environment variables, never in the Vercel frontend. Mutual-fund NAV and historical price lookups use their live data providers and need internet access.

If ports 8000 or 3000 are already in use, stop the other servers or choose ports using `FINSIGHT_BACKEND_PORT` and `FINSIGHT_FRONTEND_PORT`. Use `--no-browser` to prevent automatic browser opening.

## Run Django manually

If you prefer to start only the backend, from the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

Visit `http://127.0.0.1:8000`. No LLM key is needed for mutual-fund NAV search or RBI data. Django migrations seed the dated RBI and inflation observations into the local database.

Create a staff account to inspect records in Django Admin:

```powershell
python manage.py createsuperuser
```

## Mutual funds

Search schemes by name from the page, select two to five, and compare one-year NAV change. NAV lookups use [MFapi.in](https://www.mfapi.in/docs/), a third-party mirror, and label it as such. Verify any values with [AMFI](https://www.amfiindia.com/net-asset-value/nav-download).

AMFI’s terms limit use of its site to personal, non-commercial purposes and prohibit storing significant portions without authorization. For that reason this project does not bundle AMFI’s complete NAV dump. It provides a manual importer for source-authorized extracts instead:

```powershell
cd backend
python manage.py import_fund_data amfi-nav C:\data\amfi-nav.txt --confirm-terms
python manage.py import_fund_data factsheets C:\data\fund-factsheets.csv --source-url "https://source.example/factsheet" --confirm-terms
```

The `--confirm-terms` option is an operator attestation, not a license. Factsheet CSV headers: `scheme_code,scheme_name,category,expense_ratio,holdings_json,source_url`. `holdings_json` is a ticker-to-weight JSON object, with weights as percentages from 0 to 100. Expense ratio and holdings overlap remain blank until factsheets are imported.

## RBI records

The starter data file is [rbi_key_rates_2026-10-01.csv](data/rbi_key_rates_2026-10-01.csv). Seven policy-rate and reserve-ratio records are from the [official RBI page](https://m.rbi.org.in/home.aspx), as shown on 1 October 2026. The starter data also includes the provisional combined CPI inflation rate for August 2026 from [MoSPI/PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2310058&lang=1&reg=19) and the provisional all-commodities WPI inflation rate for August 2026 from [Commerce Ministry/PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2309977&lang=1&reg=3). Migrations `0002` and `0006` seed these dated source-linked records so a new deployment gets them after `migrate`.

For more series, download an allowed CSV from [RBI DBIE](https://data.rbi.org.in/DBIE/) and import it:

```powershell
cd backend
python manage.py import_macro_csv C:\data\rbi-series.csv
```

Required columns: `series,period,value,unit,observed_at,source_url`. `observed_at` must include a timezone, and each source URL must use HTTPS. Records appear in the RBI macro panel and at `GET /api/v1/macro`; optionally filter with `?series=Policy%20Repo%20Rate`.

## API routes

- `GET /api/v1/funds/search?q=HDFC`
- `GET /api/v1/funds/nav/{scheme_code}?days=365`
- `POST /api/v1/funds/compare` with JSON `{"scheme_codes":["125497","120503"]}`
- `GET /api/v1/macro?series=Policy%20Repo%20Rate`

One-year NAV change uses the first and last available NAV observations in the requested window. It is not a total-return calculation: distributions, taxes, and loads are not included. Fund categories/expense ratios and holdings overlap use only separately imported factsheet records with sources. No investment recommendation is produced.

## Database configuration

SQLite is the default for local use. For MySQL set `DB_ENGINE=mysql`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, and `MYSQL_PORT` in the environment. Keep production secrets out of source control and configure secure hosting before exposing the app publicly.


## Vercel frontend

The redesigned Next.js frontend is in `frontend/`. Start the Django API and then the frontend in separate terminals; full setup and Vercel configuration are in [`frontend/README.md`](frontend/README.md). Deploy `frontend/` as the Vercel root directory and set the server-only `FINSIGHT_API_URL` environment variable to the deployed Django API origin. Keep LLM keys on the Django backend. The frontend includes an allowlisted same-origin API proxy so browser requests do not require cross-origin Django calls.
