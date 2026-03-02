from typing import Callable, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.routes.inventory import inventory_summary
from api.routes.market import market_kpis, market_analysis
from api.db_maintenance import ensure_indexes, ensure_materialized_views, refresh_materialized_views


def create_scheduler() -> AsyncIOScheduler:
    """Create an APScheduler instance with cache-warming and maintenance jobs."""
    scheduler = AsyncIOScheduler()

    def safe(job: Callable[[], Any], name: str) -> None:
        try:
            job()
        except Exception:
            # Logging is configured centrally; avoid hard dependency here.
            pass

    # One-time index and materialized view creation shortly after startup
    scheduler.add_job(
        lambda: safe(ensure_indexes, "ensure_indexes"),
        "date",
        id="ensure_indexes_once",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: safe(ensure_materialized_views, "ensure_materialized_views"),
        "date",
        id="ensure_materialized_views_once",
        replace_existing=True,
    )

    # Warm key Redis-backed caches every 5–10 minutes
    scheduler.add_job(
        lambda: safe(inventory_summary, "inventory_summary"),
        "interval",
        minutes=5,
        id="warm_inventory_summary",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: safe(market_kpis, "market_kpis"),
        "interval",
        minutes=5,
        id="warm_market_kpis",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: safe(lambda: market_analysis(limit=20), "market_analysis"),
        "interval",
        minutes=10,
        id="warm_market_analysis",
        replace_existing=True,
    )

    # Refresh materialized views every 6 hours
    scheduler.add_job(
        lambda: safe(refresh_materialized_views, "refresh_materialized_views"),
        "interval",
        hours=6,
        id="refresh_materialized_views",
        replace_existing=True,
    )

    return scheduler

