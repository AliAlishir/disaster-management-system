from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="VOLUNTEER")  # ADMIN, OPERATOR, VOLUNTEER
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("VolunteerProfile", back_populates="user", uselist=False)

class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    # === رفع باگ تکرار: هر کاربر فقط دقیقاً یک پروفایل می‌تواند داشته باشد ===
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    province = Column(String, nullable=True)
    city = Column(String, nullable=True)
    can_deploy = Column(Boolean, default=False)
    bio = Column(String, nullable=True)
    skills = Column(JSON, default=[])
    rating = Column(Float, default=5.0)
    available_from = Column(DateTime, nullable=True)
    available_to = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="profile")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # === رفع باگ خوانده‌شدن پیام برای همه ===
    # دیگر هیچ پیامی receiver_id خالی (پیام مشترک بین همه) نخواهد داشت؛
    # پیام‌های همگانی هم از این پس به‌ازای هر کاربر یک رکورد جداگانه دارند
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    category = Column(String, default="سیستمی")  # ماموریت، سیستمی
    is_read = Column(Boolean, default=False)
    mission_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)