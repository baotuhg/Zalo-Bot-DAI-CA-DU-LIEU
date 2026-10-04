import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

class ConstructionDB:
    """
    Cơ sở dữ liệu Quan hệ Báo cáo Tiến độ Công trình Xây dựng (Construction Progress Relational DB).
    Lưu trữ chuẩn WBS (Work Breakdown Structure):
    Dự án -> Nhà thầu -> Báo cáo Ca -> Hạng mục công việc / Tim cọc / Ảnh hiện trường.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "construction_data.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
        self.init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Khởi tạo cấu trúc các bảng dữ liệu."""
        with self._connection() as conn:
            cursor = conn.cursor()
            
            # 1. Bảng Dự án
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    pmu_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 2. Bảng Nhà thầu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contractors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    package_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Bảng Báo cáo Ca thi công
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shift_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    contractor_id INTEGER,
                    report_date TEXT NOT NULL,
                    shift_name TEXT NOT NULL,
                    reporter_name TEXT,
                    raw_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(contractor_id) REFERENCES contractors(id)
                )
            """)

            # 4. Bảng Chi tiết Khối lượng Hạng mục (Progress Items)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS progress_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER,
                    category TEXT NOT NULL,
                    sub_item TEXT NOT NULL,
                    unit TEXT,
                    shift_qty REAL DEFAULT 0,
                    accumulated_qty REAL DEFAULT 0,
                    design_qty REAL DEFAULT 0,
                    completion_rate REAL DEFAULT 0,
                    status_note TEXT,
                    FOREIGN KEY(report_id) REFERENCES shift_reports(id) ON DELETE CASCADE
                )
            """)

            # 5. Bảng Chi tiết Tình trạng Tim Cọc / Cấu kiện
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pile_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER,
                    category TEXT,
                    location TEXT NOT NULL,
                    pile_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(report_id) REFERENCES shift_reports(id) ON DELETE CASCADE
                )
            """)

            # 6. Bảng Lưu trữ Ảnh hiện trường
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS site_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER,
                    photo_url TEXT,
                    local_path TEXT,
                    caption TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(report_id) REFERENCES shift_reports(id) ON DELETE CASCADE
                )
            """)

            # Tạo indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_date ON shift_reports(report_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_cat ON progress_items(category, sub_item)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_piles_id ON pile_details(pile_id)")
            conn.commit()

    def get_or_create_project(self, name: str, code: Optional[str] = None, pmu_name: Optional[str] = None) -> int:
        """Lấy hoặc tạo mới dự án."""
        proj_code = code or name.replace(" ", "_").upper()[:20]
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM projects WHERE code = ? OR name = ?", (proj_code, name))
            row = cursor.fetchone()
            if row:
                return row["id"]
            cursor.execute(
                "INSERT INTO projects (code, name, pmu_name) VALUES (?, ?, ?)",
                (proj_code, name, pmu_name or name)
            )
            conn.commit()
            return cursor.lastrowid

    def get_or_create_contractor(self, name: str, package_name: Optional[str] = None) -> int:
        """Lấy hoặc tạo mới nhà thầu."""
        clean_name = name.strip()
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM contractors WHERE name = ?", (clean_name,))
            row = cursor.fetchone()
            if row:
                return row["id"]
            cursor.execute(
                "INSERT INTO contractors (name, package_name) VALUES (?, ?)",
                (clean_name, package_name or "Gói thầu chính")
            )
            conn.commit()
            return cursor.lastrowid

    def save_report(self, parsed_data: Dict[str, Any], project_name: str = "PMU BĂNG HẠ TẦNG OLP", media_urls: Optional[List[str]] = None) -> int:
        """
        Lưu toàn bộ dữ liệu báo cáo thi công vào Database trong một giao dịch an toàn (Transaction).
        """
        proj_id = self.get_or_create_project(project_name, pmu_name="Ban Quản Lý Dự Án")
        contractor_name = parsed_data.get("contractor", "Nhà thầu Dự án")
        cont_id = self.get_or_create_contractor(contractor_name)

        report_date = parsed_data.get("report_date", datetime.date.today().strftime("%Y-%m-%d"))
        shift_name = parsed_data.get("shift_name", "Ca ngày")
        reporter_name = parsed_data.get("reporter_name", "Kỹ sư hiện trường")
        raw_text = parsed_data.get("raw_text", "")

        with self._connection() as conn:
            cursor = conn.cursor()
            # 1. Thêm bản ghi báo cáo ca
            cursor.execute("""
                INSERT INTO shift_reports (project_id, contractor_id, report_date, shift_name, reporter_name, raw_text)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (proj_id, cont_id, report_date, shift_name, reporter_name, raw_text))
            report_id = cursor.lastrowid

            # 2. Thêm các hạng mục công việc
            for it in parsed_data.get("items", []):
                cursor.execute("""
                    INSERT INTO progress_items (
                        report_id, category, sub_item, unit, shift_qty, accumulated_qty, design_qty, completion_rate, status_note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    report_id,
                    it.get("category", ""),
                    it.get("sub_item", ""),
                    it.get("unit", "Cấu kiện"),
                    float(it.get("shift_qty", 0)),
                    float(it.get("accumulated_qty", 0)),
                    float(it.get("design_qty", 0)),
                    float(it.get("completion_rate", 0)),
                    it.get("status_note", "")
                ))

            # 3. Thêm chi tiết tim cọc & cấu kiện
            for p in parsed_data.get("piles", []):
                cursor.execute("""
                    INSERT INTO pile_details (report_id, category, location, pile_id, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    report_id,
                    p.get("category", "Cọc khoan nhồi"),
                    p.get("location", ""),
                    p.get("pile_id", ""),
                    p.get("status", "")
                ))

            # 4. Thêm ảnh nếu có
            if media_urls:
                for url in media_urls:
                    cursor.execute("""
                        INSERT INTO site_photos (report_id, photo_url, caption)
                        VALUES (?, ?, ?)
                    """, (report_id, str(url), f"Ảnh hiện trường ca {shift_name} ngày {report_date}"))

            conn.commit()
            return report_id

    def get_latest_project_summary(self) -> List[Dict[str, Any]]:
        """
        Lấy số liệu lũy kế và tiến độ mới nhất của từng hạng mục trong dự án.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT p.category, p.sub_item, p.unit, p.shift_qty, p.accumulated_qty, p.design_qty, 
                       p.completion_rate, p.status_note, r.report_date, r.shift_name, c.name as contractor_name
                FROM progress_items p
                JOIN shift_reports r ON p.report_id = r.id
                JOIN contractors c ON r.contractor_id = c.id
                WHERE p.id IN (
                    SELECT MAX(p2.id)
                    FROM progress_items p2
                    GROUP BY p2.category, p2.sub_item
                )
                ORDER BY p.category, p.sub_item
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_active_piles(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách các tim cọc đang thi công dở dang (đang khoan, thổi rửa, hạ lồng thép...).
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT pd.location, pd.pile_id, pd.status, r.report_date, r.shift_name, c.name as contractor_name
                FROM pile_details pd
                JOIN shift_reports r ON pd.report_id = r.id
                JOIN contractors c ON r.contractor_id = c.id
                WHERE pd.id IN (
                    SELECT MAX(p2.id)
                    FROM pile_details p2
                    GROUP BY p2.pile_id
                )
                ORDER BY pd.location, pd.pile_id
            """
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]

    def get_shift_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Lấy danh sách các ca thi công đã báo cáo gần đây."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.id, r.report_date, r.shift_name, r.reporter_name, c.name as contractor_name,
                       COUNT(p.id) as item_count, r.created_at
                FROM shift_reports r
                LEFT JOIN contractors c ON r.contractor_id = c.id
                LEFT JOIN progress_items p ON r.id = p.report_id
                GROUP BY r.id
                ORDER BY r.report_date DESC, r.id DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_categories(self) -> List[str]:
        """Lấy danh sách tất cả các hạng mục chính để đưa vào bộ lọc."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM progress_items WHERE category IS NOT NULL AND category != '' ORDER BY category")
            rows = cursor.fetchall()
            return [row["category"] for row in rows]

    def search_progress_items(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        latest_only: bool = False,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm và lọc các hạng mục tiến độ theo từ khóa, danh mục, và tùy chọn chỉ lấy mới nhất.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            base_query = """
                SELECT p.id, p.report_id, p.category, p.sub_item, p.unit,
                       p.shift_qty, p.accumulated_qty, p.design_qty,
                       p.completion_rate, p.status_note,
                       r.report_date, r.shift_name, r.reporter_name,
                       c.name as contractor_name
                FROM progress_items p
                JOIN shift_reports r ON p.report_id = r.id
                JOIN contractors c ON r.contractor_id = c.id
            """
            conditions = []
            params = []

            if latest_only:
                conditions.append("""
                    p.id IN (
                        SELECT MAX(p2.id)
                        FROM progress_items p2
                        GROUP BY p2.category, p2.sub_item
                    )
                """)

            if category and category.strip() and category != "[Tất cả hạng mục]":
                conditions.append("p.category = ?")
                params.append(category.strip())

            if keyword and keyword.strip():
                kw = f"%{keyword.strip()}%"
                conditions.append("""
                    (p.category LIKE ? OR p.sub_item LIKE ? OR p.status_note LIKE ?
                     OR r.report_date LIKE ? OR r.shift_name LIKE ?
                     OR r.reporter_name LIKE ? OR c.name LIKE ?)
                """)
                params.extend([kw, kw, kw, kw, kw, kw, kw])

            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)

            base_query += " ORDER BY r.report_date DESC, p.id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(base_query, tuple(params))
            return [dict(r) for r in cursor.fetchall()]

    def search_piles(
        self,
        keyword: Optional[str] = None,
        latest_only: bool = True,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm và lọc chi tiết các tim cọc đang thi công hoặc đã ghi nhận.
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            base_query = """
                SELECT pd.id, pd.report_id, pd.category, pd.location, pd.pile_id, pd.status, pd.recorded_at,
                       r.report_date, r.shift_name, c.name as contractor_name
                FROM pile_details pd
                JOIN shift_reports r ON pd.report_id = r.id
                JOIN contractors c ON r.contractor_id = c.id
            """
            conditions = []
            params = []

            if latest_only:
                conditions.append("""
                    pd.id IN (
                        SELECT MAX(p2.id)
                        FROM pile_details p2
                        GROUP BY p2.pile_id
                    )
                """)

            if keyword and keyword.strip():
                kw = f"%{keyword.strip()}%"
                conditions.append("""
                    (pd.location LIKE ? OR pd.pile_id LIKE ? OR pd.status LIKE ?
                     OR r.report_date LIKE ? OR pd.category LIKE ? OR c.name LIKE ?)
                """)
                params.extend([kw, kw, kw, kw, kw, kw])

            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)

            base_query += " ORDER BY r.report_date DESC, pd.id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(base_query, tuple(params))
            return [dict(r) for r in cursor.fetchall()]

    def get_report_detail(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Lấy chi tiết toàn bộ nội dung của một ca báo cáo."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT r.*, c.name as contractor_name, p.name as project_name
                FROM shift_reports r
                LEFT JOIN contractors c ON r.contractor_id = c.id
                LEFT JOIN projects p ON r.project_id = p.id
                WHERE r.id = ?
            """, (report_id,))
            rep = cursor.fetchone()
            if not rep:
                return None
            res = dict(rep)

            cursor.execute("SELECT * FROM progress_items WHERE report_id = ? ORDER BY id", (report_id,))
            res["items"] = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM pile_details WHERE report_id = ? ORDER BY id", (report_id,))
            res["piles"] = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM site_photos WHERE report_id = ? ORDER BY id", (report_id,))
            res["photos"] = [dict(r) for r in cursor.fetchall()]

            return res
