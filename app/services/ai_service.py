import re
import json
import requests
from typing import List
from app.config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

_FALLBACK_SKILL_CATEGORIES = {
    "کمک‌های اولیه": ["کمک اولیه", "کمک‌های اولیه", "اورژانس", "احیا", "پزشک", "پرستار", "بهیار", "پانسمان", "تزریقات"],
    "خودرو شاسی‌بلند / آفرود": ["شاسی‌بلند", "شاسی بلند", "آفرود", "پاترول", "هایلوکس", "دو دیفرانسیل", "ماشین سنگین", "خودرو"],
    "آواربرداری": ["آوار", "آواربرداری", "تخریب", "بیل", "کلنگ", "سنگین", "عمران", "ساختمانی"],
    "اسکان اضطراری": ["چادر", "اسکان", "کمپ", "پناهگاه", "برپایی چادر"],
    "توزیع آذوقه و امداد": ["آذوقه", "غذا", "پک", "جیره", "آب معدنی", "توزیع"],
    "مهارت‌های ارتباطی و زبان": ["زبان", "انگلیسی", "عربی", "مترجم", "ارتباطات", "بی‌سیم"],
    "مدیریت بحران و فرماندهی": ["مدیریت بحران", "فرماندهی", "هماهنگی", "ستاد", "گروه نجات"],
    "امداد در آب و سیل": ["شنا", "غریق نجات", "قایق", "سیل", "غواصی", "آب‌گرفتگی"],
    "اطفا حریق": ["آتش‌نشانی", "حریق", "آتش", "کپسول", "اطفا"],
}


def _is_api_configured() -> bool:
    return bool(settings.GROQ_API_KEY) and not settings.GROQ_API_KEY.startswith("gsk_YOUR")


def _fallback_extract(text: str) -> List[str]:
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for category, keywords in _FALLBACK_SKILL_CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                found.add(category)
                break
    if not found:
        stop_words = {"است", "و", "با", "در", "از", "برای", "به", "که", "این", "آن", "دارای", "من", "او", "ما", "هستم"}
        words = [w.strip() for w in re.split(r"[\s،,-]+", text) if len(w.strip()) > 2 and w.strip() not in stop_words]
        return list(set(words[:4])) if words else ["عمومی / امدادگر"]
    return list(found)


def _call_groq(payload: dict, timeout: int = 10):
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
    if response.status_code == 200:
        res_data = response.json()
        content = res_data["choices"][0]["message"]["content"]
        return json.loads(content)
    raise RuntimeError(f"خطای Groq API - کد {response.status_code}: {response.text}")


def extract_skills_with_ai(bio_text: str) -> List[str]:
    """
    دسته‌بندی و استخراج مهارت‌ها از متن داوطلب با استفاده از هوش مصنوعی Groq.
    در صورت نبود کلید معتبر یا بروز خطا، به روش کلیدواژه‌ای محلی برمی‌گردد.
    """
    if not bio_text or not bio_text.strip():
        return []

    if not _is_api_configured():
        print("⚠️ کلید GROQ_API_KEY تنظیم نشده یا نامعتبر است - استفاده از استخراج محلی مهارت‌ها.")
        return _fallback_extract(bio_text)

    prompt = f'''
    متن داوطلب: "{bio_text}"

    وظیفه: تمام مهارت‌ها، تخصص‌ها، مدرک‌ها و امکاناتی (مثل خودرو، ابزار، زبان) که در متن ذکر شده را
    استخراج و در قالب چند دسته‌بندی کوتاه و استاندارد فارسی (نه جمله کامل) بیان کن.
    پاسخ باید دقیقاً و فقط یک JSON حاوی کلید 'skills' به‌صورت لیستی از رشته‌ها باشد، بدون هیچ توضیح اضافه.
    مثال خروجی: {{"skills": ["امدادگری", "رانندگی خودرو شاسی‌بلند", "کمک‌های اولیه"]}}
    '''

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }

    try:
        parsed = _call_groq(payload, timeout=10)
        skills = parsed.get("skills", [])
        skills = [str(s).strip() for s in skills if str(s).strip()]
        if skills:
            print(f"✅ مهارت‌های استخراج‌شده توسط AI: {skills}")
            return skills
    except Exception as e:
        print(f"❌ خطا در فراخوانی هوش مصنوعی (استخراج مهارت): {e}")

    return _fallback_extract(bio_text)


def evaluate_semantic_match(volunteer_skills: List[str], required_skills: List[str]) -> float:
    """
    سنجش معنایی میزان پوشش مهارت‌های موردنیاز ماموریت توسط داوطلب، با کمک هوش مصنوعی Groq.
    خروجی عددی بین ۰ و ۱ است. در صورت نبود کلید یا خطا، به تطبیق دقیق کلمه‌ای برمی‌گردد.
    """
    if not required_skills:
        return 1.0
    if not volunteer_skills:
        return 0.0

    vol_set = set(s.strip().lower() for s in volunteer_skills)
    req_set = set(s.strip().lower() for s in required_skills)
    exact_matches = vol_set.intersection(req_set)

    if len(exact_matches) == len(req_set):
        return 1.0

    if not _is_api_configured():
        return len(exact_matches) / len(req_set)

    prompt = f'''
    تو یک ارزیاب مهارت در مدیریت بحران هستی.
    مهارت‌های مورد نیاز ماموریت: {required_skills}
    مهارت‌های موجود داوطلب: {volunteer_skills}

    این دو لیست را از نظر معنایی و مفهومی مقایسه کن (مثلا "پرستار" پوشش‌دهنده "کمک‌های اولیه" است،
    یا "وانت" با "خودروی باری" مترادف است).
    مشخص کن داوطلب چند درصد از مهارت‌های موردنیاز ماموریت را پوشش می‌دهد.
    خروجی باید دقیقاً و فقط یک JSON با کلید 'match_percentage' (عددی بین 0 تا 100) باشد.
    مثال خروجی: {{"match_percentage": 85}}
    '''

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }

    try:
        parsed = _call_groq(payload, timeout=8)
        percentage = float(parsed.get("match_percentage", 0))
        return max(0.0, min(1.0, percentage / 100.0))
    except Exception as e:
        print(f"❌ خطا در تطبیق معنایی هوش مصنوعی: {e}")

    return len(exact_matches) / len(req_set)