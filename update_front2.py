import os

frontend_html = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سامانه مدیریت داوطلبان بحران (نسخه ۲)</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css">
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" />
    <style>
        body { font-family: 'Vazirmatn', sans-serif; background-color: #f8f9fa; }
        .card { border-radius: 12px; border: none; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    </style>
</head>
<body>

<div class="container py-4">
    <header class="pb-3 mb-4 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <h3 class="fw-bold text-primary">🚨 سامانه هوشمند مدیریت داوطلبان بحران</h3>
            <p class="text-muted mb-0">نسخه ۲.۰ (با احراز هویت JWT، لیست کشویی استان‌ها و AI)</p>
        </div>
        <div id="userInfo">
            <button class="btn btn-outline-primary btn-sm" data-bs-toggle="modal" data-bs-target="#loginModal">ورود به سیستم</button>
        </div>
    </header>

    <ul class="nav nav-pills mb-4" id="pills-tab">
        <li class="nav-item">
            <button class="nav-link active fw-bold" id="tab-reg" data-bs-toggle="pill" data-bs-target="#pills-reg">🙋‍♂️ ثبت‌نام داوطلب</button>
        </li>
        <li class="nav-item">
            <button class="nav-link fw-bold" id="tab-mis" data-bs-toggle="pill" data-bs-target="#pills-mis">📋 تعریف ماموریت</button>
        </li>
        <li class="nav-item">
            <button class="nav-link fw-bold" id="tab-match" data-bs-toggle="pill" data-bs-target="#pills-match" onclick="loadMissions()">🎯 تطبیق هوشمند</button>
        </li>
    </ul>

    <div class="tab-content">
        <!-- ۱. ثبت نام داوطلب -->
        <div class="tab-pane fade show active" id="pills-reg">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ثبت اطلاعات داوطلب جدید</h5>
                <form id="regForm">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">نام و نام خانوادگی *</label>
                            <input type="text" id="regName" class="form-control" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">شماره همراه (مثال: 09123456789) *</label>
                            <input type="tel" id="regPhone" class="form-control" pattern="09[0-9]{9}" required placeholder="09123456789">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">رمز عبور *</label>
                            <input type="password" id="regPass" class="form-control" minlength="6" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">استان *</label>
                            <select id="regProvince" class="form-select" onchange="updateCities('regProvince', 'regCity')" required>
                                <option value="">انتخاب استان...</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">شهر *</label>
                            <select id="regCity" class="form-select" required>
                                <option value="">ابتدا استان را انتخاب کنید</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">شروع زمان آزادی *</label>
                            <input type="datetime-local" id="regFrom" class="form-control" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">پایان زمان آزادی *</label>
                            <input type="datetime-local" id="regTo" class="form-control" required>
                        </div>
                        <div class="col-12">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" id="regDeploy">
                                <label class="form-check-label fw-bold" for="regDeploy">آمادگی اعزام به سایر استان‌ها/شهرها را دارم</label>
                            </div>
                        </div>
                        <div class="col-12">
                            <label class="form-label">بیوگرافی، مهارت‌ها و تجهیزات (AI هوشمند استخراج می‌کند) *</label>
                            <textarea id="regBio" class="form-control" rows="3" required placeholder="مثلا: من امدادگر هلال احمر هستم، خودروی وانت دارم و به زبان عربی مسلطم."></textarea>
                        </div>
                        <div class="col-12">
                            <button type="submit" class="btn btn-primary px-4 fw-bold">ثبت‌نام و استخراج مهارت‌ها</button>
                        </div>
                    </div>
                </form>
                <div id="regResult" class="mt-3"></div>
            </div>
        </div>

        <!-- ۲. تعریف ماموریت -->
        <div class="tab-pane fade" id="pills-mis">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ایجاد ماموریت جدید</h5>
                <form id="misForm">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">عنوان ماموریت</label>
                            <input type="text" id="misTitle" class="form-control" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">استان محل ماموریت</label>
                            <select id="misProvince" class="form-select" onchange="updateCities('misProvince', 'misCity')" required>
                                <option value="">انتخاب استان...</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">شهر محل ماموریت</label>
                            <select id="misCity" class="form-select" required>
                                <option value="">ابتدا استان را انتخاب کنید</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">مهارت‌های ضروری (با کاما جدا کنید)</label>
                            <input type="text" id="misEssential" class="form-control" placeholder="خودروی باری, امدادگری" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">مهارت‌های امتیازی (اختیاری)</label>
                            <input type="text" id="misBonus" class="form-control" placeholder="زبان عربی">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">زمان شروع</label>
                            <input type="datetime-local" id="misStart" class="form-control" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">زمان پایان</label>
                            <input type="datetime-local" id="misEnd" class="form-control" required>
                        </div>
                        <div class="col-12">
                            <button type="submit" class="btn btn-success px-4 fw-bold">ثبت ماموریت</button>
                        </div>
                    </div>
                </form>
                <div id="misResult" class="mt-3"></div>
            </div>
        </div>

        <!-- ۳. تطبیق هوشمند -->
        <div class="tab-pane fade" id="pills-match">
            <div class="card p-4 mb-4">
                <div class="row g-3">
                    <div class="col-md-8">
                        <select id="misSelect" class="form-select">
                            <option value="">در حال دریافت ماموریت‌ها...</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <button onclick="runMatching()" class="btn btn-warning w-100 fw-bold">اجرای تطبیق ۳ لایه‌ای 🚀</button>
                    </div>
                </div>
            </div>
            <div id="matchResults"></div>
        </div>
    </div>
</div>

<!-- مودال ورود -->
<div class="modal fade" id="loginModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title fw-bold">ورود به سیستم</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="loginForm">
                    <div class="mb-3">
                        <label class="form-label">شماره همراه</label>
                        <input type="tel" id="loginPhone" class="form-control" required placeholder="09123456789">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">رمز عبور</label>
                        <input type="password" id="loginPass" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100 fw-bold">ورود</button>
                </form>
                <div id="loginResult" class="mt-3"></div>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
    // اطلاعات استان‌ها و شهرهای اصلی ایران
    const iranData = {
        "تهران": ["تهران", "شهریار", "ری", "اسلامشهر", "دماوند", "پردیس"],
        "البرز": ["کرج", "فردیس", "هشتگرد", "نظرآباد", "طالقان"],
        "اصفهان": ["اصفهان", "کاشان", "خمینی‌شهر", "نجف‌آباد", "شاهین‌شهر"],
        "فارس": ["شیراز", "مرودشت", "کازرون", "جهرم", "فسا"],
        "خوزستان": ["اهواز", "دزفول", "آبادان", "خرمشهر", "ماهشهر"],
        "خراسان رضوی": ["مشهد", "نیشابور", "سبزوار", "تربت حیدریه"],
        "کرمانشاه": ["کرمانشاه", "اسلام‌آباد غرب", "سرپل ذهاب", "پاوه"],
        "آذربایجان شرقی": ["تبریز", "مراغه", "مرند", "میانه"]
    };

    function initProvinces() {
        const provinces = Object.keys(iranData);
        ['regProvince', 'misProvince'].forEach(id => {
            const el = document.getElementById(id);
            provinces.forEach(p => el.options.add(new Option(p, p)));
        });
    }

    function updateCities(provId, cityId) {
        const prov = document.getElementById(provId).value;
        const citySelect = document.getElementById(cityId);
        citySelect.innerHTML = '<option value="">انتخاب شهر...</option>';
        if (prov && iranData[prov]) {
            iranData[prov].forEach(c => citySelect.options.add(new Option(c, c)));
        }
    }

    // ثبت‌نام
    document.getElementById('regForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            full_name: document.getElementById('regName').value,
            phone_number: document.getElementById('regPhone').value,
            password: document.getElementById('regPass').value,
            province: document.getElementById('regProvince').value,
            city: document.getElementById('regCity').value,
            can_deploy: document.getElementById('regDeploy').checked,
            available_from: document.getElementById('regFrom').value,
            available_to: document.getElementById('regTo').value,
            bio_text: document.getElementById('regBio').value
        };

        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (res.ok) {
            document.getElementById('regResult').innerHTML = `
                <div class="alert alert-success">
                    ✅ <b>${result.message}</b><br>
                    🤖 <b>مهارت‌های استخراج‌شده توسط AI:</b> ${result.extracted_skills.join(', ') || 'هیچ مهارتی شناسایی نشد'}
                </div>`;
            document.getElementById('regForm').reset();
        } else {
            document.getElementById('regResult').innerHTML = `<div class="alert alert-danger">❌ ${result.detail}</div>`;
        }
    });

    // ورود
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = new URLSearchParams();
        body.append('username', document.getElementById('loginPhone').value);
        body.append('password', document.getElementById('loginPass').value);

        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: body
        });
        const result = await res.json();
        if (res.ok) {
            localStorage.setItem('token', result.access_token);
            document.getElementById('userInfo').innerHTML = `<span class="badge bg-success fs-6">👤 ${result.full_name} (${result.role})</span>`;
            bootstrap.Modal.getInstance(document.getElementById('loginModal')).hide();
        } else {
            document.getElementById('loginResult').innerHTML = `<div class="alert alert-danger">❌ ${result.detail}</div>`;
        }
    });

    async function loadMissions() {
        const res = await fetch('/api/missions/');
        const missions = await res.json();
        const sel = document.getElementById('misSelect');
        sel.innerHTML = missions.map(m => `<option value="${m.id}">${m.title} (${m.province} - ${m.city})</option>`).join('');
    }

    async function runMatching() {
        const id = document.getElementById('misSelect').value;
        const res = await fetch(`/api/missions/${id}/match`);
        const data = await res.json();
        let html = `<h5 class="fw-bold mb-3">نتایج برای ${data.mission_title}:</h5>`;

        data.recommended_volunteers.forEach((v, i) => {
            html += `
            <div class="card p-3 mb-2 border-start border-4 ${v.is_local ? 'border-success' : 'border-warning'}">
                <div class="d-flex justify-content-between">
                    <div>
                        <b>#${i+1} ${v.volunteer_name}</b> (${v.city}) - 📱 ${v.phone_number}
                        <br><small class="text-muted">🛠️ مهارت‌ها: ${v.skills.join(', ')}</small>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-primary fs-6">${v.score_breakdown.total_score}</span>
                        <div class="small text-muted">تطبیق معنایی: ${v.score_breakdown.semantic_skill_match}</div>
                    </div>
                </div>
            </div>`;
        });
        document.getElementById('matchResults').innerHTML = html;
    }

    window.onload = initProvinces;
</script>
</body>
</html>
'''


def update_frontend():
    with open("static/index.html", "w", encoding="utf-8") as f:
        f.write(frontend_html.strip())
    print("✅ فایل static/index.html با منوی کشویی و سیستم لاگین بروزرسانی شد!")


if __name__ == "__main__":
    update_frontend()