import requests
import time
import json
import re
import sys
from bs4 import BeautifulSoup
from tqdm import tqdm
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import os

PTT_URL = 'https://www.ptt.cc'
HEADERS = {'cookie': 'over18=1'}
START_PAGE = '/bbs/Beauty/index3917.html'  # 起始文章頁面
# START_PAGE = '/bbs/Beauty/index.html'  # 最新頁


ARTICLES_PATH = 'articles.jsonl'
POPULAR_ARTICLES_PATH = 'popular_articles.jsonl'
articles = []
popular_articles = []

def get_soup(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return BeautifulSoup(res.text, 'html.parser')
    except Exception as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return None

def is_valid_article(entry):
    title_tag = entry.select_one('.title a')
    if not title_tag:
        return False
    title = title_tag.text.strip()
    if '[公告]' in title or 'Fw:[公告]' in title or title == '':
        return False
    return True

def extract_article_info(entry):
    title_tag = entry.select_one('.title a')
    title = title_tag.text.strip()
    href = title_tag.get('href')
    if not href:
        return None
    url = PTT_URL + href

    date_tag = entry.select_one('.date')
    if not date_tag:
        return None

    date = date_tag.text.strip().replace('/', '').zfill(4)

    return {"date": date, "title": title, "url": url}

def is_popular(entry):
    mark = entry.select_one('.nrec').text.strip()
    return mark == '爆'

def get_article_year(article_url):
    match = re.search(r'/M\.(\d+)\.A\.', article_url)
    if match:
        timestamp = int(match.group(1))
        taiwan_time = datetime.fromtimestamp(timestamp, tz=timezone(timedelta(hours=8)))
        return taiwan_time.year
    return None

def flush_to_file(filename, data_list):
    def parse_date(item):
        d = item["date"]
        try:
            if len(d) == 3:
                month = int(d[0])
                day = int(d[1:])
            elif len(d) == 4:
                month = int(d[:2])
                day = int(d[2:])
            else:
                return datetime(2099, 1, 1)
            return datetime(2024, month, day)
        except:
            return datetime(2099, 1, 1)

    sorted_data = sorted(data_list, key=parse_date)
    with open(filename, 'w', encoding='utf-8') as f:
        for item in sorted_data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')

def parse_push(url):
    soup = get_soup(url)
    if not soup:
        return []
    pushes = soup.select('div.push')
    result = []
    for push in pushes:
        tag = push.select_one('span.push-tag')
        user = push.select_one('span.push-userid')
        if not tag or not user:
            continue
        tag_text = tag.text.strip()
        user_id = user.text.strip()
        if tag_text == '推':
            result.append((user_id, 'push'))
        elif tag_text == '噓':
            result.append((user_id, 'boo'))
    return result

def push_stat(start_date, end_date):
    start = int(start_date)
    end = int(end_date)
    with open(ARTICLES_PATH, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]

    push_counter = Counter()
    boo_counter = Counter()
    for article in data:
        date = int(article['date'])
        if start <= date <= end:
            stats = parse_push(article['url'])
            for uid, typ in stats:
                if typ == 'push':
                    push_counter[uid] += 1
                elif typ == 'boo':
                    boo_counter[uid] += 1

    result = {
        "push": {
            "total": sum(push_counter.values()),
            "top10": sorted(
                        [{"user_id": k, "count": v} for k, v in push_counter.items()],
                        key=lambda x: (-x["count"], ''.join(chr(255 - ord(c)) for c in x["user_id"]))
                    )[:10]
        },
        "boo": {
            "total": sum(boo_counter.values()),
            "top10": sorted(
                        [{"user_id": k, "count": v} for k, v in boo_counter.items()],
                        key=lambda x: (-x["count"], ''.join(chr(255 - ord(c)) for c in x["user_id"]))
                    )[:10]
        }
    }

    out_path = f"push_{start_date}_{end_date}.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    print(f"✅ 輸出: {out_path}")

def extract_images_from_article(url):
    soup = get_soup(url)
    if not soup:
        return []
    urls = re.findall(r'https?://[^\s]+?(?:\.jpg|\.jpeg|\.png|\.gif)', soup.text, re.IGNORECASE)
    return urls

def popular_stat(start_date, end_date):
    start = int(start_date)
    end = int(end_date)
    with open(POPULAR_ARTICLES_PATH, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]

    image_urls = []
    count = 0
    for article in data:
        date = int(article['date'])
        if start <= date <= end:
            count += 1
            image_urls.extend(extract_images_from_article(article['url']))

    result = {
        "number_of_popular_articles": count,
        "image_urls": image_urls
    }

    out_path = f"popular_{start_date}_{end_date}.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    print(f"✅ 輸出: {out_path}")

def keyword_stat(start_date, end_date, keyword):
    start = int(start_date)
    end = int(end_date)

    with open(ARTICLES_PATH, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]
    
    matched_articles = []
    image_urls = []

    for article in data:
        date = int(article['date'])
        if not (start <= date <= end):
            continue

        soup = get_soup(article['url'])
        if not soup:
            continue

        main_content = soup.select_one("#main-content")
        if not main_content:
            continue

        # 移除發信站後面內容
        text = main_content.text.split("※ 發信站:")[0]
        # print(text)
        if "※ 發信站:" not in main_content.text:
            continue  # 沒有發信站視為格式錯誤，跳過

        if keyword in text:
            matched_articles.append(article)

            # 擷取內文 + 推文中所有圖片網址
            html = soup.text
            # print(html)
            urls = re.findall(r'https?://[^\s]+?(?:\.jpg|\.jpeg|\.png|\.gif)', html, re.IGNORECASE)
            # urls = re.findall(r'https?://[^\\s]+?(?:\\.jpg|\\.jpeg|\\.png|\\.gif)', html, re.IGNORECASE)
            
            image_urls.extend(urls)

    result = {
        # "number_of_keyword_articles": len(matched_articles),
        "image_urls": image_urls
    }

    out_path = f"keyword_{start_date}_{end_date}_{keyword}.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    print(f"✅ 輸出: {out_path}")


def crawl():
    url = PTT_URL + START_PAGE
    pbar = tqdm(desc="Crawling", unit="page")
    #print(url)
    while url:
        soup = get_soup(url)
        if not soup:
            break

        entries = soup.select('.r-ent')
        found = False  # 每頁預設沒有 2024年文章
        has_2024 = False
        all_before_2024 = True  # 預設全部是舊的

        for entry in entries:
            if not is_valid_article(entry):
                continue
            info = extract_article_info(entry)
            if not info:
                continue

            year = get_article_year(info['url'])
            if year is None:
                continue

            if year == 2024:
                has_2024 = True
                all_before_2024 = False
                articles.append(info)
                if is_popular(entry):
                    popular_articles.append(info)
            elif year > 2024:
                all_before_2024 = False  # 有未來的年份，不能停
                continue

        if all_before_2024:
            print("🛑 停止爬蟲：這一頁全部是 2023 或更舊的文章")
            break
        # for entry in entries:
        #     if not is_valid_article(entry):
        #         continue
        #     info = extract_article_info(entry)
        #     if not info:
        #         continue

        #     year = get_article_year(info['url'])
        #     print(year)
            
        #     if year != 2024
        #         print(f" {info['date']} - {info['title']} {found}")
        #         continue  # 跳過非 2024年
            
        #     found = True  # 有符合條件的文章
        #     print(f" {info['date']} - {info['title']} {found}")
        #     articles.append(info)
        #     if is_popular(entry):
        #         popular_articles.append(info)

        # if not found:
        #     print("🛑 停止爬蟲：本頁沒有 2024年的文章")
        #     break

        prev_link = next((a['href'] for a in soup.select('a.btn.wide') if '上頁' in a.text), None)
        if prev_link:
            url = PTT_URL + prev_link
            pbar.update(1)
            time.sleep(0.2)
        else:
            print("❗ 沒有上一頁，爬蟲結束")
            break

    pbar.close()
    flush_to_file(ARTICLES_PATH, articles)
    flush_to_file(POPULAR_ARTICLES_PATH, popular_articles)
    print("✅ 已抵達最舊頁面，任務完成")

# def crawl():
#     url = PTT_URL + START_PAGE
#     pbar = tqdm(desc="Crawling", unit="page")
#     while url:
#         soup = get_soup(url)
#         if not soup:
#             break

#         entries = soup.select('.r-ent')
#         found_2024= False
#         all_before_2024= True

#         for entry in entries:
#             if not is_valid_article(entry):
#                 continue

#             info = extract_article_info(entry)
#             if not info:
#                 continue

#             year = get_article_year(info['url'])
#             if year is None:
#                 continue

#             if year == 2024
#                 found_2024= True
#                 all_before_2024= False
#                 articles.append(info)
#                 if is_popular(entry):
#                     popular_articles.append(info)
#             elif year > 2024
#                 all_before_2024= False
#                 continue
#             # 如果 year < 2024就跳過不加入

#         if found_2024
#             print(f"✅ 抓到 2024的文章，繼續往前")
#         elif all_before_2024
#             print("🛑 遇到全部是 2023 或更早的文章，結束爬蟲")
#             break

#         prev_link = next((a['href'] for a in soup.select('a.btn.wide') if '上頁' in a.text), None)
#         if prev_link:
#             url = PTT_URL + prev_link
#             pbar.update(1)
#             time.sleep(0.2)
#         else:
#             print("❗ 沒有上一頁，爬蟲結束")
#             break

#     pbar.close()
#     flush_to_file(ARTICLES_PATH, articles)
#     flush_to_file(POPULAR_ARTICLES_PATH, popular_articles)
#     print("✅ 爬蟲結束，已儲存所有 2024年文章")


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'crawl':
        crawl()
    elif len(sys.argv) == 4 and sys.argv[1] == 'push':
        push_stat(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == 'popular':
        popular_stat(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 5 and sys.argv[1] == 'keyword':
        keyword_stat(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Usage:")
        print("  python 313511022.py crawl")
        print("  python 313511022.py push MMDD MMDD")
        print("  python 313511022.py popular MMDD MMDD")
        print("  python 313511022.py keyword MMDD MMDD keyword")