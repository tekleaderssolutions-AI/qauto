"""
Qatar Used Car Market — AI Intelligence Platform API.
FastAPI app: pricing, inventory, market, matching, chat.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.middleware import SlowAPIMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.routes import pricing, inventory, market, matching, chat, competitors
from api.ml_models import ModelRegistry
from api.limiter import limiter
from api.config import get_settings
from api.logging_config import configure_logging
from api.scheduler import create_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging, Sentry, models, scheduler at startup
    settings = get_settings()
    configure_logging(debug=settings.debug)

    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration()],
            environment=settings.environment,
            traces_sample_rate=0.1,
        )

    ModelRegistry.load_all()

    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown(wait=False)


settings = get_settings()

app = FastAPI(
    title="Qatar AI Platform API",
    description="Used car market intelligence: pricing, inventory risk, demand, buyer matching, AI chat",
    version="1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)

app.include_router(pricing.router)
app.include_router(inventory.router)
app.include_router(market.router)
app.include_router(matching.router)
app.include_router(chat.router)
app.include_router(competitors.router)

# Serve React frontend (built by: cd frontend && npm install && npm run build)
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        """Catch-all: serve React index.html for any non-API route."""
        return FileResponse(_frontend_dist / "index.html")


@app.get("/")
def root():
    return {"service": "Qatar AI Platform", "docs": "/docs", "health": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics(request: Request) -> PlainTextResponse:
    """Prometheus metrics endpoint."""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    data = generate_latest()
    return PlainTextResponse(
        content=data.decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
