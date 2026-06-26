"""CondoBuddy2 Core — Application Configuration."""
import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_KEY = "change-me-in-production-condobuddy2-secret-key-2024"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    app_name: str = "CondoBuddy2 Core"
    app_version: str = "2.0.0"
    debug: bool = False

    # Database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://condobuddy:condobuddy@postgres:5432/condobuddy2"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # Security
    secret_key: str = _INSECURE_DEFAULT_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day

    # CORS — comma-separated origins; default restricts to local dev only
    cors_allowed_origins: str = "http://localhost:8080,http://localhost:3000"

    # Internal service shared secret for webhook / device endpoints
    internal_api_key: str = ""

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "condobuddy2"
    minio_secure: bool = False

    # Frappe Bridge
    frappe_base_url: str = "http://frappe:8080"
    frappe_api_key: str = ""
    frappe_api_secret: str = ""

    # NVR
    nvr_base_url: str = "http://nvr-connector:8001"

    # MQTT (IoT Sensors)
    mqtt_broker_host: str = "mqtt"
    mqtt_broker_port: int = 1883

    # CCTV
    cctv_stream_timeout: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    def validate_secret_key(self) -> None:
        """Warn loudly when the default insecure key is still in use."""
        if self.secret_key == _INSECURE_DEFAULT_KEY and not self.debug:
            import warnings
            warnings.warn(
                "SECURITY: SECRET_KEY is set to the insecure default. "
                "Set a strong, unique SECRET_KEY environment variable before deploying.",
                stacklevel=2,
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
