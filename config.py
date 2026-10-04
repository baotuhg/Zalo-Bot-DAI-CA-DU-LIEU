import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

if not ENV_FILE.exists():
    # Khởi tạo file .env mẫu
    default_env = """# Cấu hình AI Provider (gemini | lmstudio | openai)
AI_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# Nếu dùng LM Studio local
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL=qwen/qwen3.5-9b

# Zalo MCP Daemon (cổng mặc định của zalo-personal-mcp là 3712)
ZALO_DAEMON_URL=http://127.0.0.1:3712
DEFAULT_GROUP_NAME=GIA ĐÌNH_TRỢ LÝ AI
DEFAULT_STUDENT_NAME=Khôi Nguyên

# Lịch nhắc nhở tự động trong ngày
REMINDER_AFTERNOON_TIME=18:30
REMINDER_EVENING_BAG_TIME=21:30
DAILY_REPORT_TIME=23:00
"""
    ENV_FILE.write_text(default_env, encoding="utf-8")

load_dotenv(dotenv_path=ENV_FILE)

class Config:
    BASE_DIR: Path = BASE_DIR
    ENV_FILE: Path = ENV_FILE
    DATA_DIR: Path = DATA_DIR
    DB_PATH: Path = DATA_DIR / "tutor.db"
    
    # AI Config
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini").lower()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    LM_STUDIO_BASE_URL: str = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    LM_STUDIO_MODEL: str = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3.5-9b")
    
    # Zalo Config
    ZALO_DAEMON_URL: str = os.getenv("ZALO_DAEMON_URL", "http://127.0.0.1:3712")
    DEFAULT_GROUP_NAME: str = os.getenv("DEFAULT_GROUP_NAME", "GIA ĐÌNH_TRỢ LÝ AI")
    DEFAULT_STUDENT_NAME: str = os.getenv("DEFAULT_STUDENT_NAME", "Khôi Nguyên")
    
    # Schedule Times
    REMINDER_AFTERNOON_TIME: str = os.getenv("REMINDER_AFTERNOON_TIME", "18:30")
    REMINDER_EVENING_BAG_TIME: str = os.getenv("REMINDER_EVENING_BAG_TIME", "21:30")
    DAILY_REPORT_TIME: str = os.getenv("DAILY_REPORT_TIME", "23:00")
