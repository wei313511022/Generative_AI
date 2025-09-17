import requests
from bs4 import BeautifulSoup
import os
import re
import time
from datetime import datetime, timezone, timedelta
import io
import face_recognition
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import sys

if len(sys.argv) >= 2:
    try:
        SAVE_DIR = 'images' + sys.argv[1]
        START_PAGE = '/bbs/Beauty/index' + sys.argv[2] + '.html'  # 起始頁
    except ValueError:
        sys.exit(1)

PTT_URL = 'https://www.ptt.cc'
HEADERS = {'cookie': 'over18=1'}
# START_PAGE = '/bbs/Beauty/index3905.html'  # 起始頁

# SAVE_DIR = 'images'
os.makedirs(SAVE_DIR, exist_ok=True)

def get_article_year(article_url):
    match = re.search(r'/M\.(\d+)\.A\.', article_url)
    if match:
        timestamp = int(match.group(1))
        taiwan_time = datetime.fromtimestamp(timestamp, tz=timezone(timedelta(hours=8)))
        return taiwan_time.year
    return None

# def extract_and_save_face(image_bytes, save_path):
#     try:
#         image = face_recognition.load_image_file(io.BytesIO(image_bytes))
#         face_locations = face_recognition.face_locations(image)

#         if not face_locations:
#             return False

#         top, right, bottom, left = face_locations[0]  # only use first face
#         face_image = image[top:bottom, left:right]  # crop

#         # Convert to PIL for resizing
#         pil_image = Image.fromarray(face_image)
#         pil_image = pil_image.resize((64, 64))  # Resize to 64x64
#         pil_image.save(save_path)

#         return True
#     except:
#         return False

def extract_and_save_face(image_bytes, save_path, padding_ratio=0.3):
    try:
        image = face_recognition.load_image_file(io.BytesIO(image_bytes))
        face_locations = face_recognition.face_locations(image)

        if not face_locations:
            return False

        top, right, bottom, left = face_locations[0]  # only use first face

        height, width, _ = image.shape
        face_height = bottom - top
        face_width = right - left

        pad_h = int(face_height * padding_ratio)
        pad_w = int(face_width * padding_ratio)

        # Apply padding and ensure bounds are within image
        top = max(0, top - pad_h)
        bottom = min(height, bottom + pad_h)
        left = max(0, left - pad_w)
        right = min(width, right + pad_w)

        face_image = image[top:bottom, left:right]  # crop with padding

        # Convert to PIL for resizing
        pil_image = Image.fromarray(face_image)
        pil_image = pil_image.resize((64, 64))  # Resize to 64x64
        pil_image.save(save_path)

        return True
    except Exception as e:
        print(f"[ERROR] 裁切失敗：{e}")
        return False


def get_soup(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, 'html.parser')
    except Exception as e:
        print(f"[ERROR] 無法抓取 {url}：{e}")
        return None

def get_article_links(soup):
    links = []
    entries = soup.select('.r-ent')
    for entry in entries:
        a_tag = entry.select_one('.title a')
        if a_tag and a_tag.get('href'):
            links.append(PTT_URL + a_tag['href'])
    return links

def extract_main_image_links(article_url):
    soup = get_soup(article_url)
    if not soup:
        return []

    main_content = soup.select_one("#main-content")
    if not main_content:
        return []

    # 只抓內文圖片，不包含留言
    text = main_content.text.split("※ 發信站:")[0]
    image_links = re.findall(r'https?://[^\s]+?(?:\.jpg|\.jpeg|\.png|\.gif)', text, re.IGNORECASE)
    return image_links

def download_images(urls, article_idx):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    def process_one(i, url):
        # time.sleep(0.5)
        success = False
        ext = url.split('.')[-1].split('?')[0].lower()
        filename_base = f"{article_idx}_{i}"

        # Imgur 修正
        imgur_match = re.search(r'(?:i\.)?imgur\.com/([a-zA-Z0-9]+)', url)
        if imgur_match:
            imgur_id = imgur_match.group(1)
            for real_ext in ['jpg', 'png', 'webp']:
                new_url = f"https://i.imgur.com/{imgur_id}.{real_ext}"
                try:
                    res = requests.get(new_url, headers=headers, timeout=10)
                    if res.status_code == 200:
                        path = os.path.join(SAVE_DIR, f"{filename_base}.{real_ext}")
                        if extract_and_save_face(res.content, path):
                            print(f"✔ 成功下載並裁切：{new_url}")
                            return
                        else:
                            print(f"❌ 無人臉或裁切失敗，略過：{new_url}")
                except:
                    continue
            print(f"✘ imgur 圖片無法下載：{url}")
            return

        # 一般圖片
        if ext not in ['jpg', 'jpeg', 'png']:
            print(f"⏭️ 略過不支援格式：{url}")
            return

        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            path = os.path.join(SAVE_DIR, f"{filename_base}.{ext}")
            if extract_and_save_face(res.content, path):
                print(f"✔ 下載成功並裁切：{url}")
            else:
                print(f"❌ 無人臉或裁切失敗：{url}")
        except Exception as e:
            print(f"✘ 無法下載圖片：{url}，原因：{e}")

    # 使用 ThreadPool 同時下載
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.map(lambda args: process_one(*args), enumerate(urls))
        

def crawl_pages(start_page, max_pages=300):
    url = PTT_URL + start_page
    page_count = 0

    while url:
        time.sleep(0.2)
        soup = get_soup(url)
        if not soup:
            break

        article_links = get_article_links(soup)
        if not article_links:
            break

        has_2024 = False
        for idx, article_url in enumerate(article_links):
            year = get_article_year(article_url)
            if year != 2024:
                continue  # Skip non-2024
            has_2024 = True
            print(f"\n🔗 處理文章：{article_url}")
            image_links = extract_main_image_links(article_url)
            download_images(image_links, f"p{page_count}_a{idx}")
            time.sleep(0.2)

        if not has_2024:
            print("🛑 沒有 2024 年的文章，停止爬蟲")
            break

        prev_link = next((a['href'] for a in soup.select('a.btn.wide') if '上頁' in a.text), None)
        if prev_link:
            url = PTT_URL + prev_link
            page_count += 1
        else:
            print("📍 已無上一頁，結束爬蟲")
            break



crawl_pages(START_PAGE, max_pages=50)
