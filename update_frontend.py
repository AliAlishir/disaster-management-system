import os

frontend_html = '''<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>سامانه هوشمند مدیریت داوطلبان بحران</title>
    <!-- Bootstrap 5 RTL -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.rtl.min.css">
    <!-- Vazirmatn Font -->
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet" type="text/css" />
    <style>
        body { font-family: 'Vazirmatn', sans-serif; background-color: #f4f6f9; }
        .card { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .nav-pills .nav-link.active { background-color: #0d6efd; border-radius: 8px; }
        .badge-score { font-size: 1.1rem; padding: 6px 12px; border-radius: 20px; }
    </style>
</head>
<body>

<div class="container py-4">
    <header class="pb-3 mb-4 border-bottom d-flex justify-content-between align-items-center">
        <div>
            <h3 class="fw-bold text-primary">🚨 سامانه هوشمند هماهنگی داوطلبان بحران</h3>
            <p class="text-muted mb-0">تطبیق ۳ لایه‌ای داوطلبان با هوش مصنوعی (Groq & Llama 3.3)</p>
        </div>
        <span class="badge bg-success p-2">سیستم فعال است</span>
    </header>

    <!-- تب‌های اصلی -->
    <ul class="nav nav-pills mb-4 id="pills-tab" role="tablist">
        <li class="nav-item">
            <button class="nav-link active fw-bold" id="pills-volunteer-tab" data-bs-toggle="pill" data-bs-target="#pills-volunteer">🙋‍♂️ ثبت‌نام داوطلب (با AI)</button>
        </li>
        <li class="nav-item">
            <button class="nav-link fw-bold" id="pills-mission-tab" data-bs-toggle="pill" data-bs-target="#pills-mission">📋 تعریف ماموریت جدید</button>
        </li>
        <li class="nav-item">
            <button class="nav-link fw-bold" id="pills-match-tab" data-bs-toggle="pill" data-bs-target="#pills-match" onclick="loadMissionsForMatch()">🎯 تطبیق هوشمند و پیشنهادات</button>
        </li>
    </ul>

    <div class="tab-content" id="pills-tabContent">

        <!-- ۱. تب ثبت‌نام داوطلب -->
        <div class="tab-pane fade show active" id="pills-volunteer">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ثبت اطلاعات داوطلب</h5>
                <form id="volunteerForm">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">نام و نام خانوادگی</label>
                            <input type="text" id="volName" class="form-control" required placeholder="مثلا: علی محمدی">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">شماره تلفن</label>
                            <input type="text" id="volPhone" class="form-control" required placeholder="09123456789">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">شهر سکونت</label>
                            <input type="text" id="volCity" class="form-control" required placeholder="مثلا: کرج">
                        </div>
                        <div class="col-md-6 align-self-end">
                            <div class="form-check form-switch mb-2">
                                <input class="form-check-input" type="checkbox" id="volDeploy">
                                <label class="form-check-label fw-bold" for="volDeploy">آمادگی اعزام به سایر شهرها را دارم</label>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">شروع زمان آزادی</label>
                            <input type="datetime-local" id="volFrom" class="form-control" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">پایان زمان آزادی</label>
                            <input type="datetime-local" id="volTo" class="form-control" required>
                        </div>
                        <div class="col-12">
                            <label class="form-label">توضیحات، مهارت‌ها و امکانات (هوش مصنوعی مهارت‌ها را استخراج می‌کند)</label>
                            <textarea id="volBio" class="form-control" rows="3" required placeholder="مثلا: من ۲ سال امدادگر هلال احمر بودم، خودروی وانت دارم و به زبان عربی هم مسلطم."></textarea>
                        </div>
                        <div class="col-12">
                            <button type="submit" class="btn btn-primary px-4 fw-bold">ثبت داوطلب و استخراج مهارت‌ها با AI</button>
                        </div>
                    </div>
                </form>
                <div id="volResult" class="mt-3"></div>
            </div>
        </div>

        <!-- ۲. تب تعریف ماموریت -->
        <div class="tab-pane fade" id="pills-mission">
            <div class="card p-4">
                <h5 class="fw-bold mb-3">ایجاد ماموریت عملیاتی</h5>
                <form id="missionForm">
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label">عنوان ماموریت</label>
                            <input type="text" id="misTitle" class="form-control" required placeholder="مثلا: آواربرداری و توزیع غذا">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">شهر محل ماموریت</label>
                            <input type="text" id="misCity" class="form-control" required placeholder="مثلا: کرج">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">مهارت‌های ضروری/حیاتی (با کاما جدا کنید)</label>
                            <input type="text" id="misEssential" class="form-control" required placeholder="خودروی باری, امدادگری">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">مهارت‌های امتیازی (اختیاری - با کاما جدا کنید)</label>
                            <input type="text" id="misBonus" class="form-control" placeholder="زبان عربی">
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">زمان شروع ماموریت</label>
                            <input type="datetime-local" id="misStart" class="form-control" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">زمان پایان ماموریت</label>
                            <input type="datetime-local" id="misEnd" class="form-control" required>
                        </div>
                        <div class="col-12">
                            <button type="submit" class="btn btn-success px-4 fw-bold">ثبت ماموریت جدید</button>
                        </div>
                    </div>
                </form>
                <div id="misResult" class="mt-3"></div>
            </div>
        </div>

        <!-- ۳. تب تطبیق هوشمند -->
        <div class="tab-pane fade" id="pills-match">
            <div class="card p-4 mb-4">
                <h5 class="fw-bold mb-3">انتخاب ماموریت جهت تطبیق هوشمند</h5>
                <div class="row g-3">
                    <div class="col-md-8">
                        <select id="missionSelect" class="form-select">
                            <option value="">در حال دریافت لیست ماموریت‌ها...</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <button onclick="runMatching()" class="btn btn-warning w-100 fw-bold">اجرای الگوریتم تطبیق ۳ لایه‌ای 🚀</button>
                    </div>
                </div>
            </div>

            <!-- محل نمایش کارت‌های پیشنهادی -->
            <div id="matchResults"></div>
        </div>

    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
    // ۱. ثبت داوطلب
    document.getElementById('volunteerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        btn.disabled = true;
        btn.innerText = 'در حال تحلیل با هوش مصنوعی...';

        const data = {
            full_name: document.getElementById('volName').value,
            phone_number: document.getElementById('volPhone').value,
            city: document.getElementById('volCity').value,
            can_deploy: document.getElementById('volDeploy').checked,
            available_from: document.getElementById('volFrom').value,
            available_to: document.getElementById('volTo').value,
            bio_text: document.getElementById('volBio').value
        };

        try {
            const res = await fetch('/api/volunteers/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (res.ok) {
                document.getElementById('volResult').innerHTML = `
                    <div class="alert alert-success">
                        ✅ <b>${result.message}</b><br>
                        🤖 <b>مهارت‌های استخراج‌شده توسط AI:</b> ${result.extracted_skills.join(', ') || 'موردی یافت نشد'}
                    </div>`;
                document.getElementById('volunteerForm').reset();
            } else {
                document.getElementById('volResult').innerHTML = `<div class="alert alert-danger">❌ ${result.detail}</div>`;
            }
        } catch (err) {
            document.getElementById('volResult').innerHTML = `<div class="alert alert-danger">❌ خطا در ارتباط با سرور</div>`;
        }
        btn.disabled = false;
        btn.innerText = 'ثبت داوطلب و استخراج مهارت‌ها با AI';
    });

    // ۲. ثبت ماموریت
    document.getElementById('missionForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            title: document.getElementById('misTitle').value,
            city: document.getElementById('misCity').value,
            essential_skills: document.getElementById('misEssential').value.split(',').map(s => s.trim()).filter(s => s),
            bonus_skills: document.getElementById('misBonus').value.split(',').map(s => s.trim()).filter(s => s),
            start_time: document.getElementById('misStart').value,
            end_time: document.getElementById('misEnd').value
        };

        try {
            const res = await fetch('/api/missions/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (res.ok) {
                document.getElementById('misResult').innerHTML = `<div class="alert alert-success">✅ ماموریت با شناسه ${result.id} ثبت شد.</div>`;
                document.getElementById('missionForm').reset();
            }
        } catch (err) {
            document.getElementById('misResult').innerHTML = `<div class="alert alert-danger">❌ خطا در ثبت ماموریت</div>`;
        }
    });

    // ۳. بارگذاری لیست ماموریت‌ها در Dropdown
    async function loadMissionsForMatch() {
        const select = document.getElementById('missionSelect');
        select.innerHTML = '<option value="">در حال دریافت...</option>';
        try {
            const res = await fetch('/api/missions/');
            const missions = await res.json();
            if (missions.length === 0) {
                select.innerHTML = '<option value="">هیچ ماموریتی ثبت نشده است</option>';
                return;
            }
            select.innerHTML = missions.map(m => `<option value="${m.id}">${m.title} - شهر: ${m.city}</option>`).join('');
        } catch (err) {
            select.innerHTML = '<option value="">خطا در دریافت ماموریت‌ها</option>';
        }
    }

    // ۴. اجرای الگوریتم تطبیق
    async function runMatching() {
        const missionId = document.getElementById('missionSelect').value;
        const container = document.getElementById('matchResults');
        if (!missionId) {
            alert('لطفاً یک ماموریت انتخاب کنید.');
            return;
        }

        container.innerHTML = '<div class="text-center py-4">⌛ در حال پردازش معنایی و آنالیز ۳ لایه‌ای داوطلبان...</div>';

        try {
            const res = await fetch(`/api/missions/${missionId}/match`);
            const data = await res.json();

            if (!data.recommended_volunteers || data.recommended_volunteers.length === 0) {
                container.innerHTML = '<div class="alert alert-warning">هیچ داوطلب واجد شرایطی (با توجه به زمان و شهر) پیدا نشد.</div>';
                return;
            }

            let html = `<h5 class="fw-bold mb-3">نتایج تطبیق برای ماموریت: <span class="text-primary">${data.mission_title}</span> (${data.mission_city})</h5>`;

            data.recommended_volunteers.forEach((v, index) => {
                const score = parseFloat(v.score_breakdown.total_score);
                let badgeClass = 'bg-success';
                if (score < 70) badgeClass = 'bg-warning text-dark';
                if (score < 50) badgeClass = 'bg-danger';

                html += `
                <div class="card p-3 mb-3 border-start border-4 ${v.is_local ? 'border-success' : 'border-info'}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="fw-bold mb-1">
                                #${index + 1} ${v.volunteer_name} 
                                ${v.needs_deployment ? '<span class="badge bg-warning text-dark fs-6">نیازمند اعزام</span>' : '<span class="badge bg-success fs-6">بومی</span>'}
                            </h5>
                            <p class="text-muted mb-1">📍 شهر: ${v.city} | 📱 تلفن: ${v.phone_number}</p>
                            <small class="text-secondary">🛠️ مهارت‌ها: ${v.skills.join(', ') || 'ندارد'}</small>
                        </div>
                        <div class="text-end">
                            <span class="badge ${badgeClass} badge-score mb-2">تطبیق کل: ${v.score_breakdown.total_score}</span>
                            <div class="small text-muted">
                                🧠 تطبیق معنایی مهارت: <b>${v.score_breakdown.semantic_skill_match}</b><br>
                                🗺️ وضعیت بومی: <b>${v.score_breakdown.proximity_bonus}</b><br>
                                ⭐ امتیاز داوطلب: <b>${v.score_breakdown.rating_bonus}</b>
                            </div>
                        </div>
                    </div>
                </div>`;
            });

            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = '<div class="alert alert-danger">❌ خطا در دریافت نتایج تطبیق</div>';
        }
    }
</script>
</body>
</html>
'''


def update_frontend():
    with open("static/index.html", "w", encoding="utf-8") as f:
        f.write(frontend_html.strip())
    print("✅ فایل static/index.html با موفقیت ساخته شد!")


if __name__ == "__main__":
    update_frontend()