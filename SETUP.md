# Qatar AI Platform — Setup

## 1. Backend

```bash
# From project root
pip install -r requirements.txt
```

Set env (or use `.env`). **PostgreSQL is required** (no SQLite):

- **DATABASE_URL** = `postgresql://postgres:PASSWORD@localhost:5432/qauto`  
  If your password contains `@`, encode it as `%40` (e.g. `srikanthSs%401`).
- Or use: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- **REDIS_URL** (optional, recommended for production): `redis://localhost:6379`
- **GROQ_API_KEY** (optional): from [console.groq.com](https://console.groq.com); AI Advisor uses Ollama if unset.

Run API:

```bash
uvicorn api.main:app --reload --port 8000
```

## 2. Frontend (fix "@tanstack/react-query" error)

The app uses **TanStack React Query**. Install dependencies once:

**Option A — Double‑click (Windows)**  
Open `frontend` folder and run **`install-deps.bat`**.

**Option B — Terminal**

```powershell
cd frontend
npm install
npm run dev
```

Then open the URL shown (e.g. http://localhost:5173).  
If you see "Failed to resolve import @tanstack/react-query", run `npm install` inside the `frontend` folder and restart `npm run dev`.

## 3. Database indexes (PostgreSQL)

```bash
psql $DATABASE_URL -f scripts/migrations/001_add_indexes.sql
```

## 4. ETL (load data)

```bash
# Set DB_* or DATABASE_URL first
python etl/load_data.py
```

## 5. Train price model (optional)

```bash
cd ml
python price_predictor.py
```
