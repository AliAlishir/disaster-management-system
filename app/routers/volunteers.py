from fastapi import APIRouter, Depends, HTTPException
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