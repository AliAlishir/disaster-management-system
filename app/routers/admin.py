from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.models.mission import Mission
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])


def _verify_chief(current_user: User):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")


@router.get("/pending-operators")
def get_pending_operators(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_chief(current_user)

    operators = db.query(User).filter(User.role == "OPERATOR").all()

    # === رفع نیاز: ماموران تاییدنشده ابتدا و تاییدشده‌ها در انتها نمایش داده شوند ===
    operators.sort(key=lambda o: o.is_approved)

    return [
        {
            "id": o.id,
            "full_name": o.full_name,
            "phone_number": o.phone_number,
            "is_approved": o.is_approved
        } for o in operators
    ]


@router.post("/approve-operator/{user_id}")
def approve_operator(user_id: int, action: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_chief(current_user)

    user = db.query(User).filter(User.id == user_id, User.role == "OPERATOR").first()
    if not user:
        raise HTTPException(status_code=404, detail="مامور مورد نظر یافت نشد.")

    if action == "approve":
        user.is_approved = True
        msg = f"مامور {user.full_name} با موفقیت تایید شد."
    elif action == "reject":
        user.is_approved = False
        msg = f"درخواست مامور {user.full_name} رد شد."
    else:
        raise HTTPException(status_code=400, detail="عملیات نامعتبر است.")

    db.commit()
    return {"message": msg}


@router.get("/all-data")
def get_all_system_data(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _verify_chief(current_user)

    users = db.query(User).all()
    volunteers = db.query(VolunteerProfile).join(User).all()
    missions = db.query(Mission).all()

    return {
        "users": [
            {"id": u.id, "name": u.full_name, "phone": u.phone_number, "role": u.role, "approved": u.is_approved}
            for u in users
        ],
        "volunteers": [
            {
                "id": v.id,
                "name": v.user.full_name,
                "phone": v.user.phone_number,
                "province": v.province,
                "city": v.city,
                "can_deploy": v.can_deploy,
                "skills": v.skills,
                "rating": v.rating
            } for v in volunteers
        ],
        "missions": [
            {
                "id": m.id,
                "title": m.title,
                "province": m.province,
                "city": m.city,
                "address": m.address,
                "status": m.status,
                "creator_id": m.creator_id
            } for m in missions
        ]
    }