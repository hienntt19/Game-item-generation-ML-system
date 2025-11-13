import logging
import uuid

from celery import Celery
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal, GenerationRequest
from processing import load_model_and_dependencies, process_image_request
from tracing import setup_tracing

setup_tracing()

logger = logging.getLogger(__name__)

celery_app = Celery(
    "api_gateway.celery_worker",
    broker = settings.CELERY_BROKER_URL,
    backend = settings.CELERY_RESULT_BACKEND
)
celery_app.conf.task_default_queue = settings.CELERY_TASK_DEFAULT_QUEUE

logging.info("Load models and dependencies...")
try:
    pipe, device, gcs_bucket = load_model_and_dependencies()
    logger.info("Model and dependencies loaded successfully!")
except Exception as e:
    logger.critical("Can't load models, worker can't process tasks", exc_info=True)
    pipe, device, gcs_bucket = None, None, None

@celery_app.task(bind=True)
def generate_image_task(self, request_id: str, params: dict):
    if not pipe:
        logger.error("Model is not loaded, cannot process the request", extra = {"request_id": request_id})
        raise Exception("Model is not loaded")
    
    logger.info("Processing image generation request", extra = {"request_id": request_id})
    db: Session = SessionLocal()
    
    try:
        request_uuid = uuid.UUID(request_id)
        
        db.query(GenerationRequest).filter(GenerationRequest.request_id == request_uuid).update({
            "status": "Processing", "celery_task_id": self.request.id
        })
        db.commit()
        logger.info("Update request status to Processing", extra = {"request_id": request_id})
        
        image_url = process_image_request(
            pipe=pipe, 
            device=device, 
            gcs_bucket=gcs_bucket, 
            request_id=request_id,
            params=params
        )
        
        if image_url is None:
            raise Exception("Image generation failed, image_url is none")
        
        db.query(GenerationRequest).filter(GenerationRequest.request_id == request_uuid).update({
            "status": "Completed", "image_url": image_url
        })
        db.commit()
        logger.info("Image generation completed successfully", extra = {"request_id": request_id})
        
        return {
            "status": "Completed",
            "image_url": image_url
        }
    except Exception as e:
        logger.error("Error processing image generation request", exc_info=True, extra = {"request_id": request_id})
        
        db.query(GenerationRequest).filter(GenerationRequest.request_id == request_uuid).update({
            "status": "Failed"
        })
        db.commit() 
        
        raise e
    finally:
        db.close()  