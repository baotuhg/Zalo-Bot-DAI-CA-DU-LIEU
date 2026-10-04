import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from config import Config

class DBManager:
    def __init__(self, db_path=None):
        self.db_path = str(db_path or Config.DB_PATH)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Bảng học sinh
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                grade INTEGER DEFAULT 7,
                school TEXT DEFAULT '',
                group_name TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            );
            """)

            # Bảng Thời khóa biểu
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                day_of_week INTEGER NOT NULL, -- 0=Thứ 2, 1=Thứ 3, ..., 5=Thứ 7, 6=Chủ nhật
                subjects TEXT NOT NULL,       -- JSON list các môn
                special_notes TEXT DEFAULT '',
                UNIQUE(student_name, day_of_week)
            );
            """)

            # Bảng Bài tập về nhà
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS homework (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_date TEXT NOT NULL,       -- YYYY-MM-DD
                due_time TEXT DEFAULT '23:30',
                status TEXT DEFAULT 'pending', -- pending, submitted, reviewed, completed, overdue
                feedback TEXT DEFAULT '',
                submission_image TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            """)

            # Bảng Lịch nhắc
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                remind_at TEXT,               -- ISO format
                recurrence_time TEXT,         -- HH:MM (nếu lặp lại hàng ngày)
                content TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            );
            """)

            conn.commit()
            
        # Khởi tạo dữ liệu mẫu nếu chưa có
        self.seed_default_data()

    def seed_default_data(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE name = ?", (Config.DEFAULT_STUDENT_NAME,))
            if cursor.fetchone()["cnt"] == 0:
                cursor.execute("""
                INSERT INTO students (name, grade, group_name, notes)
                VALUES (?, 7, ?, 'Cần rèn luyện tính tự giác, cẩn thận từng bước giải.')
                """, (Config.DEFAULT_STUDENT_NAME, Config.DEFAULT_GROUP_NAME))

            # Thời khóa biểu mẫu thực tế từ ảnh chụp
            default_schedule = {
                0: ["Toán", "KHTN", "GDTC", "GDCD", "HĐTN"], # Thứ 2
                1: ["KHTN", "KHTN", "Ngữ văn", "Ngữ văn", "Lịch sử và Địa lí"], # Thứ 3
                2: ["Toán", "Tin học", "GDTC", "Công nghệ", "Mĩ thuật"], # Thứ 4
                3: ["Toán", "KHTN", "Lịch sử và Địa lí", "Tiếng Anh"], # Thứ 5
                4: ["Toán", "Ngữ văn", "Ngữ văn", "Mĩ thuật", "Công nghệ"], # Thứ 6
                5: ["Tiếng Anh", "Khác", "HĐTN", "HĐTN"], # Thứ 7
            }

            for day, subjects in default_schedule.items():
                cursor.execute("""
                INSERT OR REPLACE INTO schedules (student_name, day_of_week, subjects, special_notes)
                VALUES (?, ?, ?, '')
                """, (Config.DEFAULT_STUDENT_NAME, day, json.dumps(subjects, ensure_ascii=False)))

            conn.commit()

    # --- Schedule APIs ---
    def get_schedule(self, student_name: str, day_of_week: int) -> Optional[List[str]]:
        """Lấy danh sách môn học của ngày (0=Thứ Hai ... 6=Chủ Nhật)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT subjects FROM schedules WHERE student_name = ? AND day_of_week = ?
            """, (student_name, day_of_week))
            row = cursor.fetchone()
            if row:
                return json.loads(row["subjects"])
            return None

    def get_tomorrow_schedule(self, student_name: str) -> Dict[str, Any]:
        """Lấy TKB của ngày mai và tên thứ tiếng Việt."""
        tomorrow = datetime.now() + timedelta(days=1)
        day_of_week = tomorrow.weekday() # 0 = Monday, ..., 6 = Sunday
        day_names = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        subjects = self.get_schedule(student_name, day_of_week) or []
        return {
            "date_str": tomorrow.strftime("%d/%m/%Y"),
            "day_name": day_names[day_of_week],
            "day_of_week": day_of_week,
            "subjects": subjects
        }

    def save_full_schedule(self, student_name: str, schedule_dict: Dict[int, List[str]]):
        """Lưu toàn bộ TKB tuần của học sinh."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for day, subjects in schedule_dict.items():
                cursor.execute("""
                INSERT OR REPLACE INTO schedules (student_name, day_of_week, subjects)
                VALUES (?, ?, ?)
                """, (student_name, day, json.dumps(subjects, ensure_ascii=False)))
            conn.commit()

    # --- Homework APIs ---
    def add_homework(self, student_name: str, subject: str, title: str, due_date: str, due_time: str = "23:30", description: str = "") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
            INSERT INTO homework (student_name, subject, title, description, due_date, due_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (student_name, subject, title, description, due_date, due_time, now_str))
            conn.commit()
            return cursor.lastrowid

    def list_homework(self, student_name: str, date_str: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM homework WHERE student_name = ?"
            params = [student_name]
            if date_str:
                query += " AND due_date = ?"
                params.append(date_str)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY due_date, due_time"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_homework_status(self, homework_id: int, status: str, feedback: str = "", submission_image: str = ""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE homework
            SET status = ?, feedback = ?, submission_image = ?
            WHERE id = ?
            """, (status, feedback, submission_image, homework_id))
            conn.commit()

    def get_daily_summary(self, student_name: str, date_str: str) -> Dict[str, Any]:
        """Lấy dữ liệu tổng kết ngày phục vụ báo cáo cho phụ huynh."""
        all_tasks = self.list_homework(student_name, date_str)
        completed = [t for t in all_tasks if t["status"] in ("completed", "reviewed")]
        pending = [t for t in all_tasks if t["status"] in ("pending", "submitted")]
        return {
            "date": date_str,
            "student_name": student_name,
            "total_tasks": len(all_tasks),
            "completed_count": len(completed),
            "pending_count": len(pending),
            "completed_tasks": completed,
            "pending_tasks": pending
        }
