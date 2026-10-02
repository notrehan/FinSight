# FinSight frontend

A responsive Next.js App Router frontend for the FinSight Django REST API. It is designed to deploy on Vercel while leaving database access, retrieval, and model keys on the Django service.

## Easiest local run

From the repository root, run `py -3.12 run_local.py`. It prepares the local database/data, starts Django and Next.js together, and opens the website. Use `py -3.12 run_local.py --help` to see optional port/browser settings.

## Run the services separately

1. Start Django from the repository root:

   ```powershell
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```

2. In a second terminal, configure and start the frontend:

   ```powershell
   cd frontend
   Copy-Item .env.example .env.local
   npm install
   npm run dev
   ```

3. Open http://localhost:3000. `FINSIGHT_API_URL` should point to the Django origin, for example `http://127.0.0.1:8000`.

The browser sends requests to a constrained same-origin Next.js route handler. That handler forwards only the app's supported API endpoints to Django. This avoids exposing the Django host to browser JavaScript and avoids browser CORS configuration. OpenRouter, OpenAI, and Gemini credentials belong only in the Django environment; never add model keys to a `NEXT_PUBLIC_` variable. OpenRouter defaults to `OPENROUTER_MODEL=google/gemma-4-31b-it:free`; override it on the backend if you want a different model.

## Deploy the frontend to Vercel

1. Deploy the Django API first to a host that supports persistent MySQL/Redis, vector-index files, and the request duration needed for RAG. Run migrations and confirm its `/api/health` endpoint works over HTTPS.
2. Import the repository into Vercel and set **Root Directory** to `frontend`. Keep the Next.js framework preset and default build/output settings.
3. Add `FINSIGHT_API_URL` to Vercel's Production and Preview environment variables. Set it to the Django service origin, with no trailing path, such as `https://api.example.com`.
4. Optionally set `NEXT_PUBLIC_FINSIGHT_ADMIN_URL` to the Django `/admin/` URL for staff announcement review.
5. Deploy, then open the Vercel site and check its health status, filing research, macro records, fund search, and a sample CSV portfolio upload.

The Next.js proxy has a 60-second maximum duration and 55-second upstream timeout. Check the chosen Vercel plan and Django host limits before relying on synchronous RAG for public traffic. Long-running AI/PDF processing should move to a background worker before production use.

The interface includes overview, filing RAG with citations and optional calculations, a standalone deterministic calculator, price history, watchlists and approved announcements, CSV portfolio exposure/overlap, mutual-fund search/NAV/comparison, RBI/macro records, and system health/latency/provider status. Staff can use the optional Django admin link for announcement review, prompt versions, evaluation scores, and source-linked data management. Missing/imported data is shown as missing rather than filled with invented values.
