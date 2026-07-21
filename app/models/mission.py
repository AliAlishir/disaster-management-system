from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from datetime import datetime
from app.database import Base

class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    province = Column(String, index=True, nullable=False)
    city = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)

    essential_skills = Column(JSON, default=[])
    bonus_skills = Column(JSON, default=[])

    # همگام‌سازی نام ستون‌ها با درخواست فرانت‌اند
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    status = Column(String, default="OPEN") # OPEN, COMPLETED
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_volunteers = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)