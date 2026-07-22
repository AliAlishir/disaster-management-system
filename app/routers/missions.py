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
        missions = db.query(Mission).all()
    else:
        missions = db.query(Mission).filter(Mission.creator_id == current_user.id).all()

    # === رفع نیاز: ماموریت‌های باز ابتدا و ماموریت‌های خاتمه‌یافته در انتها نمایش داده شوند ===
    missions.sort(
        key=lambda m: (m.status == "COMPLETED", -(m.created_at.timestamp() if m.created_at else 0))
    )

    return [
        {
            "id": m.id,
            "title": m.title,
            "province": m.province,
            "city": m.city,
            "address": m.address,
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

    result = calculate_smart_match(mission_id, db)

    # === رفع نیاز: مشخص کردن داوطلبانی که قبلاً برای این ماموریت دعوت شده‌اند ===
    already_invited_ids = {
        row.receiver_id for row in db.query(Message.receiver_id).filter(Message.mission_id == mission.id).all()
    }
    if result and result.get("recommended_volunteers"):
        for v in result["recommended_volunteers"]:
            v["already_invited"] = v["volunteer_id"] in already_invited_ids

    if result:
        result["mission_status"] = mission.status

    return result


@router.post("/{mission_id}/invite")
def invite_volunteer(mission_id: int, data: InviteVolunteerSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)

    # === رفع نیاز: برای ماموریت خاتمه‌یافته دیگر امکان ارسال درخواست کمک وجود ندارد ===
    if mission.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="این ماموریت خاتمه یافته و امکان ارسال درخواست کمک برای آن وجود ندارد.")

    volunteer = db.query(User).filter(User.id == data.volunteer_id, User.role == "VOLUNTEER").first()
    if not volunteer:
        raise HTTPException(status_code=404, detail="داوطلب مورد نظر یافت نشد.")

    already_invited = db.query(Message).filter(
        Message.mission_id == mission.id,
        Message.receiver_id == volunteer.id
    ).first()
    if already_invited:
        raise HTTPException(status_code=400, detail="قبلاً برای این داوطلب در این ماموریت پیام دعوت ارسال شده است.")

    # === رفع نیاز: آدرس کامل و ساعت ماموریت در متن پیام دعوت قید می‌شود ===
    mission_time_text = mission.mission_date.strftime("%Y-%m-%d      %H:%M")

    msg = Message(
        sender_id=current_user.id,
        receiver_id=volunteer.id,
        title=f"دعوت به ماموریت: {mission.title}",
        body=(
            f"شما توسط ستاد بحران برای ماموریت '{mission.title}' دعوت شده‌اید.\n"
            f"📍 آدرس محل ماموریت: {mission.address} (استان {mission.province}، شهر {mission.city})\n"
            f"🗓️ زمان ماموریت: {mission_time_text}"
        ),
        category="ماموریت",
        mission_id=mission.id
    )
    db.add(msg)
    db.commit()

    return {"message": f"دعوت‌نامه با موفقیت برای داوطلب ({volunteer.full_name}) ارسال شد."}


@router.post("/{mission_id}/complete")
def complete_mission(mission_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    _check_mission_access(mission, current_user)

    if mission.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="این ماموریت قبلاً خاتمه یافته است.")

    mission.status = "COMPLETED"
    db.commit()
    return {"message": "ماموریت با موفقیت خاتمه یافت و دیگر امکان ارسال درخواست کمک برای آن وجود ندارد."}