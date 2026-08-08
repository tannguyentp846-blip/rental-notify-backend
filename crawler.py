"""
Crawler cho các website cho thuê nhà: batdongsan.com.vn, nhatot.com, alonhadat.com.vn

CÁCH HOẠT ĐỘNG: quét trực tiếp trong mã HTML thô để tìm các link tin đăng
(theo cấu trúc URL đặc trưng của từng trang), sau đó đọc một ĐOẠN NHỎ mã HTML
nằm ngay sát link đó (không phải toàn bộ thẻ cha, để tránh lấy nhầm dữ liệu
của tin khác) để tìm giá, diện tích và ảnh đại diện.
"""
import requests
from typing import List, Dict, Optional
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}

HOUSING_KEYWORDS = ["nhà", "phòng", "căn hộ", "chung cư", "trọ", "đất", "biệt thự", "mặt bằng", "văn phòng"]

LINK_TAG_RE = re.compile(r'<a\s+([^>]*)>(.*?)</a>', re.DOTALL)
IMG_SRC_RE = re.compile(r'<img[^>]+(?:src|data-src|data-original|data-lazy-src)=["\']([^"\']+)["\']')


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


def _clean_text(html_fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_fragment)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _find_image_near(window: str) -> Optional[str]:
    for m in IMG_SRC_RE.finditer(window):
        src = m.group(1)
        if src.startswith("data:"):
            continue  # ảnh placeholder base64, bỏ qua, thử ảnh tiếp theo
        return src
    return None


def _crawl_generic(search_url: str, source_label: str, url_pattern: str,
                    base_url: str, require_housing_keyword: bool = False) -> List[Dict]:
    """
    url_pattern: regex áp dụng lên href để nhận diện link tin đăng
    base_url: dùng để ghép thành URL đầy đủ nếu href là đường dẫn tương đối
    """
    results = []
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text

        seen = set()
        for m in LINK_TAG_RE.finditer(html):
            attrs_str, inner = m.group(1), m.group(2)
            href_m = re.search(r'href=["\']([^"\']+)["\']', attrs_str)
            if not href_m:
                continue
            href = href_m.group(1)
            if not re.search(url_pattern, href):
                continue

            url = href if href.startswith("http") else base_url + href
            if url in seen:
                continue
            seen.add(url)

            title_m = re.search(r'title=["\']([^"\']+)["\']', attrs_str)
            title = title_m.group(1).strip() if title_m else _clean_text(inner)
            if len(title) < 10:
                continue

            # Đọc đoạn HTML nhỏ ngay TRƯỚC và SAU vị trí link này (không lấy cả thẻ cha lớn)
            window = html[max(0, m.start() - 1500): m.start() + 900]
            window_text = _clean_text(window)

            if require_housing_keyword and not _looks_like_housing(title + " " + window_text):
                continue

            results.append({
                "source": source_label,
                "external_id": url,
                "title": title,
                "price": parse_price_to_million(window_text),
                "area": parse_area_to_number(window_text),
                "image": _find_image_near(window),
                "city": None, "district": None, "property_type": None, "bedrooms": None,
                "url": url,
                "raw_text": window_text[:400],
            })
            if len(results) >= 40:
                break

    except requests.RequestException as e:
        print(f"Lỗi crawl {search_url}: {e}")

    return results


def crawl_batdongsan(search_url: str) -> List[Dict]:
    return _crawl_generic(search_url, "batdongsan", r"-pr\d+", "https://batdongsan.com.vn")


def crawl_nhatot(search_url: str, source_label: str = "nhatot") -> List[Dict]:
    return _crawl_generic(search_url, source_label, r"/\d{6,9}\.htm", "https://www.nhatot.com",
                           require_housing_keyword=True)


def crawl_alonhadat(search_url: str) -> List[Dict]:
    return _crawl_generic(search_url, "alonhadat", r"-\d{7,9}\.html", "https://alonhadat.com.vn")


def run_all_crawlers(search_urls: Dict[str, str]) -> List[Dict]:
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


def debug_crawl_per_source(search_urls: Dict[str, str]) -> Dict:
    """Trả về số lượng tin lấy được + trạng thái HTTP riêng cho từng nguồn — dùng để chẩn đoán"""
    report = {}
    checks = [
        ("batdongsan", search_urls.get("batdongsan"), crawl_batdongsan),
        ("nhatot_house", search_urls.get("nhatot_house"), lambda u: crawl_nhatot(u, "nhatot")),
        ("nhatot_room", search_urls.get("nhatot_room"), lambda u: crawl_nhatot(u, "nhatot_phongtro")),
        ("alonhadat", search_urls.get("alonhadat"), crawl_alonhadat),
    ]
    for name, url, fn in checks:
        if not url:
            continue
        entry = {"url": url}
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            entry["http_status"] = resp.status_code
            entry["html_length"] = len(resp.text)
        except requests.RequestException as e:
            entry["fetch_error"] = str(e)
        try:
            items = fn(url)
            entry["items_found"] = len(items)
            entry["sample_titles"] = [it["title"] for it in items[:3]]
        except Exception as e:
            entry["crawl_error"] = str(e)
        report[name] = entry
    return report
