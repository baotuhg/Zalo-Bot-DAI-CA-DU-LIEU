import sys
import threading
import time
from config import Config
from database.db_manager import DBManager
from core.tutor_brain import TutorBrain
from zalo.bridge import ZaloBridge
from zalo.listener import ZaloListener
from scheduler.reminder_service import ReminderService

def check_and_run_data_boss():
    """Kiểm tra xem người dùng có yêu cầu chạy bot 'Đại ca dữ liệu' hay không."""
    if "--databoss" in sys.argv:
        import run_data_boss
        run_data_boss.main()
        sys.exit(0)
    elif "--databoss-cli" in sys.argv or "--boss" in sys.argv:
        import cli_data_boss
        cli_data_boss.main()
        sys.exit(0)

check_and_run_data_boss()

def run_cli_test_mode(db: DBManager, brain: TutorBrain):
    """Chế độ giả lập tương tác trên Terminal để test nhanh phản hồi sư phạm."""
    print("=" * 60)
    print("  CHẾ ĐỘ THỬ NGHIỆM TRỰC TIẾP: GIA SƯ NGHIÊM KHẮC JERRYHG")
    print("=" * 60)
    print(f"Học sinh mặc định: {Config.DEFAULT_STUDENT_NAME}")
    print(f"Nhóm: {Config.DEFAULT_GROUP_NAME}")
    print(f"AI Provider: {Config.AI_PROVIDER.upper()}")
    print("-" * 60)
    print("Các lệnh test nhanh:")
    print("  1. 'tkb'        -> Xem TKB ngày mai")
    print("  2. 'soancap'    -> Giả lập thông báo 21h30 nhắc soạn cặp")
    print("  3. 'baocao'     -> Giả lập báo cáo 23h00 gửi phụ huynh")
    print("  4. 'hoi <câu>'  -> Đặt câu hỏi học tập thử phản xạ gia sư")
    print("  5. 'exit'       -> Thoát")
    print("-" * 60)

    while True:
        try:
            cmd = input("\n[Bạn/Con]: ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit", "q"):
                print("Tạm biệt!")
                break
            
            if cmd.lower() == "tkb":
                tomorrow = db.get_tomorrow_schedule(Config.DEFAULT_STUDENT_NAME)
                print(f"\n[Gia sư Jerryhg]:\nNgày mai ({tomorrow['day_name']} {tomorrow['date_str']}) con học:")
                for idx, sub in enumerate(tomorrow['subjects'], 1):
                    print(f"  {idx}. {sub}")
            
            elif cmd.lower() == "soancap":
                tomorrow = db.get_tomorrow_schedule(Config.DEFAULT_STUDENT_NAME)
                msg = brain.create_bag_packing_reminder(tomorrow, student_name=Config.DEFAULT_STUDENT_NAME)
                print(f"\n[Thông báo 21:30 - Soạn sách vở]:\n{msg}")

            elif cmd.lower() == "baocao":
                today_str = time.strftime("%Y-%m-%d")
                summary = db.get_daily_summary(Config.DEFAULT_STUDENT_NAME, today_str)
                msg = brain.create_parent_report(summary)
                print(f"\n[Thông báo 23:00 - Báo cáo Phụ huynh]:\n{msg}")

            elif cmd.lower().startswith("hoi "):
                query = cmd[4:].strip()
                ans = brain.guide_exercise(query, student_name=Config.DEFAULT_STUDENT_NAME)
                print(f"\n[Gia sư Jerryhg]:\n{ans}")

            else:
                # Chat thông thường
                ans = brain.guide_exercise(cmd, student_name=Config.DEFAULT_STUDENT_NAME)
                print(f"\n[Gia sư Jerryhg]:\n{ans}")

        except KeyboardInterrupt:
            break

def main():
    print("Khởi động hệ thống Trợ lý Gia sư Nghiêm khắc Jerryhg...")
    
    # 1. Khởi tạo Database
    db = DBManager()
    print("✓ Cơ sở dữ liệu SQLite đã sẵn sàng.")

    # 2. Khởi tạo AI Brain
    brain = TutorBrain()
    if brain.is_ready():
        print(f"✓ AI Brain đã kết nối ({Config.AI_PROVIDER.upper()}).")
    else:
        print(f"⚠ AI Brain chưa có API Key. Hệ thống sẽ dùng tin nhắn mẫu có sẵn.")

    # 3. Khởi tạo Zalo Bridge
    bridge = ZaloBridge()
    zalo_status = bridge.check_connection()
    if zalo_status.get("authenticated") or zalo_status.get("success"):
        print("✓ Đã kết nối với Zalo Daemon.")
    else:
        print(f"ℹ Zalo Daemon chưa bật hoặc chưa đăng nhập ({zalo_status.get('error', 'Chưa kết nối')}).")
        print("  (Bạn có thể chạy chế độ CLI test trước bằng lệnh: python main.py --cli)")

    # Kiểm tra cờ chạy CLI
    if "--cli" in sys.argv:
        run_cli_test_mode(db, brain)
        return

    # 4. Kích hoạt Scheduler
    reminder = ReminderService(db, brain, bridge)
    reminder.start()

    # 5. Kích hoạt Zalo Listener
    listener = ZaloListener(db, brain, bridge)
    listener_thread = threading.Thread(target=listener.start_polling, daemon=True)
    listener_thread.start()

    print("\n" + "=" * 60)
    print("  HỆ THỐNG GIA SƯ NGHIÊM KHẮC JERRYHG ĐANG CHẠY NGẦM...")
    print("  Nhấn Ctrl+C để dừng.")
    print("=" * 60 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐang dừng hệ thống...")
        reminder.stop()
        listener.stop()
        print("Đã dừng an toàn.")

if __name__ == "__main__":
    main()
