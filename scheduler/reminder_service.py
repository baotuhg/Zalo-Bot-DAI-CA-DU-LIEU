from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import Config
from database.db_manager import DBManager
from core.tutor_brain import TutorBrain
from zalo.bridge import ZaloBridge

class ReminderService:
    def __init__(self, db: DBManager, brain: TutorBrain, bridge: ZaloBridge):
        self.db = db
        self.brain = brain
        self.bridge = bridge
        self.scheduler = BackgroundScheduler()

    def job_afternoon_check(self):
        """18h30: Nhắc kiểm tra bài tập hôm nay."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chạy job nhắc bài tập chiều (18h30)...")
        student = Config.DEFAULT_STUDENT_NAME
        today_str = datetime.now().strftime("%Y-%m-%d")
        pending = self.db.list_homework(student, today_str, status="pending")
        
        count = len(pending)
        msg = (
            f"🔔 **[NHẮC NHỞ KỶ LUẬT 18:30]**\n"
            f"@{student} ơi! Đã đến giờ ngồi vào bàn học và rà soát bài vở.\n\n"
            f"📋 Số lượng bài tập cần xử lý hôm nay: **{count} việc**.\n"
            f"Con hãy tập trung làm dứt điểm trước 21h30, không được vừa học vừa xem điện thoại hay trì hoãn.\n"
            f"Làm xong câu nào, chụp ảnh ngay ngắn gửi lên nhóm để Jerryhg kiểm tra nhé!"
        )
        self.bridge.send_message(msg)

    def job_evening_bag_pack(self):
        """21h30: Nhắc soạn sách vở theo TKB ngày mai."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chạy job nhắc soạn sách vở (21h30)...")
        student = Config.DEFAULT_STUDENT_NAME
        tomorrow_data = self.db.get_tomorrow_schedule(student)
        
        # Nhờ AI soạn tin nhắc nhở nghiêm khắc chuẩn mực
        if self.brain.is_ready():
            msg = self.brain.create_bag_packing_reminder(tomorrow_data, student_name=student)
        else:
            day_name = tomorrow_data["day_name"]
            subjects = ", ".join(tomorrow_data["subjects"]) if tomorrow_data["subjects"] else "Không có môn"
            msg = (
                f"🎒 **[NHẮC SOẠN CẶP THEO TKB NGÀY MAI - 21:30]**\n"
                f"@{student} lưu ý: Ngày mai ({day_name}) con học các môn: **{subjects}**.\n\n"
                f"Yêu cầu:\n"
                f"1. Kiểm tra toàn bộ bài tập của các môn trên đã xong chưa.\n"
                f"2. Soạn đủ SGK, vở bài tập và đồ dùng cần thiết (thước kẻ, compa, máy tính).\n"
                f"3. Dọn bàn học ngăn nắp trước khi đi ngủ. Tuyệt đối không để sáng mai sát giờ mới cuống cuồng soạn cặp!"
            )
        self.bridge.send_message(msg)

    def job_daily_report(self):
        """23h00: Tổng kết ngày gửi bố mẹ."""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Chạy job báo cáo tổng kết ngày (23h00)...")
        student = Config.DEFAULT_STUDENT_NAME
        today_str = datetime.now().strftime("%Y-%m-%d")
        summary = self.db.get_daily_summary(student, today_str)

        if self.brain.is_ready():
            msg = self.brain.create_parent_report(summary)
        else:
            done = summary["completed_count"]
            pending = summary["pending_count"]
            msg = (
                f"📒 **[TỔNG KẾT HỌC TẬP NGÀY {datetime.now().strftime('%d/%m/%Y')}]**\n"
                f"Học sinh: **{student}**\n\n"
                f"• Đã báo hoàn thành: **{done} việc**\n"
                f"• Việc còn nợ/chưa hoàn thành: **{pending} việc**\n\n"
                f"Jerryhg kính báo để bố mẹ nắm tình hình và kiểm tra thực tế vở của con. "
                f"Bố mẹ có thể nhắn 'được rồi' để xác nhận đã xem tổng kết."
            )
        self.bridge.send_message(msg)

    def start(self):
        # Tách giờ và phút từ Config
        def parse_time(time_str: str):
            parts = time_str.split(":")
            return int(parts[0]), int(parts[1])

        h_afternoon, m_afternoon = parse_time(Config.REMINDER_AFTERNOON_TIME)
        h_bag, m_bag = parse_time(Config.REMINDER_EVENING_BAG_TIME)
        h_report, m_report = parse_time(Config.DAILY_REPORT_TIME)

        # Đăng ký các Cron triggers
        self.scheduler.add_job(
            self.job_afternoon_check,
            CronTrigger(hour=h_afternoon, minute=m_afternoon),
            id="job_afternoon_check"
        )
        self.scheduler.add_job(
            self.job_evening_bag_pack,
            CronTrigger(hour=h_bag, minute=m_bag),
            id="job_evening_bag_pack"
        )
        self.scheduler.add_job(
            self.job_daily_report,
            CronTrigger(hour=h_report, minute=m_report),
            id="job_daily_report"
        )

        self.scheduler.start()
        print(f"[Scheduler] Đã kích hoạt lịch hẹn: {Config.REMINDER_AFTERNOON_TIME} (Nhắc bài), "
              f"{Config.REMINDER_EVENING_BAG_TIME} (Soạn sách TKB), {Config.DAILY_REPORT_TIME} (Báo cáo).")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
