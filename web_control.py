import http.server
import socketserver
import json
import subprocess
import os
import sys
import webbrowser
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from zalo.bridge import ZaloBridge
from database.construction_db import ConstructionDB
from sync_github import auto_push_to_github
from config import Config

PID_FILE = BASE_DIR / "data" / "bot.pid"
EXCEL_PATH = BASE_DIR / "data" / "Bao_cao_Tien_do_Thi_cong.xlsx"
LOG_FILE = BASE_DIR / "data" / "bot_runtime.log"

def is_pid_running(pid: int) -> bool:
    """Kiểm tra xem Process ID có đang thực sự chạy trên Windows không."""
    try:
        res = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=3)
        return str(pid) in res.stdout
    except Exception:
        return False

def get_running_bot_pid() -> Optional[int]:
    """Lấy PID của bot nếu đang chạy."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
            if is_pid_running(pid):
                return pid
            else:
                try:
                    PID_FILE.unlink()
                except Exception:
                    pass
        except Exception:
            pass
    return None

def start_bot_process() -> Dict[str, Any]:
    """Khởi động tiến trình run_data_boss.py chạy nền."""
    existing_pid = get_running_bot_pid()
    if existing_pid:
        return {"ok": True, "pid": existing_pid, "message": f"Bot đang chạy sẵn với PID: {existing_pid}"}

    python_exe = sys.executable
    script_path = BASE_DIR / "run_data_boss.py"
    
    # Mở file log để ghi output
    log_fp = open(LOG_FILE, "a", encoding="utf-8")
    
    # Chạy subprocess độc lập trên Windows
    proc = subprocess.Popen(
        [python_exe, "-u", str(script_path)],
        cwd=str(BASE_DIR),
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )
    
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    time.sleep(1.0)
    return {"ok": True, "pid": proc.pid, "message": f"Đã khởi động Bot thành công (PID: {proc.pid})!"}

def stop_bot_process() -> Dict[str, Any]:
    """Dừng tiến trình bot."""
    pid = get_running_bot_pid()
    if not pid:
        return {"ok": True, "message": "Bot hiện không chạy."}

    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass
        return {"ok": True, "message": f"Đã dừng Bot (PID: {pid})."}
    except Exception as e:
        return {"ok": False, "message": f"Lỗi dừng bot: {e}"}

def trigger_zalo_login() -> Dict[str, Any]:
    """Bật cửa sổ CMD kết nối / quét mã QR Zalo."""
    bat_file = BASE_DIR / "1_KET_NOI_ZALO.bat"
    if bat_file.exists():
        subprocess.Popen(f'start "Ket noi Zalo" cmd /c "{bat_file}"', shell=True, cwd=str(BASE_DIR))
        return {"ok": True, "message": "Đã mở cửa sổ Quét mã QR Zalo!"}
    return {"ok": False, "message": "Không tìm thấy file 1_KET_NOI_ZALO.bat"}

def open_excel_file() -> Dict[str, Any]:
    """Mở file Excel trên máy tính người dùng."""
    if EXCEL_PATH.exists():
        try:
            os.startfile(str(EXCEL_PATH))
            return {"ok": True, "message": "Đã mở file Excel tiến độ!"}
        except Exception as e:
            return {"ok": False, "message": f"Lỗi mở Excel: {e}"}
    return {"ok": False, "message": "Chưa tìm thấy file Excel tiến độ."}

class WebControlHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        # Thiết lập CORS toàn diện để hỗ trợ gọi API từ cả Localhost lẫn Cloud Pages
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()

        if self.path == "/api/status":
            bot_pid = get_running_bot_pid()
            bridge = ZaloBridge()
            cred_path = Path.home() / ".zalo-personal-mcp" / "credentials.json"
            has_creds = cred_path.exists()

            zalo_info = bridge.check_connection()
            user_name = zalo_info.get("displayName") or (zalo_info.get("user") or {}).get("displayName") or ""
            uid = str(zalo_info.get("uid") or (zalo_info.get("user") or {}).get("userId") or "")
            zalo_connected = bool(user_name or uid) or has_creds

            if not user_name and has_creds:
                user_name = "Đã lưu đăng nhập (Zalo cá nhân)"

            db = ConstructionDB()
            summary = db.get_db_summary()

            from core.claude_engine import ClaudeEngine
            claude = ClaudeEngine()

            data = {
                "bot_running": bool(bot_pid),
                "bot_pid": bot_pid,
                "zalo_connected": zalo_connected,
                "zalo_user": user_name or "Chưa đăng nhập",
                "zalo_uid": uid,
                "ai_provider": Config.AI_PROVIDER,
                "ai_available": claude.is_available,
                "ai_model": Config.CLAUDE_MODEL,
                "cloud_url": "https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/",
                "total_reports": summary.get("total_reports", 0),
                "total_items": summary.get("total_progress_items", 0),
                "total_piles": summary.get("total_piles", 0),
                "last_update": summary.get("last_report_date", "Chưa có"),
                "excel_exists": EXCEL_PATH.exists()
            }
            self._send_json(data)
            return

        if self.path == "/api/logs":
            logs = ""
            if LOG_FILE.exists():
                try:
                    lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
                    logs = "\n".join(lines[-60:])
                except Exception:
                    pass
            self._send_json({"logs": logs})
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/bot/start":
            res = start_bot_process()
            self._send_json(res)
            return

        if self.path == "/api/bot/stop":
            res = stop_bot_process()
            self._send_json(res)
            return

        if self.path == "/api/sync":
            success = auto_push_to_github("Đồng bộ từ Bảng điều hành Web")
            msg = "✅ Đã đồng bộ thành công lên GitHub Pages!" if success else "⚠️ Chưa đồng bộ được lên GitHub."
            self._send_json({"ok": success, "message": msg})
            return

        if self.path == "/api/open-excel":
            res = open_excel_file()
            self._send_json(res)
            return

        if self.path == "/api/zalo/login":
            res = trigger_zalo_login()
            self._send_json(res)
            return

        self._send_json({"ok": False, "message": "Endpoint không tồn tại"}, status=404)

def run_server(port: int = 8080, autostart_bot: bool = True, open_browser: bool = True):
    # Khởi động Bot ngầm nếu được yêu cầu
    if autostart_bot:
        print("[Hệ thống] Đang kiểm tra & kích hoạt Bot Realtime...")
        res = start_bot_process()
        print(f"        👉 {res.get('message')}")

    server_address = ("127.0.0.1", port)
    try:
        httpd = socketserver.ThreadingTCPServer(server_address, WebControlHandler)
    except OSError:
        # Nếu cổng 8080 bận, thử 8088
        port = 8088
        server_address = ("127.0.0.1", port)
        httpd = socketserver.ThreadingTCPServer(server_address, WebControlHandler)

    url = f"http://localhost:{port}"
    print("=" * 70)
    print(f" 🚀 TRUNG TÂM ĐIỀU HÀNH WEB 'ĐẠI CA DỮ LIỆU' ĐANG CHẠY")
    print(f" 🌐 Địa chỉ Web Nội Bộ:  {url}")
    print(f" ☁️  Địa chỉ Cloud Mobile: https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/")
    print("=" * 70)
    print(" 👉 Nhấn Ctrl+C trong cửa sổ này để tắt máy chủ.")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Máy chủ] Đang đóng máy chủ...")
        httpd.server_close()

if __name__ == "__main__":
    autostart = "--no-bot" not in sys.argv
    open_b = "--no-browser" not in sys.argv
    run_server(port=8080, autostart_bot=autostart, open_browser=open_b)
