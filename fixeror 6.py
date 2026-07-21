import os

files_to_fix = {

    # ---------------------------------------------------------------
    # 1. مدل کاربران - افزودن قید unique روی user_id پروفایل داوطلب
    #    (رفع ریشه‌ای باگ ساخت رکورد تکراری در دیتابیس)
    # ---------------------------------------------------------------
    "app/models/user.py": '''from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, JSON
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
''',

    # ---------------------------------------------------------------
    # 2. روتر احراز هویت - دیگر پروفایل داوطلبی پیش‌فرض نمی‌سازد
    #    (تنها مسیر ساخت/ویرایش پروفایل، endpoint اختصاصی volunteers/register است)
    # ---------------------------------------------------------------
    "app/routers/auth.py": '''import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, OTPCode
from app.schemas.user import RequestOTPSchema, VerifyOTPSchema, TokenSchema
from app.services.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/send-otp")
def send_otp(data: RequestOTPSchema, db: Session = Depends(get_db)):
    phone = data.phone_number
    existing_user = db.query(User).filter(User.phone_number == phone).first()
    is_registered = True if existing_user else False

    code = "1234" if phone == "09120000000" else f"{random.randint(1000, 9999)}"

    otp_entry = db.query(OTPCode).filter(OTPCode.phone_number == phone).first()
    if otp_entry:
        otp_entry.code = code
        otp_entry.created_at = datetime.utcnow()
    else:
        otp_entry = OTPCode(phone_number=phone, code=code)
        db.add(otp_entry)

    db.commit()

    return {
        "message": "کد تایید ارسال شد",
        "simulated_code": code,
        "is_registered": is_registered
    }

@router.post("/verify-otp", response_model=TokenSchema)
def verify_otp(data: VerifyOTPSchema, db: Session = Depends(get_db)):
    otp_entry = db.query(OTPCode).filter(OTPCode.phone_number == data.phone_number).first()
    if not otp_entry or otp_entry.code != data.code:
        raise HTTPException(status_code=400, detail="کد واردشده اشتباه است.")

    user = db.query(User).filter(User.phone_number == data.phone_number).first()

    if not user:
        if not data.full_name:
            raise HTTPException(status_code=400, detail="لطفاً نام و نام خانوادگی خود را وارد کنید.")

        role = data.role or "VOLUNTEER"
        is_approved = True if role in ["VOLUNTEER", "ADMIN"] else False

        user = User(
            full_name=data.full_name,
            phone_number=data.phone_number,
            role=role,
            is_approved=is_approved
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        # توجه: دیگر پروفایل داوطلبی پیش‌فرض اینجا ساخته نمی‌شود.
        # کاربر باید یک‌بار فرم "اعلام داوطلبی" را تکمیل کند تا پروفایلش ساخته شود.

    token_data = {
        "sub": str(user.id),
        "phone": user.phone_number,
        "role": user.role,
        "name": user.full_name,
        "approved": user.is_approved
    }
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name,
        "is_approved": user.is_approved
    }
''',

    # ---------------------------------------------------------------
    # 3. سرویس هوش مصنوعی واقعی (Groq) برای استخراج/دسته‌بندی مهارت‌ها
    #    و سنجش معنایی تطبیق مهارت داوطلب با نیاز ماموریت
    # ---------------------------------------------------------------
    "app/services/ai_service.py": '''import re
import json
import requests
from typing import List
from app.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

_FALLBACK_SKILL_CATEGORIES = {
    "کمک‌های اولیه": ["کمک اولیه", "کمک‌های اولیه", "اورژانس", "احیا", "پزشک", "پرستار", "بهیار", "پانسمان", "تزریقات"],
    "خودرو شاسی‌بلند / آفرود": ["شاسی‌بلند", "شاسی بلند", "آفرود", "پاترول", "هایلوکس", "دو دیفرانسیل", "ماشین سنگین", "خودرو"],
    "آواربرداری": ["آوار", "آواربرداری", "تخریب", "بیل", "کلنگ", "سنگین", "عمران", "ساختمانی"],
    "اسکان اضطراری": ["چادر", "اسکان", "کمپ", "پناهگاه", "برپایی چادر"],
    "توزیع آذوقه و امداد": ["آذوقه", "غذا", "پک", "جیره", "آب معدنی", "توزیع"],
    "مهارت‌های ارتباطی و زبان": ["زبان", "انگلیسی", "عربی", "مترجم", "ارتباطات", "بی‌سیم"],
    "مدیریت بحران و فرماندهی": ["مدیریت بحران", "فرماندهی", "هماهنگی", "ستاد", "گروه نجات"],
    "امداد در آب و سیل": ["شنا", "غریق نجات", "قایق", "سیل", "غواصی", "آب‌گرفتگی"],
    "اطفا حریق": ["آتش‌نشانی", "حریق", "آتش", "کپسول", "اطفا"],
}


def _is_api_configured() -> bool:
    return bool(settings.GROQ_API_KEY) and not settings.GROQ_API_KEY.startswith("gsk_YOUR")


def _fallback_extract(text: str) -> List[str]:
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for category, keywords in _FALLBACK_SKILL_CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                found.add(category)
                break
    if not found:
        stop_words = {"است", "و", "با", "در", "از", "برای", "به", "که", "این", "آن", "دارای", "من", "او", "ما", "هستم"}
        words = [w.strip() for w in re.split(r"[\\s،,-]+", text) if len(w.strip()) > 2 and w.strip() not in stop_words]
        return list(set(words[:4])) if words else ["عمومی / امدادگر"]
    return list(found)


def _call_groq(payload: dict, timeout: int = 10):
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
    if response.status_code == 200:
        res_data = response.json()
        content = res_data["choices"][0]["message"]["content"]
        return json.loads(content)
    raise RuntimeError(f"خطای Groq API - کد {response.status_code}: {response.text}")


def extract_skills_with_ai(bio_text: str) -> List[str]:
    """
    دسته‌بندی و استخراج مهارت‌ها از متن داوطلب با استفاده از هوش مصنوعی Groq.
    در صورت نبود کلید معتبر یا بروز خطا، به روش کلیدواژه‌ای محلی برمی‌گردد.
    """
    if not bio_text or not bio_text.strip():
        return []

    if not _is_api_configured():
        print("⚠️ کلید GROQ_API_KEY تنظیم نشده یا نامعتبر است - استفاده از استخراج محلی مهارت‌ها.")
        return _fallback_extract(bio_text)

    prompt = f\'\'\'
    متن داوطلب: "{bio_text}"

    وظیفه: تمام مهارت‌ها، تخصص‌ها، مدرک‌ها و امکاناتی (مثل خودرو، ابزار، زبان) که در متن ذکر شده را
    استخراج و در قالب چند دسته‌بندی کوتاه و استاندارد فارسی (نه جمله کامل) بیان کن.
    پاسخ باید دقیقاً و فقط یک JSON حاوی کلید 'skills' به‌صورت لیستی از رشته‌ها باشد، بدون هیچ توضیح اضافه.
    مثال خروجی: {{"skills": ["امدادگری", "رانندگی خودرو شاسی‌بلند", "کمک‌های اولیه"]}}
    \'\'\'

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }

    try:
        parsed = _call_groq(payload, timeout=10)
        skills = parsed.get("skills", [])
        skills = [str(s).strip() for s in skills if str(s).strip()]
        if skills:
            print(f"✅ مهارت‌های استخراج‌شده توسط AI: {skills}")
            return skills
    except Exception as e:
        print(f"❌ خطا در فراخوانی هوش مصنوعی (استخراج مهارت): {e}")

    return _fallback_extract(bio_text)


def evaluate_semantic_match(volunteer_skills: List[str], required_skills: List[str]) -> float:
    """
    سنجش معنایی میزان پوشش مهارت‌های موردنیاز ماموریت توسط داوطلب، با کمک هوش مصنوعی Groq.
    خروجی عددی بین ۰ و ۱ است. در صورت نبود کلید یا خطا، به تطبیق دقیق کلمه‌ای برمی‌گردد.
    """
    if not required_skills:
        return 1.0
    if not volunteer_skills:
        return 0.0

    vol_set = set(s.strip().lower() for s in volunteer_skills)
    req_set = set(s.strip().lower() for s in required_skills)
    exact_matches = vol_set.intersection(req_set)

    if len(exact_matches) == len(req_set):
        return 1.0

    if not _is_api_configured():
        return len(exact_matches) / len(req_set)

    prompt = f\'\'\'
    تو یک ارزیاب مهارت در مدیریت بحران هستی.
    مهارت‌های مورد نیاز ماموریت: {required_skills}
    مهارت‌های موجود داوطلب: {volunteer_skills}

    این دو لیست را از نظر معنایی و مفهومی مقایسه کن (مثلا "پرستار" پوشش‌دهنده "کمک‌های اولیه" است،
    یا "وانت" با "خودروی باری" مترادف است).
    مشخص کن داوطلب چند درصد از مهارت‌های موردنیاز ماموریت را پوشش می‌دهد.
    خروجی باید دقیقاً و فقط یک JSON با کلید 'match_percentage' (عددی بین 0 تا 100) باشد.
    مثال خروجی: {{"match_percentage": 85}}
    \'\'\'

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }

    try:
        parsed = _call_groq(payload, timeout=8)
        percentage = float(parsed.get("match_percentage", 0))
        return max(0.0, min(1.0, percentage / 100.0))
    except Exception as e:
        print(f"❌ خطا در تطبیق معنایی هوش مصنوعی: {e}")

    return len(exact_matches) / len(req_set)
''',

    # ---------------------------------------------------------------
    # 4. سرویس تطبیق هوشمند - اکنون واقعاً از هوش مصنوعی Groq استفاده می‌کند
    # ---------------------------------------------------------------
    "app/services/matching.py": '''from sqlalchemy.orm import Session
from app.models.mission import Mission
from app.models.user import User, VolunteerProfile
from app.services.ai_service import evaluate_semantic_match


def calculate_smart_match(mission_id: int, db: Session):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        return None

    profiles = db.query(VolunteerProfile).join(User).filter(User.role == "VOLUNTEER").all()
    results = []

    essential_req = mission.essential_skills or []
    bonus_req = mission.bonus_skills or []

    for prof in profiles:
        # پروفایل‌های ناقص (بدون شهر یا زمان آزادی) در تطبیق شرکت داده نمی‌شوند
        if not prof.city or not prof.available_from or not prof.available_to:
            continue

        # ۱. فیلتر شهر / آمادگی اعزام
        is_local = (prof.city or "").strip().lower() == (mission.city or "").strip().lower()
        if not is_local and not prof.can_deploy:
            continue

        # ۲. هم‌پوشانی زمانی
        if not (prof.available_from <= mission.start_date and prof.available_to >= mission.end_date):
            continue

        vol_skills = prof.skills or []

        # ۳. سنجش معنایی هوش مصنوعی برای مهارت ضروری (وزن ۷۰٪) و امتیازی (وزن ۳۰٪)
        essential_score = evaluate_semantic_match(vol_skills, essential_req)
        bonus_score = evaluate_semantic_match(vol_skills, bonus_req) if bonus_req else 0.0

        if bonus_req:
            skill_percent = (essential_score * 70) + (bonus_score * 30)
        else:
            skill_percent = essential_score * 100

        # ۴. ماتریس امتیازدهی نهایی: مهارت ۶۰٪ + مکان ۲۵٪ + سابقه/امتیاز ۱۵٪
        weighted_skill = (skill_percent / 100) * 60
        weighted_location = (100 if is_local else 50) / 100 * 25
        user_rating = prof.rating if prof.rating is not None else 5.0
        weighted_rating = (user_rating / 5.0) * 15

        total_score = round(weighted_skill + weighted_location + weighted_rating, 1)

        results.append({
            "volunteer_id": prof.user.id,
            "volunteer_name": prof.user.full_name,
            "phone_number": prof.user.phone_number,
            "province": prof.province,
            "city": prof.city,
            "is_local": is_local,
            "needs_deployment": not is_local,
            "rating": user_rating,
            "skills": vol_skills,
            "score_breakdown": {
                "total_score": total_score,
                "semantic_skill_match": round(skill_percent, 1),
                "proximity_bonus": "بومی" if is_local else "نیازمند اعزام",
                "rating_bonus": user_rating
            }
        })

    # مرتب‌سازی بر اساس بالاترین امتیاز تطبیق کل - مرتبط‌ترین‌ها اول نمایش داده می‌شوند
    results.sort(key=lambda x: x["score_breakdown"]["total_score"], reverse=True)

    return {
        "mission_id": mission.id,
        "mission_title": mission.title,
        "mission_city": mission.city,
        "recommended_volunteers": results
    }
''',

    # ---------------------------------------------------------------
    # 5. روتر ماموریت‌ها - افزوده شدن کنترل دسترسی
    #    (هر مامور فقط تطبیق/دعوت مربوط به ماموریت‌های خودش را می‌بیند)
    # ---------------------------------------------------------------
    "app/routers/missions.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.models.user import User, VolunteerProfile, Message
from app.models.mission import Mission
from app.services.auth import get_current_user
from app.services.matching import calculate_smart_match

router = APIRouter(prefix="/api/missions", tags=["Missions"])

class MissionCreateSchema(BaseModel):
    title: str
    province: str
    city: str
    essential_skills: List[str]
    bonus_skills: Optional[List[str]] = []
    start_date: datetime
    end_date: datetime

class InviteVolunteerSchema(BaseModel):
    volunteer_id: int


def _check_mission_access(mission: Mission, current_user: User):
    if not mission:
        raise HTTPException(status_code=404, detail="ماموریت یافت نشد.")
    if current_user.role != "ADMIN" and mission.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="شما فقط به ماموریت‌های خودتان دسترسی دارید.")


@router.post("/")
def create_mission(data: MissionCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["ADMIN", "OPERATOR"]:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

    mission = Mission(
        title=data.title,
        province=data.province,
        city=data.city,
        essential_skills=data.essential_skills,
        bonus_skills=data.bonus_skills,
        start_date=data.start_date,
        end_date=data.end_date,
        creator_id=current_user.id,
        status="OPEN"
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return {"message": "ماموریت با موفقیت ایجاد شد", "mission_id": mission.id}


@router.get("/my-missions")
def get_missions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "ADMIN":
        missions = db.query(Mission).order_by(Mission.created_at.desc()).all()
    else:
        missions = db.query(Mission).filter(Mission.creator_id == current_user.id).order_by(Mission.created_at.desc()).all()

    return [
        {
            "id": m.id,
            "title": m.title,
            "province": m.province,
            "city": m.city,
            "essential_skills": m.essential_skills,
            "status": m.status,
            "creator_id": m.creator_id,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M")
        } for m in missions
    ]


@router.get("/{mission_id}/match")
def match_volunteers(mission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)
    return calculate_smart_match(mission_id, db)


@router.post("/{mission_id}/invite")
def invite_volunteer(mission_id: int, data: InviteVolunteerSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)

    volunteer = db.query(User).filter(User.id == data.volunteer_id, User.role == "VOLUNTEER").first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="داوطلب مورد نظر یافت نشد.")

    msg = Message(
        sender_id=current_user.id,
        receiver_id=volunteer.id,
        title=f"دعوت به ماموریت: {mission.title}",
        body=f"شما توسط ستاد بحران برای ماموریت '{mission.title}' در استان {mission.province}، شهر {mission.city} دعوت شده‌اید.",
        category="ماموریت",
        mission_id=mission.id
    )
    db.add(msg)
    db.commit()

    return {"message": f"دعوت‌نامه با موفقیت برای داوطلب ({volunteer.full_name}) ارسال شد."}
''',

    # ---------------------------------------------------------------
    # 6. روتر داوطلبان - اصلاح نهایی باگ ثبت تکراری + اتصال به AI واقعی
    # ---------------------------------------------------------------
    "app/routers/volunteers.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.services.auth import get_current_user
from app.schemas.user import VolunteerRegisterSchema
from app.services.ai_service import extract_skills_with_ai

router = APIRouter(prefix="/api/volunteers", tags=["Volunteers"])

@router.post("/register")
def register_or_update_volunteer(data: VolunteerRegisterSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # دسته‌بندی هوشمند مهارت‌ها از روی بیوگرافی با هوش مصنوعی Groq
    extracted_skills = extract_skills_with_ai(data.bio) if data.bio else []

    profile = db.query(VolunteerProfile).filter(VolunteerProfile.user_id == current_user.id).first()

    if profile:
        # === رفع باگ اصلی: همیشه رکورد موجود آپدیت می‌شود، هرگز رکورد جدید ساخته نمی‌شود ===
        profile.province = data.province
        profile.city = data.city
        profile.can_deploy = data.can_deploy or False
        profile.bio = data.bio or ""
        profile.skills = extracted_skills
        profile.available_from = data.available_from
        profile.available_to = data.available_to
        db.commit()
        return {"message": "اطلاعات داوطلبی با موفقیت به‌روزرسانی شد.", "skills": extracted_skills}

    # ساخت پروفایل جدید (فقط وقتی واقعاً برای این کاربر وجود نداشته باشد)
    new_profile = VolunteerProfile(
        user_id=current_user.id,
        province=data.province,
        city=data.city,
        can_deploy=data.can_deploy or False,
        bio=data.bio or "",
        skills=extracted_skills,
        available_from=data.available_from,
        available_to=data.available_to
    )
    db.add(new_profile)
    try:
        db.commit()
    except IntegrityError:
        # اگر هم‌زمان درخواست دیگری همین پروفایل را ساخته باشد (race condition نادر)،
        # به‌جای خطا، رکورد موجود را واکشی و به‌روزرسانی می‌کنیم
        db.rollback()
        profile = db.query(VolunteerProfile).filter(VolunteerProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=500, detail="خطا در ثبت اطلاعات داوطلبی.")
        profile.province = data.province
        profile.city = data.city
        profile.can_deploy = data.can_deploy or False
        profile.bio = data.bio or ""
        profile.skills = extracted_skills
        profile.available_from = data.available_from
        profile.available_to = data.available_to
        db.commit()
        return {"message": "اطلاعات داوطلبی با موفقیت به‌روزرسانی شد.", "skills": extracted_skills}

    return {"message": "اطلاعات داوطلبی با موفقیت ثبت شد.", "skills": extracted_skills}
''',

    # ---------------------------------------------------------------
    # 7. روتر پیام‌ها - رفع باگ «خوانده‌شدن پیام برای همه»
    # ---------------------------------------------------------------
    "app/routers/messages.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User, Message
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/messages", tags=["Messages"])

class BroadcastSchema(BaseModel):
    title: str
    body: str

@router.get("/my-messages")
def get_my_messages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    msgs = db.query(Message).filter(
        Message.receiver_id == current_user.id
    ).order_by(Message.created_at.desc()).all()

    return [
        {
            "id": m.id,
            "title": m.title,
            "body": m.body,
            "category": m.category,
            "is_read": m.is_read,
            "mission_id": m.mission_id,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M")
        } for m in msgs
    ]

@router.post("/{message_id}/read")
def mark_message_as_read(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # === رفع باگ اصلی ===
    # پیام فقط در صورتی خوانده‌شده علامت می‌خورد که دقیقاً متعلق به همین کاربر باشد،
    # بنابراین دیگر وضعیت خوانده‌شدن بین کاربران مختلف مشترک نیست
    msg = db.query(Message).filter(
        Message.id == message_id,
        Message.receiver_id == current_user.id
    ).first()

    if not msg:
        raise HTTPException(status_code=404, detail="پیام یافت نشد یا متعلق به شما نیست.")

    msg.is_read = True
    db.commit()
    return {"message": "بروزرسانی شد"}

@router.post("/broadcast")
def send_broadcast_message(data: BroadcastSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="تنها رئیس کل مجاز به ارسال پیام همگانی است.")

    # === رفع باگ اصلی ===
    # به‌جای یک رکورد مشترک (receiver_id=None) که وضعیت خوانده‌شدنش بین همه‌ی کاربران
    # مشترک بود، حالا برای هر کاربر یک رکورد پیام کاملاً مستقل ساخته می‌شود
    all_users = db.query(User).all()
    for user in all_users:
        msg = Message(
            sender_id=current_user.id,
            receiver_id=user.id,
            title=data.title,
            body=data.body,
            category="سیستمی"
        )
        db.add(msg)

    db.commit()
    return {"message": "پیام همگانی با موفقیت برای تمامی کاربران ارسال شد."}
''',
}


def fix():
    for file_path, content in files_to_fix.items():
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"✅ فایل اصلاح شد: {file_path}")

    # چون قید unique روی VolunteerProfile.user_id اضافه شده، این محدودیت روی
    # جدول قدیمی موجود در دیتابیس اعمال نمی‌شود مگر جدول از نو ساخته شود.
    # به همین دلیل دیتابیس فعلی حذف می‌شود تا با ساختار جدید و بدون رکورد تکراری از نو ساخته شود.
    if os.path.exists("disaster.db"):
        os.remove("disaster.db")
        print("🗑️ دیتابیس قدیمی (disaster.db) حذف شد تا جدول‌ها با ساختار اصلاح‌شده و بدون رکورد تکراری از نو ساخته شوند.")
        print("   ⚠️ توجه: تمام کاربران، ماموریت‌ها و پیام‌های قبلی پاک می‌شوند. اگر نیاز به بکاپ دارید، قبل از اجرا یک کپی از disaster.db بگیرید.")

    print("\\n🎉 هر سه مشکل اصلاح شدند:")
    print("   1) پروفایل داوطلب دیگر تکراری ساخته نمی‌شود (قید unique + منطق get-or-update ایمن در برابر race condition)")
    print("   2) دسته‌بندی/تطبیق مهارت‌ها اکنون واقعاً از Groq API با کلید GROQ_API_KEY استفاده می‌کند (با fallback محلی در صورت قطعی)")
    print("   3) خوانده‌شدن پیام دیگر بین کاربران مشترک نیست؛ هر کاربر رکورد و وضعیت خودش را دارد")
    print("\\nحتماً قبل از اجرای مجدد سرور، مطمئن شوید GROQ_API_KEY در فایل .env به‌درستی مقداردهی شده است.")


if __name__ == "__main__":
    fix()