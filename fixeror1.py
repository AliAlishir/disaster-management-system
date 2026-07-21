import os

files_to_fix = {
    # ---------------------------------------------------------------
    # 1. اصلاح app/schemas/user.py (افزودن کلاس‌های مورد نیاز volunteers.py)
    # ---------------------------------------------------------------
    "app/schemas/user.py": '''import re
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

class UserRegisterSchema(BaseModel):
    full_name: str
    phone_number: str
    password: str
    role: Optional[str] = "VOLUNTEER"
    province: str
    city: str
    can_deploy: bool = False
    bio_text: str
    available_from: datetime
    available_to: datetime

    @field_validator("phone_number")
    def validate_phone(cls, v):
        pattern = r"^09\d{9}$"
        if not re.match(pattern, v):
            raise ValueError("شماره تلفن معتبر نیست. فرمت صحیح: 09123456789")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("رمز عبور باید حداقل ۶ کاراکتر باشد.")
        return v

# برای حفظ سازگاری با روت‌های قبلی
class VolunteerRegisterSchema(UserRegisterSchema):
    pass

class VolunteerResponseSchema(BaseModel):
    id: int
    full_name: str
    phone_number: str
    province: Optional[str] = None
    city: str
    can_deploy: bool
    skills: List[str]
    available_from: datetime
    available_to: datetime

    class Config:
        from_attributes = True

class TokenSchema(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
''',

    # ---------------------------------------------------------------
    # 2. اصلاح app/routers/volunteers.py (هماهنگ‌سازی با مدل‌های جدید)
    # ---------------------------------------------------------------
    "app/routers/volunteers.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.schemas.user import VolunteerRegisterSchema, VolunteerResponseSchema
from app.services.ai_service import extract_skills_with_ai

router = APIRouter(prefix="/api/volunteers", tags=["Volunteers"])

@router.get("/", response_model=List[VolunteerResponseSchema])
def get_all_volunteers(db: Session = Depends(get_db)):
    profiles = db.query(VolunteerProfile).all()
    result = []
    for p in profiles:
        result.append({
            "id": p.user.id,
            "full_name": p.user.full_name,
            "phone_number": p.user.phone_number,
            "province": p.province,
            "city": p.city,
            "can_deploy": p.can_deploy,
            "skills": p.skills or [],
            "available_from": p.available_from,
            "available_to": p.available_to
        })
    return result
'''
}

def fix():
    for file_path, content in files_to_fix.items():
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"✅ فایل اصلاح شد: {file_path}")
    print("\n🎉 ناهماهنگی فایل‌ها برطرف شد!")

if __name__ == "__main__":
    fix()