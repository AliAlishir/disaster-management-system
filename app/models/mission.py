from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from datetime import datetime
from app.database import Base

class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    province = Column(String, index=True, nullable=False)
    city = Column(String, index=True, nullable=False)

    # آدرس کامل محل ماموریت - اکنون اجباری است (در متن پیام دعوت استفاده می‌شود)
    address = Column(String, nullable=False)

    # دیگر مهارت ضروری/امتیازی جدا نداریم، فقط یک دسته مهارت مورد نیاز
    required_skills = Column(JSON, default=[])

    # ماموریت فقط یک تاریخ/ساعت دارد (نه بازه شروع و پایان)
    mission_date = Column(DateTime, nullable=False)

    status = Column(String, default="OPEN")  # OPEN, COMPLETED
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_volunteers = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)