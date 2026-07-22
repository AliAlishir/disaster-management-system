import os

files_to_fix = {

    # ---------------------------------------------------------------
    # 0. لیست ثابت و مشترک توانایی‌ها (هم بک‌اند و هم فرانت از همین استفاده می‌کنند)
    # ---------------------------------------------------------------
    "app/constants.py": '''SKILL_CHOICES = [
    "حمل و نقل با ماشین شخصی سبک",
    "حمل و نقل با وانت یا نیسان",
    "حمل و نقل با ماشین سنگین (کامیون)",
    "کمک‌های اولیه و پانسمان",
    "بنایی",
    "تاسیسات (برق‌کشی، لوله‌کشی و...)",
    "نیروی ساده",
    "آشپزی",
]
''',

    # ---------------------------------------------------------------
    # 1. مدل ماموریت: حذف essential/bonus و start/end، افزودن required_skills و mission_date
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
    address = Column(String, nullable=True)

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
    # 2. اسکیمای ماموریت با اعتبارسنجی روی لیست ثابت مهارت‌ها
    # ---------------------------------------------------------------
    "app/schemas/mission.py": '''from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
from app.constants import SKILL_CHOICES

class MissionCreateSchema(BaseModel):
    title: str
    province: str
    city: str
    address: Optional[str] = None
    required_skills: List[str]
    mission_date: datetime

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
    ratings: dict  # {volunteer_id: rating_number}
''',

    # ---------------------------------------------------------------
    # 3. اسکیمای داوطلب: دیگر بیوگرافی متنی/AI نداریم، لیست مهارت‌ها مستقیماً از کاربر گرفته می‌شود
    # ---------------------------------------------------------------
    "app/schemas/user.py": r'''import re
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
from app.constants import SKILL_CHOICES

# 1. اسکیماهای احراز هویت پیامکی (OTP)
class RequestOTPSchema(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    def validate_phone(cls, v):
        if not re.match(r"^09\d{9}$", v):
            raise ValueError("شماره تلفن معتبر نیست. فرمت صحیح: 09123456789")
        return v

class VerifyOTPSchema(BaseModel):
    phone_number: str
    code: str
    full_name: Optional[str] = None
    role: Optional[str] = "VOLUNTEER"

class TokenSchema(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    is_approved: bool

# 2. اسکیمای ثبت‌نام عمومی کاربر (در صورت نیاز آینده)
class UserRegisterSchema(BaseModel):
    full_name: str
    phone_number: str
    role: Optional[str] = "VOLUNTEER"
    password: Optional[str] = None

# 3. اسکیمای ثبت/بروزرسانی داوطلب - دیگر بیوگرافی متنی و استخراج هوش مصنوعی وجود ندارد.
#    کاربر مستقیماً از بین لیست ثابت SKILL_CHOICES، مهارت‌های خود را انتخاب می‌کند (چندگزینه‌ای).
class VolunteerRegisterSchema(BaseModel):
    province: str
    city: str
    can_deploy: bool = False
    skills: List[str] = []
    available_from: datetime
    available_to: datetime

    @field_validator("skills")
    def validate_skills(cls, v):
        # هر مقداری که در لیست استاندارد مهارت‌ها نباشد، نادیده گرفته می‌شود
        return [s for s in v if s in SKILL_CHOICES]

class VolunteerResponseSchema(BaseModel):
    id: int
    full_name: str
    phone_number: str
    province: str
    city: str
    skills: List[str] = []
    rating: float = 5.0
    can_deploy: bool = False

    class Config:
        from_attributes = True
''',

    # ---------------------------------------------------------------
    # 4. روتر داوطلبان: حذف کامل فراخوانی هوش مصنوعی، ذخیره مستقیم لیست مهارت‌های انتخابی
    # ---------------------------------------------------------------
    "app/routers/volunteers.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.services.auth import get_current_user
from app.schemas.user import VolunteerRegisterSchema

router = APIRouter(prefix="/api/volunteers", tags=["Volunteers"])

@router.post("/register")
def register_or_update_volunteer(data: VolunteerRegisterSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(VolunteerProfile).filter(VolunteerProfile.user_id == current_user.id).first()

    if profile:
        # === همیشه رکورد موجود آپدیت می‌شود، هرگز رکورد جدید ساخته نمی‌شود ===
        profile.province = data.province
        profile.city = data.city
        profile.can_deploy = data.can_deploy or False
        profile.skills = data.skills
        profile.available_from = data.available_from
        profile.available_to = data.available_to
        db.commit()
        return {"message": "اطلاعات داوطلبی با موفقیت به‌روزرسانی شد.", "skills": data.skills}

    new_profile = VolunteerProfile(
        user_id=current_user.id,
        province=data.province,
        city=data.city,
        can_deploy=data.can_deploy or False,
        skills=data.skills,
        available_from=data.available_from,
        available_to=data.available_to
    )
    db.add(new_profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        profile = db.query(VolunteerProfile).filter(VolunteerProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=500, detail="خطا در ثبت اطلاعات داوطلبی.")
        profile.province = data.province
        profile.city = data.city
        profile.can_deploy = data.can_deploy or False
        profile.skills = data.skills
        profile.available_from = data.available_from
        profile.available_to = data.available_to
        db.commit()
        return {"message": "اطلاعات داوطلبی با موفقیت به‌روزرسانی شد.", "skills": data.skills}

    return {"message": "اطلاعات داوطلبی با موفقیت ثبت شد.", "skills": data.skills}
''',

    # ---------------------------------------------------------------
    # 5. روتر ماموریت‌ها: ایجاد ماموریت با required_skills + mission_date،
    #    و جلوگیری از ارسال پیام دعوت تکراری برای یک داوطلب در یک ماموریت
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
        missions = db.query(Mission).order_by(Mission.created_at.desc()).all()
    else:
        missions = db.query(Mission).filter(Mission.creator_id == current_user.id).order_by(Mission.created_at.desc()).all()

    return [
        {
            "id": m.id,
            "title": m.title,
            "province": m.province,
            "city": m.city,
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
    return calculate_smart_match(mission_id, db)


@router.post("/{mission_id}/invite")
def invite_volunteer(mission_id: int, data: InviteVolunteerSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)

    volunteer = db.query(User).filter(User.id == data.volunteer_id, User.role == "VOLUNTEER").first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="داوطلب مورد نظر یافت نشد.")

    # === رفع نیاز اصلی: جلوگیری از ارسال پیام تکراری به یک داوطلب برای همان ماموریت ===
    already_invited = db.query(Message).filter(
        Message.mission_id == mission.id,
        Message.receiver_id == volunteer.id
    ).first()
    if already_invited:
        raise HTTPException(status_code=400, detail="قبلاً برای این داوطلب در این ماموریت پیام دعوت ارسال شده است.")

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
    # 6. سرویس تطبیق: بدون هوش مصنوعی - الگوریتم ساده و شفاف بر اساس تعداد مهارت مشترک
    # ---------------------------------------------------------------
    "app/services/matching.py": '''from sqlalchemy.orm import Session
from app.models.mission import Mission
from app.models.user import User, VolunteerProfile


def calculate_smart_match(mission_id: int, db: Session):
    """
    الگوریتم تطبیق بدون هوش مصنوعی:
    1) فقط داوطلبانی در نظر گرفته می‌شوند که یا در همان شهر ماموریت هستند
       یا تیک «آمادگی اعزام» را فعال کرده‌اند.
    2) تاریخ ماموریت باید داخل بازه زمانی آزادی داوطلب (available_from تا available_to) باشد.
    3) از بین باقی‌مانده‌ها، تعداد مهارت‌های مشترک با مهارت‌های موردنیاز ماموریت محاسبه می‌شود
       و نتایج بر اساس بیشترین اشتراک مهارت (و در مرحله بعد بومی بودن و امتیاز) مرتب می‌شوند.
    """
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        return None

    required = set(mission.required_skills or [])
    profiles = db.query(VolunteerProfile).join(User).filter(User.role == "VOLUNTEER").all()

    results = []
    for prof in profiles:
        # پروفایل ناقص (بدون شهر یا بازه زمانی آزادی) در تطبیق شرکت داده نمی‌شود
        if not prof.city or not prof.available_from or not prof.available_to:
            continue

        # ۱. فیلتر شهر / آمادگی اعزام
        is_local = (prof.city or "").strip().lower() == (mission.city or "").strip().lower()
        if not is_local and not prof.can_deploy:
            continue

        # ۲. بررسی اینکه تاریخ ماموریت داخل بازه زمانی آزادی داوطلب است یا نه
        if not (prof.available_from <= mission.mission_date <= prof.available_to):
            continue

        # ۳. شمارش مهارت‌های مشترک
        vol_skills = set(prof.skills or [])
        matched_skills = required.intersection(vol_skills)
        match_count = len(matched_skills)

        user_rating = prof.rating if prof.rating is not None else 5.0

        results.append({
            "volunteer_id": prof.user.id,
            "volunteer_name": prof.user.full_name,
            "phone_number": prof.user.phone_number,
            "province": prof.province,
            "city": prof.city,
            "is_local": is_local,
            "needs_deployment": not is_local,
            "rating": user_rating,
            "skills": list(vol_skills),
            "matched_skills": list(matched_skills),
            "match_count": match_count,
            "total_required": len(required),
        })

    # مرتب‌سازی: اول بیشترین تعداد مهارت مشترک، سپس بومی بودن، سپس بالاترین امتیاز
    results.sort(key=lambda x: (x["match_count"], x["is_local"], x["rating"]), reverse=True)

    return {
        "mission_id": mission.id,
        "mission_title": mission.title,
        "mission_city": mission.city,
        "recommended_volunteers": results
    }
''',

    # ---------------------------------------------------------------
    # 7. فرانت‌اند: چک‌باکس مهارت‌های ثابت به‌جای متن آزاد، تیک اعزام، تاریخ واحد ماموریت
    #    و نمایش نتایج تطبیق بدون امتیاز هوش مصنوعی
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
        <li class="nav-item">
            <button class="nav-link active fw-bold" data-bs-toggle="pill" data-bs-target="#tab-vol">🙋‍♂️ اعلام داوطلبی</button>
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
        <!-- ۱. اعلام داوطلبی -->
        <div class="tab-pane fade show active" id="tab-vol">
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
                        <div class="col-md-6"><label class="form-label">تاریخ و ساعت ماموریت</label><input type="datetime-local" id="misDate" class="form-control" required></div>

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
            location.reload();
        } else alert(data.detail);
    }

    function setupUI() {
        const role = localStorage.getItem('role');
        const approved = localStorage.getItem('approved') === 'true';

        document.getElementById('nav-inbox').style.display = 'none';
        document.getElementById('nav-create-mis').style.display = 'none';
        document.getElementById('nav-manage-mis').style.display = 'none';
        document.getElementById('nav-chief').style.display = 'none';
        document.getElementById('unapprovedAlert').style.display = 'none';

        if (role) {
            const roleTitle = role === 'ADMIN' ? 'رئیس کل' : (role === 'OPERATOR' ? 'مامور' : 'داوطلب');
            document.getElementById('authBox').innerHTML = `
                <span class="badge bg-primary fs-6 me-2">👤 ${localStorage.getItem('name')} (${roleTitle})</span>
                <button onclick="logout()" class="btn btn-outline-danger btn-sm fw-bold">خروج</button>
            `;

            document.getElementById('nav-inbox').style.display = 'block';
            checkUnreadMessages();

            if (role === 'OPERATOR') {
                if (approved) {
                    document.getElementById('nav-create-mis').style.display = 'block';
                    document.getElementById('nav-manage-mis').style.display = 'block';
                } else {
                    document.getElementById('unapprovedAlert').style.display = 'block';
                }
            } else if (role === 'ADMIN') {
                document.getElementById('nav-create-mis').style.display = 'block';
                document.getElementById('nav-manage-mis').style.display = 'block';
                document.getElementById('nav-chief').style.display = 'block';
            }
        }
    }

    function logout() { localStorage.clear(); location.reload(); }

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
                <div class="card p-3 mb-2 border-start border-4 ${borderClass}" onclick="markAsRead(${m.id})" style="cursor: pointer;">
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
                html += `
                <div class="card p-3 mb-3 border">
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="fw-bold text-primary m-0">${m.title}</h5>
                        <div>
                            <button onclick="openMatchModal(${m.id}, '${m.title}')" class="btn btn-outline-primary btn-sm fw-bold">🎯 تطبیق و دعوت نیرو</button>
                            <span class="badge bg-success ms-2">${m.status}</span>
                        </div>
                    </div>
                    <div class="mt-2 text-muted small">📍 موقعیت: ${m.province} - ${m.city} | 🗓️ تاریخ ماموریت: ${m.mission_date}</div>
                    <div class="mt-2">مهارت‌های مورد نیاز: ${skillsBadge}</div>
                </div>`;
            });
        }
        document.getElementById('myMissionsList').innerHTML = html;
    }

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
                html += `
                <div class="card p-3 mb-2 border bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="fw-bold m-0">${v.volunteer_name} <span class="badge bg-primary ms-2">مهارت مشترک: ${v.match_count} از ${v.total_required}</span> ${localBadge}</h6>
                            <small class="text-muted">📍 ${v.province} - ${v.city} | ⭐ امتیاز: ${v.rating}</small>
                        </div>
                        <button onclick="inviteVolunteer(${missionId}, ${v.volunteer_id}, '${v.volunteer_name}')" class="btn btn-success btn-sm fw-bold">ارسال پیام دعوت 📩</button>
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
        if(res.ok) alert(`دعوت‌نامه برای ${volunteerName} ارسال شد!`);
        else alert(data.detail);
    }

    async function loadChiefPanel() {
        const token = localStorage.getItem('token');

        const resOps = await fetch('/api/admin/pending-operators', { headers: {'Authorization': `Bearer ${token}`} });
        const operators = await resOps.json();

        let opsHtml = '';
        if (!operators || operators.length === 0) {
            opsHtml = '<div class="alert alert-success m-0">هیچ ماموری ثبت‌نام نکرده است.</div>';
        } else {
            operators.forEach(op => {
                const statusBadge = op.is_approved ? '<span class="badge bg-success">تایید شده ✅</span>' : '<span class="badge bg-danger">در انتظار تایید ❌</span>';
                opsHtml += `
                <div class="d-flex justify-content-between align-items-center mb-2 p-3 bg-white rounded border">
                    <div><b>${op.full_name}</b> (📱 ${op.phone_number}) - ${statusBadge}</div>
                    <div>
                        <button onclick="approveOp(${op.id}, 'approve')" class="btn btn-success btn-sm fw-bold">تایید ✅</button>
                        <button onclick="approveOp(${op.id}, 'reject')" class="btn btn-danger btn-sm fw-bold ms-1">رد ❌</button>
                    </div>
                </div>`;
            });
        }
        document.getElementById('pendingOpsList').innerHTML = opsHtml;

        const resData = await fetch('/api/admin/all-data', { headers: {'Authorization': `Bearer ${token}`} });
        const allData = await resData.json();
        document.getElementById('allSystemData').innerHTML = `
            <p>👥 <b>تعداد کل کاربران:</b> ${allData.users.length}</p>
            <p>📋 <b>تعداد کل ماموریت‌ها:</b> ${allData.missions.length}</p>
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
            required_skills: getCheckedSkills('misSkillsBox'),
            mission_date: document.getElementById('misDate').value
        };

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

    window.onload = () => {
        initProvinces();
        setupUI();
        renderSkillCheckboxes('volSkillsBox', 'volSkill');
        renderSkillCheckboxes('misSkillsBox', 'misSkill');
    };
</script>
</body>
</html>
''',
}


def fix():
    for file_path, content in files_to_fix.items():
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"✅ فایل بروزرسانی شد: {file_path}")

    # چون ساختار جدول Mission تغییر کرده (حذف essential/bonus/start/end، افزودن required_skills/mission_date)،
    # دیتابیس قدیمی باید پاک شود تا جدول‌ها با ساختار جدید از نو ساخته شوند.
    if os.path.exists("disaster.db"):
        os.remove("disaster.db")
        print("🗑️ دیتابیس قدیمی (disaster.db) حذف شد تا جدول‌ها با ساختار جدید از نو ساخته شوند.")
        print("   ⚠️ توجه: تمام کاربران، ماموریت‌ها و پیام‌های قبلی پاک می‌شوند.")

    print("\n🎉 تغییرات زیر با موفقیت اعمال شد:")
    print("   1) استخراج هوش مصنوعی مهارت‌ها حذف شد. حالا داوطلب از یک لیست ثابت هشت‌گزینه‌ای، توانایی‌های خود را انتخاب می‌کند.")
    print("   2) تیک «آمادگی اعزام» در فرم داوطلب اضافه شد.")
    print("   3) در ایجاد ماموریت، دیگر مهارت ضروری/امتیازی جدا وجود ندارد؛ فقط یک لیست «مهارت مورد نیاز» با چندگزینه‌ای بودن.")
    print("   4) تاریخ شروع/پایان ماموریت حذف شد و به یک «تاریخ ماموریت» تبدیل شد که باید داخل بازه آزادی داوطلب باشد.")
    print("   5) الگوریتم تطبیق دیگر از هوش مصنوعی استفاده نمی‌کند: ابتدا شهر/اعزام و بازه زمانی فیلتر می‌شود، سپس بر اساس تعداد مهارت مشترک مرتب‌سازی می‌شود.")
    print("   6) ارسال پیام دعوت تکراری برای یک داوطلب در یک ماموریت مشخص مسدود شد.")
    print("\nنکته: فایل app/services/ai_service.py دیگر در هیچ‌کجا استفاده نمی‌شود و در صورت تمایل می‌توانید آن را حذف کنید (حذف آن اختیاری و بی‌خطر است).")


if __name__ == "__main__":
    fix()