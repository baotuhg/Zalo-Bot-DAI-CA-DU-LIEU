import os
import json
import re
import datetime
from typing import Dict, Any, List, Optional
from config import Config

class ClaudeEngine:
    """
    Module tích hợp Trí tuệ Nhân tạo Claude API (Anthropic).
    Tối ưu hóa riêng cho model Claude 3.5 Haiku / Claude 3 Haiku:
    - Bóc tách báo cáo công trường tự do thành JSON chuẩn WBS (Smart Extraction).
    - Trợ lý hỏi đáp thông minh (AI Q&A) dựa trên dữ liệu thực tế trong SQLite DB.
    - Phân tích rủi ro, dự báo tiến độ và sinh câu trả lời sắc sảo phong cách 'Đại Ca Dữ Liệu'.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or Config.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or Config.CLAUDE_MODEL or "claude-3-5-haiku-20241022"
        self._client = None
        self._init_client()

    def _init_client(self):
        """Khởi tạo Anthropic Client nếu có API Key hợp lệ."""
        if self.api_key and self.api_key.startswith("sk-ant-"):
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as e:
                print(f"[ClaudeEngine] Lỗi khởi tạo Anthropic Client: {e}")
                self._client = None
        else:
            self._client = None

    @property
    def is_available(self) -> bool:
        """Kiểm tra xem Claude API đã sẵn sàng hoạt động hay chưa."""
        return self._client is not None and bool(self.api_key)

    def extract_report(self, text: str, sender_name: str = "") -> Optional[Dict[str, Any]]:
        """
        Dùng Claude Haiku bóc tách báo cáo thi công tiếng Việt tự do thành cấu trúc JSON chuẩn WBS.
        Nếu không có key hoặc lỗi, trả về None để hệ thống tự động fallback sang Regex.
        """
        if not self.is_available:
            return None

        today_str = datetime.date.today().strftime("%Y-%m-%d")
        system_prompt = (
            "Bạn là trợ lý AI chuyên gia bóc tách dữ liệu báo cáo thi công công trình xây dựng (Cầu đường, Hạ tầng, Dân dụng) tại Việt Nam.\n"
            "Nhiệm vụ của bạn là đọc báo cáo hiện trường bằng tiếng Việt (kể cả viết tắt, lộn xộn) và trích xuất thành DUY NHẤT một khối JSON hợp lệ.\n"
            "Quy tắc bóc tách:\n"
            "1. Cú pháp '3 chỉ số vàng' của công trường: Ca này / Lũy kế / Tổng thiết kế (Ví dụ: 02/20/132 tương ứng shift_qty=2, accumulated_qty=20, design_qty=132).\n"
            "2. Chi tiết từng tim cọc: mã cọc (ví dụ M2-1-4, C1, T3-2...), trạng thái (đang khoan, hạ lồng thép, đổ bê tông, xong...).\n"
            "3. Vướng mắc, sự cố máy móc, thời tiết (mưa, nắng, cẩu hỏng, mất điện...).\n"
            "Cấu trúc JSON bắt buộc phải trả về:\n"
            "{\n"
            f'  "report_date": "{today_str}",\n'
            '  "shift_name": "Cuối ca đêm / Ca ngày / ...",\n'
            '  "contractor": "Tên nhà thầu hoặc Đơn vị thi công",\n'
            f'  "reporter_name": "{sender_name or "Kỹ sư"}",\n'
            '  "weather": "Nắng / Mưa / Tốt / ...",\n'
            '  "items": [\n'
            '    {\n'
            '      "category": "Cọc khoan nhồi / Đào đắp / Bê tông / Ga thoát nước / ...",\n'
            '      "sub_item": "Tên chi tiết hạng mục hoặc cọc",\n'
            '      "unit": "cọc / m3 / m / cái",\n'
            '      "shift_qty": 2.0,\n'
            '      "accumulated_qty": 20.0,\n'
            '      "design_qty": 132.0,\n'
            '      "completion_rate": 15.15\n'
            '    }\n'
            '  ],\n'
            '  "piles": [\n'
            '    {\n'
            '      "pile_id": "Mã cọc",\n'
            '      "status": "Trạng thái thi công",\n'
            '      "pile_type": "Loại cọc (nếu có)",\n'
            '      "depth_m": 0.0,\n'
            '      "notes": "Ghi chú thêm"\n'
            '    }\n'
            '  ],\n'
            '  "issues": ["Danh sách các sự cố / vướng mắc nếu có"],\n'
            '  "site_notes": "Tóm tắt ngắn gọn tình hình ca"\n'
            "}\n"
            "Chỉ trả về JSON thuần túy, không có lời dẫn hay giải thích thêm."
        )

        user_content = f"Báo cáo thi công từ {sender_name or 'hiện trường'}:\n\n{text}"

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            raw_text = response.content[0].text.strip()
            
            # Làm sạch nếu model bọc trong ```json ... ```
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
            if json_match:
                raw_text = json_match.group(1)
            else:
                raw_text = re.sub(r'^[^{\[]*', '', raw_text)
                raw_text = re.sub(r'[^}\]]*$', '', raw_text)

            parsed = json.loads(raw_text)
            return parsed
        except Exception as e:
            print(f"[ClaudeEngine] Lỗi bóc tách báo cáo bằng Claude Haiku: {e}")
            return None

    def answer_query(self, query: str, db_context: Dict[str, Any], sender_name: str = "Chỉ huy") -> str:
        """
        Trả lời câu hỏi tự nhiên của kỹ sư/chỉ huy trưởng dựa trên số liệu thực tế trong SQLite DB.
        Phong cách: 'Đại Ca Dữ Liệu' — chuyên nghiệp, quyết đoán, dẫn chứng số liệu rõ ràng.
        """
        if not self.is_available:
            return (
                "⚠️ **[CHƯA KÍCH HOẠT CLAUDE API]**\n"
                "👉 Bạn chưa điền `ANTHROPIC_API_KEY` vào file `.env`. Hãy dán key vào để kích hoạt trợ lý AI thông minh nhé!"
            )

        system_prompt = (
            "Bạn là 'Đại Ca Dữ Liệu' (Chief Data Officer Bot) — Cố vấn & Trợ lý điều hành giám sát tiến độ công trường xây dựng uy tín.\n"
            "Đặc điểm phong cách:\n"
            "- Xưng hô: 'Đại ca' hoặc 'tôi', gọi người hỏi là 'chỉ huy' hoặc 'anh em'.\n"
            "- Phong cách nói chuyện: Ngắn gọn, dứt khoát, am hiểu kỹ thuật thi công (cọc khoan nhồi, mố trụ, ca máy, K95, K98).\n"
            "- Nguyên tắc sống còn: CHỈ TRẢ LỜI DỰA TRÊN DỮ LIỆU ĐƯỢC CUNG CẤP. Không bịa số liệu. Nếu dữ liệu chưa có hoặc bằng 0, nói thẳng là chưa có báo cáo ghi nhận.\n"
            "- Định dạng: Dễ nhìn trên màn hình điện thoại Zalo, có gạch đầu dòng, in đậm các con số quan trọng, dùng icon phù hợp (🏗️, 📊, ⚡, ⚠️, ✅)."
        )

        context_summary = json.dumps(db_context, ensure_ascii=False, indent=2)
        user_content = (
            f"DỮ LIỆU CÔNG TRƯỜNG THỰC TẾ TRONG HỆ THỐNG:\n"
            f"```json\n{context_summary}\n```\n\n"
            f"Kỹ sư @{sender_name} vừa hỏi: \"{query}\"\n"
            f"Hãy trả lời câu hỏi trên thật sắc sảo, ngắn gọn và hữu ích cho công trường."
        )

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            return f"❌ Lỗi khi hỏi Claude Haiku: {e}"

    def generate_risk_analysis(self, db_context: Dict[str, Any]) -> str:
        """Sinh báo cáo nhận định & cảnh báo rủi ro tiến độ thi công cuối ngày."""
        if not self.is_available:
            return ""

        system_prompt = (
            "Bạn là 'Đại Ca Dữ Liệu' — chuyên gia phân tích rủi ro tiến độ dự án xây dựng.\n"
            "Hãy đọc dữ liệu tiến độ công trường được cấp và đưa ra bản BÁO CÁO NHẬN ĐỊNH ĐIỀU HÀNH:\n"
            "1. Đánh giá chung: Mũi nào làm tốt, mũi nào bị chậm.\n"
            "2. Điểm nghẽn rủi ro: Cọc bị sự cố, máy móc hư hỏng, mặt bằng hoặc thời tiết.\n"
            "3. Lời khuyên chỉ đạo: Đề xuất hành động cụ thể cho ca tiếp theo.\n"
            "Trình bày ngắn gọn, sắc sảo, phù hợp gửi vào nhóm chat Zalo."
        )

        context_summary = json.dumps(db_context, ensure_ascii=False)
        user_content = f"Dữ liệu công trường:\n{context_summary}\nHãy lập báo cáo nhận định điều hành."

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=800,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"[ClaudeEngine] Lỗi phân tích rủi ro: {e}")
            return ""
