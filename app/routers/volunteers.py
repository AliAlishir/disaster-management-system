from fastapi import APIRouter, Depends, HTTPException
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