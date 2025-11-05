import requests
from bs4 import BeautifulSoup
import urllib.parse
import os

FOLDER_NAME = 'tsuki_character'

if not os.path.exists(FOLDER_NAME):
    os.makedirs(FOLDER_NAME)
    print(f"Create folder: '{FOLDER_NAME}'")
else:
    print(f"Folder '{FOLDER_NAME}' already existed")

url = "https://tsuki-adventure.fandom.com/wiki/List_of_Characters"

response = requests.get(url)

if response.status_code == 200:
    print("Start crawling...")
    soup = BeautifulSoup(response.content, 'html.parser')

    character_tables = soup.find_all('table', class_='hoverimage')

    item_number = 932

    for table in character_tables:
        character_cells = table.find_all('td')

        for cell in character_cells:
            a_tag = cell.find('a')
            img_tag = cell.find('img')

            if a_tag and img_tag:
                character_name = a_tag.get('title')
                image_url = img_tag.get('data-src') or img_tag.get('src')

                if character_name and image_url:
                    absolute_image_url = urllib.parse.urljoin(url, image_url)

                    try:
                        image_response = requests.get(absolute_image_url, stream=True)

                        if image_response.status_code == 200:
                            file_name = f"item_{item_number}.png"
                            file_path = os.path.join(FOLDER_NAME, file_name)

                            with open(file_path, 'wb') as f:
                                f.write(image_response.content)

                            print(f"({item_number}) Downloaded and saved '{character_name}' into '{file_path}'")

                            item_number += 1
                        else:
                            print(f"Error: can't download image '{character_name}'. Status: {image_response.status_code}")

                    except requests.exceptions.RequestException as e:
                        print(f"Error: network error while downloading '{character_name}': {e}")

    print("\nCompleted!")

else:
    print(f"Can't access website. Status: {response.status_code}")