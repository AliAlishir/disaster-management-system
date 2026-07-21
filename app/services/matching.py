from sqlalchemy.orm import Session
from app.models.mission import Mission
from app.models.user import User, VolunteerProfile
from app.services.ai_service import evaluate_semantic_match


def calculate_smart_match(mission_id: int, db: Session):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        return None

    profiles = db.query(VolunteerProfile).join(User).filter(User.role == "VOLUNTEER").all()
    results = []

    essential_req = mission.essential_skills or []
    bonus_req = mission.bonus_skills or []

    for prof in profiles:
        # پروفایل‌های ناقص (بدون شهر یا زمان آزادی) در تطبیق شرکت داده نمی‌شوند
        if not prof.city or not prof.available_from or not prof.available_to:
            continue

        # ۱. فیلتر شهر / آمادگی اعزام
        is_local = (prof.city or "").strip().lower() == (mission.city or "").strip().lower()
        if not is_local and not prof.can_deploy:
            continue

        # ۲. هم‌پوشانی زمانی
        if not (prof.available_from <= mission.start_date and prof.available_to >= mission.end_date):
            continue

        vol_skills = prof.skills or []

        # ۳. سنجش معنایی هوش مصنوعی برای مهارت ضروری (وزن ۷۰٪) و امتیازی (وزن ۳۰٪)
        essential_score = evaluate_semantic_match(vol_skills, essential_req)
        bonus_score = evaluate_semantic_match(vol_skills, bonus_req) if bonus_req else 0.0

        if bonus_req:
            skill_percent = (essential_score * 70) + (bonus_score * 30)
        else:
            skill_percent = essential_score * 100

        # ۴. ماتریس امتیازدهی نهایی: مهارت ۶۰٪ + مکان ۲۵٪ + سابقه/امتیاز ۱۵٪
        weighted_skill = (skill_percent / 100) * 60
        weighted_location = (100 if is_local else 50) / 100 * 25
        user_rating = prof.rating if prof.rating is not None else 5.0
        weighted_rating = (user_rating / 5.0) * 15

        total_score = round(weighted_skill + weighted_location + weighted_rating, 1)

        results.append({
            "volunteer_id": prof.user.id,
            "volunteer_name": prof.user.full_name,
            "phone_number": prof.user.phone_number,
            "province": prof.province,
            "city": prof.city,
            "is_local": is_local,
            "needs_deployment": not is_local,
            "rating": user_rating,
            "skills": vol_skills,
            "score_breakdown": {
                "total_score": total_score,
                "semantic_skill_match": round(skill_percent, 1),
                "proximity_bonus": "بومی" if is_local else "نیازمند اعزام",
                "rating_bonus": user_rating
            }
        })

    # مرتب‌سازی بر اساس بالاترین امتیاز تطبیق کل - مرتبط‌ترین‌ها اول نمایش داده می‌شوند
    results.sort(key=lambda x: x["score_breakdown"]["total_score"], reverse=True)

    return {
        "mission_id": mission.id,
        "mission_title": mission.title,
        "mission_city": mission.city,
        "recommended_volunteers": results
    }