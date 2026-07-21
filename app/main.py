from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import engine, Base, SessionLocal
import app.models
from app.models.user import User

from app.routers import volunteers, missions, auth, admin, messages

Base.metadata.create_all(bind=engine)

# ساخت رئیس کل پیش‌فرض
db = SessionLocal()
chief = db.query(User).filter(User.phone_number == "09120000000").first()
if not chief:
    chief_user = User(
        full_name="فرمانده ارشد مدیریت بحران",
        phone_number="09120000000",
        role="ADMIN",
        is_approved=True
    )
    db.add(chief_user)
    db.commit()
db.close()

app = FastAPI(title="سامانه هوشمند مدیریت بحران", version="4.0.0")

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(volunteers.router)
app.include_router(missions.router)
app.include_router(messages.router)

@app.get("/")
def root():
    return {"message": "سامانه آنلاین است", "docs": "/docs"}