"""Celery application configuration.

Uses Redis as broker and result backend. In dev mode (SIMULATION_SYNC=true),
tasks are not dispatched via Celery; the service runs them synchronously.
"""

from __future__ import annotations

from app.core.config import settings

try:
    from celery import Celery

    celery_app = Celery(
        "aftermind",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_soft_time_limit=300,  # 5 min soft timeout
        task_time_limit=600,  # 10 min hard timeout
        task_max_retries=2,
        task_default_retry_delay=5,
    )

except ImportError:
    # Celery not available — sync mode will be used
    celery_app = None
