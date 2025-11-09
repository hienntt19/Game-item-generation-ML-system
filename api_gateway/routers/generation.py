import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..celery_worker import generate_image_task
from ..config import settings
from ..database import GenerationRequest, get_db
from ..tracing import tracer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Image Generation"])


class InferenceRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    seed: int = 50


@router.post("/generate", status_code=202)
def generate_task(
    request: InferenceRequest,
    db: Session = Depends(get_db),
):
    with tracer.start_as_current_span("save_request_to_db") as db_span:
        db_request = GenerationRequest(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
            status="Queued",
        )
        db.add(db_request)
        db.commit()
        db.refresh(db_request)

        generated_request_id = str(db_request.request_id)
        db_span.set_attribute("db.request_id", generated_request_id)
        logger.info(
            "Saved request to database", extra={"request_id": generated_request_id}
        )

    try:
        with tracer.start_as_current_span("dispatch_celery_task"):
            generate_image_task.delay(
                request_id=generated_request_id, params=request.model_dump()
            )

            logger.info(
                "Dispatched task to Celery",
                extra={"request_id": generated_request_id},
            )
    except Exception as e:
        current_span = tracer.get_current_span()
        current_span.record_exception(e)
        current_span.set_status(
            tracer.Status(tracer.StatusCode.ERROR, "Failed to publish message")
        )

        logger.error(
            "Error dispatching task to Celery",
            extra={"request_id": generated_request_id},
            exc_info=True,
        )
        db.query(GenerationRequest).filter(
            GenerationRequest.request_id == db_request.request_id
        ).update({"status": "Failed"})
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to queue the request")

    return {"request_id": str(generated_request_id)}


@router.get("/status/{request_id}")
def get_status(request_id: str, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("get_request_status") as span:
        span.set_attribute("http.request.param.request_id", request_id)
        logger.info("Checking status for request", extra={"request_id": request_id})
        try:
            request_uuid = uuid.UUID(request_id)
        except ValueError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid UUID format"))
            raise HTTPException(status_code=400, detail="Invalid request_id format")

        db_request = (
            db.query(GenerationRequest)
            .filter(GenerationRequest.request_id == request_uuid)
            .first()
        )

        if not db_request:
            raise HTTPException(status_code=404, detail="request_id not found")

        response_data = {
            "request_id": str(db_request.request_id),
            "status": db_request.status,
        }

        if db_request.status == "Completed":
            response_data["image_url"] = db_request.image_url

        return response_data
