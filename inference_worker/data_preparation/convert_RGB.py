import os
from PIL import Image
from tqdm import tqdm

image_directory = "tsuki_adventure_data" 

image_files = [f for f in os.listdir(image_directory)]
processed_count = 0

for filename in tqdm(image_files, desc="Processing image"):
    file_path = os.path.join(image_directory, filename)
    
    try:
        img = Image.open(file_path)

        if img.mode == 'RGBA':
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, (0, 0), img)
            background.convert('RGB').save(file_path, 'PNG')
            
            processed_count += 1

    except Exception as e:
        print(f"Error while processing file {filename}: {e}")

print(f"\nCompleted convert {processed_count} image to white background")