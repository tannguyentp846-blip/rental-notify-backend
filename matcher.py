"""So khớp bài đăng mới với bộ lọc đã lưu (hỗ trợ multi-select)"""
from typing import Dict, List
from models import SearchFilter


def listing_matches_filter(listing: Dict, f: SearchFilter) -> bool:
    # Từ khóa
    if f.keywords:
        keywords = [k.strip().lower() for k in f.keywords.split(",") if k.strip()]
        text = (listing.get("title", "") + " " + (listing.get("raw_text") or "")).lower()
        if keywords and not any(k in text for k in keywords):
            return False

    # Tỉnh/thành — chỉ áp dụng nếu bài đăng có gắn thông tin tỉnh/thành
    # (nếu không, coi như URL crawl đã được lọc sẵn theo tỉnh/thành trên chính trang web)
    if f.city and listing.get("city") and listing["city"] != f.city:
        return False

    # Quận/huyện (multi-select)
    districts = f.to_list(f.districts)
    if districts and listing.get("district") and listing["district"] not in districts:
        return False

    # Loại nhà (multi-select)
    property_types = f.to_list(f.property_types)
    if property_types and listing.get("property_type") and listing["property_type"] not in property_types:
        return False

    # Số phòng ngủ (multi-select)
    bedrooms = f.to_list(f.bedrooms)
    if bedrooms and listing.get("bedrooms") and listing["bedrooms"] not in bedrooms:
        return False

    # Giá (đơn vị: triệu VNĐ/tháng)
    price = listing.get("price")
    if price is not None:
        if f.min_price is not None and price < f.min_price:
            return False
        if f.max_price is not None and price > f.max_price:
            return False

    # Diện tích
    area = listing.get("area")
    if area is not None:
        if f.min_area is not None and area < f.min_area:
            return False
        if f.max_area is not None and area > f.max_area:
            return False

    return True


def find_matches(listings: List[Dict], f: SearchFilter) -> List[Dict]:
    return [l for l in listings if listing_matches_filter(l, f)]
