from celery import Celery

from .config import settings

celery_app = Celery(
    "image_generation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["api_gateway.celery_worker"],
)

celery_app.conf.task_default_queue = settings.CELERY_TASK_DEFAULT_QUEUE


@celery_app.task
def generate_image_task(request_id: str, params: dict):
    pass
