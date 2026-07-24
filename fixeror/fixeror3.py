import os

files = {
    # 1. روتر احراز هویت پیامکی
    "app/routers/auth.py": '''import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, OTPCode, VolunteerProfile
from app.schemas.user import RequestOTPSchema, VerifyOTPSchema, TokenSchema
from app.services.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/send-otp")
def send_otp(data: RequestOTPSchema, db: Session = Depends(get_db)):
    phone = data.phone_number
    # ساخت یک کد ۴ رقمی شبیه‌سازی‌شده
    code = f"{random.randint(1000, 9999)}"

    # برای رئیس کل کد ثابت ۱۲۳۴ جهت سهولت تست
    if phone == "09120000000":
        code = "1234"

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
        "simulated_code": code
    }

@router.post("/verify-otp", response_model=TokenSchema)
def verify_otp(data: VerifyOTPSchema, db: Session = Depends(get_db)):
    otp_entry = db.query(OTPCode).filter(OTPCode.phone_number == data.phone_number).first()
    if not otp_entry or otp_entry.code != data.code:
        raise HTTPException(status_code=400, detail="کد واردشده اشتباه است.")

    user = db.query(User).filter(User.phone_number == data.phone_number).first()

    if not user:
        role = data.role or "VOLUNTEER"
        is_approved = True if role in ["VOLUNTEER", "ADMIN"] else False

        if data.phone_number == "09120000000":
            role = "ADMIN"
            is_approved = True

        user = User(
            full_name=data.full_name or "کاربر جدید",
            phone_number=data.phone_number,
            role=role,
            is_approved=is_approved
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        if role == "VOLUNTEER":
            prof = VolunteerProfile(
                user_id=user.id,
                province=data.province or "تهران",
                city=data.city or "تهران",
                can_deploy=data.can_deploy or False,
                bio=data.bio_text or ""
            )
            db.add(prof)
            db.commit()

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

    # 2. سرویس توکن JWT
    "app/services/auth.py": '''import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User

SECRET_KEY = "CRISIS_MANAGEMENT_SUPER_SECRET_KEY_2026"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/verify-otp")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="اعتبارسنجی ناموفق بود. لطفا مجددا وارد شوید.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user
''',

    # 3. اصلاح روتر داوطلبان برای هماهنگی با توکن جدید
    "app/routers/volunteers.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.services.auth import get_current_user
from app.schemas.user import VolunteerRegisterSchema
from app.services.ai_extractor import extract_skills_with_ai

router = APIRouter(prefix="/api/volunteers", tags=["Volunteers"])

@router.post("/register")
def register_or_update_volunteer(data: VolunteerRegisterSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = db.query(VolunteerProfile).filter(VolunteerProfile.user_id == current_user.id).first()

    extracted_skills = []
    if data.bio:
        extracted_skills = extract_skills_with_ai(data.bio)

    if not profile:
        profile = VolunteerProfile(
            user_id=current_user.id,
            province=data.province,
            city=data.city,
            can_deploy=data.can_deploy or False,
            bio=data.bio or "",
            skills=extracted_skills,
            available_from=data.available_from,
            available_to=data.available_to
        )
        db.add(profile)
    else:
        profile.province = data.province
        profile.city = data.city
        profile.can_deploy = data.can_deploy or False
        profile.bio = data.bio or ""
        profile.skills = extracted_skills
        profile.available_from = data.available_from
        profile.available_to = data.available_to

    db.commit()
    return {"message": "اطلاعات داوطلبی با موفقیت ثبت/بروزرسانی شد.", "skills": extracted_skills}
'''
}

for path, code in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(code.strip())
    print(f"✅ فایل بروزرسانی شد: {path}")