import logging
import os

import wandb
from diffusers import StableDiffusionPipeline
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def download_lora_from_wandb(artifact_path: str, output_dir: str, wandb_project: str):
    logging.info(f"Starting download of W&B artifact '{artifact_path}'...")

    os.makedirs(output_dir, exist_ok=True)

    run = None

    try:
        run = wandb.init(project=wandb_project, job_type="model_download")

        artifact = run.use_artifact(artifact_path, type="model")
        artifact_dir = artifact.download(root=output_dir)

        logging.info(f"Artifact downloaded successfully to: {artifact_dir}")

    except Exception as e:
        logging.error(f"Failed to download artifact from W&B: {e}")

    finally:
        if run:
            run.finish()


def download_model_from_huggingface(model_id: str, output_dir: str):
    logging.info(f"Downloading base model '{model_id}' from Hugging Face...")

    os.makedirs(output_dir, exist_ok=True)

    try:
        pipe = StableDiffusionPipeline.from_pretrained(model_id)

        pipe.save_pretrained(output_dir)

        logging.info(f"Model '{model_id}' downloaded and saved to: {output_dir}")

    except Exception as e:
        logging.error(f"Failed to download model from Hugging Face: {e}")


if __name__ == "__main__":
    load_dotenv()

    BASE_MODEL_DIR = "models"
    WANDB_PROJECT = "sd1.5-lora-tsuki"
    LORA_ARTIFACT_PATH = (
        "hienntt-0109/sd1.5-lora-tsuki/lora-adapter-epoch-20-xjdg9lfg:v0"
    )
    LORA_SUBDIR = "lora-tsuki-epoch-20"
    lora_output_dir = os.path.join(BASE_MODEL_DIR, LORA_SUBDIR)

    HF_MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"
    base_model_output_dir = os.path.join(BASE_MODEL_DIR, "stable-diffusion-v1-5")

    download_lora_from_wandb(
        artifact_path=LORA_ARTIFACT_PATH,
        output_dir=lora_output_dir,
        wandb_project=WANDB_PROJECT,
    )

    print("-" * 50)

    download_model_from_huggingface(
        model_id=HF_MODEL_ID, output_dir=base_model_output_dir
    )

    logging.info("All download processes are complete.")
