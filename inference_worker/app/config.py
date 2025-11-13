import logging
import os
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from pythonjsonlogger import jsonlogger
from pydantic import computed_field


class Settings(BaseSettings):
    RABBITMQ_HOST: str
    RABBITMQ_DEFAULT_USER: str
    RABBITMQ_DEFAULT_PASS: str
    
    DATABASE_URL: str

    API_GATEWAY_URL: str

    GCS_BUCKET_NAME: str
    GOOGLE_APPLICATION_CREDENTIALS: str = "gcs-key.json"

    LORA_PATH: str = "models/lora-tsuki-epoch-20/lora_adapter.safetensors"
    BASE_MODEL_PATH: str = "models/stable-diffusion-v1-5"
    IMAGES_PATH: str = "images"

    OTEL_SERVICE_NAME: str = "inference-worker"
    JAEGER_COLLECTOR_HOST: str
    
    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS}@{self.RABBITMQ_HOST}:5672//"
        
    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"rpc://{self.RABBITMQ_DEFAULT_USER}:{self.RABBITMQ_DEFAULT_PASS}@{self.RABBITMQ_HOST}:5672//"
    
    CELERY_TASK_DEFAULT_QUEUE: str  = "generation_tasks"

    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def setup_logging():
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    logHandler.setFormatter(formatter)

    logging.basicConfig(handlers=[logHandler], level=logging.INFO)

    logging.getLogger("pika").setLevel(logging.WARNING)


settings = get_settings()
