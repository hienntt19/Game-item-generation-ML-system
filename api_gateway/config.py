import logging
import os
from typing import Any, Dict

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_USER: str = os.getenv("RABBITMQ_DEFAULT_USER", "user")
    RABBITMQ_PASS: str = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
    QUEUE_NAME: str = "image_generation_queue"
    RESULTS_QUEUE_NAME: str = "image_results_queue"

    DATABASE_URL: str = (
        "postgresql://hienntt19:whN7wg7ecQlNJ2kcvYhT@/image_requests?host=/cloudsql/game-item-generation:asia-southeast1:game-item-generation-service-db"
    )

    APP_TITLE: str = "API Gateway for Game Item Generation"
    APP_DESCRIPTION: str = "Accepts requests and queues them for processing"
    APP_VERSION: str = "1.0.0"

    OTEL_SERVICE_NAME: str = "api-gateway"
    JAEGER_AGENT_HOST: str = "localhost"
    JAEGER_AGENT_PORT: int = 6831

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
