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

from api_gateway.database import SessionLocal
from api_gateway.models import GenerationRequest
    
    
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


app = FastAPI(
    title="Image Generation API gateway",
    description="Acceptes requests and queue them for processing",
    version="1.0.0"
)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_DEFAULT_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_DEFAULT_PASS", "password")
QUEUE_NAME = "image_generation_queue"


# save request id to db, send request to message queue, return request id to user
@app.post("/generate", status_code=202)
def generate_task(request: InferenceRequest, db: Session = Depends(get_db)):
    """
    Accepts an inference request, saves it to database, and pushes it to message queue
    Returns a request_id for status polling
    """
    
    # request_id = str(uuid.uuid4())
    
    db_request = GenerationRequest(
        # request_id=request_id,
        prompt = request.prompt,
        negative_prompt = request.negative_prompt,
        num_inference_steps = request.num_inference_steps,
        guidance_scale = request.guidance_scale,
        seed = request.seed
    )
    
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    # print(f"Save request {request_id} to database")
    generated_request_id = str(db_request.request_id)
    print(f"Saved request {generated_request_id} to database")
    
    
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        
        task_message = {
            "request_id": generated_request_id,
            "params": request.dict()
        }
    
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(task_message),
            properties=pika.BasicProperties(delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE)
        )
        
        connection.close()
    
    except Exception as e:
        print(f"Error publishing to RabbitMQ: {e}")
        db.query(GenerationRequest).filter(GenerationRequest.request_id == db_request.request_id).update({"status": "Failed"})
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to queue the request")
    
    
    return {"request_id": str(generated_request_id)}
    

# user send request_id to check status, if completed, return image url
@app.get("/status/{request_id}")
def get_status(request_id: str, db: Session = Depends(get_db)):
    print(f"Checking status for request {request_id}")
    
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
    print(f"Updated status for request {request_id} to {update_data.status}")
    
    return {"message": "Status updated successfully"}
    