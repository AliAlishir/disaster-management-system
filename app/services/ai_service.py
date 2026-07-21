import requests
import json
from app.config import settings

def extract_skills_with_ai(bio_text: str) -> list[str]:
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_YOUR"):
        print("❌ کلید API معتبر تنظیم نشده است.")
        return []

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    متن داوطلب: "{bio_text}"

    وظیفه: تمام مهارت‌ها، تخصص‌ها، مدرک‌ها و امکاناتی (مثل خودرو، ابزار) که در متن ذکر شده را استخراج کن.
    پاسخ باید **دقیقاً و فقط** یک JSON حاوی کلید 'skills' به‌صورت لیستی از رشته‌ها باشد.
    مثال خروجی: {{"skills": ["امدادگری", "رانندگی وانت", "کمک‌های اولیه"]}}
    """

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=8)
        if response.status_code == 200:
            res_data = response.json()
            content = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            skills = parsed.get("skills", [])
            print(f"✅ مهارت‌های استخراج‌شده: {skills}")
            return skills
        else:
            print(f"❌ خطا از سمت API Groq: {response.text}")
    except Exception as e:
        print(f"❌ خطای ارتباطی در فراخوانی هوش مصنوعی: {e}")

    return []