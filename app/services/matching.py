from sqlalchemy.orm import Session
from app.models.mission import Mission
from app.models.user import User, VolunteerProfile


def calculate_smart_match(mission_id: int, db: Session):
    """
    الگوریتم تطبیق بدون هوش مصنوعی:
    1) فقط داوطلبانی در نظر گرفته می‌شوند که یا در همان شهر ماموریت هستند
       یا تیک «آمادگی اعزام» را فعال کرده‌اند.
    2) تاریخ ماموریت باید داخل بازه زمانی آزادی داوطلب (available_from تا available_to) باشد.
    3) از بین باقی‌مانده‌ها، تعداد مهارت‌های مشترک با مهارت‌های موردنیاز ماموریت محاسبه می‌شود
       و نتایج بر اساس بیشترین اشتراک مهارت (و در مرحله بعد بومی بودن و امتیاز) مرتب می‌شوند.
    """
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        return None

    required = set(mission.required_skills or [])
    profiles = db.query(VolunteerProfile).join(User).filter(User.role == "VOLUNTEER").all()

    results = []
    for prof in profiles:
        # پروفایل ناقص (بدون شهر یا بازه زمانی آزادی) در تطبیق شرکت داده نمی‌شود
        if not prof.city or not prof.available_from or not prof.available_to:
            continue

        # ۱. فیلتر شهر / آمادگی اعزام
        is_local = (prof.city or "").strip().lower() == (mission.city or "").strip().lower()
        if not is_local and not prof.can_deploy:
            continue

        # ۲. بررسی اینکه تاریخ ماموریت داخل بازه زمانی آزادی داوطلب است یا نه
        if not (prof.available_from <= mission.mission_date <= prof.available_to):
            continue

        # ۳. شمارش مهارت‌های مشترک
        vol_skills = set(prof.skills or [])
        matched_skills = required.intersection(vol_skills)
        match_count = len(matched_skills)

        user_rating = prof.rating if prof.rating is not None else 5.0

        results.append({
            "volunteer_id": prof.user.id,
            "volunteer_name": prof.user.full_name,
            "phone_number": prof.user.phone_number,
            "province": prof.province,
            "city": prof.city,
            "is_local": is_local,
            "needs_deployment": not is_local,
            "rating": user_rating,
            "skills": list(vol_skills),
            "matched_skills": list(matched_skills),
            "match_count": match_count,
            "total_required": len(required),
        })

    # مرتب‌سازی: اول بیشترین تعداد مهارت مشترک، سپس بومی بودن، سپس بالاترین امتیاز
    results.sort(key=lambda x: (x["match_count"], x["is_local"], x["rating"]), reverse=True)

    return {
        "mission_id": mission.id,
        "mission_title": mission.title,
        "mission_city": mission.city,
        "recommended_volunteers": results
    }