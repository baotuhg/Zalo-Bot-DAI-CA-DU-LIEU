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
        print(f"❌ [CHƯA KẾT NỐI ĐƯỢC ZALO DAEMON TẠI {bridge.base_url}]")
        print("👉 Vui lòng mở thêm 1 cửa sổ PowerShell và chạy lệnh sau để kết nối:")
        print("   powershell -ExecutionPolicy Bypass -File C:\\Users\\baotu\\.zalo-personal-mcp\\connect.ps1")
        print("-" * 65)
        print("Sau khi quét mã QR và đăng nhập thành công, hãy chạy lại lệnh này nhé!")
        return

    user_name = conn_status.get("displayName", "Người dùng Zalo")
    print(f"✅ Đã kết nối Zalo thành công! Tài khoản: {user_name}")

    db = ConstructionDB()
    parser = ConstructionReportParser()
    excel_syncer = ConstructionExcelSyncer()
    html_syncer = HtmlDashboardSyncer()
    brain = DataBossBrain(db, excel_syncer, parser, html_syncer)
    listener = DataBossListener(brain, bridge)

    print(f"📁 Cơ sở dữ liệu: {db.db_path}")
    print(f"📊 Báo cáo Excel: {excel_syncer.excel_path}")
    print(f"🌐 Dashboard Web: {html_syncer.html_path}")
    print("-" * 65)
    print("🔍 Đang quét các nhóm dự án trên Zalo của bạn...")

    target_threads = []
    try:
        import httpx
        res = httpx.get(f"{bridge.base_url}/groups", timeout=6.0)
        if res.status_code == 200:
            groups = res.json().get("data", [])
            for g in groups:
                g_name = g.get("name", "")
                g_id = g.get("groupId")
                # Lọc các nhóm công trường / thi công / dự án
                if any(k in g_name.upper() for k in ["PMU", "OLP", "BĂNG HẠ TẦNG", "307", "CẦU", "THI CÔNG", "TIẾN ĐỘ", "KCS", "HỒ SƠ", "TDA2", "CAO TỐC"]):
                    target_threads.append((g_id, g_name))
                    print(f"  👉 [ĐANG THEO DÕI] Nhóm: '{g_name}' (ID: {g_id})")
    except Exception as e:
        print(f"Lỗi lấy danh sách nhóm: {e}")

    if not target_threads:
        fallback_name = Config.DEFAULT_GROUP_NAME
        print(f"  ℹ️ Tạm thời lắng nghe nhóm mặc định trong cấu hình: [{fallback_name}]")
        target_threads.append((fallback_name, fallback_name))

    print("\n" + "=" * 65)
    print(f" 🤖 'ĐẠI CA DỮ LIỆU' ĐANG BẢO VỆ & GIÁM SÁT {len(target_threads)} NHÓM DỰ ÁN")
    print("    Mọi báo cáo ca, ảnh thi công sẽ được bóc tách và đẩy lên:")
    print("    👉 https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/")
    print("    Nhấn Ctrl+C để dừng bot bất cứ lúc nào.")
    print("=" * 65 + "\n")

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
