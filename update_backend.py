import os

files_to_create = {
    # ---------------------------------------------------------------
    # 1. Models (جداول دیتابیس)
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
    role = Column(String, default="VOLUNTEER")  # ADMIN, OPERATOR, VOLUNTEER
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

    available_from = Column(DateTime, nullable=True)
    available_to = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="volunteer_profile")
''',

    "app/models/mission.py": '''from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime
from app.database import Base

class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    city = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)

    required_skills = Column(JSON, default=[])
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    status = Column(String, default="OPEN")  # OPEN, IN_PROGRESS, COMPLETED
    created_at = Column(DateTime, default=datetime.utcnow)
''',

    "app/models/__init__.py": '''from app.models.user import User, VolunteerProfile
from app.models.mission import Mission
''',

    # ---------------------------------------------------------------
    # 2. Schemas (اعتبارسنجی ورودی و خروجی‌ها)
    # ---------------------------------------------------------------
    "app/schemas/user.py": '''from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VolunteerRegisterSchema(BaseModel):
    full_name: str
    phone_number: str
    city: str
    can_deploy: bool = False
    bio_text: str
    available_from: datetime
    available_to: datetime

class VolunteerResponseSchema(BaseModel):
    id: int
    full_name: str
    phone_number: str
    city: str
    can_deploy: bool
    skills: List[str]
    available_from: datetime
    available_to: datetime

    class Config:
        from_attributes = True
''',

    "app/schemas/mission.py": '''from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MissionCreateSchema(BaseModel):
    title: str
    city: str
    address: Optional[str] = None
    required_skills: List[str]
    start_time: datetime
    end_time: datetime

class MissionResponseSchema(BaseModel):
    id: int
    title: str
    city: str
    address: Optional[str]
    required_skills: List[str]
    start_time: datetime
    end_time: datetime
    status: str

    class Config:
        from_attributes = True
''',

    # ---------------------------------------------------------------
    # 3. Services (هوش مصنوعی و منطق تطبیق هوشمند)
    # ---------------------------------------------------------------
    "app/services/ai_service.py": '''import requests
import json
from app.config import settings

def extract_skills_with_ai(bio_text: str) -> list[str]:
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_YOUR"):
        print("هشدار: کلید API تنظیم نشده است.")
        return []

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "تو یک دستیار مدیریت بحران هستی. وظیفه تو استخراج دقیق مهارت‌ها، "
                    "امکانات (مثل خودرو) و تجهیزات ذکر شده در متن کاربر است. "
                    "خروجی باید دقیقاً و فقط یک JSON با کلید 'skills' باشد."
                )
            },
            {"role": "user", "content": bio_text}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            ai_content = json.loads(res_data["choices"][0]["message"]["content"])
            return ai_content.get("skills", [])
    except Exception as e:
        print(f"خطا در فراخوانی API هوش مصنوعی: {e}")

    return []
''',

    "app/services/matching.py": '''from sqlalchemy.orm import Session
from app.models.mission import Mission
from app.models.user import VolunteerProfile

def calculate_smart_match(mission_id: int, db: Session):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        return None

    all_volunteers = db.query(VolunteerProfile).all()
    matched_results = []

    for vol in all_volunteers:
        # ۱. فیلتر شهری (شهر یکسان یا قابلیت اعزام به شهرهای دیگر)
        is_city_match = (vol.city.strip().lower() == mission.city.strip().lower()) or vol.can_deploy
        if not is_city_match:
            continue

        # ۲. هم‌پوشانی زمانی (زمان آزادی داوطلب باید بازه ماموریت را بپوشاند)
        is_time_match = (vol.available_from <= mission.start_time) and (vol.available_to >= mission.end_time)
        if not is_time_match:
            continue

        # ۳. محاسبه درصد تطبیق مهارت‌ها
        req_skills = set(mission.required_skills or [])
        vol_skills = set(vol.skills or [])

        matched_skills = req_skills.intersection(vol_skills)
        match_score = 0
        if req_skills:
            match_score = int((len(matched_skills) / len(req_skills)) * 100)

        matched_results.append({
            "volunteer_id": vol.user_id,
            "volunteer_name": vol.user.full_name,
            "phone_number": vol.user.phone_number,
            "city": vol.city,
            "needs_deployment": vol.city.strip().lower() != mission.city.strip().lower(),
            "matched_skills": list(matched_skills),
            "all_skills": vol.skills,
            "match_score": f"{match_score}%"
        })

    # مرتب‌سازی بر اساس بالاترین درصد تطبیق
    matched_results.sort(key=lambda x: int(x["match_score"].replace("%", "")), reverse=True)
    return {
        "mission_id": mission.id,
        "mission_title": mission.title,
        "mission_city": mission.city,
        "recommended_volunteers": matched_results
    }
''',

    # ---------------------------------------------------------------
    # 4. Routers (API Endpoints)
    # ---------------------------------------------------------------
    "app/routers/volunteers.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.schemas.user import VolunteerRegisterSchema, VolunteerResponseSchema
from app.services.ai_service import extract_skills_with_ai

router = APIRouter(prefix="/api/volunteers", tags=["Volunteers"])

@router.post("/register")
def register_volunteer(data: VolunteerRegisterSchema, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.phone_number == data.phone_number).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="کاربری با این شماره تلفن قبلاً ثبت‌نام کرده است.")

    # ۱. استخراج مهارت‌ها با AI
    extracted_skills = extract_skills_with_ai(data.bio_text)

    # ۲. ذخیره کاربر
    new_user = User(full_name=data.full_name, phone_number=data.phone_number, role="VOLUNTEER")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ۳. ذخیره پروفایل
    profile = VolunteerProfile(
        user_id=new_user.id,
        city=data.city,
        can_deploy=data.can_deploy,
        bio=data.bio_text,
        skills=extracted_skills,
        available_from=data.available_from,
        available_to=data.available_to
    )
    db.add(profile)
    db.commit()

    return {
        "message": "داوطلب با موفقیت ثبت شد",
        "user_id": new_user.id,
        "extracted_skills": extracted_skills
    }

@router.get("/", response_model=List[VolunteerResponseSchema])
def get_all_volunteers(db: Session = Depends(get_db)):
    profiles = db.query(VolunteerProfile).all()
    result = []
    for p in profiles:
        result.append({
            "id": p.user.id,
            "full_name": p.user.full_name,
            "phone_number": p.user.phone_number,
            "city": p.city,
            "can_deploy": p.can_deploy,
            "skills": p.skills or [],
            "available_from": p.available_from,
            "available_to": p.available_to
        })
    return result
''',

    "app/routers/missions.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.mission import Mission
from app.schemas.mission import MissionCreateSchema, MissionResponseSchema
from app.services.matching import calculate_smart_match

router = APIRouter(prefix="/api/missions", tags=["Missions"])

@router.post("/create", response_model=MissionResponseSchema)
def create_mission(data: MissionCreateSchema, db: Session = Depends(get_db)):
    new_mission = Mission(
        title=data.title,
        city=data.city,
        address=data.address,
        required_skills=data.required_skills,
        start_time=data.start_time,
        end_time=data.end_time
    )
    db.add(new_mission)
    db.commit()
    db.refresh(new_mission)
    return new_mission

@router.get("/", response_model=List[MissionResponseSchema])
def get_all_missions(db: Session = Depends(get_db)):
    return db.query(Mission).all()

@router.get("/{mission_id}/match")
def match_volunteers(mission_id: int, db: Session = Depends(get_db)):
    match_result = calculate_smart_match(mission_id, db)
    if not match_result:
        raise HTTPException(status_code=404, detail="ماموریت مورد نظر یافت نشد.")
    return match_result
''',

    # ---------------------------------------------------------------
    # 5. Main Entry Point (نقطه اتصال اصلی)
    # ---------------------------------------------------------------
    "app/main.py": '''from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import engine, Base
import app.models

from app.routers import volunteers, missions

# ایجاد خودکار جداول در دیتابیس SQLite
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="سیستم مدیریت داوطلبان با هوش مصنوعی و تطبیق هوشمند",
    version="1.0.0"
)

# اتصال پوشه فرانت‌اند
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ثبت Routerها
app.include_router(volunteers.router)
app.include_router(missions.router)

@app.get("/")
def root():
    return {"message": "سامانه مدیریت بحران آماده است", "swagger_docs": "/docs"}
'''
}


def update_backend():
    for file_path, content in files_to_create.items():
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"✅ فایل بروزرسانی شد: {file_path}")
    print("\n🎉 تمام کدهای بک‌اند به صورت کاملاً ساختاریافته قرار گرفتند!")


if __name__ == "__main__":
    update_backend()
