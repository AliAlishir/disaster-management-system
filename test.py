import os

# لیست پوشه‌هایی که باید ساخته شوند
directories = [
    "app",
    "app/models",
    "app/schemas",
    "app/services",
    "app/routers",
    "static",
    "static/css",
    "static/js",
]

# محتوای فایل‌های پایه
files_content = {
    # فایل‌های __init__.py برای ماژولار شدن پایتون
    "app/__init__.py": "",
    "app/models/__init__.py": "",
    "app/schemas/__init__.py": "",
    "app/services/__init__.py": "",
    "app/routers/__init__.py": "",

    # فایل تنظیمات پکیج‌ها
    "requirements.txt": "fastapi\nuvicorn\nsqlalchemy\npydantic\npython-dotenv\nrequests\n",

    # فایل متغیرهای محیطی
    ".env": "GROQ_API_KEY=gsk_YOUR_ACTUAL_GROQ_KEY_HERE\n",

    # فایل تنظیمات پروژه
    "app/config.py": '''import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "سامانه هوشمند مدیریت داوطلبان بحران"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DATABASE_URL: str = "sqlite:///./disaster.db"

settings = Settings()
''',

    # فایل اتصال دیتابیس
    "app/database.py": '''from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',

    # فایل‌های فرانت‌اند اولیه
    "static/index.html": "<!DOCTYPE html>\n<html lang=\"fa\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>سامانه داوطلبان بحران</title>\n</head>\n<body>\n    <h1>به سامانه هوشمند مدیریت بحران خوش آمدید</h1>\n</body>\n</html>\n",
}


def create_structure():
    # ۱. ساخت پوشه‌ها
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 پوشه ساخته شد: {directory}")

    # ۲. ساخت فایل‌ها با محتوای اولیه
    for file_path, content in files_content.items():
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"📄 فایل ساخته شد: {file_path}")
        else:
            print(f"⚠️ فایل از قبل وجود داشت: {file_path}")

    print("\n🎉 تمام پوشه‌ها و فایل‌های پروژه با موفقیت ساخته شدند!")


if __name__ == "__main__":
    create_structure()