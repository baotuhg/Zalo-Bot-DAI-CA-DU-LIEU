import re
import datetime
from typing import Dict, Any, List, Optional

class ConstructionReportParser:
    """
    Bộ bóc tách chuyên sâu dữ liệu Báo cáo thi công công trường (Civil & Infrastructure Site Reports).
    Đặc thù ngành xây dựng Việt Nam:
    - Báo cáo ca/ngày: 'cuối ca đêm 26/9/2026', 'ca ngày 27/09/2026'
    - Nhà thầu: 'Nhà thầu SGC Cầu 5B', 'Đơn vị thi công...'
    - Cú pháp 3 chỉ số vàng: 'Hôm nay / Lũy kế / Thiết kế' (Ví dụ: 00/246/280, 02/20/132, 00/14/106)
    - Chi tiết tim cọc & trạng thái thi công: 'Cọc M2-1-4: đang khoan', 'Cọc M2-3-6: Hạ ống thổi rửa chuẩn bị đổ bê tông'
    """

    def __init__(self):
        # Regex tìm ngày và ca
        self.shift_date_pattern = re.compile(
            r'(?:Báo cáo thi công|Báo cáo tiến độ|Báo cáo ca)\s+([^\d\n]+?)\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
            re.IGNORECASE
        )
        # Regex tìm nhà thầu
        self.contractor_pattern = re.compile(
            r'(?:\*|\-)?\s*(?:Nhà thầu|Đơn vị thi công|Nhà thầu thi công)\s*[:\-]?\s*([^\n\r]+)',
            re.IGNORECASE
        )
        # Regex tìm 3 chỉ số: shift / accumulated / total (hôm nay / lũy kế / thiết kế)
        self.ratio_pattern = re.compile(r'(\d+)\s*\/\s*(\d+)\s*\/\s*(\d+)')
        
        # Regex tìm tim cọc và trạng thái thi công (bắt đầu bằng dấu +, -, * và có chữ Cọc/Tim hoặc mã cọc)
        self.pile_status_pattern = re.compile(
            r'^\+\s*(?:Cọc|Tim)?\s*([A-Za-z0-9\-\_]+)\s*[:\-]?\s*(.+)$',
            re.IGNORECASE
        )

    def is_construction_report(self, text: str) -> bool:
        """Kiểm tra xem văn bản có phải là báo cáo thi công công trường hay không."""
        if not text:
            return False
        text_lower = text.lower()
        keywords = [
            "báo cáo thi công", "báo cáo ca", "báo cáo tiến độ",
            "mố m", "trụ t", "cọc khoan nhồi", "casing", "sàn đạo", "ép cừ", "lồng thép",
            "đang khoan", "thổi rửa", "hạ lồng thép", "đổ bê tông"
        ]
        matched_kw = sum(1 for kw in keywords if kw in text_lower)
        has_ratio = bool(self.ratio_pattern.search(text))
        return matched_kw >= 2 or (matched_kw >= 1 and has_ratio)

    def parse(self, text: str, sender_name: str = "") -> Dict[str, Any]:
        """
        Bóc tách toàn diện báo cáo thi công thành cấu trúc dữ liệu chuẩn.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 1. Trích xuất ca và ngày
        shift_name = "Ca ngày"
        report_date = datetime.date.today().strftime("%Y-%m-%d")
        
        shift_match = self.shift_date_pattern.search(text)
        if shift_match:
            raw_shift = shift_match.group(1).strip(" :,-")
            shift_name = raw_shift.title() if raw_shift else "Ca ngày"
            raw_date = shift_match.group(2).strip()
            try:
                parts = re.split(r'[\/\-\.]', raw_date)
                if len(parts) == 3:
                    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                    report_date = f"{y:04d}-{m:02d}-{d:02d}"
            except Exception:
                pass
        else:
            date_match = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', text)
            if date_match:
                parts = re.split(r'[\/\-\.]', date_match.group(1))
                if len(parts) == 3:
                    d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                    report_date = f"{y:04d}-{m:02d}-{d:02d}"
            if "đêm" in text.lower():
                shift_name = "Ca đêm"

        # 2. Trích xuất Nhà thầu
        contractor = "Nhà thầu SGC Cầu 5B" if "SGC" in text else "Nhà thầu Dự án"
        cont_match = self.contractor_pattern.search(text)
        if cont_match:
            contractor = cont_match.group(1).strip(" :*-")

        # 3. Phân tách từng Section đánh số: 1., 2., 3., 4...
        sections = []
        current_section = None
        current_lines = []
        section_start_pattern = re.compile(r'^(\d+)[\.\)]\s*(.+)$')

        for line in lines:
            sec_m = section_start_pattern.match(line)
            if sec_m:
                if current_section:
                    sections.append((current_section, current_lines))
                current_section = sec_m.group(2).strip(" :")
                current_lines = []
            elif current_section is not None:
                current_lines.append(line)

        if current_section:
            sections.append((current_section, current_lines))

        # 4. Trích xuất chi tiết từng hạng mục công việc
        items: List[Dict[str, Any]] = []
        piles: List[Dict[str, Any]] = []

        for sec_name, sec_lines in sections:
            # Nếu section không có dòng con nào (Ví dụ "2. Gia công lồng thép điển hình")
            if not sec_lines:
                items.append({
                    "category": sec_name,
                    "sub_item": "-",
                    "unit": "Hạng mục",
                    "shift_qty": 0.0,
                    "accumulated_qty": 0.0,
                    "design_qty": 0.0,
                    "completion_rate": 0.0,
                    "status_note": "Đang duy trì thi công liên tục"
                })
                continue

            current_sub_loc = sec_name

            for s_line in sec_lines:
                # 4.1. Kiểm tra xem có phải dòng chi tiết tim cọc: "+ Cọc M2-1-4: đang khoan"
                pile_m = self.pile_status_pattern.match(s_line)
                if pile_m:
                    pile_code = pile_m.group(1).strip()
                    pile_st = pile_m.group(2).strip(" :")
                    full_code = f"Cọc {pile_code}" if not pile_code.lower().startswith("cọc") else pile_code
                    piles.append({
                        "category": sec_name,
                        "location": current_sub_loc,
                        "pile_id": full_code,
                        "status": pile_st
                    })
                    continue

                # 4.2. Kiểm tra xem có tỷ lệ 3 số (Ca / Lũy kế / Tổng TK)
                ratio_m = self.ratio_pattern.search(s_line)
                if ratio_m:
                    shift_val = float(ratio_m.group(1))
                    accum_val = float(ratio_m.group(2))
                    total_val = float(ratio_m.group(3))
                    pct = round((accum_val / total_val * 100), 1) if total_val > 0 else 0.0

                    # Tách tên cấu kiện/vị trí trước tỷ lệ
                    sub_title = s_line[:ratio_m.start()].strip(" -+*:\t")
                    if not sub_title:
                        # Đây là dòng tổng của section (như "4. Thi công cọc khoan nhồi :\n00/14/106")
                        sub_title = "Tổng thể hạng mục"
                    else:
                        current_sub_loc = sub_title # Cập nhật mố hiện tại cho các cọc bên dưới

                    items.append({
                        "category": sec_name,
                        "sub_item": sub_title,
                        "unit": self._guess_unit(sec_name, sub_title),
                        "shift_qty": shift_val,
                        "accumulated_qty": accum_val,
                        "design_qty": total_val,
                        "completion_rate": pct,
                        "status_note": "Bình thường"
                    })
                else:
                    # Dòng text thuần túy
                    clean_line = s_line.strip(" -+*:\t")
                    if clean_line:
                        current_sub_loc = clean_line

        return {
            "report_date": report_date,
            "shift_name": shift_name,
            "contractor": contractor,
            "reporter_name": sender_name or "Kỹ sư hiện trường",
            "raw_text": text,
            "items": items,
            "piles": piles,
            "total_items_count": len(items),
            "piles_in_progress_count": len(piles)
        }

    def _guess_unit(self, category: str, sub_item: str = "") -> str:
        """Tự động suy luận đơn vị tính chuẩn ngành Xây dựng theo danh mục."""
        combined = f"{category} {sub_item}".lower()
        if "cừ" in combined or "larsen" in combined:
            return "Cây"
        if "cọc casing" in combined:
            return "Cọc"
        if "tấm sàn" in combined:
            return "Tấm"
        if "cọc khoan nhồi" in combined or "cọc" in combined:
            return "Cọc"
        if "bê tông" in combined:
            return "m³"
        if "thép" in combined:
            return "Tấn"
        if "đào" in combined or "đắp" in combined:
            return "m³"
        return "Cấu kiện"
