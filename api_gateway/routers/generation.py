import json
import logging
import uuid

import pika
from fastapi import APIRouter, Depends, HTTPException
from opentelemetry.propagate import inject
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..database import GenerationRequest, get_db
from ..services import get_mq_channel
from ..tracing import tracer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Image Generation"])


class InferenceRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    seed: int = 50


class UpdateRequest(BaseModel):
    status: str
    image_url: str = None


# save request id to db, send request to message queue, return request id to user
@router.post("/generate", status_code=202)
def generate_task(
    request: InferenceRequest,
    db: Session = Depends(get_db),
    channel: pika.channel.Channel = Depends(get_mq_channel),
):
    with tracer.start_as_current_span("save_request_to_db") as db_span:
        db_request = GenerationRequest(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
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
        task_message = {
            "request_id": generated_request_id,
            "params": request.model_dump(),
        }
        with tracer.start_as_current_span("publish_to_rabbitmq") as pika_span:
            pika_span.set_attribute("messaging.destination", settings.QUEUE_NAME)
            pika_span.set_attribute("messaging.message.id", generated_request_id)

            carrier = {}
            TraceContextTextMapPropagator().inject(carrier)
            pika_span.add_event(
                "Injecting trace context into RabbitMQ message properties."
            )

            channel.basic_publish(
                exchange="",
                routing_key=settings.QUEUE_NAME,
                body=json.dumps(task_message),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE, headers=carrier
                ),
            )
            logger.info(
                "Published message to RabbitMQ",
                extra={"request_id": generated_request_id},
            )
    except Exception as e:
        current_span = tracer.get_current_span()
        current_span.record_exception(e)
        current_span.set_status(
            tracer.Status(tracer.StatusCode.ERROR, "Failed to publish message")
        )

        logger.error(
            "Error publishing to RabbitMQ",
            extra={"request_id": generated_request_id},
            exc_info=True,
        )
        db.query(GenerationRequest).filter(
            GenerationRequest.request_id == db_request.request_id
        ).update({"status": "Failed"})
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to queue the request")

    return {"request_id": str(generated_request_id)}


# user send request_id to check status, if completed, return image url
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
