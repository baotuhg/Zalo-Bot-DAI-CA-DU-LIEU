import datetime
from typing import Dict, Any, List, Optional
from database.construction_db import ConstructionDB
from core.report_parser import ConstructionReportParser
from core.excel_syncer import ConstructionExcelSyncer
from core.html_dashboard_syncer import HtmlDashboardSyncer

class DataBossBrain:
    """
    Bộ não điều hành của 'Đại ca dữ liệu' (Chief Data Officer Bot).
    Chuyên trách:
    - Tiếp nhận và xác nhận số liệu báo cáo ca/ngày công trường.
    - Phân tích tiến độ, cảnh báo các điểm nghẽn thi công.
    - Tự động đồng bộ Database, Excel sống & Web App Dashboard HTML.
    - Trả lời các lệnh điều hành (/tiendo, /baocao, /canhbao, /coc, /excel, /web).
    """

    def __init__(
        self,
        db: ConstructionDB,
        excel_syncer: ConstructionExcelSyncer,
        parser: ConstructionReportParser,
        html_syncer: Optional[HtmlDashboardSyncer] = None
    ):
        self.db = db
        self.excel_syncer = excel_syncer
        self.parser = parser
        self.html_syncer = html_syncer or HtmlDashboardSyncer()

    def process_incoming_report(self, text: str, sender_name: str = "", media_urls: Optional[List[str]] = None, project_name: str = "PMU BĂNG HẠ TẦNG OLP") -> Dict[str, Any]:
        """
        Xử lý toàn bộ chu trình nạp báo cáo từ tin nhắn:
        Bóc tách -> Lưu DB -> Cập nhật Excel -> Cập nhật Web Dashboard HTML -> Sinh phản hồi báo cáo điều hành.
        """
        # 1. Bóc tách số liệu
        parsed = self.parser.parse(text, sender_name=sender_name)

        # 2. Lưu vào SQLite DB
        report_id = self.db.save_report(parsed, project_name=project_name, media_urls=media_urls)

        # 3. Lấy dữ liệu cập nhật và ghi vào Excel sống
        summary_items = self.db.get_latest_project_summary()
        piles = self.db.get_active_piles()
        history = self.db.get_shift_history()
        excel_path = self.excel_syncer.generate_or_update(summary_items, piles, history, project_name=project_name)

        # 4. Tự động đồng bộ vào Web App Dashboard HTML (nếu có file)
        html_res = None
        if self.html_syncer and self.html_syncer.html_path.exists():
            try:
                html_res = self.html_syncer.update_from_report(parsed)
            except Exception as e:
                print(f"[DataBossBrain] Không cập nhật được HTML Dashboard: {e}")

        # 5. Sinh thông báo phản hồi sắc sảo phong cách 'Đại ca dữ liệu'
        reply_text = self._build_ingestion_reply(parsed, report_id, excel_path, html_res)

        return {
            "report_id": report_id,
            "parsed": parsed,
            "excel_path": excel_path,
            "html_path": str(self.html_syncer.html_path) if self.html_syncer else None,
            "reply_text": reply_text
        }

    def _build_ingestion_reply(self, parsed: Dict[str, Any], report_id: int, excel_path: str, html_res: Optional[Dict[str, Any]] = None) -> str:
        """Tạo tin nhắn phản hồi xác nhận nạp data kèm bảng tóm tắt tiến độ."""
        date_str = parsed.get("report_date", "")
        # Chuyển về định dạng DD/MM/YYYY cho thân thiện
        try:
            p = date_str.split("-")
            formatted_date = f"{p[2]}/{p[1]}/{p[0]}"
        except Exception:
            formatted_date = date_str

        shift = parsed.get("shift_name", "Ca ngày")
        contractor = parsed.get("contractor", "Nhà thầu")
        reporter = parsed.get("reporter_name", "Kỹ sư")

        lines = [
            f"📊 [ĐẠI CA DỮ LIỆU ĐÃ NẠP DATA #{report_id} THÀNH CÔNG!]",
            f"━━━━━━━━━━━━━━━━━━━",
            f"📅 Báo cáo: {shift} - Ngày {formatted_date}",
            f"👷 Đơn vị: {contractor} | Người báo: @{reporter}",
            f"",
            f"📈 TIẾN ĐỘ THI CÔNG CHI TIẾT:"
        ]

        # Nhóm theo category để hiển thị đẹp
        categories_dict = {}
        for it in parsed.get("items", []):
            cat = it.get("category", "Hạng mục khác")
            if cat not in categories_dict:
                categories_dict[cat] = []
            categories_dict[cat].append(it)

        for cat, items in categories_dict.items():
            lines.append(f"🔹 {cat.upper()}:")
            for it in items:
                sub = it.get("sub_item", "-")
                shift_q = int(it.get("shift_qty", 0))
                accum_q = int(it.get("accumulated_qty", 0))
                design_q = int(it.get("design_qty", 0))
                pct = it.get("completion_rate", 0)
                unit = it.get("unit", "")
                
                if design_q > 0:
                    lines.append(f"  • {sub}: Ca này {shift_q:02d} | Lũy kế: {accum_q}/{design_q} ({pct}%) {unit}")
                else:
                    lines.append(f"  • {sub}: Đang duy trì thi công liên tục")

        # Danh sách cọc đang làm
        piles = parsed.get("piles", [])
        if piles:
            lines.append(f"")
            lines.append(f"⚡ TÌNH TRẠNG TIM CỌC ĐANG TRIỂN KHAI:")
            for p in piles:
                loc = p.get("location", "")
                pid = p.get("pile_id", "")
                st = p.get("status", "")
                
                # Bổ sung cảnh báo nghiệp vụ thông minh cho từng loại trạng thái
                note = ""
                if "thổi rửa" in st.lower() or "đổ bê tông" in st.lower():
                    note = " ➔ (⚠️ Lưu ý kiểm tra độ lắng cặn đáy hố & độ sụt bê tông)"
                elif "hạ lồng" in st.lower():
                    note = " ➔ (⚠️ Lưu ý kiểm tra tim cốt, mối nối buộc/hàn & con kê)"
                elif "đang khoan" in st.lower():
                    note = " ➔ (⚙️ Theo dõi cao độ mũi khoan & địa chất)"
                    
                lines.append(f"  • [{loc}] {pid}: {st}{note}")

        lines.append(f"")
        lines.append(f"📁 Dữ liệu đã đồng bộ 3 nơi:")
        lines.append(f"1️⃣ CSDL SQLite dự án (construction_data.db)")
        lines.append(f"2️⃣ File Excel sống: {excel_path}")
        if html_res and html_res.get("html_path"):
            lines.append(f"3️⃣ Web Dashboard: {html_res['html_path']} ({html_res.get('updated_count', 0)} mục đã nạp)")
        lines.append(f"━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💡 Gõ '/tiendo' để xem lũy kế | Gõ '/canhbao' để xem điểm nghẽn.")

        return "\n".join(lines)

    def get_progress_overview(self) -> str:
        """Tổng hợp tình hình tiến độ toàn dự án hiện tại."""
        summary = self.db.get_latest_project_summary()
        if not summary:
            return "Đại ca dữ liệu thông báo: Chưa có dữ liệu báo cáo nào trong hệ thống! Vui lòng gửi báo cáo ca thi công để nạp dữ liệu."

        lines = [
            f"📋 [BẢNG TỔNG HỢP TIẾN ĐỘ DỰ ÁN MỚI NHẤT]",
            f"━━━━━━━━━━━━━━━━━━━"
        ]

        curr_cat = None
        for it in summary:
            cat = it.get("category", "")
            if cat != curr_cat:
                curr_cat = cat
                lines.append(f"\n🏗️ **{cat.upper()}:**")

            sub = it.get("sub_item", "-")
            accum = int(it.get("accumulated_qty", 0))
            design = int(it.get("design_qty", 0))
            pct = it.get("completion_rate", 0)
            unit = it.get("unit", "")

            status_icon = "🟢" if pct >= 80 else ("🟡" if pct >= 40 else "🔴")
            if design > 0:
                lines.append(f"  {status_icon} {sub}: {accum:,}/{design:,} {unit} ({pct}%)")
            else:
                lines.append(f"  ⚙️ {sub}: Đang duy trì thi công")

        lines.append(f"\n━━━━━━━━━━━━━━━━━━━")
        lines.append(f"💡 Dữ liệu được tính toán tự động bởi 'Đại ca dữ liệu'.")
        return "\n".join(lines)

    def get_active_piles_overview(self) -> str:
        """Danh sách các tim cọc đang thi công trên hiện trường."""
        piles = self.db.get_active_piles()
        if not piles:
            return "Hiện tại không có tim cọc nào đang ở trạng thái thi công dở dang."

        lines = [
            f"🚜 [CHI TIẾT TIM CỌC ĐANG THI CÔNG HIỆN TRƯỜNG]",
            f"━━━━━━━━━━━━━━━━━━━"
        ]
        for p in piles:
            lines.append(f"• [{p['location']}] **{p['pile_id']}**: {p['status']}")
            lines.append(f"  (Cập nhật ca: {p.get('shift_name')} | Đơn vị: {p.get('contractor_name')})")

        lines.append(f"━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def get_risk_and_alerts(self) -> str:
        """Phân tích các mũi thi công chậm tiến độ hoặc điểm nóng kỹ thuật."""
        summary = self.db.get_latest_project_summary()
        piles = self.db.get_active_piles()

        lines = [
            f"⚠️ [BÁO CÁO CẢNH BÁO TIẾN ĐỘ & KỸ THUẬT CÔNG TRƯỜNG]",
            f"━━━━━━━━━━━━━━━━━━━"
        ]

        # 1. Quét các hạng mục có tiến độ thấp < 30%
        low_items = [it for it in summary if it.get("design_qty", 0) > 0 and it.get("completion_rate", 0) < 30]
        if low_items:
            lines.append(f"🔴 **CÁC HẠNG MỤC CẦN ĐẨY NHANH TIẾN ĐỘ (< 30%):**")
            for it in low_items:
                lines.append(f"  • {it['category']} - {it['sub_item']}: Mới đạt {it['accumulated_qty']}/{it['design_qty']} {it['unit']} ({it['completion_rate']}%)")
            lines.append("")

        # 2. Quét các điểm nóng tim cọc
        critical_piles = [p for p in piles if any(k in p['status'].lower() for k in ["thổi rửa", "chuẩn bị đổ", "hạ lồng"])]
        if critical_piles:
            lines.append(f"⚡ **ĐIỂM NÓNG CẦN GIÁM SÁT CHẶT CHẼ NGAY TRONG CA:**")
            for p in critical_piles:
                lines.append(f"  • {p['pile_id']} ({p['location']}): {p['status']}")
                lines.append(f"    👉 Đề nghị TVGS & Kỹ sư hiện trường nghiệm thu cốt thép và kiểm tra độ sạch đáy hố trước khi cấp lệnh đổ bê tông!")
            lines.append("")

        # 3. Các hạng mục sắp về đích
        done_items = [it for it in summary if it.get("completion_rate", 0) >= 80]
        if done_items:
            lines.append(f"🟢 **HẠNG MỤC SẮP HOÀN THÀNH (>= 80%):**")
            for it in done_items:
                lines.append(f"  • {it['category']} - {it['sub_item']}: Đã đạt {it['completion_rate']}%")

        lines.append(f"━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def get_help_message(self) -> str:
        """Hướng dẫn sử dụng bot Đại ca dữ liệu."""
        return (
            f"🤖 **ĐẠI CA DỮ LIỆU - TRỢ LÝ THU THẬP & QUẢN TRỊ DỮ LIỆU CÔNG TRƯỜNG**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Tôi được thiết kế để tự động bóc tách báo cáo ca/ngày thi công và cập nhật tức thì vào CSDL & Excel sống.\n\n"
            f"📌 **CÁCH NẠP DỮ LIỆU TỰ ĐỘNG:**\n"
            f"Chỉ cần gửi tin nhắn báo cáo thi công bình thường vào nhóm Zalo (Ví dụ: 'Báo cáo thi công cuối ca đêm 26/9/2026...', kèm tỷ lệ 00/246/280, trạng thái cọc...).\n"
            f"👉 'Đại ca dữ liệu' sẽ tự động bắt dữ liệu, phân loại, tính %, lưu DB và cập nhật Excel!\n\n"
            f"🎯 **CÁC LỆNH ĐIỀU HÀNH NHANH:**\n"
            f"• `/tiendo` hoặc `/baocao` : Xem bảng tổng hợp tiến độ toàn dự án.\n"
            f"• `/coc` : Xem chi tiết các tim cọc đang thi công dở dang.\n"
            f"• `/canhbao` : Phân tích điểm nghẽn, hạng mục chậm và các tim cọc cần nghiệm thu.\n"
            f"• `/excel` : Lấy đường dẫn file Excel báo cáo tiến độ chuẩn PMU.\n"
            f"• `/help` : Xem danh sách lệnh điều hành này.\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
