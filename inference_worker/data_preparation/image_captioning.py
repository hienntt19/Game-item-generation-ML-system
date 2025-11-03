import os
import glob
import csv
import google.generativeai as genai
import PIL.Image
from tqdm import tqdm


try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    print("Put GEMINI_API_KEY in env variables")
    exit()

IMAGE_FOLDER = "tsuki_dataset_final/images"
METADATA_FILE = "metadata_final.csv"
SUPPORTED_FORMATS = ('*.png', '*.jpg', '*.jpeg', '*.webp')

MASTER_PROMPT = """
You are an expert captioning tool for Stable Diffusion LoRA training. Your task is to generate a concise, descriptive caption for the provided image, following a specific style.
**Style to learn:** "tsuki adventure game style" - A simply, cute illustration style with thick, slightly shaky outlines, and flat colors on a white background.
**Trigger Word:** tsuki_advtr
**Rules for Captioning:**
1.  **Start with the trigger word:** Every caption MUST begin with "tsuki_advtr, ".
2.  **Describe the subject:** Provide a full and detailed description of all objects appearing in the image. If there is only one object, describe its shape, color, and specific characteristics in detail. If there are multiple objects, describe the detailed shape, color, and specific characteristics of each object and their positions in relation to each other (e.g., a brown mystery bag with rectangular pouch, slightly crumpled, folded top, beige-yellow label, dark brown question mark logo; a rounded green coconut drink, top cut open, beige visible inside, small grey-blue cocktail umbrella and dark grey straw inserted into the top).
3.  **Mention the background:** If the background is plain white, add the tag "white background", else if the image has background, describe the background in detail (e.g., outside background with trees and blue sky).
4.  **Include essential style tags:** ALWAYS include the tags "thick outlines, cartoon style, hand-drawn, 2D icon, game item, 2D game style, minimalist" to reinforce the style.
5.  **Keep it concise:** Combine everything into a single line of comma-separated keywords. Do not write full sentences.
## EXAMPLES ##
**Example 1 (Image of a brown paper bag):**
tsuki_advtr, a brown paper bag with rectangular pouch, slightly crumpled, folded top, beige-yellow rectangular label with a dark brown question mark logo in the center, white background, thick outlines, cartoon style, hand-drawn, 2D icon, game item, 2D game style, minimalist

**Example 2 (Image of coconut drink):**
tsuki_advtr, a rounded green coconut drink, top cut open, beige visible inside, small grey-blue cocktail umbrella and dark grey straw inserted into the top, white background, thick outlines, cartoon style, hand-drawn, 2D icon, game item, 2D game style, minimalist

Now, generate a caption for the image I provide.
"""

def get_image_paths(folder, formats):
    paths = []
    for fmt in formats:
        paths.extend(glob.glob(os.path.join(folder, fmt)))
    return paths

def generate_caption(image_path, model):
    try:
        img = PIL.Image.open(image_path)
        response = model.generate_content([MASTER_PROMPT, img])
        clean_caption = response.text.strip().replace('\n', ' ').replace('\r', '')
        return clean_caption
    except Exception as e:
        print(f"  [ERROR] Could not process {os.path.basename(image_path)}: {e}")
        return None 
    
def main():
    print("--- Starting Automatic Captioning for LoRA Training ---")
    all_image_paths = get_image_paths(IMAGE_FOLDER, SUPPORTED_FORMATS)
    if not all_image_paths:
        print(f"Error: No images found in '{IMAGE_FOLDER}' folder.")
        return
    
    with open(METADATA_FILE, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['image_path', 'prompt'])
        
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        print(f"Processing {len(all_image_paths)} images with gemini-1.5-flash-latest model.")

        for img_path in tqdm(all_image_paths, desc="Captioning Images"):
            caption = generate_caption(img_path, model)
            
            if caption:
                image_filename = os.path.basename(img_path)
                writer.writerow([image_filename, caption])
            

    print("\n--- Process Complete! ---")
    print(f"All captions have been successfully saved to '{METADATA_FILE}'.")


if __name__ == "__main__":
    main()