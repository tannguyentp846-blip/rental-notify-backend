"""
Đọc Google Alerts RSS feed để lấy các bài đăng (kể cả từ Facebook groups) đã
được Google index công khai.

CÁCH LẤY RSS URL TỪ GOOGLE ALERTS:
1. Vào https://www.google.com/alerts
2. Tạo alert mới, vd: từ khóa "cho thuê nhà Quận 7" hoặc "site:facebook.com cho thuê nhà Quận 7"
3. Ở phần "Deliver to", chọn "RSS feed" thay vì "Email"
4. Copy URL RSS được tạo ra, dán vào ALERT_FEEDS bên dưới
"""
import feedparser
from typing import List, Dict


def fetch_google_alert_feed(feed_url: str) -> List[Dict]:
    """Đọc 1 RSS feed từ Google Alerts, trả về danh sách bài viết mới"""
    results = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            results.append({
                "source": "facebook_rss",
                "external_id": entry.get("link", ""),
                "title": entry.get("title", ""),
                "raw_text": entry.get("summary", ""),
                "url": entry.get("link", ""),
                "price_text": None,
                "area_text": None,
                "location": None,
            })
    except Exception as e:
        print(f"Lỗi đọc RSS feed {feed_url}: {e}")

    return results


def run_all_alert_feeds(feed_urls: List[str]) -> List[Dict]:
    """feed_urls: danh sách các RSS URL từ Google Alerts (mỗi bộ lọc có thể có 1 alert riêng)"""
    all_results = []
    for url in feed_urls:
        all_results.extend(fetch_google_alert_feed(url))
    return all_results
