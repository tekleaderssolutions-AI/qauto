# Qatar Used Car Market — AI Intelligence Platform

End-to-end system from the **Qatar_AI_Platform_v3_Final** blueprint: ETL, ML pipelines (price predictor, risk scorer, demand forecaster, buyer matcher), FastAPI backend, and React frontend with 6 dashboards.

## Database: PostgreSQL (or SQLite)

- **PostgreSQL** (recommended): set `DATABASE_URL` before running ETL and API, e.g.  
  `export DATABASE_URL=postgresql://user:password@localhost:5432/qauto`  
  Create the database first: `createdb qauto`
- **SQLite** (dev fallback): if `DATABASE_URL` is not set, the app uses `qauto.db` in the project root.

## Quick start

### 1. Data & ETL

- Place your CSV/Excel files in `Data/` (see list below). The repo already includes:
  - `vehicle_inventory.csv`, `historical_sales.csv`, `customers.csv`, `purchase_orders.csv`, `competitor_pricing.csv`, `qatar_events_calendar.csv`
  - Sample: `Qatar_Economic_Indicators.csv`, `Qatar_Market_Reports.csv`
- Run ETL to load data into the database (PostgreSQL if `DATABASE_URL` is set, else SQLite):

```bash
# Optional: use PostgreSQL
# export DATABASE_URL=postgresql://user:password@localhost:5432/qauto

python etl/load_data.py
python etl/validate_data.py
```

### 2. Train ML models (optional but recommended for pricing)

```bash
pip install -r requirements.txt
python ml/price_predictor.py
```

### 3. Backend API

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:3000  
- Vite proxy forwards `/api` to the backend.

### 5. AI chat (Groq, optional)

- Set `GROQ_API_KEY` in your `.env` (see `.env.example`).
- The backend uses Groq's `llama-3.1-70b-versatile` model via the `/api/chat` and `/api/chat/stream` endpoints.
- Chat in the **AI Advisor** dashboard will call the Groq API with the platform system prompt.

## Project structure

```
qauto-platform/
├── Data/                    # CSV/Excel inputs
├── etl/                     # load_data.py, validate_data.py
├── ml/                      # price_predictor, risk_scorer, demand_forecaster, buyer_matcher
├── api/                     # FastAPI app + routes (pricing, inventory, market, matching, chat)
├── llm/                     # system_prompt.txt, Groq clients (sync + streaming)
├── frontend/                # React + Vite, 6 dashboards
├── qauto.db                 # SQLite (created by ETL)
└── requirements.txt
```

## Dashboards

1. **Market Hub** — KPIs, market health, monthly volume chart  
2. **Inventory Health** — Risk-scored inventory table with filters  
3. **Pricing Tool** — Car form → recommended price (QAR) and range  
4. **Market & Economics** — Oil, interest rate, confidence, upcoming events  
5. **Buyer Matching** — Ready buyers and top inventory matches  
6. **AI Advisor** — Chat with QAUTO-AI (Groq LLM + system prompt)

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/price` | Price prediction (make, model, trim, year, color, etc.) |
| GET | `/api/inventory` | Risk-scored inventory (optional filters) |
| GET | `/api/inventory/summary` | Counts by risk_flag |
| GET | `/api/market/kpis` | Market health, oil, interest rate, critical count, active buyers |
| GET | `/api/market/trends` | Monthly sales volume |
| GET | `/api/market/events` | Upcoming calendar events |
| GET | `/api/match/ready-buyers` | Customers with upgrade within 90 days |
| POST | `/api/match` | Matches for a given customer_id |
| GET | `/api/match/dashboard` | Ready buyers + top matches |
| POST | `/api/chat` | LLM chat (Groq) with dataset context |

## Datasets (10)

1. vehicle_inventory  
2. historical_sales  
3. customers  
4. purchase_orders  
5. competitor_pricing  
6. qatar_events_calendar  
7. Qatar_Market_Reports  
8. Qatar_Economic_Indicators  
9. social_media_trends (optional)  
10. google_trends_analysis (optional)  

ETL loads any of these that exist under `Data/` (CSV or Excel). Missing optional datasets are skipped.

## License

Confidential — Qatar AI Platform v1.0 (February 2026).
