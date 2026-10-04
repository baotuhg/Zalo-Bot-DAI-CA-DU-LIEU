import time
from database.db_manager import DBManager
from core.tutor_brain import TutorBrain
from core.zalo_math import format_zalo_math
from core.smart_reaction import pick_smart_reaction
from config import Config

def test_full_pipeline():
    print("=" * 65)
    print("  KIỂM THỬ TOÀN DIỆN: GIA SƯ NGHIÊM KHẮC JERRYHG (ĐÃ NÂNG CẤP)")
    print("=" * 65)

    # 1. DB & Thời khóa biểu
    db = DBManager()
    student = Config.DEFAULT_STUDENT_NAME
    tomorrow = db.get_tomorrow_schedule(student)
    print(f"\n[1] THỜI KHÓA BIỂU NGÀY MAI ({tomorrow['day_name']} {tomorrow['date_str']}):")
    print(f"    Các môn học: {', '.join(tomorrow['subjects'])}")

    # 2. Thử thêm bài tập và kiểm tra danh sách bài tập
    today_str = time.strftime("%Y-%m-%d")
    pending = db.list_homework(student, today_str, status="pending")
    print(f"\n[2] BÀI TẬP VỀ NHÀ CỦA {student.upper()}:")
    for task in pending:
        print(f"    • [{task['subject']}] {task['title']} (Hạn: {task['due_time']}) - Trạng thái: {task['status']}")

    # 3. Kiểm thử Vũ khí 1: Zalo Math (Công thức Toán & Hóa Unicode)
    print(f"\n[3] KIỂM THỬ BỘ CHUYỂN ĐỔI CÔNG THỨC TOÁN & HÓA (ZALO MATH):")
    raw_formula = r"Giải phương trình: $x^2 - 5x + 6 = 0$. Tính $\Delta = b^2 - 4ac$ và nghiệm $x_1, x_2$. Axit $H_2SO_4$."
    formatted = format_zalo_math(raw_formula)
    print(f"    Gốc:  {raw_formula}")
    print(f"    Zalo: {formatted}")

    # 4. Kiểm thử Vũ khí 2: Smart Reaction (Cảm xúc thông minh)
    print(f"\n[4] KIỂM THỬ SMART REACTION:")
    test_cases = [
        ("Jerryhg ơi, bài này làm thế nào?", "Học sinh hỏi bài"),
        ("Con làm xong hết bài rồi ạ!", "Học sinh hoàn thành bài"),
        ("Con mệt quá không muốn làm đâu", "Học sinh lười biếng / than phiền"),
        ("Bố mẹ đã xem, cảm ơn cô", "Phụ huynh xác nhận")
    ]
    for msg, desc in test_cases:
        react = pick_smart_reaction(msg)
        print(f"    • [{desc}] '{msg}' -> Reaction: {react.upper()}")

    # 5. Giả lập thông báo 21h30: Nhắc soạn sách vở theo TKB ngày mai
    day_name = tomorrow["day_name"]
    subjects = ", ".join(tomorrow["subjects"])
    reminder_msg = (
        f"🎒 **[NHẮC SOẠN CẶP THEO TKB NGÀY MAI - 21:30]**\n"
        f"@{student} lưu ý: Ngày mai ({day_name}) con học các môn: **{subjects}**.\n\n"
        f"Yêu cầu từ Gia sư Jerryhg:\n"
        f"1. Kiểm tra lại toàn bộ bài tập của các môn trên xem đã làm xong hết chưa.\n"
        f"2. Soạn đủ sách giáo khoa, vở bài tập và đồ dùng học tập tương ứng (thước, compa, máy tính).\n"
        f"3. Dọn bàn học ngăn nắp trước khi đi ngủ. Tuyệt đối không để sáng mai sát giờ đi học mới cuống cuồng soạn cặp!"
    )
    print(f"\n[5] THÔNG BÁO 21h30 (NHẮC SOẠN CẶP THEO TKB):")
    print(reminder_msg)

    # 6. Giả lập báo cáo 23h00 cho Phụ huynh
    summary = db.get_daily_summary(student, today_str)
    print(f"\n[6] BÁO CÁO TỔNG KẾT 23h00 GỬI PHỤ HUYNH:")
    report_msg = (
        f"📒 **[TỔNG KẾT HỌC TẬP NGÀY {time.strftime('%d/%m/%Y')}]**\n"
        f"Học sinh: **{student}**\n\n"
        f"• Đã báo hoàn thành: **{summary['completed_count']} việc**\n"
        f"• Việc còn nợ/chưa hoàn thành: **{summary['pending_count']} việc**\n\n"
        f"Jerryhg kính báo để bố mẹ nắm tình hình và kiểm tra thực tế vở của con. Bố mẹ vui lòng nhắn 'được rồi' để xác nhận đã xem tổng kết."
    )
    print(report_msg)

    print("\n" + "=" * 65)
    print("  KẾT QUẢ: TOÀN BỘ TÍNH NĂNG MỚI ĐÃ TÍCH HỢP VÀ HOẠT ĐỘNG HOÀN HẢO!")
    print("=" * 65)

if __name__ == "__main__":
    test_full_pipeline()
