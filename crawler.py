"""
Crawler cho các website cho thuê nhà chính thống.

LƯU Ý QUAN TRỌNG: Selector HTML (class name, tag) trong file này là VÍ DỤ
MINH HOẠ. Cấu trúc HTML thật của các trang thay đổi thường xuyên, bạn cần:
  1. Mở trang web, dùng "Inspect Element" (chuột phải > Kiểm tra) để xem
     đúng class/tag hiện tại của tiêu đề, giá, diện tích...
  2. Cập nhật lại các selector bên dưới cho khớp

CÁCH LỌC THEO TỈNH/QUẬN: thay vì để crawler tự đoán quận/huyện từ text (dễ
sai), cách đáng tin cậy hơn là dùng SEARCH_URLS trong main.py — dán URL kết
quả tìm kiếm đã áp filter khu vực SẴN trên chính trang web đó. Backend chỉ
việc crawl đúng URL đó, không cần tự nhận diện quận/huyện.
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def parse_price_to_million(price_text: str):
    """Chuyển '5 triệu/tháng' hoặc '5,000,000 đ' thành số (đơn vị: triệu VNĐ)"""
    if not price_text:
        return None
    text = price_text.lower()
    numbers = re.findall(r"[\d.,]+", text)
    if not numbers:
        return None
    raw = numbers[0].replace(",", "").replace(".", "")
    if not raw.isdigit():
        return None
    value = float(raw)
    if "triệu" in text:
        return value
    if value > 1000:  # có thể là số VNĐ đầy đủ, quy đổi ra triệu
        return round(value / 1_000_000, 2)
    return value


def parse_area_to_number(area_text: str):
    """Chuyển '35 m2' thành số"""
    if not area_text:
        return None
    match = re.search(r"[\d.]+", area_text)
    return float(match.group()) if match else None


def crawl_generic(search_url: str, source_name: str, item_selector: str,
                   title_selector: str, price_selector: str = None,
                   area_selector: str = None) -> List[Dict]:
    """
    Hàm crawl dùng chung — truyền vào các CSS selector tương ứng với từng
    website. Xem ví dụ cấu hình cho batdongsan/chotot bên dưới.
    """
    results = []
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(item_selector)

        for item in items:
            try:
                title_el = item.select_one(title_selector)
                link_el = item.select_one("a")
                if not title_el or not link_el:
                    continue

                url = link_el.get("href", "")
                if url and not url.startswith("http"):
                    base = "/".join(search_url.split("/")[:3])
                    url = base + url

                price_el = item.select_one(price_selector) if price_selector else None
                area_el = item.select_one(area_selector) if area_selector else None

                results.append({
                    "source": source_name,
                    "external_id": url,
                    "title": title_el.get_text(strip=True),
                    "price": parse_price_to_million(price_el.get_text(strip=True) if price_el else None),
                    "area": parse_area_to_number(area_el.get_text(strip=True) if area_el else None),
                    "city": None,        # để trống — dựa vào URL đã lọc sẵn theo khu vực
                    "district": None,
                    "property_type": None,
                    "bedrooms": None,
                    "url": url,
                    "raw_text": title_el.get_text(strip=True),
                })
            except Exception as e:
                print(f"Lỗi parse 1 item từ {source_name}: {e}")
                continue

    except requests.RequestException as e:
        print(f"Lỗi crawl {search_url}: {e}")

    return results


def crawl_batdongsan(search_url: str) -> List[Dict]:
    return crawl_generic(
        search_url,
        source_name="batdongsan",
        item_selector="div.js__card, div.re__card-full",
        title_selector="span.pr-title, h3",
        price_selector="span.re__card-config-price",
        area_selector="span.re__card-config-area",
    )


def crawl_chotot(search_url: str) -> List[Dict]:
    return crawl_generic(
        search_url,
        source_name="chotot",
        item_selector="li.list-view-item, div.AdItem_adItem__",
        title_selector="h3, span.ad-title",
    )


def run_all_crawlers(search_urls: Dict[str, str]) -> List[Dict]:
    """search_urls: dict dạng {"batdongsan": "https://...", "chotot": "https://..."}"""
    all_results = []
    if "batdongsan" in search_urls:
        all_results.extend(crawl_batdongsan(search_urls["batdongsan"]))
        time.sleep(1)
    if "chotot" in search_urls:
        all_results.extend(crawl_chotot(search_urls["chotot"]))
    return all_results
