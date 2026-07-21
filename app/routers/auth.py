import random
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