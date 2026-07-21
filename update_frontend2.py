import os

frontend_code = '''<!DOCTYPE html>
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
        .unread-msg { background-color: #eef5ff; border-right: 5px solid #0d6efd; }
    </style>
</head>
<body>

<div class="container py-4">
    <header class="pb-3 mb-4 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <h3 class="fw-bold text-primary">🚨 سامانه هوشمند فرماندهی و مدیریت بحران</h3>
            <p class="text-muted mb-0">سیستم جامع تطبیق هوشمند، مدیریت ماموریت‌ها و صندوق پیام‌ها</p>
        </div>
        <div id="authBox">
            <button class="btn btn-primary fw-bold" onclick="showAuthModal()">📲 ورود / ثبت‌نام با پیامک</button>
        </div>
    </header>

    <!-- هشدار عدم تایید مامور -->
    <div id="unapprovedAlert" class="alert alert-warning fw-bold text-center" style="display:none;">
        ⏳ حساب کاربری شما به عنوان "مامور" ثبت شده است اما هنوز توسط رئیس کل تایید نشده است.
    </div>

    <!-- منوهای اصلی -->
    <ul class="nav nav-pills mb-4" id="mainTabs">
        <li class="nav-item">
            <button class="nav-link active fw-bold" data-bs-toggle="pill" data-bs-target="#tab-vol">🙋‍♂️ اعلام داوطلبی</button>
        </li>
        <li class="nav-item" id="nav-inbox" style="display:none;">
            <button class="nav-link fw-bold position-relative" data-bs-toggle="pill" data-bs-target="#tab-msg" onclick="loadMessages()">
                📬 صندوق پیام‌ها
            </button>
        </li>
        <li class="nav-item" id="nav-create-mis" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-create-mis">📋 ایجاد ماموریت جدید</button>
        </li>
        <li class="nav-item" id="nav-manage-mis" style="display:none;">
            <button class="nav-link fw-bold" data-bs-toggle="pill" data-bs-target="#tab-manage-mis" onclick="loadMyMissions()">⚙️ مدیریت ماموریت‌های من</button>
        </li>
        <li class="nav-item" id="nav-chief" style="display:none;">
            <button class="nav-link fw-bold btn-danger text-white ms-2" data-bs-toggle="pill" data-bs-target="#tab-chief" onclick="loadChiefPanel()">👑 پنل اختصاصی رئیس کل</button>
        </li>
    </ul>

    <div class="tab-content">
        <!-- ۱. اعلام داوطلبی -->
        <div class="tab-pane fade show active" id="tab-vol">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ثبت/بروزرسانی مشخصات داوطلبی</h5>
                <p class="text-muted small">مشخصات و زمان آزادی خود را وارد کنید. هوش مصنوعی مهارت‌های شما را استخراج می‌کند.</p>
                <!-- فرم داوطلب -->
                <form id="volForm">
                    <div class="row g-3">
                        <div class="col-md-3"><select id="volProv" class="form-select" onchange="updateCities('volProv', 'volCity')" required><option value="">انتخاب استان...</option></select></div>
                        <div class="col-md-3"><select id="volCity" class="form-select" required><option value="">انتخاب شهر...</option></select></div>
                        <div class="col-md-3"><label class="form-label">از تاریخ</label><input type="datetime-local" id="volFrom" class="form-control" required></div>
                        <div class="col-md-3"><label class="form-label">تا تاریخ</label><input type="datetime-local" id="volTo" class="form-control" required></div>
                        <div class="col-12"><textarea id="volBio" class="form-control" rows="3" placeholder="توضیحات، امکانات (مثل خودرو) و توانمندی‌ها..."></textarea></div>
                        <div class="col-12"><button type="submit" class="btn btn-primary fw-bold">بروزرسانی وضعیت داوطلبی</button></div>
                    </div>
                </form>
            </div>
        </div>

        <!-- ۲. صندوق پیام‌ها -->
        <div class="tab-pane fade" id="tab-msg">
            <div class="card p-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold m-0">صندوق پیام‌ها</h5>
                    <select id="msgFilter" class="form-select w-auto" onchange="loadMessages()">
                        <option value="همه">همه دسته‌ها</option>
                        <option value="ماموریت">ماموریت</option>
                        <option value="سیستمی">سیستمی</option>
                    </select>
                </div>
                <div id="messagesList">در حال دریافت پیام‌ها...</div>
            </div>
        </div>

        <!-- ۳. ایجاد ماموریت -->
        <div class="tab-pane fade" id="tab-create-mis">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">تعریف ماموریت عملیاتی</h5>
                <form id="misForm">
                    <div class="row g-3">
                        <div class="col-md-6"><input type="text" id="misTitle" class="form-control" placeholder="عنوان ماموریت" required></div>
                        <div class="col-md-3"><select id="misProv" class="form-select" onchange="updateCities('misProv', 'misCity')" required><option value="">استان...</option></select></div>
                        <div class="col-md-3"><select id="misCity" class="form-select" required><option value="">شهر...</option></select></div>
                        <div class="col-md-6"><input type="text" id="misEssential" class="form-control" placeholder="مهارت‌های ضروری (با کاما)" required></div>
                        <div class="col-md-6"><input type="text" id="misBonus" class="form-control" placeholder="مهارت‌های امتیازی (با کاما)"></div>
                        <div class="col-md-6"><input type="datetime-local" id="misStart" class="form-control" required></div>
                        <div class="col-md-6"><input type="datetime-local" id="misEnd" class="form-control" required></div>
                        <div class="col-12"><button type="submit" class="btn btn-success fw-bold">ایجاد ماموریت</button></div>
                    </div>
                </form>
            </div>
        </div>

        <!-- ۴. مدیریت ماموریت‌های من -->
        <div class="tab-pane fade" id="tab-manage-mis">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ماموریت‌های تعریف‌شده توسط شما</h5>
                <div id="myMissionsList">در حال بارگذاری...</div>
            </div>
        </div>

        <!-- ۵. پنل اختصاصی رئیس کل -->
        <div class="tab-pane fade" id="tab-chief">
            <div class="card p-4 mb-4">
                <h5 class="fw-bold text-danger mb-3">👨‍✈️ تایید ماموران جدید ثبت‌نام‌شده</h5>
                <div id="pendingOpsList">در حال بررسی...</div>
            </div>
            <div class="card p-4">
                <h5 class="fw-bold mb-3">📊 دسترسی کلی به داده‌های سیستم</h5>
                <div id="allSystemData">در حال بارگذاری...</div>
            </div>
        </div>
    </div>
</div>

<!-- مودال تطبیق و ارسال پیام -->
<div class="modal fade" id="matchModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header"><h5 class="modal-title fw-bold">تطبیق ۳ لایه‌ای و ارسال درخواست کمک</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body" id="matchModalBody">در حال آنالیز معنایی...</div>
        </div>
    </div>
</div>

<!-- مودال احراز هویت پیامکی -->
<div class="modal fade" id="authModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header"><h5 class="modal-title fw-bold">ورود / ثبت‌نام با کد پیامکی</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
            <div class="modal-body">
                <div id="step1">
                    <input type="tel" id="authPhone" class="form-control mb-3" placeholder="09123456789">
                    <button onclick="sendOTP()" class="btn btn-primary w-100 fw-bold">ارسال کد پیامکی</button>
                </div>
                <div id="step2" style="display:none;">
                    <div class="alert alert-info">📱 کد تایید: <b id="simCode"></b></div>
                    <input type="text" id="authCode" class="form-control mb-2" placeholder="کد ۴ رقمی">
                    <div id="regFields" style="display:none;" class="border-top pt-2">
                        <input type="text" id="authName" class="form-control mb-2" placeholder="نام و نام خانوادگی">
                        <select id="authRole" class="form-select mb-2">
                            <option value="VOLUNTEER">کاربر معمولی / داوطلب</option>
                            <option value="OPERATOR">مامور ستاد بحران</option>
                        </select>
                    </div>
                    <button onclick="verifyOTP()" class="btn btn-success w-100 fw-bold mt-2">تایید و ورود</button>
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
            if(el) Object.keys(iranData).forEach(p => el.options.add(new Option(p, p)));
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
            document.getElementById('regFields').style.display = 'block';
        }
    }

    async function verifyOTP() {
        const payload = {
            phone_number: document.getElementById('authPhone').value,
            code: document.getElementById('authCode').value,
            full_name: document.getElementById('authName').value || 'کاربر',
            role: document.getElementById('authRole').value
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

        if (role) {
            document.getElementById('authBox').innerHTML = `<span class="badge bg-success fs-6">👤 ${localStorage.getItem('name')} (${role})</span> <button onclick="logout()" class="btn btn-outline-danger btn-sm ms-2">خروج</button>`;
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

    // بارگذاری پیام‌ها
    async function loadMessages() {
        const token = localStorage.getItem('token');
        const cat = document.getElementById('msgFilter').value;
        const res = await fetch(`/api/messages/?category=${cat}`, { headers: {'Authorization': `Bearer ${token}`} });
        const msgs = await res.json();

        let html = '';
        if (msgs.length === 0) html = '<div class="text-muted">هیچ پیامی در این دسته وجود ندارد.</div>';
        msgs.forEach(m => {
            html += `
            <div class="card p-3 mb-2 ${!m.is_read ? 'unread-msg' : ''}">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="fw-bold mb-1">${m.title} <span class="badge bg-secondary">${m.category}</span></h6>
                    <small class="text-muted">${m.is_read ? 'خوانده شده' : '🆕 جدید'}</small>
                </div>
                <p class="mb-2">${m.body}</p>
                ${m.invite_status === 'PENDING' ? `
                    <div>
                        <button onclick="respondMsg(${m.id}, 'accept')" class="btn btn-success btn-sm fw-bold">قبول درخواست کمک ✅</button>
                        <button onclick="respondMsg(${m.id}, 'reject')" class="btn btn-danger btn-sm fw-bold ms-1">رد درخواست ❌</button>
                    </div>` : `<span class="badge bg-info">وضعیت: ${m.invite_status}</span>`}
            </div>`;
        });
        document.getElementById('messagesList').innerHTML = html;
    }

    async function respondMsg(id, action) {
        const token = localStorage.getItem('token');
        await fetch(`/api/messages/${id}/respond?action=${action}`, { method: 'POST', headers: {'Authorization': `Bearer ${token}`} });
        loadMessages();
    }

    // بارگذاری ماموریت‌های من
    async function loadMyMissions() {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/missions/my-missions', { headers: {'Authorization': `Bearer ${token}`} });
        const list = await res.json();

        let html = '';
        list.forEach(m => {
            let teamHtml = m.team.map(t => `<span class="badge bg-success me-1">👤 ${t.full_name} (${t.phone})</span>`).join('');
            html += `
            <div class="card p-3 mb-3 border-start border-4 border-primary">
                <div class="d-flex justify-content-between">
                    <div>
                        <h5 class="fw-bold mb-1">${m.title} (${m.city})</h5>
                        <small>وضعیت: <b>${m.status}</b></small>
                        <div class="mt-2"><b>تیم انجام‌دهنده:</b> ${teamHtml || 'هنوز کسی اضافه نشده است'}</div>
                    </div>
                    <div>
                        ${m.status === 'OPEN' ? `
                            <button onclick="openMatchModal(${m.id})" class="btn btn-warning btn-sm fw-bold">🎯 تطبیق و دعوت داوطلب</button>
                            <button onclick="completeMissionPrompt(${m.id}, '${encodeURIComponent(JSON.stringify(m.team))}')" class="btn btn-danger btn-sm fw-bold ms-1">🏁 خاتمه ماموریت و نمره‌دهی</button>
                        ` : '<span class="badge bg-secondary fs-6">خاتمه یافته</span>'}
                    </div>
                </div>
            </div>`;
        });
        document.getElementById('myMissionsList').innerHTML = html || 'هیچ ماموریتی ثبت نکرده‌اید.';
    }

    async function openMatchModal(mId) {
        const token = localStorage.getItem('token');
        const modal = new bootstrap.Modal(document.getElementById('matchModal'));
        modal.show();

        const res = await fetch(`/api/missions/${mId}/match`, { headers: {'Authorization': `Bearer ${token}`} });
        const data = await res.json();

        let html = `<h6>داوطلبان پیشنهادی AI برای ${data.mission_title}:</h6>`;
        data.recommended_volunteers.forEach(v => {
            html += `
            <div class="card p-2 mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div><b>${v.volunteer_name}</b> (${v.city}) - نمره تطبیق کل: <b>${v.score_breakdown.total_score}</b></div>
                    <button onclick="sendHelpInvite(${mId}, ${v.volunteer_id})" class="btn btn-primary btn-sm">ارسال پیام درخواست کمک 📩</button>
                </div>
            </div>`;
        });
        document.getElementById('matchModalBody').innerHTML = html;
    }

    async function sendHelpInvite(mId, vId) {
        const token = localStorage.getItem('token');
        await fetch('/api/missions/send-invite', {
            method: 'POST',
            headers: {'Content-Type': 'application/json', 'Authorization': `Bearer ${token}`},
            body: JSON.stringify({mission_id: mId, volunteer_id: vId})
        });
        alert('پیام درخواست کمک به صندوق ورودی داوطلب فرستاده شد.');
    }

    // پنل رئیس کل
    async function loadChiefPanel() {
        const token = localStorage.getItem('token');
        const resPending = await fetch('/api/admin/pending-operators', { headers: {'Authorization': `Bearer ${token}`} });
        const pending = await resPending.json();

        let html = '';
        pending.forEach(op => {
            html += `
            <div class="d-flex justify-content-between align-items-center mb-2 p-2 border rounded">
                <div><b>${op.full_name}</b> (📱 ${op.phone_number})</div>
                <div>
                    <button onclick="approveOp(${op.id}, 'approve')" class="btn btn-success btn-sm">تایید مامور ✅</button>
                    <button onclick="approveOp(${op.id}, 'reject')" class="btn btn-danger btn-sm">رد ❌</button>
                </div>
            </div>`;
        });
        document.getElementById('pendingOpsList').innerHTML = html || 'هیچ مامور منتظری وجود ندارد.';
    }

    async function approveOp(id, action) {
        const token = localStorage.getItem('token');
        await fetch(`/api/admin/approve-operator/${id}?action=${action}`, { method: 'POST', headers: {'Authorization': `Bearer ${token}`} });
        loadChiefPanel();
    }

    window.onload = () => { initProvinces(); setupUI(); };
</script>
</body>
</html>
'''


def update_frontend():
    with open("static/index.html", "w", encoding="utf-8") as f:
        f.write(frontend_code.strip())
    print("✅ فایل static/index.html کاملاً بروزرسانی شد!")


if __name__ == "__main__":
    update_frontend()