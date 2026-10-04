import json
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

class HtmlDashboardSyncer:
    """
    Bộ đồng bộ Dữ liệu tự động vào Web App Dashboard HTML (ví dụ: 'Bảng điều hành TĐ3').
    Cơ chế hoạt động:
    1. Đọc file HTML đơn trang (Single-Page App).
    2. Trích xuất khối JSON nằm trong thẻ <script id="td3-data" type="application/json">.
    3. Hợp nhất (merge) dữ liệu thi công mới nhất từ Zalo vào các bảng:
       - items (Hạng mục ưu tiên & tiến độ)
       - yards (Bãi đúc ga, quân số, sản lượng ga)
       - daily (Nhật ký ngày: thời tiết, móng trụ, CNCH, cống, ghi chú)
       - issues (Vướng mắc phát sinh trên hiện trường)
       - orders (Đơn ga theo khu)
    4. Ghi đè lại nội dung JSON vào HTML với timestamp ISO mới nhất.
    """

    def __init__(self, html_path: Optional[Path] = None):
        if html_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            self.html_path = base_dir / "data" / "Bang_dieu_hanh_TD3.html"
        else:
            self.html_path = Path(html_path)

    def read_store(self) -> Dict[str, Any]:
        """Đọc và giải mã khối dữ liệu JSON từ file HTML."""
        if not self.html_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file HTML tại: {self.html_path}")

        content = self.html_path.read_text(encoding="utf-8")
        match = re.search(r'<script id="td3-data" type="application/json">(.*?)</script>', content, re.DOTALL)
        if not match:
            raise ValueError("Không tìm thấy thẻ <script id=\"td3-data\" type=\"application/json\"> trong file HTML!")

        raw_json = match.group(1).strip()
        return json.loads(raw_json)

    def write_store(self, store_data: Dict[str, Any]) -> str:
        """Cập nhật dữ liệu JSON mới vào file HTML."""
        content = self.html_path.read_text(encoding="utf-8")
        tag_marker = '<script id="td3-data" type="application/json">'
        start_idx = content.find(tag_marker)
        if start_idx == -1:
            raise ValueError("Không tìm thấy thẻ script dữ liệu để cập nhật!")

        end_tag = '</script>'
        close_idx = content.find(end_tag, start_idx)
        if close_idx == -1:
            raise ValueError("Không tìm thấy thẻ đóng </script>!")

        store_data["savedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        new_json_str = json.dumps(store_data, ensure_ascii=False, separators=(',', ':'))

        updated_html = content[:start_idx + len(tag_marker)] + new_json_str + content[close_idx:]
        self.html_path.write_text(updated_html, encoding="utf-8")

        # Đồng bộ luôn ra index.html ở thư mục gốc (phục vụ GitHub Pages)
        root_index = self.html_path.parent.parent / "index.html"
        if root_index.exists() and root_index != self.html_path:
            try:
                root_index.write_text(updated_html, encoding="utf-8")
            except Exception:
                pass

        return str(self.html_path)

    def update_from_report(self, report_data: Dict[str, Any], auto_git_push: bool = False) -> Dict[str, Any]:
        """
        Nạp dữ liệu từ báo cáo thi công của 'Đại ca dữ liệu' vào cấu trúc Dashboard HTML:
        - Tự động map các chỉ số móng, cọc, cống, bãi đúc ga vào bảng 'items', 'daily', 'yards'.
        """
        store = self.read_store()
        data = store.get("data", {})
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        today_iso = report_data.get("report_date", datetime.date.today().strftime("%Y-%m-%d"))

        updated_summary = []

        # 1. Cập nhật hoặc Thêm mới vào Nhật ký ngày ('daily')
        daily_list = data.setdefault("daily", [])
        daily_entry = next((d for d in daily_list if d.get("date") == today_iso), None)
        if not daily_entry:
            daily_entry = {
                "_id": today_iso,
                "date": today_iso,
                "weather": "Nắng tốt",
                "_ts": now_ts
            }
            daily_list.append(daily_entry)

        # Trích xuất các số liệu từ report_data nạp vào daily_entry
        for it in report_data.get("items", []):
            cat_name = it.get("category", "")
            sub_name = it.get("sub_item", "")
            accum = it.get("accumulated_qty", 0)
            design = it.get("design_qty", 0)

            # Map móng trụ / cọc khoan nhồi
            if "cọc khoan nhồi" in cat_name.lower():
                daily_entry["poleDone"] = int(accum)
                daily_entry["poleTotal"] = int(design) if design > 0 else 25
                daily_entry["_ts"] = now_ts

            # Map bãi ga / cống
            if "ga" in cat_name.lower() or "bãi đúc" in cat_name.lower():
                daily_entry["gaOutput"] = int(it.get("shift_qty", 0))
                daily_entry["_ts"] = now_ts

        # Cập nhật ghi chú tiến độ ngày
        notes = []
        for p in report_data.get("piles", []):
            notes.append(f"{p.get('pile_id')}: {p.get('status')}")
        if notes:
            daily_entry["note"] = f"Báo cáo ca {report_data.get('shift_name')}: " + "; ".join(notes)
            daily_entry["_ts"] = now_ts

        # 2. Cập nhật hoặc Thêm vào Hạng mục ưu tiên ('items')
        items_list = data.setdefault("items", [])
        for it in report_data.get("items", []):
            sub = it.get("sub_item", "")
            if not sub or sub == "-":
                continue
            item_id = f"item-{sub.lower().replace(' ', '-').replace('&', 'va')[:25]}"
            existing_item = next((x for x in items_list if x.get("_id") == item_id or sub in x.get("name", "")), None)
            
            shift_q = it.get("shift_qty", 0)
            accum_q = it.get("accumulated_qty", 0)
            design_q = it.get("design_qty", 0)
            pct = it.get("completion_rate", 0)
            unit = it.get("unit", "")

            progress_str = f"Lũy kế {int(accum_q)}/{int(design_q)} {unit} ({pct}%)" if design_q > 0 else f"Ca này {int(shift_q)} {unit}"

            if existing_item:
                existing_item["progress"] = progress_str
                existing_item["status"] = "Hoàn thành" if pct >= 100 else ("Đang làm" if pct > 0 else "Chưa bắt đầu")
                existing_item["updated"] = today_iso
                existing_item["_ts"] = now_ts
                updated_summary.append(f"Cập nhật: {existing_item['name']} -> {progress_str}")
            else:
                new_item = {
                    "_id": item_id,
                    "pri": 3,
                    "status": "Đang làm" if pct > 0 else "Chưa bắt đầu",
                    "name": f"{it.get('category')} – {sub}",
                    "detail": f"Đơn vị thi công: {report_data.get('contractor')}",
                    "owner": report_data.get("reporter_name", "Kỹ sư"),
                    "deadline": "",
                    "deadlineText": "",
                    "progress": progress_str,
                    "next": "",
                    "updated": today_iso,
                    "_ts": now_ts
                }
                items_list.append(new_item)
                updated_summary.append(f"Thêm mới: {new_item['name']} -> {progress_str}")

        # 3. Ghi đè vào file HTML
        self.write_store(store)

        # 4. Tự động Git commit & push lên GitHub nếu được bật
        git_pushed = False
        if auto_git_push:
            try:
                from sync_github import auto_push_to_github
                git_pushed = auto_push_to_github(f"Auto-update: {report_data.get('shift_name')} {report_data.get('report_date')}")
            except Exception as e:
                print(f"[HtmlDashboardSyncer] Không push được lên git: {e}")

        return {
            "html_path": str(self.html_path),
            "updated_count": len(updated_summary),
            "updated_summary": updated_summary,
            "git_pushed": git_pushed
        }
