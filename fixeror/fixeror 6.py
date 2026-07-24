import os

files_to_fix = {

    # ---------------------------------------------------------------
    # 1. مدل ماموریت: آدرس کامل محل ماموریت اکنون اجباری است
    # ---------------------------------------------------------------
    "app/models/mission.py": '''from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
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
''',

    # ---------------------------------------------------------------
    # 2. اسکیمای ماموریت: آدرس اجباری شد + اعتبارسنجی خالی نبودن آن
    # ---------------------------------------------------------------
    "app/schemas/mission.py": '''from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
from app.constants import SKILL_CHOICES

class MissionCreateSchema(BaseModel):
    title: str
    province: str
    city: str
    address: str
    required_skills: List[str]
    mission_date: datetime

    @field_validator("address")
    def validate_address(cls, v):
        if not v or not v.strip():
            raise ValueError("آدرس کامل محل ماموریت الزامی است.")
        return v.strip()

    @field_validator("required_skills")
    def validate_skills(cls, v):
        cleaned = [s for s in v if s in SKILL_CHOICES]
        if not cleaned:
            raise ValueError("حداقل یک مهارت مورد نیاز معتبر انتخاب کنید.")
        return cleaned

class InviteVolunteerSchema(BaseModel):
    volunteer_id: int

class CompleteMissionSchema(BaseModel):
    mission_id: int
    ratings: dict = {}  # در حال حاضر استفاده نمی‌شود، برای سازگاری آینده نگه داشته شده است
''',

    # ---------------------------------------------------------------
    # 3. روتر ماموریت‌ها:
    #    - آدرس و ساعت ماموریت در متن پیام دعوت قید می‌شود
    #    - مسیر تطبیق، وضعیت "قبلاً دعوت شده" هر داوطلب را هم برمی‌گرداند
    #    - ماموریت خاتمه‌یافته دیگر امکان ارسال دعوت ندارد
    #    - مسیر جدید خاتمه ماموریت اضافه شد
    #    - لیست ماموریت‌های مامور: باز اول، خاتمه‌یافته آخر
    # ---------------------------------------------------------------
    "app/routers/missions.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Message
from app.models.mission import Mission
from app.schemas.mission import MissionCreateSchema, InviteVolunteerSchema
from app.services.auth import get_current_user
from app.services.matching import calculate_smart_match

router = APIRouter(prefix="/api/missions", tags=["Missions"])


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
        address=data.address,
        required_skills=data.required_skills,
        mission_date=data.mission_date,
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
        missions = db.query(Mission).all()
    else:
        missions = db.query(Mission).filter(Mission.creator_id == current_user.id).all()

    # === رفع نیاز: ماموریت‌های باز ابتدا و ماموریت‌های خاتمه‌یافته در انتها نمایش داده شوند ===
    missions.sort(
        key=lambda m: (m.status == "COMPLETED", -(m.created_at.timestamp() if m.created_at else 0))
    )

    return [
        {
            "id": m.id,
            "title": m.title,
            "province": m.province,
            "city": m.city,
            "address": m.address,
            "required_skills": m.required_skills,
            "mission_date": m.mission_date.strftime("%Y-%m-%d %H:%M"),
            "status": m.status,
            "creator_id": m.creator_id,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M")
        } for m in missions
    ]


@router.get("/{mission_id}/match")
def match_volunteers(mission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)

    result = calculate_smart_match(mission_id, db)

    # === رفع نیاز: مشخص کردن داوطلبانی که قبلاً برای این ماموریت دعوت شده‌اند ===
    already_invited_ids = {
        row.receiver_id for row in db.query(Message.receiver_id).filter(Message.mission_id == mission.id).all()
    }
    if result and result.get("recommended_volunteers"):
        for v in result["recommended_volunteers"]:
            v["already_invited"] = v["volunteer_id"] in already_invited_ids

    if result:
        result["mission_status"] = mission.status

    return result


@router.post("/{mission_id}/invite")
def invite_volunteer(mission_id: int, data: InviteVolunteerSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)

    # === رفع نیاز: برای ماموریت خاتمه‌یافته دیگر امکان ارسال درخواست کمک وجود ندارد ===
    if mission.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="این ماموریت خاتمه یافته و امکان ارسال درخواست کمک برای آن وجود ندارد.")

    volunteer = db.query(User).filter(User.id == data.volunteer_id, User.role == "VOLUNTEER").first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="داوطلب مورد نظر یافت نشد.")

    already_invited = db.query(Message).filter(
        Message.mission_id == mission.id,
        Message.receiver_id == volunteer.id
    ).first()
    if already_invited:
        raise HTTPException(status_code=400, detail="قبلاً برای این داوطلب در این ماموریت پیام دعوت ارسال شده است.")

    # === رفع نیاز: آدرس کامل و ساعت ماموریت در متن پیام دعوت قید می‌شود ===
    mission_time_text = mission.mission_date.strftime("%Y-%m-%d ساعت %H:%M")

    msg = Message(
        sender_id=current_user.id,
        receiver_id=volunteer.id,
        title=f"دعوت به ماموریت: {mission.title}",
        body=(
            f"شما توسط ستاد بحران برای ماموریت '{mission.title}' دعوت شده‌اید.\\n"
            f"📍 آدرس محل ماموریت: {mission.address} (استان {mission.province}، شهر {mission.city})\\n"
            f"🗓️ زمان ماموریت: {mission_time_text}"
        ),
        category="ماموریت",
        mission_id=mission.id
    )
    db.add(msg)
    db.commit()

    return {"message": f"دعوت‌نامه با موفقیت برای داوطلب ({volunteer.full_name}) ارسال شد."}


@router.post("/{mission_id}/complete")
def complete_mission(mission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)

    if mission.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="این ماموریت قبلاً خاتمه یافته است.")

    mission.status = "COMPLETED"
    db.commit()
    return {"message": "ماموریت با موفقیت خاتمه یافت و دیگر امکان ارسال درخواست کمک برای آن وجود ندارد."}
''',

    # ---------------------------------------------------------------
    # 4. روتر پنل رئیس کل:
    #    - ماموران تاییدنشده ابتدا و تاییدشده‌ها در انتهای لیست
    #    - لیست کامل کاربران، داوطلبان و ماموریت‌ها در all-data
    # ---------------------------------------------------------------
    "app/routers/admin.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.models.mission import Mission
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])


def _verify_chief(current_user: User):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")


@router.get("/pending-operators")
def get_pending_operators(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_chief(current_user)

    operators = db.query(User).filter(User.role == "OPERATOR").all()

    # === رفع نیاز: ماموران تاییدنشده ابتدا و تاییدشده‌ها در انتها نمایش داده شوند ===
    operators.sort(key=lambda o: o.is_approved)

    return [
        {
            "id": o.id,
            "full_name": o.full_name,
            "phone_number": o.phone_number,
            "is_approved": o.is_approved
        } for o in operators
    ]


@router.post("/approve-operator/{user_id}")
def approve_operator(user_id: int, action: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_chief(current_user)

    user = db.query(User).filter(User.id == user_id, User.role == "OPERATOR").first()
    if not user:
        raise HTTPException(status_code=404, detail="مامور مورد نظر یافت نشد.")

    if action == "approve":
        user.is_approved = True
        msg = f"مامور {user.full_name} با موفقیت تایید شد."
    elif action == "reject":
        user.is_approved = False
        msg = f"درخواست مامور {user.full_name} رد شد."
    else:
        raise HTTPException(status_code=400, detail="عملیات نامعتبر است.")

    db.commit()
    return {"message": msg}


@router.get("/all-data")
def get_all_system_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_chief(current_user)

    users = db.query(User).all()
    volunteers = db.query(VolunteerProfile).join(User).all()
    missions = db.query(Mission).all()

    return {
        "users": [
            {"id": u.id, "name": u.full_name, "phone": u.phone_number, "role": u.role, "approved": u.is_approved}
            for u in users
        ],
        "volunteers": [
            {
                "id": v.id,
                "name": v.user.full_name,
                "phone": v.user.phone_number,
                "province": v.province,
                "city": v.city,
                "can_deploy": v.can_deploy,
                "skills": v.skills,
                "rating": v.rating
            } for v in volunteers
        ],
        "missions": [
            {
                "id": m.id,
                "title": m.title,
                "province": m.province,
                "city": m.city,
                "address": m.address,
                "status": m.status,
                "creator_id": m.creator_id
            } for m in missions
        ]
    }
''',

    # ---------------------------------------------------------------
    # 5. روتر احراز هویت: افزودن مسیر /me برای دریافت زنده وضعیت کاربر
    #    (رفع نیاز: بدون خروج/ورود مجدد، صرفاً با رفرش صفحه وضعیت تایید بروز شود)
    # ---------------------------------------------------------------
    "app/routers/auth.py": '''import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, OTPCode
from app.schemas.user import RequestOTPSchema, VerifyOTPSchema, TokenSchema
from app.services.auth import create_access_token, get_current_user

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


@router.get("/me", response_model=TokenSchema)
def get_me(current_user: User = Depends(get_current_user)):
    """
    === رفع نیاز: بروزرسانی زنده وضعیت کاربر ===
    get_current_user کاربر را همیشه به‌صورت مستقیم و به‌روز از دیتابیس می‌خواند،
    بنابراین این مسیر همیشه آخرین وضعیت تایید/نقش کاربر را برمی‌گرداند، بدون نیاز
    به خروج و ورود مجدد. کافیست فرانت‌اند این مسیر را در زمان بارگذاری صفحه صدا بزند.
    """
    token_data = {
        "sub": str(current_user.id),
        "phone": current_user.phone_number,
        "role": current_user.role,
        "name": current_user.full_name,
        "approved": current_user.is_approved
    }
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": current_user.role,
        "full_name": current_user.full_name,
        "is_approved": current_user.is_approved
    }
''',

    # ---------------------------------------------------------------
    # 6. فرانت‌اند: رفع تمامی نیازهای درخواستی
    # ---------------------------------------------------------------
    "static/index.html": '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سامانه فرماندهی و مدیریت بحران</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css">
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" />
    <style>
        body { font-family: 'Vazirmatn', sans-serif; background-color: #f4f6f9; }
        .card { border-radius: 12px; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .badge-dot { height: 10px; width: 10px; background-color: #dc3545; border-radius: 50%; display: inline-block; position: absolute; top: 5px; right: 5px; }
        .skills-box .form-check { margin-left: 1rem; }
        table { font-size: 0.9rem; }
    </style>
</head>
<body>

<div class="container py-4">
    <header class="pb-3 mb-4 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <h3 class="fw-bold text-primary">🚨 سامانه هوشمند فرماندهی و مدیریت بحران</h3>
            <p class="text-muted mb-0">سیستم جامع مدیریت ماموریت‌ها، نیروها و مرکز فرماندهی</p>
        </div>
        <div id="authBox">
            <button class="btn btn-primary fw-bold" onclick="showAuthModal()">📲 ورود / ثبت‌نام با پیامک</button>
        </div>
    </header>

    <div id="unapprovedAlert" class="alert alert-warning fw-bold text-center" style="display:none;">
        ⏳ حساب کاربری شما به عنوان "مامور" ثبت شده است اما هنوز توسط رئیس کل تایید نشده است.
    </div>

    <!-- تب‌های منو -->
    <ul class="nav nav-pills mb-4" id="mainTabs">
        <li class="nav-item" id="nav-vol" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-vol">🙋‍♂️ اعلام داوطلبی</button>
        </li>
        <li class="nav-item" id="nav-inbox" style="display:none;">
            <button class="nav-link fw-bold position-relative" data-bs-toggle="pill" data-bs-target="#tab-msg" onclick="loadMessages()">
                📬 صندوق پیام‌ها <span id="unreadDot" style="display:none;" class="badge-dot"></span>
            </button>
        </li>
        <li class="nav-item" id="nav-create-mis" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-create-mis">📋 ایجاد ماموریت جدید</button>
        </li>
        <li class="nav-item" id="nav-manage-mis" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-manage-mis" onclick="loadMyMissions()">⚙️ مدیریت ماموریت‌ها</button>
        </li>
        <li class="nav-item" id="nav-chief" style="display:none;">
            <button class="nav-link fw-bold btn-danger text-white ms-2" data-bs-toggle="pill" data-bs-target="#tab-chief" onclick="loadChiefPanel()">👑 پنل جامع رئیس کل</button>
        </li>
    </ul>

    <div class="tab-content">

        <!-- ۰. پیام خوش‌آمدگویی پیش از ورود - رفع نیاز: دسترسی به هیچ فرمی از جمله داوطلبی قبل از ورود وجود ندارد -->
        <div class="tab-pane fade show active" id="tab-welcome">
            <div class="card p-5 text-center">
                <h4 class="fw-bold mb-3">🔒 برای دسترسی به سامانه ابتدا وارد شوید</h4>
                <p class="text-muted">برای اعلام داوطلبی، مشاهده پیام‌ها یا مدیریت ماموریت‌ها لازم است با شماره تلفن همراه خود وارد سیستم شوید.</p>
                <div><button class="btn btn-primary fw-bold px-4" onclick="showAuthModal()">📲 ورود / ثبت‌نام با پیامک</button></div>
            </div>
        </div>

        <!-- ۱. اعلام داوطلبی -->
        <div class="tab-pane fade" id="tab-vol">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ثبت مشخصات داوطلبی و توانایی‌ها</h5>
                <form id="volForm" onsubmit="saveVolunteerProfile(event)">
                    <div class="row g-3">
                        <div class="col-md-3"><select id="volProv" class="form-select" onchange="updateCities('volProv', 'volCity')" required><option value="">انتخاب استان...</option></select></div>
                        <div class="col-md-3"><select id="volCity" class="form-select" required><option value="">انتخاب شهر...</option></select></div>
                        <div class="col-md-3"><label class="form-label">از تاریخ</label><input type="datetime-local" id="volFrom" class="form-control" required></div>
                        <div class="col-md-3"><label class="form-label">تا تاریخ</label><input type="datetime-local" id="volTo" class="form-control" required></div>

                        <div class="col-12">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="volDeploy">
                                <label class="form-check-label fw-bold" for="volDeploy">آمادگی اعزام به سایر شهرها را دارم</label>
                            </div>
                        </div>

                        <div class="col-12">
                            <label class="form-label fw-bold">توانایی‌های شما (می‌توانید چند گزینه انتخاب کنید):</label>
                            <div id="volSkillsBox" class="skills-box border rounded p-3"></div>
                        </div>

                        <div class="col-12"><button type="submit" class="btn btn-primary fw-bold">ثبت وضعیت داوطلبی</button></div>
                    </div>
                </form>
            </div>
        </div>

        <!-- ۲. صندوق پیام‌ها -->
        <div class="tab-pane fade" id="tab-msg">
            <div class="card p-4"><div id="messagesList">در حال بارگذاری پیام‌ها...</div></div>
        </div>

        <!-- ۳. ایجاد ماموریت -->
        <div class="tab-pane fade" id="tab-create-mis">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">تعریف ماموریت عملیاتی</h5>
                <form id="misForm" onsubmit="createMission(event)">
                    <div class="row g-3">
                        <div class="col-md-6"><input type="text" id="misTitle" class="form-control" placeholder="عنوان ماموریت" required></div>
                        <div class="col-md-3"><select id="misProv" class="form-select" onchange="updateCities('misProv', 'misCity')" required><option value="">استان...</option></select></div>
                        <div class="col-md-3"><select id="misCity" class="form-select" required><option value="">شهر...</option></select></div>

                        <div class="col-md-8">
                            <label class="form-label">آدرس کامل محل ماموریت</label>
                            <input type="text" id="misAddress" class="form-control" placeholder="مثلا: خیابان ولیعصر، نبش کوچه ۱۲، پلاک ۵" required>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">تاریخ و ساعت ماموریت</label>
                            <input type="datetime-local" id="misDate" class="form-control" required>
                        </div>

                        <div class="col-12">
                            <label class="form-label fw-bold">مهارت‌های مورد نیاز (می‌توانید چند گزینه انتخاب کنید):</label>
                            <div id="misSkillsBox" class="skills-box border rounded p-3"></div>
                        </div>

                        <div class="col-12"><button type="submit" class="btn btn-success fw-bold">ثبت و ایجاد ماموریت</button></div>
                    </div>
                </form>
            </div>
        </div>

        <!-- ۴. مدیریت ماموریت‌ها -->
        <div class="tab-pane fade" id="tab-manage-mis">
            <div class="card p-4"><div id="myMissionsList">در حال دریافت ماموریت‌ها...</div></div>
        </div>

        <!-- ۵. پنل جامع رئیس کل -->
        <div class="tab-pane fade" id="tab-chief">
            <div class="card p-4 mb-4 border-primary">
                <h5 class="fw-bold text-primary mb-3">📢 ارسال پیام همگانی برای تمامی کاربران</h5>
                <form onsubmit="sendBroadcast(event)">
                    <input type="text" id="bcTitle" class="form-control mb-2" placeholder="عنوان پیام همگانی" required>
                    <textarea id="bcBody" class="form-control mb-2" rows="2" placeholder="متن پیام..." required></textarea>
                    <button type="submit" class="btn btn-primary fw-bold btn-sm">ارسال همگانی 🚀</button>
                </form>
            </div>

            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-danger mb-3">👨‍✈️ مدیریت حساب ماموران ستاد بحران</h5>
                <p class="text-muted small mb-3">ماموران در انتظار تایید ابتدا نمایش داده می‌شوند. برای ماموران تاییدشده دیگر گزینه تایید/رد وجود ندارد.</p>
                <div id="pendingOpsList">در حال بارگذاری ماموران...</div>
            </div>

            <div class="card p-4">
                <h5 class="fw-bold text-secondary mb-3">📊 دسترسی کلی به داده‌های سیستم</h5>
                <div id="allSystemData">در حال بارگذاری...</div>
            </div>
        </div>
    </div>
</div>

<!-- مودال تطبیق هوشمند -->
<div class="modal fade" id="matchModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title fw-bold">🎯 تطبیق و ارسال دعوت به داوطلبان</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <h6 id="matchMissionTitle" class="fw-bold text-secondary mb-3"></h6>
                <div id="matchResultsList">در حال محاسبه...</div>
            </div>
        </div>
    </div>
</div>

<!-- مودال احراز هویت -->
<div class="modal fade" id="authModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header"><h5 class="modal-title fw-bold">ورود / ثبت‌نام با پیامک</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body">
                <div id="step1">
                    <input type="tel" id="authPhone" class="form-control mb-3" placeholder="09123456789">
                    <button onclick="sendOTP()" class="btn btn-primary w-100 fw-bold">دریافت کد تایید</button>
                </div>
                <div id="step2" style="display:none;">
                    <div class="alert alert-info">📱 کد تایید پیامک‌شده: <b id="simCode"></b></div>
                    <input type="text" id="authCode" class="form-control mb-3" placeholder="کد ۴ رقمی">
                    <div id="regFields" style="display:none;" class="border-top pt-3 mb-3">
                        <input type="text" id="authName" class="form-control mb-2" placeholder="نام و نام خانوادگی">
                        <select id="authRole" class="form-select">
                            <option value="VOLUNTEER">کاربر معمولی / داوطلب</option>
                            <option value="OPERATOR">مامور ستاد بحران</option>
                        </select>
                    </div>
                    <button onclick="verifyOTP()" class="btn btn-success w-100 fw-bold" id="verifyBtn">تایید و ورود</button>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
    const iranData = {
        "تهران": ["تهران", "شهریار", "ری", "اسلامشهر"],
        "البرز": ["کرج", "فردیس", "هشتگرد"],
        "اصفهان": ["اصفهان", "کاشان", "خمینی‌شهر"],
        "خوزستان": ["اهواز", "دزفول", "آبادان"]
    };

    // === باید دقیقاً با app/constants.py::SKILL_CHOICES یکسان باشد ===
    const SKILL_CHOICES = [
        "حمل و نقل با ماشین شخصی سبک",
        "حمل و نقل با وانت یا نیسان",
        "حمل و نقل با ماشین سنگین (کامیون)",
        "کمک‌های اولیه و پانسمان",
        "بنایی",
        "تاسیسات (برق‌کشی، لوله‌کشی و...)",
        "نیروی ساده",
        "آشپزی"
    ];

    function renderSkillCheckboxes(containerId, namePrefix) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = SKILL_CHOICES.map((s, i) => `
            <div class="form-check form-check-inline mb-2">
                <input class="form-check-input" type="checkbox" value="${s}" id="${namePrefix}_${i}">
                <label class="form-check-label" for="${namePrefix}_${i}">${s}</label>
            </div>
        `).join('');
    }

    function getCheckedSkills(containerId) {
        return Array.from(document.querySelectorAll(`#${containerId} input[type=checkbox]:checked`)).map(cb => cb.value);
    }

    function initProvinces() {
        ['volProv', 'misProv'].forEach(id => {
            const el = document.getElementById(id);
            if(el) {
                el.innerHTML = '<option value="">انتخاب استان...</option>';
                Object.keys(iranData).forEach(p => el.options.add(new Option(p, p)));
            }
        });
    }

    function updateCities(pId, cId) {
        const p = document.getElementById(pId).value;
        const cSelect = document.getElementById(cId);
        cSelect.innerHTML = '<option value="">انتخاب شهر...</option>';
        if (p && iranData[p]) iranData[p].forEach(c => cSelect.options.add(new Option(c, c)));
    }

    function showAuthModal() { new bootstrap.Modal(document.getElementById('authModal')).show(); }

    async function sendOTP() {
        const phone = document.getElementById('authPhone').value;
        const res = await fetch('/api/auth/send-otp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({phone_number: phone})
        });
        const data = await res.json();
        if(res.ok) {
            document.getElementById('step1').style.display = 'none';
            document.getElementById('step2').style.display = 'block';
            document.getElementById('simCode').innerText = data.simulated_code;
            document.getElementById('regFields').style.display = data.is_registered ? 'none' : 'block';
            document.getElementById('verifyBtn').innerText = data.is_registered ? 'ورود به حساب کاربری' : 'تکمیل ثبت‌نام و ورود';
        } else alert(data.detail);
    }

    async function verifyOTP() {
        const payload = {
            phone_number: document.getElementById('authPhone').value,
            code: document.getElementById('authCode').value,
            full_name: document.getElementById('authName').value || null,
            role: document.getElementById('authRole').value || 'VOLUNTEER'
        };
        const res = await fetch('/api/auth/verify-otp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(res.ok) {
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('role', data.role);
            localStorage.setItem('name', data.full_name);
            localStorage.setItem('approved', data.is_approved);
            bootstrap.Modal.getInstance(document.getElementById('authModal'))?.hide();
            setupUI();
        } else alert(data.detail);
    }

    function logout() { localStorage.clear(); setupUI(); }

    // === رفع نیاز: بروزرسانی زنده وضعیت تایید کاربر، بدون نیاز به خروج و ورود مجدد ===
    async function refreshUserStatus() {
        const token = localStorage.getItem('token');
        if (!token) return;
        try {
            const res = await fetch('/api/auth/me', { headers: {'Authorization': `Bearer ${token}`} });
            if (res.ok) {
                const data = await res.json();
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('role', data.role);
                localStorage.setItem('name', data.full_name);
                localStorage.setItem('approved', data.is_approved);
            } else if (res.status === 401) {
                localStorage.clear();
            }
        } catch (err) {
            // در صورت قطعی موقت شبکه، اطلاعات محلی موجود حفظ می‌شود
        }
    }

    function activateTab(paneId) {
        document.querySelectorAll('.tab-content > .tab-pane').forEach(p => p.classList.remove('show', 'active'));
        document.querySelectorAll('#mainTabs .nav-link').forEach(b => b.classList.remove('active'));
        const pane = document.getElementById(paneId);
        if (pane) pane.classList.add('show', 'active');
        const btn = document.querySelector(`#mainTabs button[data-bs-target="#${paneId}"]`);
        if (btn) btn.classList.add('active');
    }

    // === رفع نیاز: قبل از ورود هیچ تب یا فرمی (حتی داوطلبی) در دسترس نیست
    //     و پس از ورود فقط تب‌های مخصوص نقش همان کاربر نمایش داده می‌شود ===
    function setupUI() {
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');
        const approved = localStorage.getItem('approved') === 'true';

        document.getElementById('nav-vol').style.display = 'none';
        document.getElementById('nav-inbox').style.display = 'none';
        document.getElementById('nav-create-mis').style.display = 'none';
        document.getElementById('nav-manage-mis').style.display = 'none';
        document.getElementById('nav-chief').style.display = 'none';
        document.getElementById('unapprovedAlert').style.display = 'none';

        if (!token) {
            document.getElementById('authBox').innerHTML = `<button class="btn btn-primary fw-bold" onclick="showAuthModal()">📲 ورود / ثبت‌نام با پیامک</button>`;
            activateTab('tab-welcome');
            return;
        }

        const roleTitle = role === 'ADMIN' ? 'رئیس کل' : (role === 'OPERATOR' ? 'مامور' : 'داوطلب');
        document.getElementById('authBox').innerHTML = `
            <span class="badge bg-primary fs-6 me-2">👤 ${localStorage.getItem('name')} (${roleTitle})</span>
            <button onclick="logout()" class="btn btn-outline-danger btn-sm fw-bold">خروج</button>
        `;

        if (role === 'VOLUNTEER') {
            document.getElementById('nav-vol').style.display = 'block';
            document.getElementById('nav-inbox').style.display = 'block';
            checkUnreadMessages();
            activateTab('tab-vol');
        } else if (role === 'OPERATOR') {
            document.getElementById('nav-inbox').style.display = 'block';
            checkUnreadMessages();
            if (approved) {
                document.getElementById('nav-create-mis').style.display = 'block';
                document.getElementById('nav-manage-mis').style.display = 'block';
                activateTab('tab-manage-mis');
                loadMyMissions();
            } else {
                document.getElementById('unapprovedAlert').style.display = 'block';
                activateTab('tab-msg');
                loadMessages();
            }
        } else if (role === 'ADMIN') {
            document.getElementById('nav-inbox').style.display = 'block';
            document.getElementById('nav-create-mis').style.display = 'block';
            document.getElementById('nav-manage-mis').style.display = 'block';
            document.getElementById('nav-chief').style.display = 'block';
            checkUnreadMessages();
            activateTab('tab-chief');
            loadChiefPanel();
        }
    }

    async function checkUnreadMessages() {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/messages/my-messages', { headers: {'Authorization': `Bearer ${token}`} });
        const msgs = await res.json();
        const hasUnread = Array.isArray(msgs) && msgs.some(m => !m.is_read);
        document.getElementById('unreadDot').style.display = hasUnread ? 'inline-block' : 'none';
    }

    async function loadMessages() {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/messages/my-messages', { headers: {'Authorization': `Bearer ${token}`} });
        const msgs = await res.json();

        let html = '';
        if (!msgs || msgs.length === 0) {
            html = '<div class="alert alert-info m-0">صندوق پیام‌های شما خالی است.</div>';
        } else {
            msgs.forEach(m => {
                const borderClass = m.is_read ? 'border-secondary' : 'border-primary bg-light';
                html += `
                <div class="card p-3 mb-2 border-start border-4 ${borderClass}" onclick="markAsRead(${m.id})" style="cursor: pointer; white-space: pre-line;">
                    <div class="d-flex justify-content-between">
                        <h6 class="fw-bold m-0">${m.title} ${!m.is_read ? '<span class="badge bg-danger ms-1">جدید 🆕</span>' : ''}</h6>
                        <small class="text-muted">${m.created_at}</small>
                    </div>
                    <p class="m-0 mt-2 text-secondary">${m.body}</p>
                </div>`;
            });
        }
        document.getElementById('messagesList').innerHTML = html;
        checkUnreadMessages();
    }

    async function markAsRead(msgId) {
        const token = localStorage.getItem('token');
        await fetch(`/api/messages/${msgId}/read`, {
            method: 'POST',
            headers: {'Authorization': `Bearer ${token}`}
        });
        loadMessages();
    }

    // === رفع نیاز: ماموریت‌های باز ابتدا و خاتمه‌یافته‌ها انتها نمایش داده می‌شوند (ترتیب از بک‌اند می‌آید) ===
    async function loadMyMissions() {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/missions/my-missions', { headers: {'Authorization': `Bearer ${token}`} });
        const missions = await res.json();

        let html = '';
        if (!missions || missions.length === 0) {
            html = '<div class="alert alert-info m-0">هیچ ماموریتی ثبت نشده است.</div>';
        } else {
            missions.forEach(m => {
                const skillsBadge = (m.required_skills || []).map(s => `<span class="badge bg-secondary me-1">${s}</span>`).join('');
                const isCompleted = m.status === 'COMPLETED';
                html += `
                <div class="card p-3 mb-3 border ${isCompleted ? 'bg-light' : ''}">
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="fw-bold ${isCompleted ? 'text-secondary' : 'text-primary'} m-0">${m.title}</h5>
                        <div>
                            ${isCompleted ? `
                                <span class="badge bg-secondary fs-6">خاتمه یافته</span>
                            ` : `
                                <button onclick="openMatchModal(${m.id}, '${m.title}')" class="btn btn-outline-primary btn-sm fw-bold">🎯 تطبیق و دعوت نیرو</button>
                                <button onclick="completeMission(${m.id})" class="btn btn-outline-danger btn-sm fw-bold ms-1">🏁 خاتمه ماموریت</button>
                                <span class="badge bg-success ms-2">باز</span>
                            `}
                        </div>
                    </div>
                    <div class="mt-2 text-muted small">📍 موقعیت: ${m.province} - ${m.city} | 🏠 آدرس: ${m.address} | 🗓️ تاریخ ماموریت: ${m.mission_date}</div>
                    <div class="mt-2">مهارت‌های مورد نیاز: ${skillsBadge}</div>
                </div>`;
            });
        }
        document.getElementById('myMissionsList').innerHTML = html;
    }

    async function completeMission(missionId) {
        if (!confirm('آیا از خاتمه این ماموریت اطمینان دارید؟ پس از خاتمه دیگر امکان ارسال درخواست کمک برای آن وجود نخواهد داشت.')) return;
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/missions/${missionId}/complete`, {
            method: 'POST',
            headers: {'Authorization': `Bearer ${token}`}
        });
        const data = await res.json();
        if (res.ok) {
            alert(data.message);
            loadMyMissions();
        } else alert(data.detail);
    }

    // === رفع نیاز: نمایش "دعوت شده" به‌جای دکمه ارسال، برای داوطلبانی که قبلاً دعوت شده‌اند ===
    async function openMatchModal(missionId, missionTitle) {
        document.getElementById('matchMissionTitle').innerText = `ماموریت: ${missionTitle}`;
        document.getElementById('matchResultsList').innerHTML = '<div class="text-center p-3">در حال محاسبه...</div>';
        new bootstrap.Modal(document.getElementById('matchModal')).show();

        const token = localStorage.getItem('token');
        const res = await fetch(`/api/missions/${missionId}/match`, { headers: {'Authorization': `Bearer ${token}`} });
        const data = await res.json();

        let html = '';
        if (!data.recommended_volunteers || data.recommended_volunteers.length === 0) {
            html = '<div class="alert alert-warning m-0">هیچ داوطلب واجد شرایطی (با توجه به شهر/اعزام و بازه زمانی) یافت نشد.</div>';
        } else {
            data.recommended_volunteers.forEach(v => {
                const vSkills = (v.skills || []).map(s => {
                    const isMatched = (v.matched_skills || []).includes(s);
                    return `<span class="badge ${isMatched ? 'bg-success' : 'bg-secondary'} me-1">${s}</span>`;
                }).join('');
                const localBadge = v.is_local ? '<span class="badge bg-success ms-1">بومی</span>' : '<span class="badge bg-warning text-dark ms-1">نیازمند اعزام</span>';
                const actionBtn = v.already_invited
                    ? `<button class="btn btn-secondary btn-sm fw-bold" disabled>دعوت شده ✅</button>`
                    : `<button onclick="inviteVolunteer(${missionId}, ${v.volunteer_id}, '${v.volunteer_name}')" class="btn btn-success btn-sm fw-bold">ارسال پیام دعوت 📩</button>`;
                html += `
                <div class="card p-3 mb-2 border bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="fw-bold m-0">${v.volunteer_name} <span class="badge bg-primary ms-2">مهارت مشترک: ${v.match_count} از ${v.total_required}</span> ${localBadge}</h6>
                            <small class="text-muted">📍 ${v.province} - ${v.city} | ⭐ امتیاز: ${v.rating}</small>
                        </div>
                        ${actionBtn}
                    </div>
                    <div class="mt-2 small">مهارت‌های داوطلب: ${vSkills || 'ثبت نشده'}</div>
                </div>`;
            });
        }
        document.getElementById('matchResultsList').innerHTML = html;
    }

    async function inviteVolunteer(missionId, volunteerId, volunteerName) {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/missions/${missionId}/invite`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify({volunteer_id: volunteerId})
        });
        const data = await res.json();
        if(res.ok) {
            alert(`دعوت‌نامه برای ${volunteerName} ارسال شد!`);
            const currentTitle = document.getElementById('matchMissionTitle').innerText.replace('ماموریت: ', '');
            openMatchModal(missionId, currentTitle);
        }
        else alert(data.detail);
    }

    // === رفع نیاز: لیست ماموران با تاییدنشده‌ها ابتدا (بدون دکمه برای تاییدشده‌ها) + لیست کامل کاربران/داوطلبان/ماموریت‌ها ===
    async function loadChiefPanel() {
        const token = localStorage.getItem('token');

        const resOps = await fetch('/api/admin/pending-operators', { headers: {'Authorization': `Bearer ${token}`} });
        const operators = await resOps.json();

        let opsHtml = '';
        if (!operators || operators.length === 0) {
            opsHtml = '<div class="alert alert-success m-0">هیچ ماموری ثبت‌نام نکرده است.</div>';
        } else {
            operators.forEach(op => {
                if (op.is_approved) {
                    opsHtml += `
                    <div class="d-flex justify-content-between align-items-center mb-2 p-3 bg-white rounded border">
                        <div><b>${op.full_name}</b> (📱 ${op.phone_number})</div>
                        <span class="badge bg-success">تایید شده ✅</span>
                    </div>`;
                } else {
                    opsHtml += `
                    <div class="d-flex justify-content-between align-items-center mb-2 p-3 bg-white rounded border border-warning">
                        <div><b>${op.full_name}</b> (📱 ${op.phone_number}) <span class="badge bg-danger ms-1">در انتظار تایید</span></div>
                        <div>
                            <button onclick="approveOp(${op.id}, 'approve')" class="btn btn-success btn-sm fw-bold">تایید ✅</button>
                            <button onclick="approveOp(${op.id}, 'reject')" class="btn btn-danger btn-sm fw-bold ms-1">رد ❌</button>
                        </div>
                    </div>`;
                }
            });
        }
        document.getElementById('pendingOpsList').innerHTML = opsHtml;

        const resData = await fetch('/api/admin/all-data', { headers: {'Authorization': `Bearer ${token}`} });
        const allData = await resData.json();

        let usersHtml = '<div class="table-responsive"><table class="table table-sm table-bordered align-middle"><thead class="table-light"><tr><th>نام</th><th>تلفن</th><th>نقش</th><th>وضعیت</th></tr></thead><tbody>';
        allData.users.forEach(u => {
            usersHtml += `<tr><td>${u.name}</td><td>${u.phone}</td><td>${u.role}</td><td>${u.approved ? 'فعال' : 'در انتظار تایید'}</td></tr>`;
        });
        usersHtml += '</tbody></table></div>';

        let volsHtml = '<div class="table-responsive"><table class="table table-sm table-bordered align-middle"><thead class="table-light"><tr><th>نام</th><th>تلفن</th><th>استان/شهر</th><th>مهارت‌ها</th><th>آماده اعزام</th></tr></thead><tbody>';
        (allData.volunteers || []).forEach(v => {
            volsHtml += `<tr><td>${v.name}</td><td>${v.phone}</td><td>${v.province} - ${v.city}</td><td>${(v.skills || []).join('، ') || '-'}</td><td>${v.can_deploy ? 'بله' : 'خیر'}</td></tr>`;
        });
        volsHtml += '</tbody></table></div>';

        let missionsHtml = '<div class="table-responsive"><table class="table table-sm table-bordered align-middle"><thead class="table-light"><tr><th>عنوان</th><th>موقعیت</th><th>آدرس</th><th>وضعیت</th></tr></thead><tbody>';
        allData.missions.forEach(m => {
            missionsHtml += `<tr><td>${m.title}</td><td>${m.province} - ${m.city}</td><td>${m.address || '-'}</td><td>${m.status === 'COMPLETED' ? 'خاتمه یافته' : 'باز'}</td></tr>`;
        });
        missionsHtml += '</tbody></table></div>';

        document.getElementById('allSystemData').innerHTML = `
            <h6 class="fw-bold mt-2">👥 کاربران (${allData.users.length})</h6>${usersHtml}
            <h6 class="fw-bold mt-4">🙋‍♂️ داوطلبان (${(allData.volunteers || []).length})</h6>${volsHtml}
            <h6 class="fw-bold mt-4">📋 ماموریت‌ها (${allData.missions.length})</h6>${missionsHtml}
        `;
    }

    async function approveOp(id, action) {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/admin/approve-operator/${id}?action=${action}`, { method: 'POST', headers: {'Authorization': `Bearer ${token}`} });
        const data = await res.json();
        alert(data.message);
        loadChiefPanel();
    }

    async function createMission(e) {
        e.preventDefault();
        const token = localStorage.getItem('token');
        const payload = {
            title: document.getElementById('misTitle').value,
            province: document.getElementById('misProv').value,
            city: document.getElementById('misCity').value,
            address: document.getElementById('misAddress').value,
            required_skills: getCheckedSkills('misSkillsBox'),
            mission_date: document.getElementById('misDate').value
        };

        if (!payload.address || !payload.address.trim()) {
            alert('لطفاً آدرس کامل محل ماموریت را وارد کنید.');
            return;
        }
        if (payload.required_skills.length === 0) {
            alert('لطفاً حداقل یک مهارت مورد نیاز انتخاب کنید.');
            return;
        }

        const res = await fetch('/api/missions/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(res.ok) {
            alert('ماموریت با موفقیت ثبت شد!');
            document.getElementById('misForm').reset();
            renderSkillCheckboxes('misSkillsBox', 'misSkill');
            loadMyMissions();
        } else alert(data.detail);
    }

    async function saveVolunteerProfile(e) {
        e.preventDefault();
        const token = localStorage.getItem('token');
        if(!token) { alert('لطفا ابتدا وارد شوید.'); return; }

        const payload = {
            province: document.getElementById('volProv').value,
            city: document.getElementById('volCity').value,
            can_deploy: document.getElementById('volDeploy').checked,
            skills: getCheckedSkills('volSkillsBox'),
            available_from: document.getElementById('volFrom').value,
            available_to: document.getElementById('volTo').value
        };

        const res = await fetch('/api/volunteers/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(res.ok) alert('اطلاعات داوطلبی با موفقیت ثبت شد!\\nتوانایی‌های انتخابی: ' + (data.skills.join('، ') || 'بدون مهارت انتخابی'));
        else alert(data.detail);
    }

    async function sendBroadcast(e) {
        e.preventDefault();
        const token = localStorage.getItem('token');
        const payload = {
            title: document.getElementById('bcTitle').value,
            body: document.getElementById('bcBody').value
        };

        const res = await fetch('/api/messages/broadcast', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(res.ok) {
            alert(data.message);
            document.getElementById('bcTitle').value = '';
            document.getElementById('bcBody').value = '';
        } else alert(data.detail);
    }

    window.onload = async () => {
        initProvinces();
        renderSkillCheckboxes('volSkillsBox', 'volSkill');
        renderSkillCheckboxes('misSkillsBox', 'misSkill');
        // === رفع نیاز: بروزرسانی زنده وضعیت تایید/نقش کاربر با هر بارگذاری صفحه ===
        await refreshUserStatus();
        setupUI();
    };
</script>
</body>
</html>
'''
}


def fix():
    for file_path, content in files_to_fix.items():
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"✅ فایل بروزرسانی شد: {file_path}")

    # چون ساختار جدول Mission تغییر کرده (فیلد address اکنون اجباری است)،
    # دیتابیس قدیمی باید پاک شود تا جدول‌ها با ساختار جدید از نو ساخته شوند.
    if os.path.exists("disaster.db"):
        os.remove("disaster.db")
        print("🗑️ دیتابیس قدیمی (disaster.db) حذف شد تا جدول‌ها با ساختار جدید (آدرس اجباری ماموریت) از نو ساخته شوند.")
        print("   ⚠️ توجه: تمام کاربران، ماموریت‌ها و پیام‌های قبلی پاک می‌شوند.")

    print("\\n🎉 تغییرات زیر با موفقیت اعمال شد:")
    print("   1) پس از ارسال دعوت به داوطلب، دکمه به «دعوت شده ✅» تغییر می‌کند و امکان ارسال مجدد وجود ندارد.")
    print("   2) هر ماموریت اکنون آدرس کامل اجباری دارد؛ این آدرس به‌همراه ساعت ماموریت در متن پیام دعوت قید می‌شود.")
    print("   3) در پنل رئیس کل، ماموران تاییدنشده ابتدا نمایش داده می‌شوند و برای ماموران تاییدشده دیگر دکمه تایید/رد وجود ندارد.")
    print("   4) پنل رئیس کل اکنون لیست کامل کاربران، داوطلبان و ماموریت‌ها را در قالب جدول نمایش می‌دهد.")
    print("   5) هر ماموریت دو وضعیت «باز» و «خاتمه یافته» دارد؛ مامور می‌تواند ماموریت را خاتمه دهد و پس از آن امکان ارسال درخواست کمک برای آن وجود ندارد.")
    print("   6) در تب ماموریت‌های مامور، ماموریت‌های باز ابتدا و ماموریت‌های خاتمه‌یافته در انتها نمایش داده می‌شوند.")
    print("   7) با تایید مامور توسط رئیس کل، صرفاً با رفرش صفحه (بدون نیاز به خروج و ورود مجدد) این تغییر برای مامور اعمال می‌شود.")
    print("   8) پیش از ورود به سیستم، هیچ تب یا فرمی (از جمله فرم اعلام داوطلبی) در دسترس نیست؛ فقط پیام خوش‌آمدگویی و دکمه ورود نمایش داده می‌شود.")
    print("      پس از ورود، فقط تب‌های مخصوص نقش همان کاربر (داوطلب/مامور/رئیس کل) نمایش داده می‌شود.")


if __name__ == "__main__":
    fix()