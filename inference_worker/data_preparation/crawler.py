import requests
from bs4 import BeautifulSoup
import os
import re
import time

def download_images_from_tsuki_wiki():
    """Download item images from Tsuki Adventure Wiki with simple incremental naming"""
    url = "https://tsuki-adventure-2.fandom.com/wiki/Items"
    folder = 'tsuki_items'
    
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"Created directory: {folder}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"Fetching page: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        image_counter = 1
        
        img_tags = soup.find_all('img', class_=lambda c: c and ('lazyload' in c or 'thumbimage' in c))
        
        if not img_tags:
            print("No lazyload/thumbimage classes found, trying all images in tables")
            tables = soup.find_all('table', class_='wikitable')
            for table in tables:
                img_tags.extend(table.find_all('img'))
        
        print(f"Found {len(img_tags)} potential image tags")
        
        downloaded = set()
        
        for img_tag in img_tags:
            img_url = None
            
            if img_tag.get('data-src') and not img_tag['data-src'].startswith('data:'):
                img_url = img_tag['data-src']
            elif img_tag.get('src') and not img_tag['src'].startswith('data:'):
                img_url = img_tag['src']
            
            if not img_url:
                continue
                
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
                
            if 'width=' in img_url and re.search(r'width=(\d+)', img_url):
                width = int(re.search(r'width=(\d+)', img_url).group(1))
                if width < 30:
                    continue
            
            if img_url in downloaded:
                continue
                
            if '/thumb/' in img_url:
                try:
                    parts = img_url.split('/thumb/')
                    if len(parts) == 2:
                        base_part = parts[0]
                        file_part = parts[1].split('/')
                        if len(file_part) > 1:
                            original_img_url = f"{base_part}/{'/'.join(file_part[:-1])}"
                            img_url = original_img_url
                except:
                    pass
            
            try:
                print(f"Downloading: {img_url}")
                img_response = requests.get(img_url, headers=headers)
                img_response.raise_for_status()
                
                content_type = img_response.headers.get('Content-Type', '')
                if 'image' not in content_type:
                    print(f"Skipping non-image content: {content_type}")
                    continue
                
                filename = f"item_{image_counter}.jpg"
                file_path = os.path.join(folder, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(img_response.content)
                
                print(f"Downloaded: {filename}")
                downloaded.add(img_url)
                image_counter += 1
                
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Error downloading {img_url}: {e}")
        
        print(f"Completed! Downloaded {image_counter-1} item images.")
        
    except Exception as e:
        print(f"Error crawling the page: {e}")

if __name__ == "__main__":
    download_images_from_tsuki_wiki()