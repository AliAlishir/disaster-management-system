from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User, Message
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/messages", tags=["Messages"])

class BroadcastSchema(BaseModel):
    title: str
    body: str

@router.get("/my-messages")
def get_my_messages(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    msgs = db.query(Message).filter(
        (Message.receiver_id == current_user.id) | (Message.receiver_id == None)
    ).order_by(Message.created_at.desc()).all()

    return [
        {
            "id": m.id,
            "title": m.title,
            "body": m.body,
            "category": m.category,
            "is_read": m.is_read,
            "mission_id": m.mission_id,
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M")
        } for m in msgs
    ]

@router.post("/{message_id}/read")
def mark_message_as_read(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if msg:
        msg.is_read = True
        db.commit()
    return {"message": "بروزرسانی شد"}

@router.post("/broadcast")
def send_broadcast_message(data: BroadcastSchema, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="تنها رئیس کل مجاز به ارسال پیام همگانی است.")

    msg = Message(
        sender_id=current_user.id,
        receiver_id=None,
        title=data.title,
        body=data.body,
        category="سیستمی"
    )
    db.add(msg)
    db.commit()
    return {"message": "پیام همگانی با موفقیت برای تمامی کاربران ارسال شد."}