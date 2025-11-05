import logging.config
import threading
from contextlib import asynccontextmanager
from logging.config import dictConfig

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .result_consumer import ResultConsumer
from .routers import generation
from .services import rabbitmq_manager

dictConfig(settings.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

result_consumer = ResultConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not rabbitmq_manager.connect():
        logger.critical("Application startup failed: Could not connect to RabbitMQ.")
    result_consumer.start()
    yield
    rabbitmq_manager.close()
    result_consumer.stop()


app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)
app.include_router(generation.router)


@app.get("/")
def read_root():
    return {"status": "ok"}
