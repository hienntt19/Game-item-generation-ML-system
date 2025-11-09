import logging
import os
from typing import Any, Dict

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    RABBITMQ_HOST: str
    RABBITMQ_USER: str
    RABBITMQ_PASS: str

    DATABASE_URL: str = (
        "postgresql://hienntt19:whN7wg7ecQlNJ2kcvYhT@/image_requests?host=/cloudsql/game-item-generation:asia-southeast1:game-item-generation-service-db"
    )
    DATABASE_PASS: str

    APP_TITLE: str = "API Gateway for Game Item Generation"
    APP_DESCRIPTION: str = "Accepts requests and queues them for processing"
    APP_VERSION: str = "1.0.0"

    OTEL_SERVICE_NAME: str
    JAEGER_AGENT_HOST: str
    JAEGER_AGENT_PORT: int

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:5672//"

    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"rpc://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}:5672//"

    CELERY_TASK_DEFAULT_QUEUE: str = "generation_tasks"

    LOG_LEVEL: str = "INFO"
    JSON_FORMAT: str = (
        "%(timestamp)s %(levelname)s %(message)s "
        "%(otelTraceID)s %(otelSpanID)s %(otelServiceName)s"
    )

    @property
    def LOGGING_CONFIG(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": self.JSON_FORMAT,
                    "rename_fields": {"levelname": "level", "asctime": "timestamp"},
                },
            },
            "handlers": {
                "default": {
                    "formatter": "json",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": self.LOG_LEVEL,
                    "propagate": True,
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": self.LOG_LEVEL,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": self.LOG_LEVEL,
                    "propagate": False,
                },
            },
        }

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
