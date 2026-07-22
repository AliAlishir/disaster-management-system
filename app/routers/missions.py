from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, Message
from app.models.mission import Mission
from app.schemas.mission import MissionCreateSchema, InviteVolunteerSchema
from app.services.auth import get_current_user
from app.services.matching import calculate_smart_match

router = APIRouter(prefix="/api/missions", tags=["Missions"])


def _check_mission_access(mission: Mission, current_user: User):
    if not mission:
        raise HTTPException(status_code=404, detail="ماموریت یافت نشد.")
    if current_user.role != "ADMIN" and mission.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="شما فقط به ماموریت‌های خودتان دسترسی دارید.")


@router.post("/")
def create_mission(data: MissionCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ["ADMIN", "OPERATOR"]:
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

    mission = Mission(
        title=data.title,
        province=data.province,
        city=data.city,
        address=data.address,
        required_skills=data.required_skills,
        mission_date=data.mission_date,
        creator_id=current_user.id,
        status="OPEN"
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return {"message": "ماموریت با موفقیت ایجاد شد", "mission_id": mission.id}


@router.get("/my-missions")
def get_missions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "ADMIN":
        missions = db.query(Mission).order_by(Mission.created_at.desc()).all()
    else:
        missions = db.query(Mission).filter(Mission.creator_id == current_user.id).order_by(Mission.created_at.desc()).all()

    return [
        {
            "id": m.id,
            "title": m.title,
            "province": m.province,
            "city": m.city,
            "required_skills": m.required_skills,
            "mission_date": m.mission_date.strftime("%Y-%m-%d %H:%M"),
            "status": m.status,
            "creator_id": m.creator_id,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M")
        } for m in missions
    ]


@router.get("/{mission_id}/match")
def match_volunteers(mission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)
    return calculate_smart_match(mission_id, db)


@router.post("/{mission_id}/invite")
def invite_volunteer(mission_id: int, data: InviteVolunteerSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)

    volunteer = db.query(User).filter(User.id == data.volunteer_id, User.role == "VOLUNTEER").first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="داوطلب مورد نظر یافت نشد.")

    # === رفع نیاز اصلی: جلوگیری از ارسال پیام تکراری به یک داوطلب برای همان ماموریت ===
    already_invited = db.query(Message).filter(
        Message.mission_id == mission.id,
        Message.receiver_id == volunteer.id
    ).first()
    if already_invited:
        raise HTTPException(status_code=400, detail="قبلاً برای این داوطلب در این ماموریت پیام دعوت ارسال شده است.")

    msg = Message(
        sender_id=current_user.id,
        receiver_id=volunteer.id,
        title=f"دعوت به ماموریت: {mission.title}",
        body=f"شما توسط ستاد بحران برای ماموریت '{mission.title}' در استان {mission.province}، شهر {mission.city} دعوت شده‌اید.",
        category="ماموریت",
        mission_id=mission.id
    )
    db.add(msg)
    db.commit()

    return {"message": f"دعوت‌نامه با موفقیت برای داوطلب ({volunteer.full_name}) ارسال شد."}