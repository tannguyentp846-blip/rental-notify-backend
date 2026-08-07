"""
Database models: SearchFilter (bộ lọc duy nhất của bạn — app cá nhân nên chỉ
cần 1 bộ lọc, không cần hệ thống user), Listing (bài đăng đã crawl được).
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./rental_notify.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class SearchFilter(Base):
    """
    Bộ lọc tìm kiếm. App chỉ dùng 1 bản ghi duy nhất (id=1) vì đây là app cá nhân.
    Các trường multi-select (districts, property_types, bedrooms) lưu dạng
    chuỗi phân cách bởi dấu phẩy, vd: "Quận 7,Quận 1"
    """
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, index=True)
    keywords = Column(String, nullable=True)
    city = Column(String, nullable=True)
    districts = Column(String, nullable=True)        # "Quận 7,Quận 1"
    property_types = Column(String, nullable=True)    # "Phòng trọ,Căn hộ / chung cư"
    bedrooms = Column(String, nullable=True)           # "1 PN,2 PN"
    min_price = Column(Float, nullable=True)           # triệu VNĐ/tháng
    max_price = Column(Float, nullable=True)
    min_area = Column(Float, nullable=True)            # m2
    max_area = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_list(self, field_value):
        return [v for v in (field_value or "").split(",") if v]


class Listing(Base):
    """Bài đăng đã crawl được, lưu lại để tránh crawl trùng liên tục trong cùng phiên"""
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    external_id = Column(String, unique=True, index=True)
    title = Column(String)
    price = Column(Float, nullable=True)
    area = Column(Float, nullable=True)
    city = Column(String, nullable=True)
    district = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    bedrooms = Column(String, nullable=True)
    url = Column(String)
    raw_text = Column(Text, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
