import os
import time
import httpx
from typing import Optional, Dict, Any, List
from config import Config

class ZaloBridge:
    """
    Cầu nối giao tiếp với Zalo thông qua Zalo Personal Daemon (HTTP API).
    Học tập các cơ chế bảo vệ từ 2anh-zalo-bot:
    - Rate limiting chống ban acc.
    - Cắt nhỏ tin nhắn dài tránh lỗi giới hạn UTF-16 của Zalo (>3000 ký tự).
    - Hiệu ứng gõ chữ (typing indicator) và Thả cảm xúc thông minh (Reactions).
    """
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or Config.ZALO_DAEMON_URL).rstrip("/")
        self.last_send_time = 0.0
        self.min_send_interval = 1.2 # Giãn cách tối thiểu 1.2s giữa 2 tin nhắn chống Zalo khóa acc

    def _wait_rate_limit(self):
        """Giãn cách nhịp gửi tin để đảm bảo an toàn cho tài khoản Zalo."""
        elapsed = time.time() - self.last_send_time
        if elapsed < self.min_send_interval:
            time.sleep(self.min_send_interval - elapsed)
        self.last_send_time = time.time()

    def check_connection(self) -> Dict[str, Any]:
        """Kiểm tra xem Zalo daemon có đang chạy và đã đăng nhập chưa."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/auth/status")
                if res.status_code == 200:
                    return res.json()
                return {"success": False, "error": f"HTTP {res.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"Không thể kết nối tới Zalo Daemon tại {self.base_url} ({str(e)})"}

    def send_typing(self, thread_id: Optional[str] = None, is_group: bool = True) -> bool:
        """Gửi sự kiện 'đang soạn tin...' để tạo trải nghiệm tự nhiên."""
        target = thread_id or Config.DEFAULT_GROUP_NAME
        url = f"{self.base_url}/message/typing"
        payload = {"threadId": target, "isGroup": is_group}
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.post(url, json=payload)
                return res.status_code == 200
        except Exception:
            return False

    def add_reaction(self, thread_id: str, msg_id: str, reaction: str = "like", is_group: bool = True) -> bool:
        """Thả cảm xúc vào tin nhắn (heart, like, haha, wow, cry, angry)."""
        if not msg_id:
            return False
        url = f"{self.base_url}/send/reaction"
        payload = {
            "threadId": thread_id,
            "msgId": str(msg_id),
            "reaction": reaction,
            "isGroup": is_group
        }
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            print(f"[ZaloBridge] Không thả được reaction: {e}")
            return False

    def send_message(self, text: str, thread_id: Optional[str] = None, is_group: bool = True) -> bool:
        """
        Gửi tin nhắn văn bản tới nhóm hoặc cá nhân.
        Tự động chia nhỏ nếu tin nhắn vượt quá ngưỡng an toàn của Zalo (2500 ký tự).
        """
        target = thread_id or Config.DEFAULT_GROUP_NAME
        url = f"{self.base_url}/send/message"

        # Tách tin nhắn dài thành nhiều đoạn nếu cần
        max_chunk = 2500
        chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)] if len(text) > max_chunk else [text]

        overall_success = True
        for chunk in chunks:
            self._wait_rate_limit()
            payload = {
                "threadId": target,
                "isGroup": is_group,
                "text": chunk
            }
            try:
                with httpx.Client(timeout=10.0) as client:
                    res = client.post(url, json=payload)
                    if res.status_code != 200:
                        print(f"[ZaloBridge] Gửi tin thất bại HTTP {res.status_code}: {res.text}")
                        overall_success = False
            except Exception as e:
                print(f"[ZaloBridge] Lỗi khi gửi tin nhắn Zalo: {e}")
                overall_success = False

        return overall_success

    def send_image(self, image_path: str, caption: str = "", thread_id: Optional[str] = None, is_group: bool = True) -> bool:
        """Gửi ảnh kèm chú thích tới Zalo."""
        target = thread_id or Config.DEFAULT_GROUP_NAME
        url = f"{self.base_url}/send/image"
        self._wait_rate_limit()
        payload = {
            "threadId": target,
            "isGroup": is_group,
            "imagePath": os.path.abspath(image_path),
            "caption": caption
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            print(f"[ZaloBridge] Lỗi khi gửi ảnh Zalo: {e}")
            return False

    def get_recent_messages(self, thread_id: Optional[str] = None, count: int = 10) -> List[Dict[str, Any]]:
        """Lấy danh sách tin nhắn gần nhất từ nhóm gia đình."""
        target = thread_id or Config.DEFAULT_GROUP_NAME
        url = f"{self.base_url}/messages"
        params = {"threadId": target, "limit": count}
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("data", [])
                return []
        except Exception as e:
            print(f"[ZaloBridge] Lỗi lấy tin nhắn: {e}")
            return []
