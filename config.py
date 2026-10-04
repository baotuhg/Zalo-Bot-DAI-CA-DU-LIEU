import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

if not ENV_FILE.exists():
    default_env = """# Cấu hình Bot Zalo 'Đại ca dữ liệu' - Giám sát Dự án Công trường
ZALO_DAEMON_URL=http://127.0.0.1:3712
DEFAULT_GROUP_NAME=307 HỒ SƠ SẠT LỞ

# Cấu hình AI Provider (tùy chọn)
AI_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
"""
    ENV_FILE.write_text(default_env, encoding="utf-8")

load_dotenv(dotenv_path=ENV_FILE)

class Config:
    BASE_DIR: Path = BASE_DIR
    ENV_FILE: Path = ENV_FILE
    DATA_DIR: Path = DATA_DIR
    
    # Đường dẫn cơ sở dữ liệu và báo cáo
    DB_PATH: Path = DATA_DIR / "construction_data.db"
    EXCEL_PATH: Path = DATA_DIR / "Bao_cao_Tien_do_Thi_cong.xlsx"
    HTML_PATH: Path = DATA_DIR / "Bang_dieu_hanh_TD3.html"
    INDEX_HTML_PATH: Path = BASE_DIR / "index.html"
    
    # Cấu hình Zalo cá nhân
    ZALO_DAEMON_URL: str = os.getenv("ZALO_DAEMON_URL", "http://127.0.0.1:3712")
    DEFAULT_GROUP_NAME: str = os.getenv("DEFAULT_GROUP_NAME", "307 HỒ SƠ SẠT LỞ")
    
    # AI Config (tùy chọn nâng cao)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "gemini").lower()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
