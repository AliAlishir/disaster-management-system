import re
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

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

# 2. اسکیماهای کاربر و ثبت نام
class UserRegisterSchema(BaseModel):
    full_name: str
    phone_number: str
    role: Optional[str] = "VOLUNTEER"
    password: Optional[str] = None

# 3. اسکیماهای مربوط به داوطلبان
class VolunteerRegisterSchema(BaseModel):
    full_name: str
    phone_number: str
    province: str
    city: str
    can_deploy: Optional[bool] = False
    bio: Optional[str] = None
    available_from: Optional[datetime] = None
    available_to: Optional[datetime] = None

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