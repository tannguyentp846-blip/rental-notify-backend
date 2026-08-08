"""
Crawler cho các website cho thuê nhà.

CÁCH HOẠT ĐỘNG: thay vì đoán tên class CSS (dễ sai vì web hay đổi giao diện),
crawler này nhận diện tin đăng qua CẤU TRÚC ĐƯỜNG LINK — mọi tin trên
batdongsan.com.vn đều có URL kết thúc dạng "...-prNNNNNNN" (số ID tin đăng).
Sau khi tìm được link, nó đọc đoạn text xung quanh (trong cùng thẻ cha) để
tìm giá (dạng "X triệu/tháng") và diện tích (dạng "X m²"). Cách này bền hơn
nhiều so với dựa vào tên class, vốn có thể đổi bất cứ lúc nào.
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


def parse_price_to_million(text: str):
    """Chuyển '5 triệu/tháng' thành số (đơn vị: triệu VNĐ)"""
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
    """Chuyển '35 m²' thành số"""
    if not text:
        return None
    match = re.search(r"([\d.,]+)\s*m", text)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


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
                continue  # không phải link tin đăng

            url = href if href.startswith("http") else "https://batdongsan.com.vn" + href
            if url in seen:
                continue
            seen.add(url)

            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if len(title) < 10:
                continue  # bỏ qua link rác (nút chia sẻ, icon...)

            # Tìm giá/diện tích trong text của thẻ cha chứa link này
            container = a.find_parent(["div", "li"]) or a
            context_text = container.get_text(" ", strip=True)

            results.append({
                "source": "batdongsan",
                "external_id": url,
                "title": title,
                "price": parse_price_to_million(context_text),
                "area": parse_area_to_number(context_text),
                "city": None,
                "district": None,
                "property_type": None,
                "bedrooms": None,
                "url": url,
                "raw_text": context_text[:400],
            })

            if len(results) >= 40:
                break

    except requests.RequestException as e:
        print(f"Lỗi crawl {search_url}: {e}")

    return results


def crawl_chotot(search_url: str) -> List[Dict]:
    """Chotot chưa được kiểm chứng thực tế — có thể cần điều chỉnh thêm."""
    results = []
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not re.search(r"\d{8,}", href):  # chotot dùng ID số dài trong URL
                continue
            url = href if href.startswith("http") else "https://www.chotot.com" + href
            if url in seen:
                continue
            seen.add(url)

            title = (a.get("title") or a.get_text(strip=True) or "").strip()
            if len(title) < 10:
                continue

            container = a.find_parent(["div", "li"]) or a
            context_text = container.get_text(" ", strip=True)

            results.append({
                "source": "chotot",
                "external_id": url,
                "title": title,
                "price": parse_price_to_million(context_text),
                "area": parse_area_to_number(context_text),
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
    all_results = []
    if "batdongsan" in search_urls:
        all_results.extend(crawl_batdongsan(search_urls["batdongsan"]))
        time.sleep(1)
    if "chotot" in search_urls:
        all_results.extend(crawl_chotot(search_urls["chotot"]))
    return all_results
