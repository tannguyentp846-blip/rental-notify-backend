"""
Crawler cho các website cho thuê nhà: batdongsan.com.vn, nhatot.com, alonhadat.com.vn

CÁCH HOẠT ĐỘNG: nhận diện tin đăng qua CẤU TRÚC ĐƯỜNG LINK thay vì đoán tên
class CSS (dễ sai vì web hay đổi giao diện):
  - batdongsan.com.vn: link tin đăng kết thúc dạng "...-prNNNNNNN"
  - nhatot.com: link tin đăng có dạng ".../NNNNNNNN.htm"
  - alonhadat.com.vn: link tin đăng có dạng "...-NNNNNNNN.html"
Sau khi tìm được link, code đọc đoạn text xung quanh (thẻ cha) để tìm giá,
diện tích, và ảnh đại diện (thẻ <img> gần nhất).
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

HOUSING_KEYWORDS = ["nhà", "phòng", "căn hộ", "chung cư", "trọ", "đất", "biệt thự", "mặt bằng", "văn phòng"]


def parse_price_to_million(text: str):
    if not text:
        return None
    match = re.search(r"([\d.,]+)\s*tri", text, re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_area_to_number(text: str):
    if not text:
        return None
    match = re.search(r"([\d.,]+)\s*m", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _looks_like_housing(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in HOUSING_KEYWORDS)


def _extract_image(container) -> Optional[str]:
    """Tìm ảnh đại diện gần nhất trong thẻ cha chứa link tin đăng"""
    img = container.find("img")
    if not img:
        return None
    src = img.get("src") or img.get("data-src") or img.get("data-original") or img.get("data-lazy-src")
    if not src:
        return None
    if src.startswith("data:"):  # ảnh placeholder base64, bỏ qua
        return None
    return src


def crawl_batdongsan(search_url: str) -> List[Dict]:
    results = []
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.search(r"-pr\d+", href):
                continue

            url = href if href.startswith("http") else "https://batdongsan.com.vn" + href
            if url in seen:
                continue
            seen.add(url)

            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if len(title) < 10:
                continue

            container = a.find_parent(["div", "li"]) or a
            context_text = container.get_text(" ", strip=True)

            results.append({
                "source": "batdongsan",
                "external_id": url,
                "title": title,
                "price": parse_price_to_million(context_text),
                "area": parse_area_to_number(context_text),
                "image": _extract_image(container),
                "city": None, "district": None, "property_type": None, "bedrooms": None,
                "url": url,
                "raw_text": context_text[:400],
            })
            if len(results) >= 40:
                break

    except requests.RequestException as e:
        print(f"Lỗi crawl {search_url}: {e}")

    return results


def crawl_nhatot(search_url: str, source_label: str = "nhatot") -> List[Dict]:
    results = []
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.search(r"/\d{6,9}\.htm", href):
                continue

            url = href if href.startswith("http") else "https://www.nhatot.com" + href
            if url in seen:
                continue
            seen.add(url)

            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if len(title) < 10:
                continue

            container = a.find_parent(["div", "li"]) or a
            context_text = container.get_text(" ", strip=True)

            if not _looks_like_housing(title + " " + context_text):
                continue

            results.append({
                "source": source_label,
                "external_id": url,
                "title": title,
                "price": parse_price_to_million(context_text),
                "area": parse_area_to_number(context_text),
                "image": _extract_image(container),
                "city": None, "district": None, "property_type": None, "bedrooms": None,
                "url": url,
                "raw_text": context_text[:400],
            })
            if len(results) >= 40:
                break

    except requests.RequestException as e:
        print(f"Lỗi crawl {search_url}: {e}")

    return results


def crawl_alonhadat(search_url: str) -> List[Dict]:
    results = []
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.search(r"-\d{7,9}\.html", href):
                continue

            url = href if href.startswith("http") else "https://alonhadat.com.vn" + href
            if url in seen:
                continue
            seen.add(url)

            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if len(title) < 10:
                continue

            container = a.find_parent(["div", "li"]) or a.parent or a
            context_text = container.get_text(" ", strip=True)

            results.append({
                "source": "alonhadat",
                "external_id": url,
                "title": title,
                "price": parse_price_to_million(context_text),
                "area": parse_area_to_number(context_text),
                "image": _extract_image(container),
                "city": None, "district": None, "property_type": None, "bedrooms": None,
                "url": url,
                "raw_text": context_text[:400],
            })
            if len(results) >= 40:
                break

    except requests.RequestException as e:
        print(f"Lỗi crawl {search_url}: {e}")

    return results


def run_all_crawlers(search_urls: Dict[str, str]) -> List[Dict]:
    """search_urls keys hỗ trợ: batdongsan, nhatot_house, nhatot_room, alonhadat"""
    all_results = []
    if "batdongsan" in search_urls:
        all_results.extend(crawl_batdongsan(search_urls["batdongsan"]))
        time.sleep(1)
    if "nhatot_house" in search_urls:
        all_results.extend(crawl_nhatot(search_urls["nhatot_house"], "nhatot"))
        time.sleep(1)
    if "nhatot_room" in search_urls:
        all_results.extend(crawl_nhatot(search_urls["nhatot_room"], "nhatot_phongtro"))
        time.sleep(1)
    if "alonhadat" in search_urls:
        all_results.extend(crawl_alonhadat(search_urls["alonhadat"]))
    return all_results
