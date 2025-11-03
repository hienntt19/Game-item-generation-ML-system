import torch
from diffusers import StableDiffusionPipeline, DDIMScheduler
import os
from safetensors.torch import load_file
import pika
import json 
import time
import requests
from google.cloud import storage
import uuid
from dotenv import load_dotenv
import logging
from pythonjsonlogger import jsonlogger
import sys

from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from tracing import setup_tracing, tracer

load_dotenv()

setup_tracing()

logHandler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s')
logHandler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_USER = os.getenv("RABBITMQ_DEFAULT_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_DEFAULT_PASS")
QUEUE_NAME = "image_generation_queue"

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcs-key.json"

LORA_PATH = os.path.join("models", "lora-tsuki-epoch-20", "lora_adapter.safetensors")
IMAGES_PATH = "images"
MODEL_ID = "models/stable-diffusion-v1-5"

os.makedirs(IMAGES_PATH, exist_ok=True)

def update_status(request_id, status, image_url=None):
    with tracer.start_as_current_span("call_update_db_api") as span:
        span.set_attribute("request_id", request_id)
        span.set_attribute("update_status", status)
    
        if not API_GATEWAY_URL:
            logger.info("API_GATEWAY_URL is not set. Skipping status update.")
            return
        
        endpoint = f"{API_GATEWAY_URL}/update_db/{request_id}"
        
        payload = {
            "status": status
        }
        if image_url:
            payload["image_url"] = image_url
        
        try:
            response = requests.put(endpoint, json=payload)
            response.raise_for_status()
            logger.info(
                "Status updated for request_id",
                extra={'request_id': request_id, 'status': status}           
            )
        except requests.exceptions.RequestException as e:
            logger.error(
                "Failed to update status for request_id",
                extra={'request_id': request_id, 'error': str(e)}
            )


def upload_to_gcs(source_file_path, request_id):
    with tracer.start_as_current_span("upload_image_to_gcs") as span:
        span.set_attribute("request_id", request_id)
        span.set_attribute("bucket_name", GCS_BUCKET_NAME)
        if not GCS_BUCKET_NAME:
            logger.info("GCS_BUCKET_NAME is not set. Skipping upload to GCS.")
            return None
        
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            
            destination_blob_name = f"generated/{request_id}.png"
            blob = bucket.blob(destination_blob_name)
            
            blob.upload_from_filename(source_file_path)
            
            span.set_attribute("public_url", blob.public_url)
            logger.info(
                "File uploaded in bucket with Public URL",
                extra={'request_id': request_id, 
                    'destination': destination_blob_name,
                    'GCS_BUCKET_NAME': GCS_BUCKET_NAME,
                    'public URL': blob.public_url
                }
            )
            return blob.public_url
    
        except Exception as e:
            span.record_exception(e)
            logger.error(
                "Failed to upload file to GCS",
                extra={'request_id': request_id, 'error': str(e)}
            )
            return None


def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    
    logger.info("Loading pipeline on device...", extra={'device': device})
    
    pipe = StableDiffusionPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False
    )
    
    logger.info("Loading and setting DDIMScheduler...")
    scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
    pipe.scheduler = scheduler

    pipe.to(device)

    logger.info("Loading lora weights from path...", extra={'LORA_PATH': LORA_PATH})
    if not os.path.exists(LORA_PATH):
        logger.info("CRITICAL: Lora file not found at path inside the container!", extra={'LORA_PATH': LORA_PATH})
        return
        
    pipe.load_lora_weights(LORA_PATH)
    logger.info("Lora loaded successfully.")
    
    return pipe, device


def generate_and_upload_image(pipe, device, request_id, params):
    with tracer.start_as_current_span("stable_diffusion_inference_and_upload") as span:
        span.set_attribute("request_id", request_id)
    
        prompt = params.get("prompt")
        negative_prompt = params.get("negative_prompt")
        num_inference_steps = int(params.get("num_inference_steps", 50))
        guidance_scale = float(params.get("guidance_scale", 7.5))
        seed = int(params.get("seed", 50))
        
        if not prompt:
            raise ValueError("Prompt is required for image generation.")
    
        logger.info(
            "Generating image with seed...",
            extra={'request_id': request_id, 'seed': seed}
        )
        
        with tracer.start_as_current_span("run_sd_pipeline") as inference_span:
            inference_span.set_attribute("prompt", prompt)
            inference_span.set_attribute("seed", seed)
            inference_span.set_attribute("steps", num_inference_steps)
    
            generator = torch.Generator(device=device).manual_seed(seed)
            
            image = pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator,
                cross_attention_kwargs={"scale": 1.0}
            ).images[0]
    
        local_output_path = os.path.join(IMAGES_PATH, f"{request_id}.png")
        image.save(local_output_path)
        
        logger.info(
            "Image saved locally to output...",
            extra={'request_id': request_id, 'local_output_path': local_output_path}
        )
        
        image_url = upload_to_gcs(local_output_path, request_id)
    
        try: os.remove(local_output_path)
        except OSError as e: logger.error("Error removing temporary file", extra={'request_id': request_id, 'error': str(e)})
        return image_url


def on_message_callback(ch, method, properties, body, pipe, device):
    request_id = None
    
    carrier = properties.headers if properties.headers else {}
    ctx = TraceContextTextMapPropagator().extract(carrier=carrier)
    
    try:
        message = json.loads(body.decode('utf-8'))
        request_id = message.get("request_id")
        
        with tracer.start_as_current_span("process_inference_request", context=ctx) as parent_span:
            parent_span.set_attribute("messaging.system", "rabbitmq")
            parent_span.set_attribute("messaging.destination", QUEUE_NAME)
            
            if request_id:
                parent_span.set_attribute("request_id", request_id)
            
        
            params = message.get("params")
        
            if not request_id or not params: raise ValueError("Invalid message format.")
        
            logger.info(
                "Received message...",
                extra={'request_id': request_id, 'payload': message}
            )
            
            update_status(request_id, "processing")
            
            image_url = generate_and_upload_image(pipe, device, request_id, params)
            
            if image_url:
                update_status(request_id, "Completed", image_url=image_url)
                logger.info("Task completed successfully.", extra={'request_id': request_id}) 
            else:
                logger.info("Upload failed, updating status to 'failed'.", extra={'request_id': request_id})
                update_status(request_id, "failed")
        
            ch.basic_ack(delivery_tag=method.delivery_tag)  
        
    except Exception as e:
        current_span = trace.get_current_span()
        if current_span.is_recording():
            current_span.record_exception(e)
            current_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        
        logger.error(
            "Error processing message",
            extra={'request_id': request_id, 'error': str(e)}    
        )
        
        if request_id: update_status(request_id, "failed")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
        logger.info("Task failed and acknowledged.", extra={'request_id': request_id})
    finally:
        try:
            trace.get_tracer_provider().force_flush()
            logger.info("Spans flushed successfully.", extra={'request_id': request_id})
        except Exception as e:
            logger.error("Failed to flush spans", extra={'request_id': request_id, 'error': str(e)})

def main():
    pipe, device = load_model()
    if pipe is None: return
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials, heartbeat=600))
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1)
            on_message_with_args = lambda ch, method, properties, body: on_message_callback(ch, method, properties, body, pipe, device)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message_with_args, auto_ack=False)
            logger.info('--> Connected to RabbitMQ. Waiting for messages...')
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError as e:
            logger.error("Connection to RabbitMQ failed: Retrying in 10 seconds...", extra={'error': str(e)})
            time.sleep(10)
        except Exception as e:
            logger.error("An unexpected error occurred: Restarting consumer...", extra={'error': str(e)})
            time.sleep(10)

if __name__ == "__main__":
    main()