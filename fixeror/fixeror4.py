import os

os.makedirs("app/services", exist_ok=True)

files = {
    # 1. ساخت __init__.py برای ماژول services
    "app/services/__init__.py": "",

    # 2. سرویس استخراج هوشمند مهارت‌ها از متن (AI Extractor)
    "app/services/ai_extractor.py": '''import re
from typing import List

def extract_skills_with_ai(text: str) -> List[str]:
    if not text:
        return []

    # بانک کلیدواژه‌های هوشمند حوزه امداد و بحران
    skills_db = {
        "کمک‌های اولیه": ["کمک", "اولیه", "پزشک", "پرستار", "درمان", "اورژانس", "احیا"],
        "خودرو شاسی‌بلند": ["خودرو", "شاسی", "آفرود", "ماشین", "4x4", "پاترول", "هایلوکس"],
        "آواربرداری": ["آوار", "تخریب", "بیل", "کلنگ", "ماشین‌آلات", "سنگین"],
        "اسکان اضطراری": ["چادر", "اسکان", "کمپ", "پناهگاه"],
        "توزیع آذوقه": ["غذا", "پک", "آذوقه", "جیره", "آب"],
        "مترجمی": ["زبان", "مترجم", "انگلیسی", "عربی"],
        "مدیریت بحران": ["مدیریت", "فرماندهی", "هماهنگی", "ارتباطات"]
    }

    found_skills = set()
    text_lower = text.lower()

    for skill, keywords in skills_db.items():
        for kw in keywords:
            if kw in text_lower:
                found_skills.add(skill)
                break

    if not found_skills:
        words = [w.strip() for w in re.split(r"[\\s،,-]+", text) if len(w.strip()) > 3]
        return list(set(words[:5]))

    return list(found_skills)
''',

    # 3. سرویس تطبیق و رتبه‌بندی ۳ لایه‌ای (Matching Service)
    "app/services/matching.py": '''from sqlalchemy.orm import Session
from app.models.mission import Mission
from app.models.user import User, VolunteerProfile

def calculate_smart_match(mission_id: int, db: Session):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        return {"mission_title": "یافت نشد", "recommended_volunteers": []}

    profiles = db.query(VolunteerProfile).join(User).filter(User.role == "VOLUNTEER").all()

    results = []
    essential_set = set(mission.essential_skills or [])
    bonus_set = set(mission.bonus_skills or [])

    for prof in profiles:
        vol_skills = set(prof.skills or [])

        # ۱. امتیاز مهارت (۰ تا ۵۰)
        matched_essential = essential_set.intersection(vol_skills)
        matched_bonus = bonus_set.intersection(vol_skills)

        essential_score = (len(matched_essential) / len(essential_set) * 40) if essential_set else 20
        bonus_score = (len(matched_bonus) * 5) if bonus_set else 0
        skill_score = min(essential_score + bonus_score, 50)

        # ۲. امتیاز مکانی (۰ تا ۳۰)
        loc_score = 0
        if prof.province == mission.province:
            loc_score += 15
        if prof.city == mission.city:
            loc_score += 15

        # ۳. امتیاز سابقه و رتبه (۰ تا ۲۰)
        rating_score = (prof.rating / 5.0) * 20 if prof.rating else 15

        total_score = round(skill_score + loc_score + rating_score, 1)

        results.append({
            "volunteer_id": prof.user.id,
            "volunteer_name": prof.user.full_name,
            "phone": prof.user.phone_number,
            "province": prof.province,
            "city": prof.city,
            "rating": prof.rating,
            "skills": prof.skills,
            "score_breakdown": {
                "total_score": total_score,
                "skill_score": round(skill_score, 1),
                "location_score": loc_score,
                "rating_score": round(rating_score, 1)
            }
        })

    results.sort(key=lambda x: x["score_breakdown"]["total_score"], reverse=True)

    return {
        "mission_id": mission.id,
        "mission_title": mission.title,
        "recommended_volunteers": results
    }
'''
}

for path, code in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(code.strip())
    print(f"✅ فایل ایجاد شد: {path}")

print("\n🎉 تمامی سرویس‌های هوش مصنوعی و تطبیق با موفقیت مستقر شدند!")