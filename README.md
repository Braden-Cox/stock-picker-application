# Stock Picker Application
### *Social Signal* — Turning social media stock chatter into verified, credibility-scored predictions
 
A backend pipeline and API that mines X (formerly Twitter) for stock picks, scores them with LLMs, and tracks which posters actually call it right.
 
It scrapes stock-related posts, filters them for relevance and sentiment using Gemini and Claude, verifies each pick against real price movement via historical market data, builds a running credibility score per poster, and surfaces a ranked list of the current best picks through a REST API.
 
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
 
**Status:** Backend/API complete and functional. No frontend is planned — this is designed to be consumed as a JSON API or queried directly.
 
This is a **self-hosted project**: clone it, plug in your own API keys, and run it against your own database. There is no shared or hosted instance — each person who runs this project uses their own credentials and pays only for their own usage.

> ⚠️ **Cost and runtime note:** Scraping and classification stages make real, billed calls to GetXAPI, Gemini, and Anthropic. Verifying all pending users' historical picks can take hours to complete and cost several dollars depending on volume — this is expected behavior, not a bug. See [Known limitations](#known-limitations--calibration) below before running the pipeline at scale.

---
 
## How it works
 
The system runs as independent pipeline stages, each triggerable on demand via the CLI or the API.
 
```
1. Ticker sync         NASDAQ/NYSE screener → clean & flag symbols → upsert into tickers table
2. Scrape              GetX API search per active ticker → dedupe/merge → store posts + users
3. Classify relevance  Gemini 2.5 Flash Lite batches posts → is this post actually a stock pick?
4. Classify sentiment  Claude Haiku 4.5 batches relevant posts → bullish/bearish/neutral + confidence
5. Verify picks        yfinance price data at +30/60/90 days → was the pick actually correct?
6. Credibility         hit-rate per user → whitelist / greylist / blacklist
7. Rank & store        score = sentiment_score × user hit_rate × engagement → top N persisted
```
 
### 1. Ticker sync
Pulls the full NASDAQ + NYSE symbol list, flags/deactivates junk tickers (single-character symbols, symbols over 5 characters, common English words, symbols with dots or special characters), and upserts into `tickers`. Tickers whose scraped posts stay below a relevance threshold over enough volume get auto-deactivated ([`update_ticker_status.py`](app/pipeline/update_ticker_status.py)) so the scraper stops wasting calls on noisy symbols.

Ticker cleaning depends on [`data/common_words.json`](data/common_words.json), a list of common English words used to flag tickers that collide with ordinary vocabulary (e.g. "ARE", "IT") so they get search-prefixed with `$` instead of matching everywhere. This file must exist for `clean_tickers.py` to run.

### 2. Scrape
For each active ticker, queries the GetX API (X/Twitter search) for recent posts, tagging single-character/common-word tickers with a `$` prefix to cut down on false matches. Posts below an engagement threshold (`likes + 2×reposts < 5`) are dropped before they ever hit the database. New posters are auto-created in `users` with `list_status="unknown"`. Posts from already-blacklisted users are never stored at all.
 
### 3. Relevance classification
Batches of up to 50 unprocessed posts go to **Gemini 2.5 Flash Lite** ([`llm_relevance.py`](app/pipeline/llm_relevance.py)), which returns a strict-JSON verdict on whether each post is an actual stock opinion/prediction versus spam, a bare mention, or a news headline. Posts from blacklisted users are excluded from every batch. Failed or malformed responses are retried automatically before giving up on a batch.
 
### 4. Sentiment classification
Posts that passed relevance go to **Claude Haiku 4.5** ([`llm_sentiment.py`](app/pipeline/llm_sentiment.py)) in batches of 25, which assigns `bullish` / `bearish` / `neutral`, a 0–1 confidence score, and whether the post is a concrete, actionable pick (`is_valid`) versus vague commentary.
 
### 5. Pick verification
For each user with unverified valid picks, the pipeline backfills up to two years of their historical posts (skipping accounts that are suspended, deleted, or otherwise unreachable), runs those historical posts through the same relevance/sentiment classifiers, then checks every pick's ticker against **yfinance** price data at day 0/30/60/90 ([`verify_picks.py`](app/pipeline/verify_picks.py)). A pick is marked correct if the average percent change over that window matches the claimed direction (bullish needs >+3%, bearish needs <-3%, neutral needs to stay within -1%..+3%). Users who were verified within the last 31 days are skipped on subsequent runs to avoid redundant re-scraping.
 
### 6. Credibility & ranking
[`update_credibility.py`](app/pipeline/update_credibility.py) computes each user's hit rate once they have more than 6 verified picks, and buckets them into `whitelist` (≥50% hit rate), `greylist`, or `blacklist` (<10%) — blacklisted users are excluded from all future scraping and classification. [`rank_picks.py`](app/pipeline/rank_picks.py) then scores every unverified, still-current pick as `sentiment_score × user.hit_rate × engagement_weight`, and [`store_top_picks.py`](app/pipeline/store_top_picks.py) persists the top N as the current picks list, retiring anything that falls out of the ranking.
 
---
 
## API
 
All endpoints are namespaced by router and documented interactively at `/docs` (FastAPI's built-in Swagger UI) once the server is running.
 
| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/picks/top` | Current ranked top picks, with post content and score |
| GET | `/tickers/active` | All currently active tickers |
| GET | `/tickers/{ticker_symbol}` | A single ticker's relevance/activity stats |
| GET | `/users/top` | Whitelisted users sorted by hit rate |
| GET | `/users/{user_id}` | A single user's credibility record |
| POST | `/pipeline/tickers/sync` | Trigger ticker sync (background task) |
| POST | `/pipeline/tickers/status` | Trigger ticker activity/relevance re-evaluation |
| POST | `/pipeline/scrape` | Trigger post scraping |
| POST | `/pipeline/classify` | Trigger relevance + sentiment classification |
| POST | `/pipeline/verify` | Trigger pick verification against price data |
| POST | `/pipeline/rank` | Trigger re-ranking and top-picks storage |
 
Every `/pipeline/*` route requires a `pipeline-Key` header matching your own `PIPELINE_API_KEY`, since these trigger paid LLM/API calls and background work — this is a value **you invent yourself**, purely to stop anyone else from remotely triggering your pipeline on your own API budget. The read endpoints under `/picks`, `/tickers`, and `/users` are open.
 
Trigger endpoints return immediately and run in the background, since some stages (especially historical verification) can take a long time. Progress and errors print to the server's own console — check there for run status.
 
---
 
## Data model
 
| Table | Purpose |
|---|---|
| `tickers` | Symbol universe with active/flagged status and running relevance rate |
| `posts` | Scraped posts with relevance/sentiment/validity flags and pick-verification outcome |
| `users` | Posters, with running hit rate and whitelist/greylist/blacklist status |
| `top_picks` | Snapshot of currently ranked picks, retired (`is_current=False`) as new ones outrank them |
 
Schema lives in [`migrations/`](migrations/) as plain numbered SQL files (no migration framework — apply in order against the target database).
 
---
 
## Tech stack
 
- **API:** FastAPI + Uvicorn
- **Database:** PostgreSQL 16 via SQLAlchemy ORM
- **LLMs:** Google Gemini 2.5 Flash Lite (relevance filtering), Anthropic Claude Haiku 4.5 (sentiment scoring)
- **Market data:** yfinance (free, no API key required)
- **Social data:** GetX API (X/Twitter search)
- **Config:** pydantic-settings, `.env`-driven
- **Deployment:** Docker + Docker Compose

---
 
## Setup
 
### Prerequisites
- Docker and Docker Compose
- API keys for: GetX API, Anthropic, Google Gemini

### Local environment (for running pipeline stages manually)
The Docker setup runs the API server, but the CLI commands below (for manually running individual pipeline stages) execute directly on your machine, not inside the container. Set up a local virtual environment first:

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

You'll also need Postgres reachable from your host machine for these commands to work — `docker-compose up -d` needs to be running alongside.

### Configuration
Copy `.env.example` to `.env` and fill in:
 
| Variable | Purpose |
|---|---|
| `GETXAPI_KEY` | X/Twitter scraping via GetX API |
| `ANTHROPIC_API_KEY` | Claude Haiku sentiment classification |
| `GOOGLE_GEMINI_API_KEY` | Gemini relevance classification |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` / `POSTGRES_HOST` | Database connection |
| `PIPELINE_API_KEY` | Secret you invent yourself, required to trigger `/pipeline/*` routes |
 
### Run
```bash
docker-compose up --build
```
This starts Postgres and the FastAPI app together (`localhost:8000`), since the app container's entrypoint runs `uvicorn` automatically.

### Run the API locally (alternative to Docker)
If you've set up the local virtual environment above and have Postgres reachable (e.g. via `docker-compose up -d` for just the database), you can run the API directly with auto-reload for faster iteration while developing:

```bash
uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/docs`.

### Apply migrations
The `migrations/` folder isn't copied into the container, so run these from your host machine, piping into the running `db` container (only needed once, the first time you set up the database):
```bash
docker exec -i <db-container-name> psql -U postgres -d stockpicker < migrations/001_create_tickers.sql
docker exec -i <db-container-name> psql -U postgres -d stockpicker < migrations/002_create_posts.sql
docker exec -i <db-container-name> psql -U postgres -d stockpicker < migrations/003_create_users.sql
docker exec -i <db-container-name> psql -U postgres -d stockpicker < migrations/004_create_top_picks.sql
```
 
### Running pipeline stages manually
Every pipeline module is also a standalone CLI for local testing/backfills, e.g.:
```bash
python -m app.pipeline.fetch_tickers
python -m app.pipeline.scrape_posts --limit_tickers 5 --limit_calls 3
python -m app.pipeline.llm_relevance --limit 200
python -m app.pipeline.verify_picks --all
python -m app.pipeline.rank_picks
```
Most commands accept `--limit` to cap how much they process in one run, and `verify_picks` accepts `--user_id` to target a single user instead of everyone pending.
 
---
 
## Project structure
```
app/
  main.py              FastAPI app + router registration
  config.py             Settings loaded from .env
  database.py            SQLAlchemy engine/session setup
  models/                 ORM models: Post, Ticker, TopPick, User
  routers/                picks, tickers, users, pipeline (trigger endpoints)
  pipeline/               Each stage of the scrape → classify → verify → rank flow
  services/               External API clients: Anthropic, Gemini, GetX, yfinance
migrations/               Numbered SQL schema files
data/                     Static reference data (e.g. common_words.json for ticker cleaning)
```
 
---

## Known limitations & calibration
 
A handful of thresholds in this project are intentional starting estimates, chosen before enough real data existed to validate them properly. They're designed to be easy to tune (most are function parameters or CLI flags, not hardcoded constants), and are documented here so they're not mistaken for carefully-tuned production values:
 
- **Ticker relevance threshold** (`update_ticker_status.py`, default `0.01`) — deliberately lenient to avoid deactivating tickers prematurely on limited data; expected to be tightened once a larger sample of per-ticker relevance rates is available.
- **Ticker minimum post volume** (`update_ticker_status.py`, default `500`) — the number of scraped posts required before a ticker's relevance rate is trusted at all.
- **Post engagement weight cap** (`rank_picks.py`, default `100`) — used to normalize raw engagement into a 0–1 weight; based on an early, small sample of real engagement numbers and likely to shift as more posts are scraped.
- **User credibility thresholds** (`update_credibility.py`) — `>6` verified picks required before a hit rate is trusted, `≥50%` for whitelist, `<10%` for blacklist. These were set from a very small early sample of verified users and should be revisited once a much larger population has been verified.
- **Historical scrape window** (`verify_picks.py`, 2 years) — not yet validated against how far back genuinely useful, gradable picks tend to go; a shorter window may capture nearly the same signal for a fraction of the API cost.

None of these require code changes to adjust — they're all parameters or defaults that can be overridden via CLI flags or function arguments as more data becomes available.
 
---
 
## Design notes
 
- **Self-hosted, not a hosted service.** Every person who runs this project brings their own API keys and controls their own costs — there is no shared instance and no central API key.
- **Cost-conscious throughout.** Blacklisted posters are filtered out before their posts ever reach the LLM stages. Tickers that consistently produce irrelevant chatter get automatically deactivated. Every external API call has retry logic so a single transient failure doesn't waste an entire batch.
- **No automated scheduling.** Given the real per-call costs of the LLM and scraping services involved, this project intentionally does not run on a cron schedule — every stage is triggered manually (CLI or API), so nothing runs, and nothing costs money, without an explicit decision to run it.
- **Background tasks for pipeline triggers.** Some stages — especially historical pick verification — can take hours to complete (multiple GetXAPI calls, LLM classification, and price lookups per user). If a `/pipeline/*` endpoint ran these synchronously, the HTTP request would simply hang until the entire run finished, which isn't a workable API experience. Trigger endpoints instead schedule the work as a FastAPI background task and return immediately; the actual database session used by the background function is opened and closed independently of the request/response cycle, since the session FastAPI injects into the endpoint itself closes the moment the response is sent.
---
 
## License
 
MIT — see [LICENSE](LICENSE).