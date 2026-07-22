from pydantic import BaseModel, field_validator
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