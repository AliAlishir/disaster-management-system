import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "سامانه هوشمند مدیریت داوطلبان بحران"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    DATABASE_URL: str = "sqlite:///./disaster.db"

settings = Settings()
