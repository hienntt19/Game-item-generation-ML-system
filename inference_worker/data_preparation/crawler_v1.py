import requests
from bs4 import BeautifulSoup
import os
import re
import time

def download_images_from_tsuki_wiki():
    """Download item images and their names from Tsuki Adventure Wiki"""
    # url = "https://tsuki-adventure-2.fandom.com/wiki/Items"
    # url = "https://tsuki-adventure.fandom.com/wiki/Items"
    # url = "https://tsuki-adventure.fandom.com/wiki/Items/Event_Items#"
    # url = "https://tsuki-adventure.fandom.com/wiki/Diary_Entries"
    url = "https://tsuki-adventure.fandom.com/wiki/Fishing"
    folder = 'tsuki_items_v5'
    
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"Created directory: {folder}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    item_names = []
    
    try:
        print(f"Fetching page: {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        image_counter = 796
        
        tables = soup.find_all('table')
        
        print(f"Found {len(tables)} tables to process")
        
        for table_idx, table in enumerate(tables):
            print(f"Processing table {table_idx + 1}/{len(tables)}")
            
            rows = table.find_all('tr')
            
            if len(rows) < 2:
                continue
                
            header_cells = rows[0].find_all(['th', 'td'])
            img_col_idx = -1
            name_col_idx = -1
            
            for i, cell in enumerate(header_cells):
                cell_text = cell.text.strip().lower()
                if 'Image' in cell_text:
                    img_col_idx = i
                elif 'Item Name' in cell_text or 'name' in cell_text:
                    name_col_idx = i
            
            if img_col_idx == -1:
                img_col_idx = 0
            if name_col_idx == -1:
                name_col_idx = 1
                
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                
                if len(cells) <= max(img_col_idx, name_col_idx):
                    continue
                    
                img_cell = cells[img_col_idx]
                name_cell = cells[name_col_idx]
                
                item_name = name_cell.text.strip()
                if not item_name:
                    continue
                
                img_tag = img_cell.find('img')
                if not img_tag:
                    continue
                
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
                    print(f"Downloading: {img_url} - {item_name}")
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
                    
                    print(f"Downloaded: {filename} - {item_name}")
                    
                    item_names.append(f"item_{image_counter}.jpg, {item_name}")
                    
                    image_counter += 1
                    
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"Error downloading {img_url}: {e}")
        
        with open(os.path.join(folder, 'item_names.txt'), 'w', encoding='utf-8') as f:
            for item_entry in item_names:
                f.write(f"{item_entry}\n")
        
        print(f"Completed! Downloaded {len(item_names)} item images.")
        print(f"Item names saved to {os.path.join(folder, 'item_names.txt')}")
        
    except Exception as e:
        print(f"Error crawling the page: {e}")

if __name__ == "__main__":
    download_images_from_tsuki_wiki()