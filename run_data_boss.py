import time
import sys
from pathlib import Path
from config import Config
from database.construction_db import ConstructionDB
from core.report_parser import ConstructionReportParser
from core.excel_syncer import ConstructionExcelSyncer
from core.data_boss_brain import DataBossBrain
from zalo.bridge import ZaloBridge
from zalo.data_boss_listener import DataBossListener

def main():
    print("=" * 65)
    print(" 🤖 KHỞI ĐỘNG BOT 'ĐẠI CA DỮ LIỆU' - TRỢ LÝ GIÁM SÁT DỰ ÁN ZALO")
    print("=" * 65)

    bridge = ZaloBridge()
    conn_status = bridge.check_connection()
    if not conn_status.get("authenticated", False):
        print(f"[CẢNH BÁO] Chưa kết nối được Zalo Daemon tại {bridge.base_url}")
        print(f"Chi tiết: {conn_status.get('error', 'Chưa đăng nhập')}")
        print("Vui lòng đảm bảo Zalo Personal Daemon đang chạy trên cổng 3712.")
        return

    user_name = conn_status.get("displayName", "Người dùng Zalo")
    print(f"✅ Đã kết nối Zalo thành công! Tài khoản: {user_name}")

    db = ConstructionDB()
    parser = ConstructionReportParser()
    excel_syncer = ConstructionExcelSyncer()
    brain = DataBossBrain(db, excel_syncer, parser)
    listener = DataBossListener(brain, bridge)

    print(f"📁 Cơ sở dữ liệu: {db.db_path}")
    print(f"📊 Báo cáo Excel: {excel_syncer.excel_path}")
    print("\n[ĐẠI CA DỮ LIỆU ĐANG LẮNG NGHE CÁC NHÓM CÔNG TRƯỜNG...]")
    print("Nhấn Ctrl+C để dừng bot.\n")

    # Lấy danh sách các nhóm Zalo để theo dõi
    target_threads = []
    try:
        import httpx
        res = httpx.get(f"{bridge.base_url}/groups", timeout=5.0)
        if res.status_code == 200:
            groups = res.json().get("data", [])
            for g in groups:
                g_name = g.get("name", "")
                # Tìm các nhóm có tên liên quan đến thi công / công trình / PMU
                if any(k in g_name.upper() for k in ["PMU", "OLP", "BĂNG HẠ TẦNG", "307", "CẦU", "THI CÔNG", "TIẾN ĐỘ", "KCS"]):
                    target_threads.append((g.get("groupId"), g_name))
                    print(f"  👉 Giám sát nhóm: [{g_name}] (ID: {g.get('groupId')})")
    except Exception as e:
        print(f"Lỗi lấy danh sách nhóm: {e}")

    if not target_threads:
        print("  ⚠️ Không tìm thấy nhóm dự án tự động, sẽ lắng nghe theo cấu hình mặc định.")
        target_threads.append((Config.DEFAULT_GROUP_NAME, Config.DEFAULT_GROUP_NAME))

    # Vòng lặp lắng nghe liên tục
    try:
        while True:
            for thread_id, thread_name in target_threads:
                try:
                    listener.poll_messages(thread_id=thread_id)
                except Exception as e:
                    # Bỏ qua lỗi kết nối tạm thời để không ngắt vòng lặp
                    pass
                time.sleep(1.0)
            time.sleep(3.0)
    except KeyboardInterrupt:
        print("\n[Đại ca dữ liệu] Đã dừng theo yêu cầu của chỉ huy!")

if __name__ == "__main__":
    main()
