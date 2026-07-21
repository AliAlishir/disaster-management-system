import os

files = {
    # ---------------------------------------------------------------
    # 1. مدل‌های دیتابیس (User, Mission, Message, OTP)
    # ---------------------------------------------------------------
    "app/models/user.py": '''from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, default="VOLUNTEER") # VOLUNTEER, OPERATOR, ADMIN
    is_approved = Column(Boolean, default=True) # برای ماموران False ست می‌شود تا رئیس تایید کند
    created_at = Column(DateTime, default=datetime.utcnow)

    volunteer_profile = relationship("VolunteerProfile", back_populates="user", uselist=False)

class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    province = Column(String, index=True, nullable=False)
    city = Column(String, index=True, nullable=False)
    can_deploy = Column(Boolean, default=False)
    bio = Column(Text, nullable=True)
    skills = Column(JSON, default=[])

    rating = Column(Float, default=5.0)      # میانگین امتیاز
    rating_count = Column(Integer, default=1) # تعداد دفعات امتیازدهی

    available_from = Column(DateTime, nullable=True)
    available_to = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="volunteer_profile")

class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
''',

    "app/models/mission.py": '''from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
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

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    status = Column(String, default="OPEN") # OPEN, COMPLETED
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_volunteers = Column(JSON, default=[]) # لیست آیدی کاربران پذیرفته‌شده
    created_at = Column(DateTime, default=datetime.utcnow)
''',

    "app/models/message.py": '''from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from datetime import datetime
from app.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    category = Column(String, default="ماموریت") # ماموریت, سیستمی
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)

    is_read = Column(Boolean, default=False)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=True)
    invite_status = Column(String, default="PENDING") # PENDING, ACCEPTED, REJECTED, NONE

    created_at = Column(DateTime, default=datetime.utcnow)
''',

    "app/models/__init__.py": "from app.models.user import User, VolunteerProfile, OTPCode\nfrom app.models.mission import Mission\nfrom app.models.message import Message\n",

    # ---------------------------------------------------------------
    # 2. Schemas
    # ---------------------------------------------------------------
    "app/schemas/user.py": '''import re
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

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
    province: Optional[str] = None
    city: Optional[str] = None
    can_deploy: Optional[bool] = False
    bio_text: Optional[str] = None
    available_from: Optional[datetime] = None
    available_to: Optional[datetime] = None

class TokenSchema(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    is_approved: bool
''',

    "app/schemas/mission.py": '''from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MissionCreateSchema(BaseModel):
    title: str
    province: str
    city: str
    address: Optional[str] = None
    essential_skills: List[str]
    bonus_skills: List[str] = []
    start_time: datetime
    end_time: datetime

class SendInviteSchema(BaseModel):
    mission_id: int
    volunteer_id: int

class CompleteMissionSchema(BaseModel):
    mission_id: int
    ratings: dict # {volunteer_id: rating_number}
''',

    # ---------------------------------------------------------------
    # 3. Router پیام‌ها و صندوق ورودی (Messages Router)
    # ---------------------------------------------------------------
    "app/routers/messages.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.message import Message
from app.models.mission import Mission
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/messages", tags=["Messages"])

@router.get("/")
def get_my_messages(category: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Message).filter(Message.recipient_id == current_user.id)
    if category and category != "همه":
        query = query.filter(Message.category == category)

    messages = query.order_by(Message.created_at.desc()).all()
    return messages

@router.post("/{message_id}/read")
def mark_as_read(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    msg = db.query(Message).filter(Message.id == message_id, Message.recipient_id == current_user.id).first()
    if msg:
        msg.is_read = True
        db.commit()
    return {"status": "ok"}

@router.post("/{message_id}/respond")
def respond_invite(message_id: int, action: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    msg = db.query(Message).filter(Message.id == message_id, Message.recipient_id == current_user.id).first()
    if not msg or not msg.mission_id:
        raise HTTPException(status_code=404, detail="پیام یا ماموریت مربوطه یافت نشد.")

    if action not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="عملیات نامعتبر است.")

    mission = db.query(Mission).filter(Mission.id == msg.mission_id).first()

    if action == "accept":
        msg.invite_status = "ACCEPTED"
        msg.is_read = True
        if mission:
            current_team = list(mission.assigned_volunteers or [])
            if current_user.id not in current_team:
                current_team.append(current_user.id)
                mission.assigned_volunteers = current_team
    else:
        msg.invite_status = "REJECTED"
        msg.is_read = True

    db.commit()
    return {"message": "پاسخ شما با موفقیت ثبت شد."}
''',

    # ---------------------------------------------------------------
    # 4. Router ماموریت‌ها و دعوت از داوطلبان (Missions Router)
    # ---------------------------------------------------------------
    "app/routers/missions.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.mission import Mission
from app.models.user import User, VolunteerProfile
from app.models.message import Message
from app.schemas.mission import MissionCreateSchema, SendInviteSchema, CompleteMissionSchema
from app.services.matching import calculate_smart_match
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/missions", tags=["Missions"])

def verify_operator_or_admin(user: User):
    if user.role not in ["OPERATOR", "ADMIN"]:
        raise HTTPException(status_code=403, detail="فقط ماموران تاییدشده دسترسی دارند.")
    if user.role == "OPERATOR" and not user.is_approved:
        raise HTTPException(status_code=403, detail="حساب شما هنوز توسط رئیس کل تایید نشده است.")

@router.post("/create")
def create_mission(data: MissionCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_operator_or_admin(current_user)

    new_mission = Mission(
        title=data.title,
        province=data.province,
        city=data.city,
        address=data.address,
        essential_skills=data.essential_skills,
        bonus_skills=data.bonus_skills,
        start_time=data.start_time,
        end_time=data.end_time,
        creator_id=current_user.id
    )
    db.add(new_mission)
    db.commit()
    db.refresh(new_mission)
    return new_mission

@router.get("/my-missions")
def get_my_created_missions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_operator_or_admin(current_user)
    missions = db.query(Mission).filter(Mission.creator_id == current_user.id).order_by(Mission.created_at.desc()).all()

    result = []
    for m in missions:
        # دریافت اطلاعات افراد پذیرفته‌شده
        team_users = []
        if m.assigned_volunteers:
            users = db.query(User).filter(User.id.in_(m.assigned_volunteers)).all()
            team_users = [{"id": u.id, "full_name": u.full_name, "phone": u.phone_number} for u in users]

        result.append({
            "id": m.id,
            "title": m.title,
            "province": m.province,
            "city": m.city,
            "status": m.status,
            "team": team_users
        })
    return result

@router.get("/{mission_id}/match")
def match_volunteers(mission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_operator_or_admin(current_user)
    return calculate_smart_match(mission_id, db)

@router.post("/send-invite")
def send_invite(data: SendInviteSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_operator_or_admin(current_user)
    mission = db.query(Mission).filter(Mission.id == data.mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="ماموریت یافت نشد.")

    msg = Message(
        recipient_id=data.volunteer_id,
        sender_id=current_user.id,
        category="ماموریت",
        title=f"دعوت به ماموریت: {mission.title}",
        body=f"سلام. شما برای ماموریت '{mission.title}' در شهر {mission.city} انتخاب شده‌اید. آیا تمایل به همکاری دارید؟",
        mission_id=mission.id,
        invite_status="PENDING"
    )
    db.add(msg)
    db.commit()
    return {"message": "پیام درخواست کمک با موفقیت ارسال شد."}

@router.post("/complete")
def complete_mission(data: CompleteMissionSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_operator_or_admin(current_user)
    mission = db.query(Mission).filter(Mission.id == data.mission_id, Mission.creator_id == current_user.id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="ماموریت یافت نشد.")

    mission.status = "COMPLETED"

    # ثبت نمرات داوطلبان
    for vol_id_str, rating_val in data.ratings.items():
        vol_id = int(vol_id_str)
        profile = db.query(VolunteerProfile).filter(VolunteerProfile.user_id == vol_id).first()
        if profile:
            count = profile.rating_count or 1
            old_rating = profile.rating or 5.0
            new_rating = ((old_rating * count) + float(rating_val)) / (count + 1)
            profile.rating = round(new_rating, 2)
            profile.rating_count = count + 1

    db.commit()
    return {"message": "ماموریت خاتمه یافت و امتیاز داوطلبان ثبت گردید."}
''',

    # ---------------------------------------------------------------
    # 5. Router رئیس کل (Admin Router)
    # ---------------------------------------------------------------
    "app/routers/admin.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.models.mission import Mission
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Chief Admin Panel"])

def verify_chief_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز! فقط رئیس کل اجازه ورود دارد.")
    return current_user

@router.get("/pending-operators")
def get_pending_operators(db: Session = Depends(get_db), admin: User = Depends(verify_chief_admin)):
    return db.query(User).filter(User.role == "OPERATOR", User.is_approved == False).all()

@router.post("/approve-operator/{operator_id}")
def approve_operator(operator_id: int, action: str, db: Session = Depends(get_db), admin: User = Depends(verify_chief_admin)):
    op = db.query(User).filter(User.id == operator_id).first()
    if not op:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

    if action == "approve":
        op.is_approved = True
        msg = "مامور با موفقیت تایید شد."
    else:
        db.delete(op)
        msg = "درخواست مامور رد و حذف گردید."

    db.commit()
    return {"message": msg}

@router.get("/all-data")
def get_all_system_data(db: Session = Depends(get_db), admin: User = Depends(verify_chief_admin)):
    users = db.query(User).all()
    missions = db.query(Mission).all()
    return {
        "users": [{"id": u.id, "name": u.full_name, "phone": u.phone_number, "role": u.role, "approved": u.is_approved} for u in users],
        "missions": [{"id": m.id, "title": m.title, "city": m.city, "status": m.status} for m in missions]
    }
''',

    # ---------------------------------------------------------------
    # 6. main.py با پیش‌فرض رئیس کل
    # ---------------------------------------------------------------
    "app/main.py": '''from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import engine, Base, SessionLocal
import app.models
from app.models.user import User

from app.routers import volunteers, missions, auth, admin, messages

Base.metadata.create_all(bind=engine)

# ساخت رئیس کل پیش‌فرض
db = SessionLocal()
chief = db.query(User).filter(User.phone_number == "09120000000").first()
if not chief:
    chief_user = User(
        full_name="فرمانده ارشد مدیریت بحران",
        phone_number="09120000000",
        role="ADMIN",
        is_approved=True
    )
    db.add(chief_user)
    db.commit()
db.close()

app = FastAPI(title="سامانه هوشمند مدیریت بحران", version="4.0.0")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(volunteers.router)
app.include_router(missions.router)
app.include_router(messages.router)

@app.get("/")
def root():
    return {"message": "سامانه آنلاین است", "docs": "/docs"}
'''
}


def update_backend():
    for path, code in files.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(code.strip())
        print(f"✅ فایل بروزرسانی شد: {path}")

    if os.path.exists("disaster.db"):
        os.remove("disaster.db")
        print("🗑️ دیتابیس قدیمی پاک شد تا جداول جدید اضافه شوند.")

    print("\n🎉 بک‌اند کامل سیستم با پشتیبانی از پیام‌ها، تایید رئیس کل و امتیازدهی آماده است!")


if __name__ == "__main__":
    update_backend()