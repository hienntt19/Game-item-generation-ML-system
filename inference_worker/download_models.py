import os
import wandb
from dotenv import load_dotenv

load_dotenv()

print("Starting download lora from w&b...")

MODEL_DIR = "models"
LORA_SUBDIR = "lora-tsuki-epoch-20"

output_dir = os.path.join(MODEL_DIR,LORA_SUBDIR)
os.makedirs(output_dir, exist_ok=True)

run = wandb.init(project="sd1.5-lora-tsuki", job_type="inference")

artifact_path = "hienntt-0109/sd1.5-lora-tsuki/lora-adapter-epoch-20-xjdg9lfg:v0"
artifact = run.use_artifact(artifact_path, type="model")
artifact_dir = artifact.download(root=output_dir)

run.finish()

print(f"Lora downloaded successfully to: {output_dir}")


from diffusers import StableDiffusionPipeline

MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"
OUTPUT_DIR = os.path.join("models", "stable-diffusion-v1-5")

print(f"Downloading base model {MODEL_ID} to {OUTPUT_DIR}...")

pipe = StableDiffusionPipeline.from_pretrained(MODEL_ID)

pipe.save_pretrained(OUTPUT_DIR)

print("Download complete.")
