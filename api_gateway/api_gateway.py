from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import os
import pika
import json
import uuid
from sqlalchemy import create_engine, Column, String, Text, Integer, Float, BigInteger, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from contextlib import asynccontextmanager
import logging 
import logging.config

from api_gateway.database import SessionLocal
from api_gateway.models import GenerationRequest
from api_gateway.tracing import setup_tracing
from api_gateway.logging_config import LOGGING_CONFIG

from prometheus_fastapi_instrumentator import Instrumentator


logger = logging.getLogger(__name__)

class RabbitMQManager:
    def __init__(self, host, user, password, queue_name):
        self.host = host
        self.user = user
        self.password = password
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
    
    def _is_connection_open(self):
        return (self.connection and self.connection.is_open and
                self.channel and self.channel.is_open)
        
    
    def connect(self):
        if self._is_connection_open():
            logger.debug("Connection is already open.")
            return True
        try:
            logger.info("Attempting to connect to RabbitMQ...")
            credentials = pika.PlainCredentials(self.user, self.password)
            params = pika.ConnectionParameters(
                host=self.host,
                credentials=credentials,
                heartbeat=60,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            self.channel.confirm_delivery()
            
            logger.info("RabbitMQ connection and channel established successfully!")
            return True
        
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            return False
            
    def get_channel(self):
        if self._is_connection_open():
            return self.channel
        
        logger.warning("RabbitMQ connection is closed or not established. Attempting to connect.")
        if self.connect():
            return self.channel
        else:
            logger.critical("Could not re-establish connection to RabbitMQ.")
            return None
        
    def close(self):
        if self.connection and self.connection.is_open:
            logger.info("Closing RabbitMQ connection...")
            self.connection.close()
            logger.info("RabbitMQ connection closed.")   

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_DEFAULT_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
QUEUE_NAME = "image_generation_queue"

rabbitmq_manager = RabbitMQManager(RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS, QUEUE_NAME)     

def get_mq_channel():
    channel = rabbitmq_manager.get_channel()
    if not channel:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: Cannot connect to message queue"
        )
    return channel


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    rabbitmq_manager.close()


app = FastAPI(
    title="Image Generation API Gateway",
    description="Acceptes requests and queue them for processing",
    version="1.0.0",
    lifespan = lifespan
)

Instrumentator().instrument(app).expose(app)
setup_tracing(app)
    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class InferenceRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    num_inference_steps: int = 50
    guidance_scale: float = 7.5
    seed: int = 50


# save request id to db, send request to message queue, return request id to user
@app.post("/generate", status_code=202)
def generate_task(request: InferenceRequest, db: Session = Depends(get_db), channel: pika.channel.Channel = Depends(get_mq_channel)):
    """
    Accepts an inference request, saves it to database, and pushes it to message queue
    Returns a request_id for status polling
    """    
    db_request = GenerationRequest(
        prompt = request.prompt,
        negative_prompt = request.negative_prompt,
        num_inference_steps = request.num_inference_steps,
        guidance_scale = request.guidance_scale,
        seed = request.seed
    )
    
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    generated_request_id = str(db_request.request_id)
    logger.info(
        "Saved request to database", 
        extra={"request_id": generated_request_id}
    )
    
    try:
        task_message = {
            "request_id": generated_request_id,
            "params": request.model_dump()
        }
    
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(task_message),
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
        )
            
    except Exception as e:
        logger.error(
            "Error publishing to RabbitMQ",
            extra={"request_id": generated_request_id},
            exc_info=True
        )
        db.query(GenerationRequest).filter(GenerationRequest.request_id == db_request.request_id).update({"status": "Failed"})
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to queue the request")
    
    
    return {"request_id": str(generated_request_id)}
    

# user send request_id to check status, if completed, return image url
@app.get("/status/{request_id}")
def get_status(request_id: str, db: Session = Depends(get_db)):
    logger.info(
        "Checking status for request",
        extra={"request_id": request_id}
    )
    
    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request_id format")

    db_request = db.query(GenerationRequest).filter(GenerationRequest.request_id == request_uuid).first()
    
    if not db_request:
        raise HTTPException(status_code=404, detail="request_id not found")
    
    response_data = {
        "request_id": str(db_request.request_id),
        "status": db_request.status
    }
    
    if db_request.status == "Completed":
        response_data["image_url"] = db_request.image_url
    
    return response_data


class UpdateRequest(BaseModel):
    status: str
    image_url: str = None


# Inference service call to update database
@app.put("/update_db/{request_id}")
def update_db(request_id: str, update_data: UpdateRequest, db: Session = Depends(get_db)):
    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request_id format")
    
    db_request = db.query(GenerationRequest).filter(GenerationRequest.request_id == request_uuid).first()
    
    if not db_request:
        raise HTTPException(status_code=404, detail="request_id not found")
    
    db_request.status = update_data.status
    if update_data.image_url:
        db_request.image_url = update_data.image_url
        
    db.commit()
    logger.info(
        "Updated status for request to status",
        extra={"request_id": request_id, "status": update_data.status}
    )
    
    return {"message": "Status updated successfully"}
    