import logging.config
from logging.config import dictConfig

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .routers import generation
from .tracing import setup_tracing

dictConfig(settings.LOGGING_CONFIG)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

setup_tracing(app)
Instrumentator().instrument(app).expose(app)
app.include_router(generation.router)


@app.get("/")
def read_root():
    return {"status": "ok"}
