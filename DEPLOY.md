# Deploy to Render

## 1. PostgreSQL

- Create a **PostgreSQL** database in Render (Dashboard → New → PostgreSQL).
- Copy the **Internal Database URL** (or **External** if your app is not on Render).
- In your **qatar-api** service, add env var:
  - **Key:** `DATABASE_URL`
  - **Value:** paste the connection string (Render can also link it via “fromDatabase” in `render.yaml`).

## 2. Redis URL (production cache)

- In Render Dashboard: **New → Redis**. Create a Redis instance (e.g. **qatar-cache**).
- Open the Redis service → **Info** or **Connect**.
- Copy the **Internal Redis URL** (e.g. `redis://red-xxxx:6379`).
- In your **qatar-api** service, add env var:
  - **Key:** `REDIS_URL`
  - **Value:** paste the Internal Redis URL.

If you use the repo’s `render.yaml`, `REDIS_URL` is already wired from the Redis service:

```yaml
- key: REDIS_URL
  fromService:
    type: redis
    name: qatar-cache
    property: connectionString
```

So you only need to create a Redis service named **qatar-cache** and deploy; Render will inject `REDIS_URL` automatically.

## 3. Groq API key

- Get a key from [console.groq.com](https://console.groq.com).
- In **qatar-api** service → **Environment**:
  - **Key:** `GROQ_API_KEY`
  - **Value:** your key (mark as **Secret** in Render).
- Do **not** commit the key to git; set it only in Render (and in local `.env` if you use it there).

## Summary

| Variable       | Where to set it | Notes |
|----------------|-----------------|--------|
| `DATABASE_URL` | Render → qatar-api → Environment (or from linked DB) | Required. |
| `REDIS_URL`    | Render → qatar-api → Environment (or from linked Redis) | Use Internal Redis URL. |
| `GROQ_API_KEY` | Render → qatar-api → Environment (Secret) | Optional; Ollama used if unset. |
