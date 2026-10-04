import os
import io
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
from PIL import Image
import httpx
from config import Config
from core.prompts import (
    STRICT_TUTOR_SYSTEM_PROMPT,
    SOCRATIC_HINT_PROMPT,
    HOMEWORK_CHECK_PROMPT
)
from core.zalo_math import format_zalo_math

class TutorBrain:
    def __init__(self):
        self.provider = Config.AI_PROVIDER
        self.gemini_client = None
        
        if self.provider == "gemini":
            api_key = Config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
            if api_key:
                try:
                    from google import genai
                    self.gemini_client = genai.Client(api_key=api_key)
                except Exception as e:
                    print(f"[TutorBrain] Lỗi khởi tạo Gemini client: {e}")

    def is_ready(self) -> bool:
        if self.provider == "gemini":
            return bool(self.gemini_client)
        elif self.provider in ("lmstudio", "openai"):
            return True
        return False

    def _call_gemini(self, prompt: str, image_path: Optional[str] = None, image_bytes: Optional[bytes] = None) -> str:
        """Gọi Gemini API qua google-genai SDK mới nhất."""
        if not self.gemini_client:
            return "[Thông báo] Chưa cấu hình GEMINI_API_KEY trong file .env. Bố mẹ vui lòng điền API Key để kích hoạt cô giáo nhé!"

        contents = []
        if image_path and Path(image_path).exists():
            img = Image.open(image_path)
            contents.append(img)
        elif image_bytes:
            img = Image.open(io.BytesIO(image_bytes))
            contents.append(img)

        contents.append(prompt)

        try:
            response = self.gemini_client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=contents,
                config={
                    "system_instruction": STRICT_TUTOR_SYSTEM_PROMPT,
                    "temperature": 0.3, # Giữ tính nhất quán, chuẩn mực sư phạm
                }
            )
            return response.text.strip()
        except Exception as e:
            return f"[Gia sư Jerryhg] Jerryhg đang gặp trục trặc khi kết nối mạng ({str(e)}). Con chờ một lát rồi hỏi lại nhé!"

    def _call_lmstudio_or_openai(self, prompt: str, image_bytes: Optional[bytes] = None) -> str:
        """Gọi LM Studio hoặc OpenAI-compatible endpoint."""
        url = f"{Config.LM_STUDIO_BASE_URL.rstrip('/')}/chat/completions"
        messages = [
            {"role": "system", "content": STRICT_TUTOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": Config.LM_STUDIO_MODEL,
            "messages": messages,
            "temperature": 0.3
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"[Gia sư Jerryhg] Không kết nối được với LM Studio ({str(e)})."

    def generate_response(self, prompt: str, image_path: Optional[str] = None, image_bytes: Optional[bytes] = None) -> str:
        if self.provider == "gemini":
            raw = self._call_gemini(prompt, image_path, image_bytes)
        else:
            raw = self._call_lmstudio_or_openai(prompt, image_bytes)
        return format_zalo_math(raw)

    # --- Nghiệp vụ Gia Sư Nghiêm Khắc ---

    def guide_exercise(self, user_query: str, student_name: str = Config.DEFAULT_STUDENT_NAME, image_path: Optional[str] = None) -> str:
        """
        Hướng dẫn giải bài tập theo phương pháp Socratic.
        Tuyệt đối không giải hộ, chỉ đặt câu hỏi gợi mở hoặc nhắc lại công thức.
        """
        prompt = SOCRATIC_HINT_PROMPT.format(user_query=f"Học sinh {student_name} hỏi: {user_query}")
        return self.generate_response(prompt, image_path=image_path)

    def review_homework(self, image_path: str, student_name: str = Config.DEFAULT_STUDENT_NAME, subject: str = "") -> str:
        """
        Soi xét bài tập con đã làm qua ảnh chụp.
        Kiểm tra tính cẩu thả, đề bài trắng, hoặc chấm từng bước giải.
        """
        prompt = HOMEWORK_CHECK_PROMPT.format(student_name=student_name)
        if subject:
            prompt += f"\nMôn học: {subject}"
        return self.generate_response(prompt, image_path=image_path)

    def create_bag_packing_reminder(self, tomorrow_data: Dict[str, Any], student_name: str = Config.DEFAULT_STUDENT_NAME) -> str:
        """Tạo tin nhắn 21h30 nhắc soạn sách vở theo TKB ngày mai."""
        day_name = tomorrow_data.get("day_name", "")
        subjects = tomorrow_data.get("subjects", [])
        subjects_str = ", ".join(subjects) if subjects else "Không có lịch học cố định"

        prompt = f"""
Hãy soạn 1 tin nhắn vào lúc 21h30 tối gửi vào nhóm gia đình gửi tới @{student_name}:
- Ngày mai là {day_name}, thời khóa biểu gồm các môn: {subjects_str}.
- Yêu cầu học sinh dọn bàn học, kiểm tra toàn bộ bài tập của các môn ngày mai và soạn đúng sách vở, dụng cụ (thước, compa, máy tính nếu có môn Toán/KHTN).
- Giọng văn: Jerryhg - Gia sư nghiêm khắc, dứt khoát, rèn luyện tính tự giác, không để sáng mai vội vàng quên sách vở.
"""
        return self.generate_response(prompt)

    def create_parent_report(self, summary_data: Dict[str, Any]) -> str:
        """Tạo báo cáo tổng kết 23h00 gửi phụ huynh."""
        student_name = summary_data.get("student_name", Config.DEFAULT_STUDENT_NAME)
        date_str = summary_data.get("date", "")
        completed_count = summary_data.get("completed_count", 0)
        pending_count = summary_data.get("pending_count", 0)
        
        prompt = f"""
Hãy soạn báo cáo tổng kết ngày gửi vào nhóm gia đình lúc 23h00:
- Ngày: {date_str}
- Học sinh: @{student_name}
- Số bài đã hoàn thành: {completed_count} việc
- Số bài còn nợ / chưa nộp: {pending_count} việc
- Tác phong: Nghiêm túc, khách quan, báo cáo rõ ràng để bố mẹ kiểm tra thực tế. Mời bố mẹ nhắn xác nhận.
"""
        return self.generate_response(prompt)
