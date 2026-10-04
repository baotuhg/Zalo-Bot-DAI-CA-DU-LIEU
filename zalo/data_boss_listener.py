import time
import httpx
from typing import Dict, Any, List, Optional
from config import Config
from core.data_boss_brain import DataBossBrain
from zalo.bridge import ZaloBridge

class DataBossListener:
    """
    Module Lắng nghe và Điều phối Zalo của Bot 'Đại ca dữ liệu'.
    Tự động thu thập báo cáo thi công từ các nhóm Zalo dự án,
    phân tích số liệu, cập nhật Database/Excel và phản hồi điều hành.
    """

    def __init__(self, brain: DataBossBrain, bridge: ZaloBridge, target_group_keywords: Optional[List[str]] = None):
        self.brain = brain
        self.bridge = bridge
        self.is_running = False
        # Các từ khóa nhận diện nhóm công trường cần giám sát
        self.target_group_keywords = target_group_keywords or [
            "PMU", "BĂNG HẠ TẦNG", "OLP", "307", "CẦU", "THI CÔNG", "TIẾN ĐỘ", "KCS", "HỒ SƠ"
        ]
        self.processed_msg_ids = set()

    def handle_message(self, msg: Dict[str, Any], project_name: Optional[str] = None):
        """Xử lý từng tin nhắn đến từ Zalo."""
        msg_id = msg.get("msgId")
        if msg_id and str(msg_id) in self.processed_msg_ids:
            return
        if msg_id:
            self.processed_msg_ids.add(str(msg_id))

        thread_id = msg.get("threadId") or Config.DEFAULT_GROUP_NAME
        sender_name = msg.get("senderName", "Kỹ sư")
        content = (msg.get("content") or "").strip()
        media_urls = msg.get("mediaUrls") or []
        is_from_bot = msg.get("isFromBot", False)

        resolved_project = project_name or msg.get("projectName") or msg.get("threadName") or "Dự án Công trường"

        if is_from_bot:
            return

        content_lower = content.lower()

        # 1. Kiểm tra xem có phải lệnh điều hành nhanh không
        if content_lower in ["/theodoi", "theo dõi", "/kichhoat", "kích hoạt", "@đại ca theo dõi"]:
            self.bridge.send_typing(thread_id)
            if msg_id:
                self.bridge.add_reaction(thread_id, str(msg_id), reaction="heart")
            reply = (
                f"✅ **[ĐÃ KÍCH HOẠT GIÁM SÁT NHÓM NÀY]**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Đại ca dữ liệu đã nhận lệnh từ @{sender_name}!\n"
                f"Từ bây giờ, mọi báo cáo ca thi công và ảnh hiện trường gửi vào nhóm sẽ được tự động bóc tách, lưu trữ và đồng bộ tức thì lên Web Dashboard:\n"
                f"👉 https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/\n\n"
                f"Anh em kỹ sư cứ bắn báo cáo ca bình thường nhé! 🚀"
            )
            self.bridge.send_message(reply, thread_id=thread_id)
            return

        if content_lower in ["/help", "help", "hướng dẫn", "/huongdan"]:
            self.bridge.send_typing(thread_id)
            reply = self.brain.get_help_message()
            self.bridge.send_message(reply, thread_id=thread_id)
            return

        if content_lower in ["/tiendo", "tiến độ", "/baocao", "báo cáo"]:
            self.bridge.send_typing(thread_id)
            reply = self.brain.get_progress_overview()
            self.bridge.send_message(reply, thread_id=thread_id)
            return

        if content_lower in ["/coc", "tim cọc", "cọc", "/piles"]:
            self.bridge.send_typing(thread_id)
            reply = self.brain.get_active_piles_overview()
            self.bridge.send_message(reply, thread_id=thread_id)
            return

        if content_lower in ["/canhbao", "cảnh báo", "/alert"]:
            self.bridge.send_typing(thread_id)
            reply = self.brain.get_risk_and_alerts()
            self.bridge.send_message(reply, thread_id=thread_id)
            return

        if content_lower in ["/excel", "/xuat_excel", "xuất excel", "file excel"]:
            self.bridge.send_typing(thread_id)
            reply = (
                f"📊 **BẢNG TÍNH EXCEL TIẾN ĐỘ THI CÔNG ĐÃ ĐƯỢC ĐỒNG BỘ MỚI NHẤT!**\n"
                f"📁 Đường dẫn lưu trữ trên máy chủ:\n"
                f"`{self.brain.excel_syncer.excel_path}`\n\n"
                f"👉 File gồm 3 Sheet chuẩn PMU: 'Tổng hợp Tiến độ' (có công thức sống), 'Theo dõi Tim Cọc', và 'Nhật trình Ca thi công'."
            )
            self.bridge.send_message(reply, thread_id=thread_id)
            return

        # 2. Kiểm tra xem có phải báo cáo thi công công trường hay không
        if self.brain.parser.is_construction_report(content):
            print(f"[Đại ca dữ liệu] Phát hiện báo cáo thi công từ {sender_name}! Tiến hành bóc tách...")
            
            # Thả cảm xúc 'like' hoặc 'heart' ngay để người gửi yên tâm
            if msg_id:
                self.bridge.add_reaction(thread_id, str(msg_id), reaction="like")

            # Gửi hiệu ứng 'đang soạn tin...'
            self.bridge.send_typing(thread_id)

            # Thực thi chu trình nạp dữ liệu
            result = self.brain.process_incoming_report(
                text=content,
                sender_name=sender_name,
                media_urls=media_urls,
                project_name=resolved_project
            )

            # Gửi phản hồi xác nhận
            self.bridge.send_message(result["reply_text"], thread_id=thread_id)
            print(f"[Đại ca dữ liệu] Đã nạp thành công báo cáo #{result['report_id']} và gửi phản hồi!")
            return

        # 3. Nếu tin nhắn có nhắc tên "Đại ca dữ liệu" hoặc "đại ca"
        if any(k in content_lower for k in ["đại ca dữ liệu", "đại ca", "bot dữ liệu"]):
            self.bridge.send_typing(thread_id)
            reply = (
                f"Chào anh em! 'Đại ca dữ liệu' có mặt ở đây để phục vụ dự án.\n"
                f"Anh em cứ bắn báo cáo ca/ngày thi công vào nhóm, việc tổng hợp số liệu, cập nhật Database và xuất Excel để tôi lo!\n"
                f"Gõ `/help` để xem hướng dẫn lệnh điều hành nhé."
            )
            self.bridge.send_message(reply, thread_id=thread_id)
            return

    def poll_messages(self, thread_id: Optional[str] = None):
        """Quét và xử lý tin nhắn mới từ Zalo."""
        messages = self.bridge.get_recent_messages(thread_id=thread_id, count=10)
        for msg in reversed(messages):
            self.handle_message(msg)
