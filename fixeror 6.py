import os

files = {
    # 1. روتر ادمین (مدیریت کامل ماموران با قابلیت تایید مجدد ردشدگان و دریافت تمام داده‌ها)
    "app/routers/admin.py": '''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, VolunteerProfile
from app.models.mission import Mission
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["Admin Panel"])

@router.get("/pending-operators")
def get_pending_operators(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

    operators = db.query(User).filter(User.role == "OPERATOR").all()
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
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

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
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="دسترسی غیرمجاز")

    users = db.query(User).all()
    volunteers = db.query(VolunteerProfile).join(User).all()
    missions = db.query(Mission).all()

    return {
        "users": [{"id": u.id, "name": u.full_name, "phone": u.phone_number, "role": u.role, "approved": u.is_approved} for u in users],
        "volunteers": [{"id": v.id, "name": v.user.full_name, "province": v.province, "city": v.city, "skills": v.skills, "bio": v.bio} for v in volunteers],
        "missions": [{"id": m.id, "title": m.title, "province": m.province, "city": m.city, "status": m.status} for m in missions]
    }
''',

    # 2. روتر پیام‌ها (مدیریت خوانده شدن پیام‌ها، نشانگر و ارسال همگانی)
    "app/routers/messages.py": '''from fastapi import APIRouter, Depends, HTTPException
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
''',

    # 3. رابط کاربری کامل (static/index.html)
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
        .badge-dot { height: 10px; width: 10px; background-color: #dc3545; border-radius: 50%; display: inline-block; position: absolute; top: 5px; right: 5px; }
    </style>
</head>
<body>

<div class="container py-4">
    <header class="pb-3 mb-4 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <h3 class="fw-bold text-primary">🚨 سامانه هوشمند فرماندهی و مدیریت بحران</h3>
            <p class="text-muted mb-0">سیستم جامع مدیریت ماموریت‌ها، نیروها و مرکز فرماندهی</p>
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
            <button class="nav-link fw-bold position-relative" data-bs-toggle="pill" data-bs-target="#tab-msg" onclick="loadMessages()">
                📬 صندوق پیام‌ها <span id="unreadDot" style="display:none;" class="badge-dot"></span>
            </button>
        </li>
        <li class="nav-item" id="nav-create-mis" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-create-mis">📋 ایجاد ماموریت جدید</button>
        </li>
        <li class="nav-item" id="nav-manage-mis" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-manage-mis" onclick="loadMyMissions()">⚙️ مدیریت ماموریت‌ها</button>
        </li>
        <li class="nav-item" id="nav-chief" style="display:none;">
            <button class="nav-link fw-bold btn-danger text-white ms-2" data-bs-toggle="pill" data-bs-target="#tab-chief" onclick="loadChiefPanel()">👑 پنل جامع رئیس کل</button>
        </li>
    </ul>

    <div class="tab-content">
        <!-- ۱. اعلام داوطلبی -->
        <div class="tab-pane fade show active" id="tab-vol">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ثبت مشخصات داوطلبی و توانمندی‌ها</h5>
                <form id="volForm" onsubmit="saveVolunteerProfile(event)">
                    <div class="row g-3">
                        <div class="col-md-3"><select id="volProv" class="form-select" onchange="updateCities('volProv', 'volCity')" required><option value="">انتخاب استان...</option></select></div>
                        <div class="col-md-3"><select id="volCity" class="form-select" required><option value="">انتخاب شهر...</option></select></div>
                        <div class="col-md-3"><label class="form-label">از تاریخ</label><input type="datetime-local" id="volFrom" class="form-control" required></div>
                        <div class="col-md-3"><label class="form-label">تا تاریخ</label><input type="datetime-local" id="volTo" class="form-control" required></div>
                        <div class="col-12"><textarea id="volBio" class="form-control" rows="3" placeholder="توضیحات، مهارت‌ها و تجهیزات..."></textarea></div>
                        <div class="col-12"><button type="submit" class="btn btn-primary fw-bold">ثبت وضعیت داوطلبی</button></div>
                    </div>
                </form>
            </div>
        </div>

        <!-- ۲. صندوق پیام‌ها -->
        <div class="tab-pane fade" id="tab-msg">
            <div class="card p-4"><div id="messagesList">در حال بارگذاری پیام‌ها...</div></div>
        </div>

        <!-- ۳. ایجاد ماموریت -->
        <div class="tab-pane fade" id="tab-create-mis">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">تعریف ماموریت عملیاتی</h5>
                <form id="misForm" onsubmit="createMission(event)">
                    <div class="row g-3">
                        <div class="col-md-6"><input type="text" id="misTitle" class="form-control" placeholder="عنوان ماموریت" required></div>
                        <div class="col-md-3"><select id="misProv" class="form-select" onchange="updateCities('misProv', 'misCity')" required><option value="">استان...</option></select></div>
                        <div class="col-md-3"><select id="misCity" class="form-select" required><option value="">شهر...</option></select></div>
                        <div class="col-md-6"><input type="text" id="misEssential" class="form-control" placeholder="مهارت‌های ضروری (با کاما)" required></div>
                        <div class="col-md-6"><input type="text" id="misBonus" class="form-control" placeholder="مهارت‌های امتیازی (با کاما)"></div>
                        <div class="col-md-6"><label class="form-label">زمان شروع</label><input type="datetime-local" id="misStart" class="form-control" required></div>
                        <div class="col-md-6"><label class="form-label">زمان پایان</label><input type="datetime-local" id="misEnd" class="form-control" required></div>
                        <div class="col-12"><button type="submit" class="btn btn-success fw-bold">ثبت و ایجاد ماموریت</button></div>
                    </div>
                </form>
            </div>
        </div>

        <!-- ۴. مدیریت ماموریت‌ها -->
        <div class="tab-pane fade" id="tab-manage-mis">
            <div class="card p-4"><div id="myMissionsList">در حال دریافت ماموریت‌ها...</div></div>
        </div>

        <!-- ۵. پنل جامع رئیس کل -->
        <div class="tab-pane fade" id="tab-chief">
            <div class="card p-4 mb-4 border-primary">
                <h5 class="fw-bold text-primary mb-3">📢 ارسال پیام همگانی برای تمامی کاربران</h5>
                <form onsubmit="sendBroadcast(event)">
                    <input type="text" id="bcTitle" class="form-control mb-2" placeholder="عنوان پیام همگانی" required>
                    <textarea id="bcBody" class="form-control mb-2" rows="2" placeholder="متن پیام..." required></textarea>
                    <button type="submit" class="btn btn-primary fw-bold btn-sm">ارسال همگانی 🚀</button>
                </form>
            </div>

            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-danger mb-3">👨‍✈️ مدیریت حساب ماموران ستاد بحران</h5>
                <div id="operatorsList">در حال بارگذاری ماموران...</div>
            </div>

            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-success mb-3">🙋‍♂️ لیست تمام درخواست‌های داوطلبی ثبت‌شده</h5>
                <div id="allVolunteersList">در حال بارگذاری داوطلبان...</div>
            </div>

            <div class="card p-4">
                <h5 class="fw-bold text-secondary mb-3">📋 لیست تمام ماموریت‌های ثبت‌شده در سیستم</h5>
                <div id="allMissionsList">در حال بارگذاری ماموریت‌ها...</div>
            </div>
        </div>
    </div>
</div>

<!-- مودال تطبیق هوشمند -->
<div class="modal fade" id="matchModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title fw-bold">🎯 تطبیق هوشمند و رتبه‌بندی داوطلبان</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <h6 id="matchMissionTitle" class="fw-bold text-secondary mb-3"></h6>
                <div id="matchResultsList">در حال محاسبه...</div>
            </div>
        </div>
    </div>
</div>

<!-- مودال احراز هویت -->
<div class="modal fade" id="authModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header"><h5 class="modal-title fw-bold">ورود / ثبت‌نام با پیامک</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body">
                <div id="step1">
                    <input type="tel" id="authPhone" class="form-control mb-3" placeholder="09123456789">
                    <button onclick="sendOTP()" class="btn btn-primary w-100 fw-bold">دریافت کد تایید</button>
                </div>
                <div id="step2" style="display:none;">
                    <div class="alert alert-info">📱 کد تایید پیامک‌شده: <b id="simCode"></b></div>
                    <input type="text" id="authCode" class="form-control mb-3" placeholder="کد ۴ رقمی">
                    <div id="regFields" style="display:none;" class="border-top pt-3 mb-3">
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
            document.getElementById('regFields').style.display = data.is_registered ? 'none' : 'block';
            document.getElementById('verifyBtn').innerText = data.is_registered ? 'ورود به حساب کاربری' : 'تکمیل ثبت‌نام و ورود';
        } else alert(data.detail);
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
            checkUnreadMessages();

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

    async function checkUnreadMessages() {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/messages/my-messages', { headers: {'Authorization': `Bearer ${token}`} });
        const msgs = await res.json();
        const hasUnread = msgs.some(m => !m.is_read);
        document.getElementById('unreadDot').style.display = hasUnread ? 'inline-block' : 'none';
    }

    async function loadMessages() {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/messages/my-messages', { headers: {'Authorization': `Bearer ${token}`} });
        const msgs = await res.json();

        let html = '';
        if (!msgs || msgs.length === 0) {
            html = '<div class="alert alert-info m-0">صندوق پیام‌های شما خالی است.</div>';
        } else {
            msgs.forEach(m => {
                const borderClass = m.is_read ? 'border-secondary' : 'border-primary bg-light';
                html += `
                <div class="card p-3 mb-2 border-start border-4 ${borderClass}" onclick="markAsRead(${m.id})" style="cursor: pointer;">
                    <div class="d-flex justify-content-between">
                        <h6 class="fw-bold m-0">${m.title} ${!m.is_read ? '<span class="badge bg-danger ms-1">جدید 🆕</span>' : ''}</h6>
                        <small class="text-muted">${m.created_at}</small>
                    </div>
                    <p class="m-0 mt-2 text-secondary">${m.body}</p>
                </div>`;
            });
        }
        document.getElementById('messagesList').innerHTML = html;
        checkUnreadMessages();
    }

    async function markAsRead(msgId) {
        const token = localStorage.getItem('token');
        await fetch(`/api/messages/${msgId}/read`, {
            method: 'POST',
            headers: {'Authorization': `Bearer ${token}`}
        });
        loadMessages();
    }

    async function loadMyMissions() {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/missions/my-missions', { headers: {'Authorization': `Bearer ${token}`} });
        const missions = await res.json();

        let html = '';
        if (!missions || missions.length === 0) {
            html = '<div class="alert alert-info m-0">هیچ ماموریتی ثبت نشده است.</div>';
        } else {
            missions.forEach(m => {
                const skillsBadge = (m.essential_skills || []).map(s => `<span class="badge bg-secondary me-1">${s}</span>`).join('');
                html += `
                <div class="card p-3 mb-3 border">
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="fw-bold text-primary m-0">${m.title}</h5>
                        <div>
                            <button onclick="openMatchModal(${m.id}, '${m.title}')" class="btn btn-outline-primary btn-sm fw-bold">🎯 تطبیق و دعوت نیرو</button>
                            <span class="badge bg-success ms-2">${m.status}</span>
                        </div>
                    </div>
                    <div class="mt-2 text-muted small">📍 موقعیت: ${m.province} - ${m.city} | 🗓️ ثبت: ${m.created_at}</div>
                    <div class="mt-2">مهارت‌های ضروری: ${skillsBadge}</div>
                </div>`;
            });
        }
        document.getElementById('myMissionsList').innerHTML = html;
    }

    async function openMatchModal(missionId, missionTitle) {
        document.getElementById('matchMissionTitle').innerText = `ماموریت: ${missionTitle}`;
        document.getElementById('matchResultsList').innerHTML = '<div class="text-center p-3">در حال تحلیل هوش مصنوعی...</div>';
        new bootstrap.Modal(document.getElementById('matchModal')).show();

        const token = localStorage.getItem('token');
        const res = await fetch(`/api/missions/${missionId}/match`, { headers: {'Authorization': `Bearer ${token}`} });
        const data = await res.json();

        let html = '';
        if (!data.recommended_volunteers || data.recommended_volunteers.length === 0) {
            html = '<div class="alert alert-warning m-0">هیچ داوطلبی یافت نشد.</div>';
        } else {
            data.recommended_volunteers.forEach(v => {
                const vSkills = (v.skills || []).map(s => `<span class="badge bg-info text-dark me-1">${s}</span>`).join('');
                html += `
                <div class="card p-3 mb-2 border bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="fw-bold m-0">${v.volunteer_name} <span class="badge bg-success ms-2">امتیاز: ${v.score_breakdown.total_score}</span></h6>
                            <small class="text-muted">📍 ${v.province} - ${v.city} | امتیاز کیفی: ${v.rating}</small>
                        </div>
                        <button onclick="inviteVolunteer(${missionId}, ${v.volunteer_id}, '${v.volunteer_name}')" class="btn btn-success btn-sm fw-bold">ارسال پیام دعوت 📩</button>
                    </div>
                    <div class="mt-2 small">مهارت‌ها: ${vSkills}</div>
                </div>`;
            });
        }
        document.getElementById('matchResultsList').innerHTML = html;
    }

    async function inviteVolunteer(missionId, volunteerId, volunteerName) {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/missions/${missionId}/invite`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify({volunteer_id: volunteerId})
        });
        const data = await res.json();
        if(res.ok) alert(`دعوت‌نامه برای ${volunteerName} ارسال شد!`);
        else alert(data.detail);
    }

    async function loadChiefPanel() {
        const token = localStorage.getItem('token');

        const resOps = await fetch('/api/admin/pending-operators', { headers: {'Authorization': `Bearer ${token}`} });
        const operators = await resOps.json();

        let opsHtml = '';
        if (operators.length === 0) {
            opsHtml = '<div class="alert alert-success m-0">هیچ ماموری ثبت‌نام نکرده است.</div>';
        } else {
            operators.forEach(op => {
                const statusBadge = op.is_approved ? '<span class="badge bg-success">تایید شده ✅</span>' : '<span class="badge bg-danger">رد شده / در انتظار ❌</span>';
                opsHtml += `
                <div class="d-flex justify-content-between align-items-center mb-2 p-3 bg-white rounded border">
                    <div><b>${op.full_name}</b> (📱 ${op.phone_number}) - ${statusBadge}</div>
                    <div>
                        <button onclick="approveOp(${op.id}, 'approve')" class="btn btn-success btn-sm fw-bold">تایید ✅</button>
                        <button onclick="approveOp(${op.id}, 'reject')" class="btn btn-danger btn-sm fw-bold ms-1">رد ❌</button>
                    </div>
                </div>`;
            });
        }
        document.getElementById('operatorsList').innerHTML = opsHtml;

        const resData = await fetch('/api/admin/all-data', { headers: {'Authorization': `Bearer ${token}`} });
        const allData = await resData.json();

        let volsHtml = '';
        if (allData.volunteers.length === 0) {
            volsHtml = '<div class="alert alert-info m-0">هیچ داوطلبی ثبت‌نام نکرده است.</div>';
        } else {
            allData.volunteers.forEach(v => {
                const sBadge = (v.skills || []).map(s => `<span class="badge bg-secondary me-1">${s}</span>`).join('');
                volsHtml += `
                <div class="card p-3 mb-2 border bg-white">
                    <h6 class="fw-bold text-success m-0">👤 ${v.name} - 📍 ${v.province}، ${v.city}</h6>
                    <p class="m-0 mt-1 small text-muted">توضیحات: ${v.bio || 'بدون توضیحات'}</p>
                    <div class="mt-1">مهارت‌ها: ${sBadge}</div>
                </div>`;
            });
        }
        document.getElementById('allVolunteersList').innerHTML = volsHtml;

        let missHtml = '';
        if (allData.missions.length === 0) {
            missHtml = '<div class="alert alert-info m-0">هیچ ماموریتی ثبت نشده است.</div>';
        } else {
            allData.missions.forEach(m => {
                missHtml += `
                <div class="card p-3 mb-2 border bg-white d-flex flex-row justify-content-between align-items-center">
                    <div>
                        <h6 class="fw-bold text-primary m-0">${m.title}</h6>
                        <small class="text-muted">📍 موقعیت: ${m.province} - ${m.city}</small>
                    </div>
                    <span class="badge bg-success">${m.status}</span>
                </div>`;
            });
        }
        document.getElementById('allMissionsList').innerHTML = missHtml;
    }

    async function approveOp(id, action) {
        const token = localStorage.getItem('token');
        const res = await fetch(`/api/admin/approve-operator/${id}?action=${action}`, { method: 'POST', headers: {'Authorization': `Bearer ${token}`} });
        const data = await res.json();
        alert(data.message);
        loadChiefPanel();
    }

    async function createMission(e) {
        e.preventDefault();
        const token = localStorage.getItem('token');
        const payload = {
            title: document.getElementById('misTitle').value,
            province: document.getElementById('misProv').value,
            city: document.getElementById('misCity').value,
            essential_skills: document.getElementById('misEssential').value.split(',').map(s => s.trim()).filter(s => s),
            bonus_skills: document.getElementById('misBonus').value ? document.getElementById('misBonus').value.split(',').map(s => s.trim()).filter(s => s) : [],
            start_date: document.getElementById('misStart').value,
            end_date: document.getElementById('misEnd').value
        };

        const res = await fetch('/api/missions/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(res.ok) {
            alert('ماموریت با موفقیت ثبت شد!');
            document.getElementById('misForm').reset();
            loadMyMissions();
        } else alert(data.detail);
    }

    async function saveVolunteerProfile(e) {
        e.preventDefault();
        const token = localStorage.getItem('token');
        if(!token) { alert('لطفا ابتدا وارد شوید.'); return; }

        const payload = {
            full_name: localStorage.getItem('name'),
            phone_number: "09000000000",
            province: document.getElementById('volProv').value,
            city: document.getElementById('volCity').value,
            bio: document.getElementById('volBio').value,
            available_from: document.getElementById('volFrom').value,
            available_to: document.getElementById('volTo').value
        };

        const res = await fetch('/api/volunteers/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(res.ok) alert('اطلاعات داوطلبی و استخراج هوشمند مهارت‌ها ثبت شد!');
        else alert(data.detail);
    }

    async function sendBroadcast(e) {
        e.preventDefault();
        const token = localStorage.getItem('token');
        const payload = {
            title: document.getElementById('bcTitle').value,
            body: document.getElementById('bcBody').value
        };

        const res = await fetch('/api/messages/broadcast', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if(res.ok) {
            alert(data.message);
            document.getElementById('bcTitle').value = '';
            document.getElementById('bcBody').value = '';
        } else alert(data.detail);
    }

    window.onload = () => { initProvinces(); setupUI(); };
</script>
</body>
</html>
'''
}

for path, code in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code.strip())
    print(f"✅ فایل با موفقیت اصلاح و ذخیره شد: {path}")

print("\n🎉 تمامی تغییرات با موفقیت روی پروژه اعمال شدند! اکنون سرور را اجرا کنید.")