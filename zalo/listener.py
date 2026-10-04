import time
import httpx
from typing import Dict, Any, List
from config import Config
from database.db_manager import DBManager
from core.tutor_brain import TutorBrain
from core.smart_reaction import pick_smart_reaction
from core.zalo_math import format_zalo_math
from zalo.bridge import ZaloBridge

class ZaloListener:
    def __init__(self, db: DBManager, brain: TutorBrain, bridge: ZaloBridge):
        self.db = db
        self.brain = brain
        self.bridge = bridge
        self.is_running = False

    def handle_message(self, msg: Dict[str, Any]):
        msg_id = msg.get("msgId")
        thread_id = msg.get("threadId") or Config.DEFAULT_GROUP_NAME
        sender_name = msg.get("senderName", "")
        content = (msg.get("content") or "").strip()
        media_urls = msg.get("mediaUrls") or []
        is_from_bot = msg.get("isFromBot", False)

        # Bỏ qua tin nhắn do chính bot gửi
        if is_from_bot:
            return

        print(f"[Listener] Nhận tin nhắn từ {sender_name}: {content} (Ảnh: {len(media_urls)})")

        # 1. Thả Reaction thông minh ngay khi nhận tin (học từ 2anh-zalo-bot)
        if msg_id:
            reaction = pick_smart_reaction(content, is_photo=bool(media_urls))
            self.bridge.add_reaction(thread_id, msg_id, reaction=reaction)

        # 2. Gửi hiệu ứng 'đang soạn tin...'
        self.bridge.send_typing(thread_id)

        reply = ""

        # 3. Phân loại và xử lý nội dung
        # TH 1: Có ảnh gửi kèm (ảnh bài tập hoặc đề bài)
        if media_urls:
            img_url = media_urls[0]
            if "hướng dẫn" in content.lower() or "giải" in content.lower() or "câu" in content.lower():
                reply = (
                    f"@{sender_name} ơi, Jerryhg đã nhận được ảnh bài tập.\n"
                    f"Lưu ý nguyên tắc: Jerryhg không giải hộ để con chép. Con cho Jerryhg biết:\n"
                    f"1. Con muốn hỏi chính xác câu nào?\n"
                    f"2. Con đã làm được đến bước nào rồi, hay đang vướng ở công thức nào?\n"
                    f"Hãy nhắn rõ để Jerryhg hướng dẫn con tự tư duy nhé!"
                )
            else:
                reply = (
                    f"@{sender_name} ơi, ảnh này là đề bài hay bài con đã làm?\n"
                    f"• Nếu nộp bài: Con phải chụp rõ chữ viết tay bài con đã làm đầy đủ các bước.\n"
                    f"• Nếu hỏi bài: Nhắn kèm 'Jerryhg ơi, hướng dẫn con câu...' nhé!"
                )

        # TH 2: Xử lý lệnh hoặc hỏi về Thời khóa biểu
        elif any(k in content.lower() for k in ["/tkb", "thời khóa biểu", "mai học gì", "lịch học"]):
            tomorrow = self.db.get_tomorrow_schedule(Config.DEFAULT_STUDENT_NAME)
            day_name = tomorrow["day_name"]
            subjects = ", ".join(tomorrow["subjects"]) if tomorrow["subjects"] else "Không có môn"
            reply = (
                f"📅 **Thời khóa biểu ngày mai ({day_name}) của @{Config.DEFAULT_STUDENT_NAME}:**\n"
                f"👉 Các môn: **{subjects}**\n\n"
                f"Con nhớ hoàn thành hết bài tập của các môn này và soạn sách vở ngăn nắp trước khi đi ngủ!"
            )

        # TH 3: Xử lý lệnh kiểm tra bài tập
        elif any(k in content.lower() for k in ["/baitap", "bài tập", "cần làm gì"]):
            today_str = time.strftime("%Y-%m-%d")
            pending = self.db.list_homework(Config.DEFAULT_STUDENT_NAME, today_str, status="pending")
            if not pending:
                reply = f"✅ Hiện tại không có bài tập nào tồn đọng trong danh sách của @{Config.DEFAULT_STUDENT_NAME}. Con chủ động ôn lại bài nhé!"
            else:
                tasks_text = "\n".join([f"• [{t['subject']}] {t['title']} (Hạn: {t['due_time']})" for t in pending])
                reply = f"📋 **Danh sách bài tập cần hoàn thành:**\n{tasks_text}\n\nCon làm xong nhớ chụp ảnh nộp ngay cho Jerryhg!"

        # TH 4: Phụ huynh nhắn xác nhận tổng kết ("được rồi", "đã xem", "ok")
        elif content.lower() in ["được rồi", "da xem", "đã xem", "ok", "oke"]:
            reply = f"Dạ, Jerryhg đã ghi nhận xác nhận của bố mẹ. Chúc cả nhà ngủ ngon! 🙏"

        # TH 5: Học sinh hoặc phụ huynh trò chuyện / hỏi bài bằng văn bản
        elif any(k in content.lower() for k in ["jerryhg", "jerryhg ơi", "thầy ơi", "thư ơi", "cô ơi"]):
            if self.brain.is_ready():
                reply = self.brain.guide_exercise(content, student_name=sender_name)
            else:
                reply = f"Jerryhg chào {sender_name}! Con đang cần Jerryhg hướng dẫn bài nào? Con gửi đề bài và cho Jerryhg biết con vướng ở bước nào nhé!"

        # 4. Gửi phản hồi (đã qua bộ chuyển đổi công thức Toán Zalo Math)
        if reply:
            formatted_reply = format_zalo_math(reply)
            self.bridge.send_message(formatted_reply, thread_id=thread_id)

        # 5. Đánh dấu đã đọc
        if msg_id:
            try:
                with httpx.Client(timeout=3.0) as client:
                    client.post(f"{self.bridge.base_url}/messages/{msg_id}/read")
            except Exception:
                pass

    def start_polling(self, interval_seconds: float = 3.0):
        """Vòng lặp lắng nghe tin nhắn chưa đọc từ Zalo daemon."""
        self.is_running = True
        print(f"[Listener] Bắt đầu lắng nghe tin nhắn Zalo (chu kỳ {interval_seconds}s)...")
        while self.is_running:
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.get(f"{self.bridge.base_url}/messages/unread")
                    if res.status_code == 200:
                        data = res.json()
                        messages = data.get("data", [])
                        for msg in messages:
                            self.handle_message(msg)
            except Exception:
                pass
            time.sleep(interval_seconds)

    def stop(self):
        self.is_running = False
