"""Celery application for CondoBuddy2 Core background tasks.

The Celery worker is started with ``celery -A app.tasks worker``; Celery
therefore looks for a module-level ``celery`` (or ``app``) instance here.
"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "condobuddy2",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

# Backwards/compat alias so `celery -A app.tasks` works regardless of the
# attribute name Celery probes for.
app = celery


@celery.task(name="health.ping")
def ping() -> str:
    """Trivial task used to verify the worker is alive."""
    return "pong"
