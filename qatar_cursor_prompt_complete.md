

================================================================================
## 1. CONTEXT
================================================================================

You are working on the **Qatar AI Platform** — a full-stack data analytics and AI
advisory application for the Qatar automotive market. The project is functional but
has severe performance problems that make it unusable under real load.

---

### Current Tech Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Backend    | FastAPI (Python)                                |
| Database   | PostgreSQL (with SQLite fallback)               |
| LLM        | Ollama → Qwen2.5:7b (running locally)          |
| Frontend   | React + Vite (mixed JS/TS)                      |
| ML Models  | scikit-learn (price, risk, demand, match)       |
| Styling    | Plain CSS                                       |

---

### Current Directory Structure

```
project/
├── Data/         — 10 CSV/Excel source datasets (DO NOT MODIFY)
├── etl/          — load_data.py, validate_data.py
├── ml/           — 4 trained model files (.pkl)
├── api/          — FastAPI app + route files
├── llm/          — system_prompt + ollama_client
└── frontend/     — React + Vite, 6 dashboards
```

---

### The 6 Dashboards (must all be preserved)

1. **Market Hub** — KPIs, health score, volume metrics
2. **Inventory Health** — risk-scored vehicle table
3. **Pricing Tool** — ML price predictor form
4. **Market & Economics** — oil prices, rates, macro events
5. **Buyer Matching** — ready buyer recommendations
6. **AI Advisor** — chat interface with Qwen LLM

---

### Diagnosed Performance Problems (Root Causes)

**[CRITICAL] No API Response Caching — Every Request Hits the DB**
Market KPIs, inventory summaries, and trend data are re-queried from PostgreSQL
on every single page load. With no Redis/in-memory cache layer, each dashboard
tab triggers multiple full-table scans. At scale, load time explodes to 3–8 seconds.

**[CRITICAL] LLM Runs Synchronously — Blocks the Entire API Thread**
The Ollama Qwen2.5:7b call is made inline, synchronously in the FastAPI route
handler. Since Qwen2.5:7b takes 5–30s to respond, the entire Python thread is
blocked. No streaming, no async, no background task queue — the AI Advisor is
completely unusable under any concurrent load.

**[CRITICAL] ML Models Loaded On-Demand (No Warm State)**
The price_predictor, risk_scorer, demand_forecaster, and buyer_matcher .pkl files
are loaded on each request or cold start. No singleton pattern = repeated
deserialization on every prediction API call.

**[HIGH] No Database Connection Pooling**
db.py creates a new SQLAlchemy engine/connection per request. Without connection
pooling (min 5, max 20 connections), every API call pays a full TCP handshake +
auth cost to PostgreSQL. Under concurrent users this bottlenecks immediately.

**[HIGH] Frontend Fetches All Dashboards on Mount**
React loads all 6 dashboard data sources on initial mount using parallel useEffect
hooks. Tabs that aren't even visible trigger network requests. No lazy loading,
no suspense boundaries, no route-based code splitting.

**[MED] No Database Indexes on Filter Columns**
Inventory queries filter by make, model, risk_flag, year — none are indexed.
Full sequential table scans on every filter. With 10k+ rows this is immediately
noticeable.

**[MED] No ETL Materialized Views / Pre-Aggregation**
Market trends and KPI aggregations are computed at query time. These must be
materialized views refreshed on a schedule (every 6–24 hrs), not recomputed
on every API call.

---

### Current vs Target Performance

| Metric                     | Current (Estimated)  | Target After Rebuild   | Fix                          |
|----------------------------|----------------------|------------------------|------------------------------|
| Dashboard initial load     | 4–8 seconds          | < 800ms                | Redis cache                  |
| Market KPIs API            | 800ms–2s             | < 50ms                 | Cached response (TTL 5min)   |
| Inventory table load       | 1–3s                 | < 200ms                | DB indexes + pagination      |
| Price prediction           | 300–800ms            | < 100ms                | Preloaded model singleton    |
| AI Advisor first token     | 8–30s (blocking)     | 2–5s (streaming)       | Async streaming SSE          |
| Concurrent users supported | 1–3 users            | 50+ users              | Workers + connection pool    |


================================================================================
## 2. GOAL
================================================================================

Refactor and rebuild the Qatar AI Platform to be **production-ready, fast, and
fully deployable on Render.com** — without changing any core business features,
datasets, or ML models.

The rebuild targets the architecture below:

```
[ CLIENT LAYER ]
  React + Vite SPA (code-split by route)
  TanStack Query (client-side caching)
  Recharts / D3 (dashboard charts)
  SSE Client (LLM token streaming)

        ↕  HTTPS / REST / SSE

[ API GATEWAY LAYER ]
  FastAPI async — 4 Uvicorn workers
  Rate Limiter (slowapi)
  CORS + Auth (JWT optional)
  Response Cache (Cache-Control headers)

        ↕

[ SERVICE LAYER ]
  Market Service     — KPIs, trends, events
  Inventory Service  — Risk, filters, pagination
  Pricing Service    — ML inference
  Matching Service   — Buyer-vehicle matching
  LLM Service        — Async streaming

        ↕

[ INFRASTRUCTURE LAYER ]
  PostgreSQL        — Connection pool (10–20)
  Redis Cache       — TTL 5min–24hr
  Groq API (cloud)  — Replaces local Ollama
  ML Model Store    — Preloaded singletons

        ↕

[ BACKGROUND JOBS ]
  ETL Scheduler  — APScheduler
  Cache Warmer   — Pre-compute KPIs on startup
  ML Retrainer   — Scheduled model refresh
```


================================================================================
## 3. INPUTS
================================================================================

The following already exist and must be preserved or migrated — do not delete or
rewrite these from scratch:

- `Data/` — 10 CSV/Excel source files (read-only, never modify)
- `etl/load_data.py` and `etl/validate_data.py` — ETL pipeline (keep as-is)
- `ml/price_model.pkl` — trained price prediction model
- `ml/risk_model.pkl` — trained risk scoring model
- `ml/demand_model.pkl` — trained demand forecasting model
- `ml/match_model.pkl` — trained buyer matching model
- `api/` — existing FastAPI routes (refactor structure, keep business logic)
- `llm/system_prompt` — LLM system prompt (reuse in Groq integration)
- `llm/ollama_client` — replace with Groq async client
- `frontend/` — 6 React dashboard components (restructure, do not rewrite features)


================================================================================
## 4. REQUIREMENTS / CONSTRAINTS
================================================================================

---

### BACKEND REQUIREMENTS

#### Fix 1 — Async SQLAlchemy + Connection Pooling
Replace the synchronous engine in `db.py` with async SQLAlchemy.

**File: `api/database.py`**
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

#### Fix 2 — Redis Cache Decorator on All GET Endpoints
Create a reusable `@cache(ttl=...)` decorator. Apply it to all KPI, inventory
summary, and trend GET routes.

**File: `api/cache.py`**
```python
import redis.asyncio as redis
import json, functools

r = redis.from_url("redis://localhost:6379")

def cache(ttl: int = 300):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"cache:{func.__name__}:{kwargs}"
            cached = await r.get(key)
            if cached:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            await r.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

# Usage on every GET route:
# @router.get("/api/market/kpis")
# @cache(ttl=300)
# async def get_market_kpis():
#     ...
```

---

#### Fix 3 — ML Model Singleton Registry (Load Once at Startup)
Load all 4 models once when FastAPI starts. Never load them per-request.

**File: `api/ml_models.py`**
```python
import joblib

class ModelRegistry:
    _models = {}

    @classmethod
    def load_all(cls):
        cls._models = {
            "price":  joblib.load("ml/price_model.pkl"),
            "risk":   joblib.load("ml/risk_model.pkl"),
            "demand": joblib.load("ml/demand_model.pkl"),
            "match":  joblib.load("ml/match_model.pkl"),
        }

    @classmethod
    def get(cls, name):
        return cls._models[name]
```

**File: `api/main.py` — startup hook**
```python
@app.on_event("startup")
async def startup():
    ModelRegistry.load_all()
    await warm_cache()  # pre-populate Redis on boot
```

---

#### Fix 4 — Async LLM Streaming via SSE (Replace Blocking Ollama Call)
Convert the synchronous LLM call to a fully async streaming SSE response.

**File: `api/routes/chat.py`**
```python
from fastapi.responses import StreamingResponse
import httpx

async def stream_ollama(prompt: str):
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            "http://localhost:11434/api/generate",
            json={"model": "qwen2.5:7b", "prompt": prompt, "stream": True}
        ) as resp:
            async for chunk in resp.aiter_lines():
                yield f"data: {chunk}\n\n"

@router.post("/api/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        stream_ollama(req.message),
        media_type="text/event-stream"
    )
```

---

#### Fix 5 — Replace Ollama with Groq API (Cloud LLM for Render)
Render does NOT support GPU instances. Qwen2.5:7b on CPU will take 60–120s.
Replace with Groq API (free tier: 500 req/day, Llama3 70B, <2s response).

- Install: `pip install groq`
- Use `GROQ_API_KEY` from environment variable
- Keep the existing `llm/system_prompt` content, pass it as the system message
- Maintain the same streaming SSE interface on the frontend

---

#### Fix 6 — Database Indexes on Filter Columns
Add indexes on all columns used in WHERE/ORDER BY clauses.

```sql
CREATE INDEX idx_inventory_make      ON inventory(make);
CREATE INDEX idx_inventory_model     ON inventory(model);
CREATE INDEX idx_inventory_year      ON inventory(year);
CREATE INDEX idx_inventory_risk_flag ON inventory(risk_flag);
CREATE INDEX idx_customers_id        ON customers(customer_id);
```

---

#### Fix 7 — PostgreSQL Materialized Views + APScheduler Refresh
Pre-aggregate KPI and trend data. Refresh every 6 hours.

```sql
CREATE MATERIALIZED VIEW market_kpis AS
SELECT
    COUNT(*)                    AS total_inventory,
    AVG(price)                  AS avg_price,
    SUM(CASE WHEN risk_flag = 'high' THEN 1 ELSE 0 END) AS high_risk_count
FROM inventory;

CREATE MATERIALIZED VIEW monthly_trends AS
SELECT
    DATE_TRUNC('month', sale_date) AS month,
    COUNT(*)                        AS sales_volume,
    AVG(price)                      AS avg_price
FROM sales
GROUP BY 1
ORDER BY 1;
```

APScheduler job in `api/main.py`:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("interval", hours=6)
async def refresh_views():
    async with engine.begin() as conn:
        await conn.execute(text("REFRESH MATERIALIZED VIEW market_kpis"))
        await conn.execute(text("REFRESH MATERIALIZED VIEW monthly_trends"))

scheduler.start()
```

---

#### Fix 8 — Pydantic Settings (Centralized Config)

**File: `api/config.py`**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    groq_api_key: str
    debug: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
```

---

#### Fix 9 — Add /health and /metrics Endpoints
```python
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    return {"uptime": "...", "cache_hits": "..."}
```

---

#### Fix 10 — Rate Limiting on LLM Endpoint
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/chat")
@limiter.limit("10/minute")
async def chat(req: ChatRequest, request: Request):
    ...
```

---

### BACKEND FOLDER STRUCTURE (Target)

```
api/
├── main.py              # App factory, startup hooks, scheduler
├── database.py          # Async SQLAlchemy engine + session
├── cache.py             # Redis cache decorator
├── config.py            # Pydantic Settings (all env vars)
├── dependencies.py      # DB session, auth dependencies
├── ml_models.py         # ModelRegistry singleton
├── models/
│   ├── vehicle.py
│   ├── customer.py
│   └── market.py
├── schemas/             # Pydantic I/O schemas
│   ├── pricing.py
│   └── chat.py
├── routes/
│   ├── market.py
│   ├── inventory.py
│   ├── pricing.py
│   ├── matching.py
│   └── chat.py
└── services/            # Business logic (no direct DB calls)
    ├── market_service.py
    ├── pricing_service.py
    └── llm_service.py
```

---

### FRONTEND REQUIREMENTS

#### Fix 1 — Install TanStack Query + Replace All useEffect Fetches

```bash
npm i @tanstack/react-query
```

**File: `frontend/src/hooks/useMarketKPIs.ts`**
```typescript
import { useQuery } from '@tanstack/react-query';

export const useMarketKPIs = () =>
  useQuery({
    queryKey: ['market-kpis'],
    queryFn: () => fetch('/api/market/kpis').then(r => r.json()),
    staleTime: 5 * 60 * 1000,       // 5 min client cache
    gcTime: 10 * 60 * 1000,         // 10 min garbage collection
    refetchOnWindowFocus: false,
  });
```

Replace every `useEffect` + `fetch` pattern across all 6 dashboards with the
equivalent `useQuery` hook.

---

#### Fix 2 — Lazy Load All 6 Dashboards with Suspense Skeletons

**File: `frontend/src/App.tsx`**
```typescript
import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import DashboardSkeleton from './components/ui/DashboardSkeleton';

const MarketHub   = lazy(() => import('./dashboards/MarketHub'));
const Inventory   = lazy(() => import('./dashboards/Inventory'));
const PricingTool = lazy(() => import('./dashboards/PricingTool'));
const MarketEcon  = lazy(() => import('./dashboards/MarketEcon'));
const BuyerMatch  = lazy(() => import('./dashboards/BuyerMatch'));
const AIAdvisor   = lazy(() => import('./dashboards/AIAdvisor'));

<Suspense fallback={<DashboardSkeleton />}>
  <Routes>
    <Route path="/"         element={<MarketHub />} />
    <Route path="/inventory" element={<Inventory />} />
    <Route path="/pricing"  element={<PricingTool />} />
    <Route path="/economics" element={<MarketEcon />} />
    <Route path="/buyers"   element={<BuyerMatch />} />
    <Route path="/ai"       element={<AIAdvisor />} />
  </Routes>
</Suspense>
```

---

#### Fix 3 — SSE Chat Client for Streaming LLM Output

```typescript
// frontend/src/dashboards/AIAdvisor.tsx
const sendMessage = (message: string) => {
  const source = new EventSource(`/api/chat?message=${encodeURIComponent(message)}`);
  source.onmessage = (e) => {
    const chunk = JSON.parse(e.data);
    setResponse(prev => prev + chunk.response);
  };
  source.onerror = () => source.close();
};
```

---

#### Fix 4 — Full TypeScript Migration

- Add a `frontend/src/types/` folder
- Create shared type files that mirror all API response schemas
- Example:

```typescript
// frontend/src/types/market.ts
export interface MarketKPIs {
  total_inventory: number;
  avg_price: number;
  high_risk_count: number;
}

// frontend/src/types/inventory.ts
export interface Vehicle {
  id: string;
  make: string;
  model: string;
  year: number;
  price: number;
  risk_flag: 'low' | 'medium' | 'high';
}
```

---

### FRONTEND FOLDER STRUCTURE (Target)

```
frontend/src/
├── App.tsx
├── api/                  # All raw API fetch functions
│   ├── market.ts
│   ├── inventory.ts
│   ├── pricing.ts
│   ├── matching.ts
│   └── chat.ts
├── hooks/                # TanStack Query hooks (one per data source)
│   ├── useMarketKPIs.ts
│   ├── useInventory.ts
│   ├── usePricing.ts
│   └── useBuyerMatch.ts
├── components/
│   ├── ui/               # Reusable: KPICard, DataTable, Chart, Skeleton
│   └── layout/           # Sidebar, Header, Shell
├── dashboards/           # Each dashboard = its own lazy-loaded chunk
│   ├── MarketHub.tsx
│   ├── Inventory.tsx
│   ├── PricingTool.tsx
│   ├── MarketEcon.tsx
│   ├── BuyerMatch.tsx
│   └── AIAdvisor.tsx
├── store/                # Zustand global state (filters, user prefs)
└── types/                # Shared TypeScript interfaces matching API schemas
```

---

### RENDER DEPLOYMENT REQUIREMENTS

#### render.yaml (Infrastructure as Code — create this file at project root)

```yaml
services:
  - type: web
    name: qatar-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 4
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: qatar-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          type: redis
          name: qatar-cache
          property: connectionString
      - key: GROQ_API_KEY
        sync: false    # must be set manually in Render dashboard

  - type: web
    name: qatar-frontend
    runtime: static
    buildCommand: cd frontend && npm ci && npm run build
    staticPublishPath: frontend/dist
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
    envVars:
      - key: VITE_API_URL
        value: https://qatar-api.onrender.com

  - type: redis
    name: qatar-cache
    plan: free

databases:
  - name: qatar-db
    plan: free
```

#### Render Service Summary

| Service       | Type             | Plan                           | Notes                        |
|---------------|------------------|--------------------------------|------------------------------|
| qatar-api     | Web Service      | Starter $7/mo → Standard $25   | Python 3.11, 4 workers       |
| qatar-frontend| Static Site      | Free                           | Vite build → dist/           |
| qatar-db      | PostgreSQL       | Free 90 days → Starter $7/mo  | Auto-injects DATABASE_URL    |
| qatar-cache   | Redis            | Free → $10/mo for persistence  | Auto-injects REDIS_URL       |

#### GitHub Actions CI/CD (`.github/workflows/deploy.yml`)

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest

  lint-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm ci && npm run lint
```

---

### HARD CONSTRAINTS (Never violate these)

- Do NOT use GPU-dependent features — Render has no GPU support
- Do NOT modify anything inside `Data/` — source files are read-only
- Do NOT rewrite the ETL pipeline or ML model training logic
- Do NOT change the 6 dashboard features — only restructure and optimise
- Do NOT hardcode any secrets — use environment variables for all keys and URLs
- All secrets go in `.env` locally and Render dashboard in production


================================================================================
## 5. OUTPUT FORMAT
================================================================================

Execute this rebuild in **5 sequential phases**. Complete and verify each phase
before starting the next. Do not skip ahead.

---

### Phase 1 — Critical Performance Fixes (Days 1–5)
**Goal:** Stop the bleeding. Fix the 3 critical issues first.

Deliver:
- [ ] `api/database.py` — async engine with connection pool
- [ ] `api/cache.py` — Redis cache decorator
- [ ] `api/ml_models.py` — ModelRegistry singleton
- [ ] All GET route files updated with `@cache(ttl=300)`
- [ ] `api/routes/chat.py` — async SSE streaming endpoint
- [ ] SQL migration script with all 5 DB indexes
- [ ] Bash commands: `pip install redis[asyncio] httpx sqlalchemy[asyncio]`

**Verify before Phase 2:**
- Dashboard load time drops below 1s on repeated requests
- ML prediction endpoints respond in under 100ms
- Chat endpoint streams tokens instead of waiting 30s

---

### Phase 2 — Code Architecture Refactor (Days 6–10)
**Goal:** Restructure codebase to industry standard layered architecture.

Deliver:
- [ ] Full restructured `api/` with models/, schemas/, routes/, services/ layers
- [ ] `api/config.py` — Pydantic Settings with all env vars
- [ ] `api/services/` — market_service.py, pricing_service.py, llm_service.py
- [ ] Restructured `frontend/src/` — api/, hooks/, components/, dashboards/, types/
- [ ] TanStack Query installed and all useEffect fetches replaced with useQuery
- [ ] React.lazy() + Suspense + DashboardSkeleton applied to all 6 dashboards
- [ ] Full TypeScript migration with shared `types/` folder

**Verify before Phase 3:**
- All 6 dashboards load independently without triggering other dashboard fetches
- No TypeScript errors across the entire frontend
- Service layer has no direct DB imports (only via dependency injection)

---

### Phase 3 — LLM Upgrade + UI Polish (Days 11–15)
**Goal:** Make the AI Advisor production-ready and improve perceived performance.

Deliver:
- [ ] `api/services/llm_service.py` — Groq API async streaming client
- [ ] `llm/system_prompt` wired into Groq system message
- [ ] `frontend/src/dashboards/AIAdvisor.tsx` — SSE EventSource chat client
- [ ] Skeleton loaders for all 6 dashboards (perceived performance)
- [ ] PostgreSQL materialized views SQL: `market_kpis`, `monthly_trends`
- [ ] APScheduler job in `api/main.py` refreshing views every 6 hours
- [ ] Bash commands: `pip install groq apscheduler`

**Verify before Phase 4:**
- AI Advisor shows first token within 3 seconds
- Groq API key loads from environment variable correctly
- Materialized views return correct aggregated data
- Skeleton loaders appear instantly while data loads

---

### Phase 4 — Render Deployment (Days 16–20)
**Goal:** Full live deployment on Render.com.

Deliver:
- [ ] `render.yaml` — all 4 services defined
- [ ] `.github/workflows/deploy.yml` — CI/CD pipeline
- [ ] `api/routes/health.py` — `/health` + `/metrics` endpoints
- [ ] Vite `vite.config.ts` updated with production API proxy to Render URL
- [ ] ETL migration script adapted for Render PostgreSQL
- [ ] slowapi rate limiter applied to `/api/chat` endpoint
- [ ] Bash commands: `pip install slowapi`

**Verify before Phase 5:**
- All 6 dashboards load on live Render URL
- AI Advisor streams correctly via Groq on Render
- `/health` returns 200 and Render health checks pass
- GitHub push to `main` triggers automatic Render redeploy

---

### Phase 5 — Scale & Observability (Ongoing)
**Goal:** Add production monitoring and protection.

Deliver:
- [ ] Sentry integration (`pip install sentry-sdk`) — backend error tracking
- [ ] `structlog` structured logging — JSON logs visible in Render log tail
- [ ] Prometheus `/metrics` endpoint for API latency tracking
- [ ] Notes on when to upgrade: Render Standard plan ($25/mo) once user base grows
- [ ] Notes on PostgreSQL read replica for heavy analytics queries

---

### For Each Phase, Always Provide:

1. **All new and modified file contents** — complete code, no placeholders or `...`
2. **Bash install commands** — exact pip/npm commands needed
3. **SQL scripts** — any migrations, index creation, or view definitions
4. **What to test** — explicit checklist of what must pass before next phase
5. **What NOT to touch** — confirm which existing files remain unchanged


================================================================================
Qatar AI Platform — Architecture Analysis v1.0 | Feb 2026 | Confidential
================================================================================
