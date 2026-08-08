"""
FastAPI backend — phiên bản đơn giản hóa: không chạy nền, không push
notification. App di động sẽ gọi API mỗi khi mở lên để lấy tin mới nhất.

Chạy: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from models import init_db, get_db, SearchFilter, Listing
from crawler import run_all_crawlers
from rss_alerts import run_all_alert_feeds
from matcher import find_matches

app = FastAPI(title="Rental Notify API")

# Cho phép app mobile gọi API từ mọi origin (app cá nhân nên không cần siết chặt)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Cấu hình nguồn crawl: điền URL search THẬT của bạn (đã lọc theo khu vực trên chính website) ----
SEARCH_URLS = {
    "batdongsan": "https://batdongsan.com.vn/cho-thue-nha-quan-7",
    "chotot": "https://www.chotot.com/tp-ho-chi-minh/thue-nha",
}
GOOGLE_ALERT_FEEDS: List[str] = [
    # "https://www.google.com/alerts/feeds/xxxx/yyyy",
]


@app.on_event("startup")
def startup():
    init_db()


class FilterIn(BaseModel):
    keywords: Optional[str] = None
    city: Optional[str] = None
    districts: Optional[List[str]] = []
    property_types: Optional[List[str]] = []
    bedrooms: Optional[List[str]] = []
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_area: Optional[float] = None
    max_area: Optional[float] = None


def filter_to_response(f: SearchFilter):
    if not f:
        return None
    return {
        "keywords": f.keywords,
        "city": f.city,
        "districts": f.to_list(f.districts),
        "property_types": f.to_list(f.property_types),
        "bedrooms": f.to_list(f.bedrooms),
        "min_price": f.min_price,
        "max_price": f.max_price,
        "min_area": f.min_area,
        "max_area": f.max_area,
        "updated_at": f.updated_at,
    }


# ---------- API: Lấy bộ lọc đã lưu (app gọi lúc mở lên để khôi phục) ----------
@app.get("/filter")
def get_filter(db: Session = Depends(get_db)):
    f = db.query(SearchFilter).filter(SearchFilter.id == 1).first()
    return filter_to_response(f)


# ---------- API: Lưu / cập nhật bộ lọc (chỉ 1 bản ghi duy nhất, id=1) ----------
@app.put("/filter")
def save_filter(payload: FilterIn, db: Session = Depends(get_db)):
    f = db.query(SearchFilter).filter(SearchFilter.id == 1).first()
    if not f:
        f = SearchFilter(id=1)
        db.add(f)

    f.keywords = payload.keywords
    f.city = payload.city
    f.districts = ",".join(payload.districts or [])
    f.property_types = ",".join(payload.property_types or [])
    f.bedrooms = ",".join(payload.bedrooms or [])
    f.min_price = payload.min_price
    f.max_price = payload.max_price
    f.min_area = payload.min_area
    f.max_area = payload.max_area
    f.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(f)
    return filter_to_response(f)


# ---------- API chính: crawl ngay + lọc theo bộ lọc đã lưu, trả về kết quả ----------
# ---------- API debug: xem crawler có lấy được tin thật không (bỏ qua bộ lọc) ----------
@app.get("/debug/crawl")
def debug_crawl():
    raw = run_all_crawlers(SEARCH_URLS)
    return {"count": len(raw), "sample": raw[:5]}


@app.get("/listings/fetch")
def fetch_listings(db: Session = Depends(get_db)):
    """
    Gọi API này mỗi khi mở app: crawl trực tiếp (không cần chờ job nền),
    lọc theo bộ lọc đã lưu, và trả kết quả luôn trong 1 lần gọi.
    """
    f = db.query(SearchFilter).filter(SearchFilter.id == 1).first()
    if not f:
        return {"listings": [], "message": "Chưa thiết lập bộ lọc"}

    raw_listings = run_all_crawlers(SEARCH_URLS)
    raw_listings += run_all_alert_feeds(GOOGLE_ALERT_FEEDS)

    matched = find_matches(raw_listings, f)

    # Lưu lại để tránh mất dữ liệu nếu cần xem lại (không bắt buộc cho luồng chính)
    for item in matched:
        exists = db.query(Listing).filter(Listing.external_id == item["external_id"]).first()
        if exists:
            continue
        db.add(Listing(
            source=item["source"], external_id=item["external_id"], title=item["title"],
            price=item.get("price"), area=item.get("area"), city=item.get("city"),
            district=item.get("district"), property_type=item.get("property_type"),
            bedrooms=item.get("bedrooms"), url=item["url"], raw_text=item.get("raw_text"),
            crawled_at=datetime.utcnow(),
        ))
    db.commit()

    return {
        "listings": matched,
        "fetched_at": datetime.utcnow().isoformat(),
        "count": len(matched),
    }
