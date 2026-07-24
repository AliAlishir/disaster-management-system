import os

files_to_update = {
    # ---------------------------------------------------------------
    # 1. مدل دیتابیس کاربر و داوطلب (با فیلد امتیاز rating)
    # ---------------------------------------------------------------
    "app/models/user.py": '''from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="VOLUNTEER")
    created_at = Column(DateTime, default=datetime.utcnow)

    volunteer_profile = relationship("VolunteerProfile", back_populates="user", uselist=False)


class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    city = Column(String, index=True, nullable=False)
    can_deploy = Column(Boolean, default=False)
    bio = Column(Text, nullable=True)
    skills = Column(JSON, default=[])

    rating = Column(Integer, default=5)  # امتیاز پیش‌فرض ۵ برای کاربر جدید

    available_from = Column(DateTime, nullable=True)
    available_to = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="volunteer_profile")
''',

    # ---------------------------------------------------------------
    # 2. مدل دیتابیس ماموریت (تفکیک مهارت حیاتی و امتیازی)
    # ---------------------------------------------------------------
    "app/models/mission.py": '''from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime
from app.database import Base

class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    city = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)

    essential_skills = Column(JSON, default=[])  # مهارت‌های ضروری (۷۰٪ وزن)
    bonus_skills = Column(JSON, default=[])      # مهارت‌های امتیازی (۳۰٪ وزن)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)
''',

    # ---------------------------------------------------------------
    # 3. Schema جدید ماموریت برای Pydantic
    # ---------------------------------------------------------------
    "app/schemas/mission.py": '''from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MissionCreateSchema(BaseModel):
    title: str
    city: str
    address: Optional[str] = None
    essential_skills: List[str]  # مهارت‌های حیاتی
    bonus_skills: List[str] = [] # مهارت‌های امتیازی
    start_time: datetime
    end_time: datetime

class MissionResponseSchema(BaseModel):
    id: int
    title: str
    city: str
    address: Optional[str]
    essential_skills: List[str]
    bonus_skills: List[str]
    start_time: datetime
    end_time: datetime
    status: str

    class Config:
        from_attributes = True
''',

    # ---------------------------------------------------------------
    # 4. موتور تطبیق پیشرفته (تطبیق معنایی AI + وزن‌دهی + امتیاز چندبعدی)
    # ---------------------------------------------------------------
    "app/services/matching.py": '''import json
import requests
from sqlalchemy.orm import Session
from app.models.mission import Mission
from app.models.user import VolunteerProfile
from app.config import settings


def evaluate_semantic_skill_match(vol_skills: list[str], required_skills: list[str]) -> float:
    """
    لایه ۱: استفاده از هوش مصنوعی برای سنجش تشابه معنایی کلمات (مثلا وانت = خودرو باری)
    """
    if not required_skills:
        return 1.0
    if not vol_skills:
        return 0.0

    vol_set = set(s.strip().lower() for s in vol_skills)
    req_set = set(s.strip().lower() for s in required_skills)
    exact_matches = vol_set.intersection(req_set)

    # اگر تطبیق کلمه‌ای کاملاً ۱۰۰٪ بود، نیازی به مصرف API نیست
    if len(exact_matches) == len(req_set):
        return 1.0

    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_YOUR"):
        return len(exact_matches) / len(req_set)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    تو یک ارزیاب مهارت در مدیریت بحران هستی.
    لیست مهارت‌های مورد نیاز ماموریت: {required_skills}
    لیست مهارت‌های موجود داوطلب: {vol_skills}

    این دو لیست را از نظر معنایی و مفهومی مقایسه کن (مثلا "پرستار" پوشش‌دهنده "کمک‌های اولیه" است، یا "وانت" با "خودروی باری" مترادف است).
    مشخص کن داوطلب چند درصد از مهارت‌های مورد نیاز ماموریت را پوشش می‌دهد.
    خروجی باید **دقیقاً و فقط** یک JSON با کلید 'match_percentage' (عددی بین 0 تا 100) باشد.
    مثال خروجی: {{"match_percentage": 85}}
    """

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            ai_content = json.loads(res_data["choices"][0]["message"]["content"])
            percentage = float(ai_content.get("match_percentage", 0))
            return max(0.0, min(1.0, percentage / 100.0))
    except Exception as e:
        print(f"خطا در تطبیق معنایی AI: {e}")

    return len(exact_matches) / len(req_set)


def calculate_smart_match(mission_id: int, db: Session):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        return None

    all_volunteers = db.query(VolunteerProfile).all()
    matched_results = []

    for vol in all_volunteers:
        # -------------------------------------------------------------
        # فیلتر ۱: بررسی شرط شهر / اعزام
        # -------------------------------------------------------------
        is_local = (vol.city.strip().lower() == mission.city.strip().lower())
        if not is_local and not vol.can_deploy:
            continue

        # -------------------------------------------------------------
        # فیلتر ۲: هم‌پوشانی زمانی
        # -------------------------------------------------------------
        is_time_match = (vol.available_from <= mission.start_time) and (vol.available_to >= mission.end_time)
        if not is_time_match:
            continue

        # -------------------------------------------------------------
        # فیلتر ۳ - لایه ۱ و ۲: سنجش معنایی AI + وزن‌دهی مهارت‌ها
        # -------------------------------------------------------------
        vol_skills = vol.skills or []
        essential_req = mission.essential_skills or []
        bonus_req = mission.bonus_skills or []

        # ۱. سنجش معنایی با AI
        essential_score = evaluate_semantic_skill_match(vol_skills, essential_req)
        bonus_score = evaluate_semantic_skill_match(vol_skills, bonus_req)

        # ۲. اعمال وزن ۷۰٪ ضروری + ۳۰٪ امتیازی
        if bonus_req:
            skill_score_percent = (essential_score * 70) + (bonus_score * 30)
        else:
            skill_score_percent = essential_score * 100

        # -------------------------------------------------------------
        # فیلتر ۳ - لایه ۳: ماتریس امتیازدهی چندبعدی
        # -------------------------------------------------------------
        # الف) نمره مهارت (وزن ۶۰٪ از نمره نهایی)
        weighted_skill_score = (skill_score_percent / 100) * 60

        # ب) نمره بومی بودن / سرعت رسیدن (وزن ۲۵٪ از نمره نهایی)
        proximity_score = 100 if is_local else 50
        weighted_proximity_score = (proximity_score / 100) * 25

        # ج) نمره سابقه و امتیاز داوطلب (وزن ۱۵٪ از نمره نهایی)
        # اگر داوطلب جدید باشد، امتیاز ۵ به‌صورت پیش‌فرض لحاظ می‌شود
        user_rating = vol.rating if vol.rating is not None else 5
        weighted_rating_score = (user_rating / 5) * 15

        # محاسبه نمره نهایی کل (از ۱۰۰٪)
        total_final_score = round(weighted_skill_score + weighted_proximity_score + weighted_rating_score, 1)

        matched_results.append({
            "volunteer_id": vol.user_id,
            "volunteer_name": vol.user.full_name,
            "phone_number": vol.user.phone_number,
            "city": vol.city,
            "is_local": is_local,
            "needs_deployment": not is_local,
            "rating": user_rating,
            "skills": vol_skills,
            "score_breakdown": {
                "total_score": f"{total_final_score}%",
                "semantic_skill_match": f"{round(skill_score_percent, 1)}%",
                "proximity_bonus": "۱۰۰٪ (بومی)" if is_local else "۵۰٪ (نیازمند اعزام)",
                "rating_bonus": f"{user_rating}/5 ستاره"
            }
        })

    # مرتب‌سازی بر اساس بالاترین نمره نهایی کل
    matched_results.sort(
        key=lambda x: float(x["score_breakdown"]["total_score"].replace("%", "")), 
        reverse=True
    )

    return {
        "mission_id": mission.id,
        "mission_title": mission.title,
        "mission_city": mission.city,
        "recommended_volunteers": matched_results
    }
'''
}


def update():
    for file_path, content in files_to_update.items():
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"✅ فایل بروزرسانی شد: {file_path}")

    # پاک کردن دیتابیس قدیمی برای ساخت جداول جدید
    if os.path.exists("disaster.db"):
        os.remove("disaster.db")
        print("🗑️ دیتابیس قدیمی پاک شد تا جداول جدید با فیلد امتیاز و مهارت‌های جدید ساخته شوند.")

    print("\n🎉 سیستم تطبیق کامل ۳ لایه‌ای با موفقیت جایگزین شد!")


if __name__ == "__main__":
    update()