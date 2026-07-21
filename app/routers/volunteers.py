from fastapi import APIRouter, Depends, HTTPException
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