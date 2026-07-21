import os

files_to_update = {
    # ---------------------------------------------------------------
    # 1. نصب پکیج‌های جدید احراز هویت در requirements.txt
    # ---------------------------------------------------------------
    "requirements.txt": "fastapi\nuvicorn\nsqlalchemy\npydantic\npython-dotenv\nrequests\npython-jose[cryptography]\npasslib[bcrypt]\npython-multipart\n",

    # ---------------------------------------------------------------
    # 2. اصلاح مدل دیتابیس کاربر (افزودن password_hash, province, role)
    # ---------------------------------------------------------------
    "app/models/user.py": '''from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="VOLUNTEER") # VOLUNTEER, OPERATOR, ADMIN
    created_at = Column(DateTime, default=datetime.utcnow)

    volunteer_profile = relationship("VolunteerProfile", back_populates="user", uselist=False)


class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    province = Column(String, index=True, nullable=False)
    city = Column(String, index=True, nullable=False)
    can_deploy = Column(Boolean, default=False)
    bio = Column(Text, nullable=True)
    skills = Column(JSON, default=[])

    rating = Column(Integer, default=5)
    available_from = Column(DateTime, nullable=True)
    available_to = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="volunteer_profile")
''',

    # ---------------------------------------------------------------
    # 3. اصلاح مدل دیتابیس ماموریت (افزودن province)
    # ---------------------------------------------------------------
    "app/models/mission.py": '''from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from datetime import datetime
from app.database import Base

class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    province = Column(String, index=True, nullable=False)
    city = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)

    essential_skills = Column(JSON, default=[])
    bonus_skills = Column(JSON, default=[])

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)
''',

    # ---------------------------------------------------------------
    # 4. اعتبارسنجی دقیق ورودی‌ها با Pydantic
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

class TokenSchema(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
''',

    # ---------------------------------------------------------------
    # 5. سرویس هوش مصنوعی مقاوم‌تر برای استخراج مهارت‌ها
    # ---------------------------------------------------------------
    "app/services/ai_service.py": '''import requests
import json
from app.config import settings

def extract_skills_with_ai(bio_text: str) -> list[str]:
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_YOUR"):
        print("❌ کلید API معتبر تنظیم نشده است.")
        return []

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    متن داوطلب: "{bio_text}"

    وظیفه: تمام مهارت‌ها، تخصص‌ها، مدرک‌ها و امکاناتی (مثل خودرو، ابزار) که در متن ذکر شده را استخراج کن.
    پاسخ باید **دقیقاً و فقط** یک JSON حاوی کلید 'skills' به‌صورت لیستی از رشته‌ها باشد.
    مثال خروجی: {{"skills": ["امدادگری", "رانندگی وانت", "کمک‌های اولیه"]}}
    """

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=8)
        if response.status_code == 200:
            res_data = response.json()
            content = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            skills = parsed.get("skills", [])
            print(f"✅ مهارت‌های استخراج‌شده: {skills}")
            return skills
        else:
            print(f"❌ خطا از سمت API Groq: {response.text}")
    except Exception as e:
        print(f"❌ خطای ارتباطی در فراخوانی هوش مصنوعی: {e}")

    return []
''',

    # ---------------------------------------------------------------
    # 6. سرویس احراز هویت (JWT & Password Hashing)
    # ---------------------------------------------------------------
    "app/services/auth.py": '''from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User

SECRET_KEY = "SUPER_SECRET_KEY_DISASTER_MANAGEMENT_APP"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="اعتبارنامه احراز هویت نامعتبر است",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone_number: str = payload.get("sub")
        if phone_number is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.phone_number == phone_number).first()
    if user is None:
        raise credentials_exception
    return user
''',

    # ---------------------------------------------------------------
    # 7. Router جدید احراز هویت (ورود و ثبت نام)
    # ---------------------------------------------------------------
    "app/routers/auth.py": '''from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.schemas.user import UserRegisterSchema, TokenSchema
from app.services.auth import hash_password, verify_password, create_access_token
from app.services.ai_service import extract_skills_with_ai

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register", response_model=dict)
def register_user(data: UserRegisterSchema, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.phone_number == data.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="این شماره تلفن قبلاً ثبت‌نام شده است.")

    # ۱. استخراج مهارت‌ها با AI
    skills = extract_skills_with_ai(data.bio_text)

    # ۲. ذخیره کاربر
    new_user = User(
        full_name=data.full_name,
        phone_number=data.phone_number,
        hashed_password=hash_password(data.password),
        role=data.role or "VOLUNTEER"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ۳. ذخیره پروفایل داوطلبی
    profile = VolunteerProfile(
        user_id=new_user.id,
        province=data.province,
        city=data.city,
        can_deploy=data.can_deploy,
        bio=data.bio_text,
        skills=skills,
        available_from=data.available_from,
        available_to=data.available_to
    )
    db.add(profile)
    db.commit()

    return {"message": "ثبت‌نام با موفقیت انجام شد", "extracted_skills": skills}

@router.post("/login", response_model=TokenSchema)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone_number == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="شماره تلفن یا رمز عبور نادرست است.")

    token = create_access_token(data={"sub": user.phone_number, "role": user.role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name
    }
''',

    # ---------------------------------------------------------------
    # 8. اتصال Router جدید Auth در main.py
    # ---------------------------------------------------------------
    "app/main.py": '''from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import engine, Base
import app.models

from app.routers import volunteers, missions, auth

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="سیستم مدیریت داوطلبان بحران با احراز هویت و AI",
    version="2.0.0"
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(volunteers.router)
app.include_router(missions.router)

@app.get("/")
def root():
    return {"message": "سامانه مدیریت بحران آنلاین است", "docs": "/docs"}
'''
}


def update():
    for file_path, content in files_to_update.items():
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"✅ فایل بروزرسانی شد: {file_path}")

    if os.path.exists("disaster.db"):
        os.remove("disaster.db")
        print("🗑️ دیتابیس قدیمی پاک شد تا ساختار جدید جداول ایجاد شود.")

    print("\n🎉 ساختار جدید بک‌اند و احراز هویت با موفقیت پیاده‌سازی شد!")


if __name__ == "__main__":
    update()