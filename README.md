# 🛡️ سامانه هوشمند مدیریت، تطبیق و تخصیص داوطلبان بحران
> **Crisis Volunteer Management & Smart Matching System**
> 
> سامانه چابک، سبک و پایدار جهت مدیریت، رتبه‌بندی و فراخوانی هوشمند داوطلبان مردمی در شرایط اضطراری و بحران‌های طبیعی.

---

## 📌 درباره پروژه

در شرایط بحران (زلزله، سیل و...)، بزرگ‌ترین چالش ستادهای مدیریت بحران، عدم وجود یک سیستم سریع و قابل اعتماد برای **تطبیق مهارت داوطلبان با نیازهای میدانی** است. این پروژه یک پلتفرم کامل و آفلاین-محور است که به ماموران ستادی اجازه می‌دهد با ثبت ماموریت‌ها، بهترین داوطلبان واجد شرایط را بر اساس **مهارت‌های تخصصی، موقعیت مکانی و بازه زمانی آمادگی** شناسایی و فراخوانی کنند.

### ✨ ویژگی‌های کلیدی سیستم
- **ورود بدون رمز عبور (OTP-based Auth):** ورود سریع کاربران تنها با شماره موبایل و کد یک‌بارمصرف.
- **کنترل دسترسی مبتنی بر نقش (RBAC):** تفکیک کامل سطوح دسترسی برای ۳ نقش `VOLUNTEER` (داوطلب)، `OPERATOR` (مامور) و `ADMIN` (رئیس کل).
- **موتور تطبیق هوشمند (Offline Matching Engine):** الگوریتم ۳ مرحله‌ای منطقی جهت رتبه‌بندی داوطلبان بر اساس بیشترین انطباق مهارتی و مکانی بدون وابستگی به اینترنت یا سرویس‌های ابری خارجی.
- **جلوگیری از دعوت تکراری (Idempotency):** مکانیزم هوشمند جلوگیری از ارسال چندباره دعوت‌نامه به یک داوطلب در یک ماموریت.
- **صندوق پیام شخصی و Broadcast:** قابلیت ارسال پیام اضطراری همگانی توسط مدیر کل و مدیریت وضعیت خوانده‌شدن پیام‌ها به‌صورت مجزا.
- **طراحی مقاوم در برابر بحران:** پیاده‌سازی کامل به صورت آفلاین برای پایداری ۱۰۰٪ در زمان قطعی اینترنت بین‌المللی.

---

## 🛠️ تکنولوژی‌ها و ابزارهای استفاده‌شده

| بخش | تکنولوژی / کتابخانه |
| :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) |
| **Database & ORM** | SQLite + [SQLAlchemy](https://www.sqlalchemy.org/) |
| **Authentication** | OAuth2 + JWT (JSON Web Tokens) + Passlib |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **Frontend** | HTML5, CSS3 (Modern Responsive UI), Vanilla JavaScript |
| **Version Control** | Git & GitHub |

---

## 📂 ساختار پروژه (Directory Structure)

```text
├── main.py                   # نقطه ورود برنامه و اجرای FastAPI
├── database.py               # تنظیمات اتصال به دیتابیس و Sessionها
├── models.py                 # مدل‌های دیتابیس (SQLAlchemy Models)
├── schemas.py                # Schemaهای اعتبارسنجی داده (Pydantic Models)
├── auth.py                   # منطق احراز هویت، تولید OTP و مدیریت توکن‌های JWT
├── routers/                  # اندپوینت‌های تفکیک‌شده API
│   ├── auth_router.py        # ثبت‌نام، ورود و مدیریت دسترسی کاربران
│   ├── volunteer_router.py   # پروفایل و مهارت‌های داوطلبان
│   ├── mission_router.py     # مدیریت ماموریت‌ها و موتور تطبیق
│   └── message_router.py     # صندوق پیام‌ها و Broadcast
├── static/                   # فایل‌های فرانت‌اند (HTML/CSS/JS)
└── README.md                 # مستندات راهنمای پروژه
```
---
## 🚀 راهنمای نصب و اجرای پروژه
پیش‌نیازها
نصب بودن Python 3.10 یا نسخه‌های بالاتر

نصب بودن pip و git

مراحل اجرا
۱. کلون کردن مخزن پروژه:

```text
git clone [https://github.com/USERNAME/REPO_NAME.git](https://github.com/AliAlishir/disaster-management-system.git)
cd REPO_NAME
```

۲. ایجاد و فعال‌سازی محیط مجازی (Virtual Environment):

```text
# Linux / macOS
python3 -m venv venv
source venv/bin/venv/activate

# Windows
python -m venv venv
venv\Scripts\activate
```
۳. نصب کتابخانه‌های مورد نیاز:

```text
pip install -r requirements.txt
```

۴. اجرای سرور توسعه:
```text
uvicorn main:app --reload
```
۵. دسترسی به سامانه:

واسط کاربری (UI): .0.0.1:8000/static/index.html?

مستندات تعاملی API (Swagger UI): http://127.0.0.1:8000/docs

مستندات جایگزین (ReDoc): http://127.0.0.1:8000/redoc

📊 متدولوژی و مدیریت پروژه (Agile / Scrum)
این پروژه در قالب ۶ اسپرینت چابک (Sprint 0 تا Sprint 5) مدیریت و پیاده‌سازی شده است.

مجموع داستان‌های کاربر (Story Points): ۱۰۶ پوینت (بر اساس دنباله فیبوناچی)

سرعت متوسط تیم (Velocity): ۱۷.۶ پوینت در هر اسپرینت

آرتیفکت‌های اسکرام
Product Backlog: شامل ۲۱ داستان کاربر و تسک فنی به ترتیب اولویت ارزش کسب‌وکار.

Sprint Backlog: تفکیک دقیق کارهای جاری در بازه‌های ۲ هفته‌ای.

Increment: تحویل یک نسخه کارکردنی و قابل دمو در پایان هر اسپرینت بر اساس معیارهای Definition of Done (DoD).

🤖 ابزارهای هوش مصنوعی بکاررفته (AI Collaboration)
در طول توسعه این پروژه، از هوش مصنوعی به عنوان همکار مهندسی (Co-pilot) بهره گرفته شده است:

Google Gemini: ایده‌پردازی معماری اولیه، تفکیک User Storyها و تدوین گزارش‌های مدیریت پروژه.

Claude (via GitHub Integration): توسعه کدهای پایتون، refactoring چندفایلی و دیباگ همزمانی دیتابیس (IntegrityError).

ChatGPT: طراحی بصری و تولید پوستر گرافیکی ارائه پروژه.