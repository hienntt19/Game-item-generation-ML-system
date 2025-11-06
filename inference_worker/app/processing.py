import logging
import os

import torch
from diffusers import DDIMScheduler, StableDiffusionPipeline
from google.cloud import storage

from config import settings
from tracing import tracer

logger = logging.getLogger(__name__)


def load_model_and_dependencies():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    logger.info(
        "Loading pipeline on device...", extra={"device": device, "dtype": str(dtype)}
    )

    pipe = StableDiffusionPipeline.from_pretrained(
        settings.BASE_MODEL_PATH,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    )

    logger.info("Loading and setting DDIMScheduler...")
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
    pipe.to(device)

    if os.path.exists(settings.LORA_PATH):
        logger.info("Loading LoRA weights", extra={"path": settings.LORA_PATH})
        pipe.load_lora_weights(settings.LORA_PATH)
    else:
        logger.critical("LoRA file not found", extra={"path": settings.LORA_PATH})

    logger.info("Model loaded successfully.")

    gcs_bucket = None
    if settings.GCS_BUCKET_NAME:
        try:
            storage_client = storage.Client()
            gcs_bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
            logger.info("GCS client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
    else:
        logger.warning("GCS_BUCKET_NAME not set. GCS uploader will be disabled.")

    os.makedirs(settings.IMAGES_PATH, exist_ok=True)

    return pipe, device, gcs_bucket


def _upload_to_gcs(gcs_bucket, source_file_path: str, request_id: str) -> str | None:
    if not gcs_bucket:
        logger.info("Skipping upload to GCS as bucket is not configured.")
        return None

    with tracer.start_as_current_span("upload_image_to_gcs") as span:
        span.set_attribute("request_id", request_id)
        try:
            destination_blob_name = f"generated/{request_id}.png"
            blob = gcs_bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_path)

            logger.info(
                "File uploaded to GCS",
                extra={"request_id": request_id, "url": blob.public_url},
            )
            return blob.public_url
        except Exception as e:
            span.record_exception(e)
            logger.error(
                "Failed to upload file to GCS",
                extra={"request_id": request_id, "error": str(e)},
            )
            return None


def process_image_request(
    pipe, device, gcs_bucket, request_id: str, params: dict
) -> str | None:
    with tracer.start_as_current_span("stable_diffusion_inference_and_upload") as span:
        span.set_attribute("request_id", request_id)

        prompt = params.get("prompt")
        seed = int(params.get("seed", 50))
        if not prompt:
            raise ValueError("Prompt is required.")

        logger.info("Generating image", extra={"request_id": request_id, "seed": seed})

        generator = torch.Generator(device=device).manual_seed(seed)
        image = pipe(
            prompt=prompt,
            negative_prompt=params.get("negative_prompt"),
            num_inference_steps=int(params.get("num_inference_steps", 50)),
            guidance_scale=float(params.get("guidance_scale", 7.5)),
            generator=generator,
            cross_attention_kwargs={"scale": 1.0},
        ).images[0]

        local_path = os.path.join(settings.IMAGES_PATH, f"{request_id}.png")
        image.save(local_path)
        logger.info(
            "Image saved locally", extra={"request_id": request_id, "path": local_path}
        )

        image_url = _upload_to_gcs(gcs_bucket, local_path, request_id)

        try:
            os.remove(local_path)
        except OSError as e:
            logger.error(
                "Error removing temp file",
                extra={"request_id": request_id, "error": str(e)},
            )

        return image_url
