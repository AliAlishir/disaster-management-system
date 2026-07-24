import os

files = {
    # ---------------------------------------------------------------
    # 1. روتر احراز هویت هوشمند (تفکیک ورود از ثبت‌نام)
    # ---------------------------------------------------------------
    "app/routers/auth.py": '''import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, OTPCode, VolunteerProfile
from app.schemas.user import RequestOTPSchema, VerifyOTPSchema, TokenSchema
from app.services.auth import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/send-otp")
def send_otp(data: RequestOTPSchema, db: Session = Depends(get_db)):
    phone = data.phone_number

    # بررسی اینکه آیا کاربر قبلاً ثبت‌نام کرده است؟
    existing_user = db.query(User).filter(User.phone_number == phone).first()
    is_registered = True if existing_user else False

    # کد ۴ رقمی شبیه‌سازی‌شده (برای رئیس کل کد ثابت ۱۲۳۴)
    code = "1234" if phone == "09120000000" else f"{random.randint(1000, 9999)}"

    otp_entry = db.query(OTPCode).filter(OTPCode.phone_number == phone).first()
    if otp_entry:
        otp_entry.code = code
        otp_entry.created_at = datetime.utcnow()
    else:
        otp_entry = OTPCode(phone_number=phone, code=code)
        db.add(otp_entry)

    db.commit()

    return {
        "message": "کد تایید ارسال شد",
        "simulated_code": code,
        "is_registered": is_registered  # اطلاع به فرانت‌اند که کاربر قدیمی است یا جدید
    }

@router.post("/verify-otp", response_model=TokenSchema)
def verify_otp(data: VerifyOTPSchema, db: Session = Depends(get_db)):
    otp_entry = db.query(OTPCode).filter(OTPCode.phone_number == data.phone_number).first()
    if not otp_entry or otp_entry.code != data.code:
        raise HTTPException(status_code=400, detail="کد واردشده اشتباه است.")

    user = db.query(User).filter(User.phone_number == data.phone_number).first()

    # اگر کاربر جدید است، ثبت‌نامش می‌کنیم
    if not user:
        if not data.full_name:
            raise HTTPException(status_code=400, detail="لطفاً نام و نام خانوادگی خود را وارد کنید.")

        role = data.role or "VOLUNTEER"
        is_approved = True if role in ["VOLUNTEER", "ADMIN"] else False

        user = User(
            full_name=data.full_name,
            phone_number=data.phone_number,
            role=role,
            is_approved=is_approved
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        if role == "VOLUNTEER":
            prof = VolunteerProfile(
                user_id=user.id,
                province="تهران",
                city="تهران",
                can_deploy=False,
                bio=""
            )
            db.add(prof)
            db.commit()

    # اگر کاربر از قبل وجود دارد، توکن ورودی صادر می‌شود
    token_data = {
        "sub": str(user.id),
        "phone": user.phone_number,
        "role": user.role,
        "name": user.full_name,
        "approved": user.is_approved
    }
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name,
        "is_approved": user.is_approved
    }
''',

    # ---------------------------------------------------------------
    # 2. فرانت‌اند بروزرسانی‌شده با تایید زنده رئیس کل و ورود هوشمند
    # ---------------------------------------------------------------
    "static/index.html": '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سامانه فرماندهی و مدیریت بحران</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css">
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" />
    <style>
        body { font-family: 'Vazirmatn', sans-serif; background-color: #f4f6f9; }
        .card { border-radius: 12px; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    </style>
</head>
<body>

<div class="container py-4">
    <header class="pb-3 mb-4 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <h3 class="fw-bold text-primary">🚨 سامانه هوشمند فرماندهی و مدیریت بحران</h3>
            <p class="text-muted mb-0">سیستم مدیریت ماموریت‌ها، داوطلبان و تاییدات مرکز فرماندهی</p>
        </div>
        <div id="authBox">
            <button class="btn btn-primary fw-bold" onclick="showAuthModal()">📲 ورود / ثبت‌نام با پیامک</button>
        </div>
    </header>

    <div id="unapprovedAlert" class="alert alert-warning fw-bold text-center" style="display:none;">
        ⏳ حساب کاربری شما به عنوان "مامور" ثبت شده است اما هنوز توسط رئیس کل تایید نشده است.
    </div>

    <!-- تب‌های منو -->
    <ul class="nav nav-pills mb-4" id="mainTabs">
        <li class="nav-item">
            <button class="nav-link active fw-bold" data-bs-toggle="pill" data-bs-target="#tab-vol">🙋‍♂️ اعلام داوطلبی</button>
        </li>
        <li class="nav-item" id="nav-inbox" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-msg" onclick="loadMessages()">📬 صندوق پیام‌ها</button>
        </li>
        <li class="nav-item" id="nav-create-mis" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-create-mis">📋 ایجاد ماموریت جدید</button>
        </li>
        <li class="nav-item" id="nav-manage-mis" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-manage-mis" onclick="loadMyMissions()">⚙️ مدیریت ماموریت‌ها</button>
        </li>
        <li class="nav-item" id="nav-chief" style="display:none;">
            <button class="nav-link fw-bold btn-danger text-white ms-2" data-bs-toggle="pill" data-bs-target="#tab-chief" onclick="loadChiefPanel()">👑 پنل اختصاصی رئیس کل</button>
        </li>
    </ul>

    <div class="tab-content">
        <!-- اعلام داوطلبی -->
        <div class="tab-pane fade show active" id="tab-vol">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ثبت مشخصات داوطلبی</h5>
                <form id="volForm" onsubmit="saveVolunteerProfile(event)">
                    <div class="row g-3">
                        <div class="col-md-3"><select id="volProv" class="form-select" onchange="updateCities('volProv', 'volCity')" required><option value="">انتخاب استان...</option></select></div>
                        <div class="col-md-3"><select id="volCity" class="form-select" required><option value="">انتخاب شهر...</option></select></div>
                        <div class="col-md-3"><label class="form-label">از تاریخ</label><input type="datetime-local" id="volFrom" class="form-control" required></div>
                        <div class="col-md-3"><label class="form-label">تا تاریخ</label><input type="datetime-local" id="volTo" class="form-control" required></div>
                        <div class="col-12"><textarea id="volBio" class="form-control" rows="3" placeholder="توضیحات و توانمندی‌ها..."></textarea></div>
                        <div class="col-12"><button type="submit" class="btn btn-primary fw-bold">ثبت وضعیت داوطلبی</button></div>
                    </div>
                </form>
            </div>
        </div>

        <!-- صندوق پیام‌ها -->
        <div class="tab-pane fade" id="tab-msg">
            <div class="card p-4"><div id="messagesList">در حال بارگذاری پیام‌ها...</div></div>
        </div>

        <!-- ایجاد ماموریت -->
        <div class="tab-pane fade" id="tab-create-mis">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">تعریف ماموریت عملیاتی</h5>
                <form id="misForm">
                    <div class="row g-3">
                        <div class="col-md-6"><input type="text" id="misTitle" class="form-control" placeholder="عنوان ماموریت" required></div>
                        <div class="col-md-3"><select id="misProv" class="form-select" onchange="updateCities('misProv', 'misCity')" required><option value="">استان...</option></select></div>
                        <div class="col-md-3"><select id="misCity" class="form-select" required><option value="">شهر...</option></select></div>
                        <div class="col-md-6"><input type="text" id="misEssential" class="form-control" placeholder="مهارت‌های ضروری" required></div>
                        <div class="col-md-6"><input type="text" id="misBonus" class="form-control" placeholder="مهارت‌های امتیازی"></div>
                        <div class="col-md-6"><input type="datetime-local" id="misStart" class="form-control" required></div>
                        <div class="col-md-6"><input type="datetime-local" id="misEnd" class="form-control" required></div>
                        <div class="col-12"><button type="submit" class="btn btn-success fw-bold">ثبت ماموریت</button></div>
                    </div>
                </form>
            </div>
        </div>

        <!-- مدیریت ماموریت‌ها -->
        <div class="tab-pane fade" id="tab-manage-mis">
            <div class="card p-4"><div id="myMissionsList">در حال دریافت ماموریت‌ها...</div></div>
        </div>

        <!-- پنل رئیس کل -->
        <div class="tab-pane fade" id="tab-chief">
            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-danger mb-3">👨‍✈️ ماموران در انتظار تایید سیستم</h5>
                <div id="pendingOpsList">در حال بررسی...</div>
            </div>
            <div class="card p-4">
                <h5 class="fw-bold mb-3">📊 دسترسی کلی به تمام داده‌ها</h5>
                <div id="allSystemData">در حال بارگذاری...</div>
            </div>
        </div>
    </div>
</div>

<!-- مودال احراز هویت -->
<div class="modal fade" id="authModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header"><h5 class="modal-title fw-bold" id="authModalTitle">ورود / ثبت‌نام با پیامک</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body">
                <div id="step1">
                    <label class="form-label">شماره تلفن همراه:</label>
                    <input type="tel" id="authPhone" class="form-control mb-3" placeholder="09123456789">
                    <button onclick="sendOTP()" class="btn btn-primary w-100 fw-bold">دریافت کد تایید</button>
                </div>
                <div id="step2" style="display:none;">
                    <div class="alert alert-info">📱 کد تایید پیامک‌شده: <b id="simCode"></b></div>
                    <input type="text" id="authCode" class="form-control mb-3" placeholder="کد ۴ رقمی">

                    <!-- بخش ثبت‌نام فقط برای کاربر جدید نمایش داده می‌شود -->
                    <div id="regFields" style="display:none;" class="border-top pt-3 mb-3">
                        <p class="text-primary small fw-bold">شما کاربر جدید هستید. لطفاً اطلاعات زیر را تکمیل کنید:</p>
                        <input type="text" id="authName" class="form-control mb-2" placeholder="نام و نام خانوادگی">
                        <select id="authRole" class="form-select">
                            <option value="VOLUNTEER">کاربر معمولی / داوطلب</option>
                            <option value="OPERATOR">مامور ستاد بحران</option>
                        </select>
                    </div>

                    <button onclick="verifyOTP()" class="btn btn-success w-100 fw-bold" id="verifyBtn">تایید و ورود</button>
                </div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
    const iranData = {
        "تهران": ["تهران", "شهریار", "ری", "اسلامشهر"],
        "البرز": ["کرج", "فردیس", "هشتگرد"],
        "اصفهان": ["اصفهان", "کاشان", "خمینی‌شهر"],
        "خوزستان": ["اهواز", "دزفول", "آبادان"]
    };

    function initProvinces() {
        ['volProv', 'misProv'].forEach(id => {
            const el = document.getElementById(id);
            if(el) {
                el.innerHTML = '<option value="">انتخاب استان...</option>';
                Object.keys(iranData).forEach(p => el.options.add(new Option(p, p)));
            }
        });
    }

    function updateCities(pId, cId) {
        const p = document.getElementById(pId).value;
        const cSelect = document.getElementById(cId);
        cSelect.innerHTML = '<option value="">انتخاب شهر...</option>';
        if (p && iranData[p]) iranData[p].forEach(c => cSelect.options.add(new Option(c, c)));
    }

    function showAuthModal() { new bootstrap.Modal(document.getElementById('authModal')).show(); }

    // ۱. ارسال OTP و بررسی وجود کاربر در دیتابیس
    async function sendOTP() {
        const phone = document.getElementById('authPhone').value;
        const res = await fetch('/api/auth/send-otp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({phone_number: phone})
        });
        const data = await res.json();
        if(res.ok) {
            document.getElementById('step1').style.display = 'none';
            document.getElementById('step2').style.display = 'block';
            document.getElementById('simCode').innerText = data.simulated_code;

            if (data.is_registered) {
                // کاربر قبلا وجود دارد -> فیلدهای ثبت نام پنهان میشوند
                document.getElementById('regFields').style.display = 'none';
                document.getElementById('verifyBtn').innerText = 'ورود به حساب کاربری';
            } else {
                // کاربر جدید است -> فیلدهای ثبت نام فعال میشوند
                document.getElementById('regFields').style.display = 'block';
                document.getElementById('verifyBtn').innerText = 'تکمیل ثبت‌نام و ورود';
            }
        } else alert(data.detail || 'خطا در ارسال پیامک');
    }

    async function verifyOTP() {
        const payload = {
            phone_number: document.getElementById('authPhone').value,
            code: document.getElementById('authCode').value,
            full_name: document.getElementById('authName').value || null,
            role: document.getElementById('authRole').value || 'VOLUNTEER'
        };
        const res = await fetch('/api/auth/verify-otp', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(res.ok) {
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('role', data.role);
            localStorage.setItem('name', data.full_name);
            localStorage.setItem('approved', data.is_approved);
            location.reload();
        } else alert(data.detail);
    }

    function setupUI() {
        const role = localStorage.getItem('role');
        const approved = localStorage.getItem('approved') === 'true';

        document.getElementById('nav-inbox').style.display = 'none';
        document.getElementById('nav-create-mis').style.display = 'none';
        document.getElementById('nav-manage-mis').style.display = 'none';
        document.getElementById('nav-chief').style.display = 'none';
        document.getElementById('unapprovedAlert').style.display = 'none';

        if (role) {
            const roleTitle = role === 'ADMIN' ? 'رئیس کل' : (role === 'OPERATOR' ? 'مامور' : 'داوطلب');
            document.getElementById('authBox').innerHTML = `
                <span class="badge bg-primary fs-6 me-2">👤 ${localStorage.getItem('name')} (${roleTitle})</span>
                <button onclick="logout()" class="btn btn-outline-danger btn-sm fw-bold">خروج</button>
            `;

            document.getElementById('nav-inbox').style.display = 'block';

            if (role === 'OPERATOR') {
                if (approved) {
                    document.getElementById('nav-create-mis').style.display = 'block';
                    document.getElementById('nav-manage-mis').style.display = 'block';
                } else {
                    document.getElementById('unapprovedAlert').style.display = 'block';
                }
            } else if (role === 'ADMIN') {
                document.getElementById('nav-create-mis').style.display = 'block';
                document.getElementById('nav-manage-mis').style.display = 'block';
                document.getElementById('nav-chief').style.display = 'block';
            }
        }
    }

    function logout() { localStorage.clear(); location.reload(); }

    // ۲. بارگذاری و بروزرسانی زنده پنل رئیس کل
    async function loadChiefPanel() {
        const token = localStorage.getItem('token');
        const resPending = await fetch('/api/admin/pending-operators', { headers: {'Authorization': `Bearer ${token}`} });
        const pending = await resPending.json();

        let html = '';
        if (pending.length === 0) {
            html = '<div class="alert alert-success m-0">✅ هیچ مامور منتظری در صف تایید وجود ندارد.</div>';
        } else {
            pending.forEach(op => {
                html += `
                <div class="d-flex justify-content-between align-items-center mb-2 p-3 bg-white rounded border">
                    <div><b>${op.full_name}</b> (📱 ${op.phone_number})</div>
                    <div>
                        <button onclick="approveOp(${op.id}, 'approve')" class="btn btn-success btn-sm fw-bold">تایید مامور ✅</button>
                        <button onclick="approveOp(${op.id}, 'reject')" class="btn btn-danger btn-sm fw-bold ms-1">رد درخواست ❌</button>
                    </div>
                </div>`;
            });
        }
        document.getElementById('pendingOpsList').innerHTML = html;

        // دریافت کلیه داده‌های سیستم برای رئیس
        const resData = await fetch('/api/admin/all-data', { headers: {'Authorization': `Bearer ${token}`} });
        const allData = await resData.json();
        document.getElementById('allSystemData').innerHTML = `
            <p>👥 <b>تعداد کل کاربران:</b> ${allData.users.length}</p>
            <p>📋 <b>تعداد کل ماموریت‌ها:</b> ${allData.missions.length}</p>
        `;
    }

    // عملیات تایید مامور و رفرش آنی صفحه
    async function approveOp(id, action) {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/admin/approve-operator/${id}?action=${action}`, { method: 'POST', headers: {'Authorization': `Bearer ${token}`} });
        const data = await res.json();
        alert(data.message);
        loadChiefPanel(); // رفرش آنی پنل رئیس
    }

    window.onload = () => { initProvinces(); setupUI(); };
</script>
</body>
</html>
'''
}

for path, code in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(code.strip())
    print(f"✅ فایل به روز شد: {path}")

print("\n🎉 تمامی اصلاحات با موفقیت اعمال شدند!")