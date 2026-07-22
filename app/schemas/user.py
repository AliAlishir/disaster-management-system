import re
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