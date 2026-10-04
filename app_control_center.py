import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import sys
import webbrowser
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

# Thêm đường dẫn project vào sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Config
from database.construction_db import ConstructionDB
from core.report_parser import ConstructionReportParser
from core.excel_syncer import ConstructionExcelSyncer
from core.html_dashboard_syncer import HtmlDashboardSyncer
from core.data_boss_brain import DataBossBrain
from zalo.bridge import ZaloBridge
from zalo.data_boss_listener import DataBossListener
from sync_github import auto_push_to_github
from run_data_boss import ensure_daemon_running


class DataBossControlApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🏗️ BẢNG ĐIỀU KHIỂN & TRA CỨU DỮ LIỆU — ĐẠI CA DỮ LIỆU (CONTECH ZALO)")
        self.root.geometry("1020x750")
        self.root.minsize(880, 640)
        self.root.configure(bg="#F4F6F8")

        # Khởi tạo lõi hệ thống
        self.bridge = ZaloBridge()
        self.db = ConstructionDB()
        self.parser = ConstructionReportParser()
        self.excel_syncer = ConstructionExcelSyncer()
        self.html_syncer = HtmlDashboardSyncer()
        self.brain = DataBossBrain(self.db, self.excel_syncer, self.parser, self.html_syncer)
        self.listener = DataBossListener(self.brain, self.bridge)

        self.bot_running = False
        self.bot_thread = None
        self.groups_data = []
        self.group_name_map = {}

        # Dữ liệu tìm kiếm hiện tại
        self.current_items: List[Dict[str, Any]] = []
        self.current_piles: List[Dict[str, Any]] = []
        self.sort_column = ""
        self.sort_reverse = False

        self._setup_styles()
        self._build_ui()
        self._check_zalo_status_async()
        self._refresh_filter_categories()
        self._do_search()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TLabel", background="#F4F6F8", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"), foreground="#1F4E79")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#5A6A80")
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))

        style.configure("TNotebook", background="#F4F6F8")
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[14, 6], background="#E2E8F0")
        style.map("TNotebook.Tab",
                  background=[("selected", "#1F4E79")],
                  foreground=[("selected", "#FFFFFF")])

        # Style Treeview bảng dữ liệu
        style.configure("Treeview",
                        font=("Segoe UI", 9),
                        rowheight=24,
                        background="#FFFFFF",
                        fieldbackground="#FFFFFF")
        style.configure("Treeview.Heading",
                        font=("Segoe UI", 9, "bold"),
                        background="#E2E8F0",
                        foreground="#1E293B")
        style.map("Treeview.Heading", background=[("active", "#CBD5E1")])

    def _build_ui(self):
        # 1. Header Frame (Cố định ở đỉnh)
        header_frame = tk.Frame(self.root, bg="#FFFFFF", padx=18, pady=12, relief="ridge", bd=1)
        header_frame.pack(fill="x", padx=12, pady=(10, 6))

        top_row = tk.Frame(header_frame, bg="#FFFFFF")
        top_row.pack(fill="x")

        lbl_title = ttk.Label(top_row, text="🏗️ BẢNG ĐIỀU KHIỂN & TRA CỨU DỮ LIỆU — ĐẠI CA DỮ LIỆU", style="Header.TLabel", background="#FFFFFF")
        lbl_title.pack(side="left")

        # Status Bar Zalo bên phải
        status_box = tk.Frame(top_row, bg="#FFFFFF")
        status_box.pack(side="right")

        self.lbl_zalo_status = tk.Label(status_box, text="🟡 Đang kết nối Zalo...", font=("Segoe UI", 9, "bold"), bg="#FFFFFF", fg="#B8740A")
        self.lbl_zalo_status.pack(side="left", padx=6)

        btn_reconnect = tk.Button(status_box, text="🔄 Kết nối lại", font=("Segoe UI", 8), bg="#E9ECE6", relief="flat", command=self._reconnect_zalo)
        btn_reconnect.pack(side="left")

        lbl_sub = ttk.Label(
            header_frame,
            text="Thu thập tự động báo cáo thi công Zalo ➔ Phân tích ngữ nghĩa ➔ CSDL SQLite WBS ➔ Excel sống ➔ Web Dashboard",
            style="SubHeader.TLabel",
            background="#FFFFFF"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # 2. Main Notebook Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(4, 10))

        # Tab 1: Giám sát & Điều khiển
        self.tab_monitor = tk.Frame(self.notebook, bg="#F4F6F8")
        self.notebook.add(self.tab_monitor, text="  🎛️ BẢNG ĐIỀU KHIỂN & GIÁM SÁT REALTIME  ")
        self._build_tab_monitor()

        # Tab 2: Tra cứu & Lọc dữ liệu
        self.tab_search = tk.Frame(self.notebook, bg="#F4F6F8")
        self.notebook.add(self.tab_search, text="  🔍 TÌM KIẾM & LỌC DỮ LIỆU  ")
        self._build_tab_search()

    def _build_tab_monitor(self):
        # 1. Main Control Frame (Chọn nhóm & Bật/Tắt Bot)
        ctrl_frame = tk.LabelFrame(self.tab_monitor, text=" 🎯 Cấu hình & Giám sát Nhóm Zalo ", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", padx=16, pady=10)
        ctrl_frame.pack(fill="x", padx=10, pady=6)

        row_group = tk.Frame(ctrl_frame, bg="#F4F6F8")
        row_group.pack(fill="x", pady=4)

        tk.Label(row_group, text="Nhóm Zalo cần lọc báo cáo:", font=("Segoe UI", 10, "bold"), bg="#F4F6F8").pack(side="left")

        self.combo_group = ttk.Combobox(row_group, font=("Segoe UI", 10), state="readonly", width=38)
        self.combo_group.pack(side="left", padx=10, fill="x", expand=True)
        self.combo_group.set("Đang tải danh sách nhóm...")
        self.combo_group.bind("<<ComboboxSelected>>", self._on_group_selected)

        # Nút Quét ngay dữ liệu nhóm
        btn_scan_now = tk.Button(
            row_group,
            text="📥 QUÉT TIN HIỆN CÓ",
            font=("Segoe UI", 9, "bold"),
            bg="#1F4E79",
            fg="#FFFFFF",
            activebackground="#153654",
            activeforeground="#FFFFFF",
            relief="raised",
            bd=2,
            padx=10,
            pady=2,
            cursor="hand2",
            command=self._scan_current_group_now
        )
        btn_scan_now.pack(side="left", padx=4)

        btn_refresh_groups = ttk.Button(row_group, text="🔄 Tải lại nhóm", command=self._load_zalo_groups)
        btn_refresh_groups.pack(side="left", padx=4)

        # Hàng nút Bật / Tắt Bot
        row_bot_btn = tk.Frame(ctrl_frame, bg="#F4F6F8")
        row_bot_btn.pack(fill="x", pady=(8, 4))

        self.btn_toggle_bot = tk.Button(
            row_bot_btn,
            text="▶️ BẬT BOT GIÁM SÁT REALTIME (TỰ ĐỘNG BẮT BÁO CÁO ZALO)",
            font=("Segoe UI", 11, "bold"),
            bg="#0E6655",
            fg="#FFFFFF",
            activebackground="#094A3E",
            activeforeground="#FFFFFF",
            relief="raised",
            bd=2,
            padx=14,
            pady=8,
            cursor="hand2",
            command=self._toggle_bot
        )
        self.btn_toggle_bot.pack(side="left", fill="x", expand=True)

        self.lbl_bot_state = tk.Label(row_bot_btn, text="⚪ Bot đang Dừng", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", fg="#5A6A80", padx=14)
        self.lbl_bot_state.pack(side="left")

        # 2. Phím bấm thao tác nhanh 1-Click
        action_frame = tk.LabelFrame(self.tab_monitor, text=" ⚡ Thao tác nhanh 1-Click ", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", padx=12, pady=10)
        action_frame.pack(fill="x", padx=10, pady=6)

        btn_grid = tk.Frame(action_frame, bg="#F4F6F8")
        btn_grid.pack(fill="x")

        # NÚT ĐẶC BIỆT 1: TÌM KIẾM & LỌC DỮ LIỆU
        btn_goto_search = tk.Button(
            btn_grid,
            text="🔍 TÌM KIẾM & LỌC DỮ LIỆU",
            font=("Segoe UI", 9, "bold"),
            bg="#0284C7",
            fg="#FFFFFF",
            padx=8,
            pady=8,
            cursor="hand2",
            relief="raised",
            bd=2,
            command=self._switch_to_search_tab
        )
        btn_goto_search.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

        # NÚT ĐẶC BIỆT 2: DÁN NHANH BÁO CÁO (COPY & PASTE TỪ ZALO)
        btn_quick_paste = tk.Button(
            btn_grid,
            text="📋 NẠP LỊCH SỬ NHIỀU CA (ZALO)",
            font=("Segoe UI", 9, "bold"),
            bg="#D97706",
            fg="#FFFFFF",
            padx=8,
            pady=8,
            cursor="hand2",
            relief="raised",
            bd=2,
            command=self._quick_paste_report_dialog
        )
        btn_quick_paste.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        # Nút Mở Web Dashboard
        btn_web = tk.Button(
            btn_grid,
            text="🌐 MỞ WEB DASHBOARD ONLINE",
            font=("Segoe UI", 9, "bold"),
            bg="#1F4E79",
            fg="#FFFFFF",
            padx=8,
            pady=8,
            cursor="hand2",
            relief="groove",
            command=self._open_web_dashboard
        )
        btn_web.grid(row=0, column=2, padx=4, pady=4, sticky="nsew")

        # Nút Mở Excel
        btn_excel = tk.Button(
            btn_grid,
            text="📑 MỞ BẢNG EXCEL SỐNG",
            font=("Segoe UI", 9, "bold"),
            bg="#2E7A48",
            fg="#FFFFFF",
            padx=8,
            pady=8,
            cursor="hand2",
            relief="groove",
            command=self._open_excel
        )
        btn_excel.grid(row=0, column=3, padx=4, pady=4, sticky="nsew")

        # Nút Đồng bộ Toàn bộ Hệ thống
        btn_git = tk.Button(
            btn_grid,
            text="⚡ ĐỒNG BỘ TOÀN BỘ (EXCEL + WEB)",
            font=("Segoe UI", 9, "bold"),
            bg="#7C3AED",
            fg="#FFFFFF",
            padx=8,
            pady=8,
            cursor="hand2",
            relief="raised",
            bd=2,
            command=self._resync_all_system
        )
        btn_git.grid(row=0, column=4, padx=4, pady=4, sticky="nsew")

        for c in range(5):
            btn_grid.columnconfigure(c, weight=1)

        # 3. Live Log Window
        log_frame = tk.LabelFrame(self.tab_monitor, text=" 📜 Nhật ký hoạt động Realtime Zalo ", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", padx=10, pady=8)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(6, 8))

        self.txt_log = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), bg="#1E2227", fg="#ABB2BF", wrap="word", relief="flat")
        self.txt_log.pack(fill="both", expand=True)

        self._log("Hệ thống Bảng điều khiển Realtime Zalo sẵn sàng.")
        self._log("Link Web trực tuyến: https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/")

    def _build_tab_search(self):
        # 1. Filter Control Box
        filter_box = tk.LabelFrame(self.tab_search, text=" 🎯 Bộ lọc & Điều kiện tìm kiếm ", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", padx=12, pady=10)
        filter_box.pack(fill="x", padx=10, pady=6)

        # Hàng 1: Từ khóa + Dự án + Hạng mục + Nút Tìm kiếm
        row1 = tk.Frame(filter_box, bg="#F4F6F8")
        row1.pack(fill="x", pady=3)

        tk.Label(row1, text="🔍 Từ khóa:", font=("Segoe UI", 9, "bold"), bg="#F4F6F8").pack(side="left")
        self.entry_keyword = ttk.Entry(row1, font=("Segoe UI", 9), width=16)
        self.entry_keyword.pack(side="left", padx=(4, 8))
        self.entry_keyword.bind("<Return>", lambda e: self._do_search())

        tk.Label(row1, text="🏗️ Nhóm / DA:", font=("Segoe UI", 9, "bold"), bg="#F4F6F8").pack(side="left")
        self.combo_filter_proj = ttk.Combobox(row1, font=("Segoe UI", 9), state="readonly", width=18)
        self.combo_filter_proj.pack(side="left", padx=(4, 8))
        self.combo_filter_proj.set("[Tất cả nhóm/dự án]")
        self.combo_filter_proj.bind("<<ComboboxSelected>>", lambda e: self._do_search())

        tk.Label(row1, text="📁 Hạng mục:", font=("Segoe UI", 9, "bold"), bg="#F4F6F8").pack(side="left")
        self.combo_filter_cat = ttk.Combobox(row1, font=("Segoe UI", 9), state="readonly", width=16)
        self.combo_filter_cat.pack(side="left", padx=(4, 8))
        self.combo_filter_cat.set("[Tất cả hạng mục]")
        self.combo_filter_cat.bind("<<ComboboxSelected>>", lambda e: self._do_search())

        self.var_latest_only = tk.BooleanVar(value=False)
        chk_latest = ttk.Checkbutton(row1, text="Chỉ mới nhất", variable=self.var_latest_only, command=self._do_search)
        chk_latest.pack(side="left", padx=6)

        btn_search = tk.Button(
            row1,
            text="🔍 TÌM KIẾM",
            font=("Segoe UI", 9, "bold"),
            bg="#0E6655",
            fg="#FFFFFF",
            activebackground="#094A3E",
            padx=10,
            pady=3,
            relief="raised",
            cursor="hand2",
            command=self._do_search
        )
        btn_search.pack(side="left", padx=4)

        btn_reset = tk.Button(
            row1,
            text="🔄 TẤT CẢ",
            font=("Segoe UI", 9),
            bg="#E2E8F0",
            fg="#1E293B",
            padx=8,
            pady=3,
            relief="flat",
            cursor="hand2",
            command=self._reset_search
        )
        btn_reset.pack(side="left", padx=4)

        # Hàng 2: Chọn chế độ xem & Thao tác xuất
        row2 = tk.Frame(filter_box, bg="#F4F6F8")
        row2.pack(fill="x", pady=(8, 2))

        tk.Label(row2, text="Chế độ xem:", font=("Segoe UI", 9, "bold"), bg="#F4F6F8").pack(side="left")

        self.var_view_type = tk.StringVar(value="items")
        rb_items = ttk.Radiobutton(row2, text="📊 Hạng mục & Khối lượng (WBS)", variable=self.var_view_type, value="items", command=self._switch_view_mode)
        rb_items.pack(side="left", padx=8)

        rb_piles = ttk.Radiobutton(row2, text="📍 Chi tiết Tim cọc Hiện trường", variable=self.var_view_type, value="piles", command=self._switch_view_mode)
        rb_piles.pack(side="left", padx=8)

        btn_view_detail = tk.Button(
            row2,
            text="📋 Xem chi tiết ca",
            font=("Segoe UI", 9),
            bg="#1F4E79",
            fg="#FFFFFF",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._view_selected_detail
        )
        btn_view_detail.pack(side="right", padx=4)

        btn_export = tk.Button(
            row2,
            text="📑 Xuất kết quả ra Excel",
            font=("Segoe UI", 9, "bold"),
            bg="#2E7A48",
            fg="#FFFFFF",
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._export_search_excel
        )
        btn_export.pack(side="right", padx=4)

        # 2. Thống kê kết quả tìm kiếm
        summary_frame = tk.Frame(self.tab_search, bg="#E2E8F0", padx=10, pady=4)
        summary_frame.pack(fill="x", padx=10, pady=(2, 4))

        self.lbl_search_summary = tk.Label(
            summary_frame,
            text="📊 Đang tải dữ liệu...",
            font=("Segoe UI", 9, "bold"),
            bg="#E2E8F0",
            fg="#1E293B"
        )
        self.lbl_search_summary.pack(side="left")

        lbl_hint = tk.Label(
            summary_frame,
            text="💡 Mẹo: Nhấn đúp vào dòng để xem nội dung báo cáo gốc từ Zalo | Nhấn tiêu đề cột để sắp xếp",
            font=("Segoe UI", 8, "italic"),
            bg="#E2E8F0",
            fg="#64748B"
        )
        lbl_hint.pack(side="right")

        # 3. Data Table Treeview with Scrollbars
        table_frame = tk.Frame(self.tab_search, bg="#F4F6F8")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical")
        self.tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal")

        self.tree = ttk.Treeview(
            table_frame,
            selectmode="browse",
            yscrollcommand=self.tree_scroll_y.set,
            xscrollcommand=self.tree_scroll_x.set
        )

        self.tree_scroll_y.config(command=self.tree.yview)
        self.tree_scroll_x.config(command=self.tree.xview)

        self.tree_scroll_y.pack(side="right", fill="y")
        self.tree_scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.tag_configure("evenrow", background="#FFFFFF")
        self.tree.tag_configure("oddrow", background="#F8FAFC")
        self.tree.bind("<Double-1>", lambda e: self._view_selected_detail())

    def _switch_to_search_tab(self):
        """Chuyển sang Tab Tìm kiếm và focus vào ô nhập từ khóa."""
        self._refresh_filter_categories()
        curr_group_name = self.group_var.get().strip()
        if curr_group_name and curr_group_name in self.combo_filter_proj["values"]:
            self.combo_filter_proj.set(curr_group_name)
        self.notebook.select(self.tab_search)
        self.entry_keyword.focus_set()
        self.entry_keyword.select_range(0, tk.END)
        self._do_search()

    def _refresh_filter_categories(self):
        """Cập nhật danh sách dự án và hạng mục trong combobox từ DB."""
        try:
            projs = self.db.get_projects()
            proj_values = ["[Tất cả nhóm/dự án]"] + projs
            self.combo_filter_proj["values"] = proj_values
            
            cats = self.db.get_categories()
            cat_values = ["[Tất cả hạng mục]"] + cats
            self.combo_filter_cat["values"] = cat_values
        except Exception:
            pass

    def _switch_view_mode(self):
        """Chuyển giữa xem Hạng mục WBS và Chi tiết Tim cọc."""
        self._do_search()

    def _do_search(self):
        """Thực hiện tìm kiếm và hiển thị dữ liệu lên bảng."""
        keyword = self.entry_keyword.get().strip()
        proj = self.combo_filter_proj.get()
        cat = self.combo_filter_cat.get()
        latest_only = self.var_latest_only.get()
        view_type = self.var_view_type.get()

        if view_type == "items":
            self._search_and_show_items(keyword, cat, proj, latest_only)
        else:
            self._search_and_show_piles(keyword, proj, latest_only)

    def _reset_search(self):
        """Xóa toàn bộ điều kiện lọc và nạp lại tất cả."""
        self.entry_keyword.delete(0, tk.END)
        self.combo_filter_proj.set("[Tất cả nhóm/dự án]")
        self.combo_filter_cat.set("[Tất cả hạng mục]")
        self.var_latest_only.set(False)
        self._refresh_filter_categories()
        self._do_search()

    def _search_and_show_items(self, keyword: str, category: str, project: str, latest_only: bool):
        columns = ("stt", "project", "date", "shift", "contractor", "category", "sub_item", "unit", "shift_qty", "accumulated_qty", "design_qty", "rate", "status_note")
        self.tree["columns"] = columns
        self.tree["show"] = "headings"

        col_defs = [
            ("stt", "STT", 45, "center"),
            ("project", "Dự án / Nhóm Zalo", 150, "w"),
            ("date", "Ngày", 85, "center"),
            ("shift", "Ca", 85, "center"),
            ("contractor", "Nhà thầu", 110, "w"),
            ("category", "Hạng mục thi công", 160, "w"),
            ("sub_item", "Vị trí / Cấu kiện", 150, "w"),
            ("unit", "ĐVT", 55, "center"),
            ("shift_qty", "Ca này", 65, "e"),
            ("accumulated_qty", "Lũy kế", 70, "e"),
            ("design_qty", "Tổng TK", 70, "e"),
            ("rate", "Tiến độ", 75, "center"),
            ("status_note", "Tình trạng / Tim cọc", 220, "w"),
        ]

        for col_id, col_text, col_w, col_anchor in col_defs:
            self.tree.heading(col_id, text=col_text, command=lambda c=col_id: self._sort_tree(c))
            self.tree.column(col_id, width=col_w, minwidth=40, anchor=col_anchor)

        for item in self.tree.get_children():
            self.tree.delete(item)

        items = self.db.search_progress_items(keyword=keyword, category=category, project_name=project, latest_only=latest_only, limit=300)
        self.current_items = items

        total_shift = 0.0
        total_acc = 0.0
        total_pct = 0.0

        for idx, it in enumerate(items, 1):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            shift_q = it.get("shift_qty", 0.0)
            acc_q = it.get("accumulated_qty", 0.0)
            des_q = it.get("design_qty", 0.0)
            rate = it.get("completion_rate", 0.0)

            total_shift += shift_q
            total_acc += acc_q
            total_pct += rate

            str_shift = f"{shift_q:g}"
            str_acc = f"{acc_q:g}"
            str_des = f"{des_q:g}"
            str_rate = f"{rate:.1f}%" if des_q > 0 else "-"

            row_values = (
                idx,
                it.get("project_name", "-"),
                it.get("report_date", "-"),
                it.get("shift_name", "-"),
                it.get("contractor_name", "-"),
                it.get("category", "-"),
                it.get("sub_item", "-"),
                it.get("unit", "Cấu kiện"),
                str_shift,
                str_acc,
                str_des,
                str_rate,
                it.get("status_note", "-"),
            )
            self.tree.insert("", "end", iid=f"item_{it.get('id')}_{it.get('report_id')}", values=row_values, tags=(tag,))

        count = len(items)
        avg_pct = (total_pct / count) if count > 0 else 0.0
        mode_text = "Mới nhất" if latest_only else "Toàn bộ lịch sử"
        self.lbl_search_summary.config(
            text=f"📊 Tìm thấy: {count} hạng mục [{mode_text}] | Tổng KL ca: {total_shift:g} | Tổng lũy kế: {total_acc:g} | Tiến độ TB: {avg_pct:.1f}%"
        )

    def _search_and_show_piles(self, keyword: str, project: str, latest_only: bool):
        columns = ("stt", "project", "date", "shift", "contractor", "location", "pile_id", "status")
        self.tree["columns"] = columns
        self.tree["show"] = "headings"

        col_defs = [
            ("stt", "STT", 50, "center"),
            ("project", "Dự án / Nhóm Zalo", 150, "w"),
            ("date", "Ngày", 95, "center"),
            ("shift", "Ca", 95, "center"),
            ("contractor", "Nhà thầu", 130, "w"),
            ("location", "Vị trí / Mố trụ", 150, "w"),
            ("pile_id", "Mã cọc / Tim cọc", 140, "center"),
            ("status", "Trạng thái thi công hiện trường", 360, "w"),
        ]

        for col_id, col_text, col_w, col_anchor in col_defs:
            self.tree.heading(col_id, text=col_text, command=lambda c=col_id: self._sort_tree(c))
            self.tree.column(col_id, width=col_w, minwidth=50, anchor=col_anchor)

        for item in self.tree.get_children():
            self.tree.delete(item)

        piles = self.db.search_piles(keyword=keyword, project_name=project, latest_only=latest_only, limit=300)
        self.current_piles = piles

        for idx, p in enumerate(piles, 1):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            row_values = (
                idx,
                p.get("project_name", "-"),
                p.get("report_date", "-"),
                p.get("shift_name", "-"),
                p.get("contractor_name", "-"),
                p.get("location", "-"),
                p.get("pile_id", "-"),
                p.get("status", "-"),
            )
            self.tree.insert("", "end", iid=f"pile_{p.get('id')}_{p.get('report_id')}", values=row_values, tags=(tag,))

        count = len(piles)
        mode_text = "Hiện trạng mới nhất" if latest_only else "Lịch sử ghi nhận"
        self.lbl_search_summary.config(
            text=f"📍 Tìm thấy: {count} tim cọc hiện trường [{mode_text}]"
        )

    def _sort_tree(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_reverse = False
            self.sort_column = col

        l = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            l.sort(key=lambda t: float(t[0].replace("%", "").replace(",", "")), reverse=self.sort_reverse)
        except ValueError:
            l.sort(reverse=self.sort_reverse)

        for index, (val, k) in enumerate(l):
            self.tree.move(k, "", index)

    def _export_search_excel(self):
        keyword = self.entry_keyword.get().strip()
        proj = self.combo_filter_proj.get()
        cat = self.combo_filter_cat.get()
        filter_summary = f"Từ khóa: '{keyword or 'Tất cả'}' | Dự án: '{proj}' | Hạng mục: '{cat}'"

        if not self.current_items and not self.current_piles:
            messagebox.showwarning("Thông báo", "Không có dữ liệu để xuất Excel!")
            return

        try:
            path = self.excel_syncer.export_search_results(
                items=self.current_items,
                piles=self.current_piles,
                filter_summary=filter_summary
            )
            self._log(f"📑 Đã xuất kết quả lọc ra file Excel: {path}")
            if messagebox.askyesno("Thành công", f"Đã xuất dữ liệu lọc ra Excel thành công!\nĐường dẫn: {path}\n\nBạn có muốn mở file Excel ngay không?"):
                os.startfile(str(path))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất file Excel: {e}")

    def _view_selected_detail(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Hướng dẫn", "Vui lòng chọn một dòng trên bảng để xem chi tiết báo cáo.")
            return

        iid = selected[0]
        parts = iid.split("_")
        if len(parts) < 3:
            return
        report_id = int(parts[2])

        rep = self.db.get_report_detail(report_id)
        if not rep:
            messagebox.showwarning("Thông báo", "Không tìm thấy chi tiết báo cáo này trong CSDL.")
            return

        detail_win = tk.Toplevel(self.root)
        detail_win.title(f"📄 Chi Tiết Báo Cáo Ca #{report_id} — {rep.get('contractor_name', 'Dự án')}")
        detail_win.geometry("760x600")
        detail_win.minsize(680, 500)
        detail_win.configure(bg="#F4F6F8")

        h_box = tk.Frame(detail_win, bg="#1F4E79", padx=16, pady=12)
        h_box.pack(fill="x")

        tk.Label(
            h_box,
            text=f"BÁO CÁO THI CÔNG #{report_id} — NGÀY {rep.get('report_date')} ({rep.get('shift_name')})",
            font=("Segoe UI", 12, "bold"),
            bg="#1F4E79",
            fg="#FFFFFF"
        ).pack(anchor="w")

        info_text = f"Nhà thầu: {rep.get('contractor_name')} | Người báo cáo: {rep.get('reporter_name', 'Kỹ sư')} | Thời gian nạp: {rep.get('created_at')}"
        tk.Label(h_box, text=info_text, font=("Segoe UI", 9), bg="#1F4E79", fg="#D9E1F2").pack(anchor="w", pady=(2, 0))

        txt_box = tk.LabelFrame(detail_win, text=" 💬 Nội dung tin nhắn gốc từ Zalo ", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", padx=10, pady=8)
        txt_box.pack(fill="both", expand=True, padx=14, pady=8)

        st = scrolledtext.ScrolledText(txt_box, font=("Consolas", 10), bg="#FFFFFF", fg="#1E293B", wrap="word")
        st.pack(fill="both", expand=True)
        raw_content = rep.get("raw_text") or "Không có văn bản gốc."
        st.insert(tk.END, raw_content)
        st.config(state="disabled")

        btn_close = tk.Button(detail_win, text="Đóng cửa sổ", font=("Segoe UI", 9, "bold"), bg="#4B5563", fg="#FFFFFF", padx=16, pady=6, command=detail_win.destroy)
        btn_close.pack(pady=8)

    # ---------------- Quét dữ liệu nhóm & Nhập nhanh ----------------
    def _on_group_selected(self, event=None):
        """Khi người dùng chọn một nhóm khác trên Combobox."""
        selected = self.combo_group.get()
        self._log(f"🎯 Đã chọn nhóm mục tiêu: {selected}")
        self._scan_current_group_now(silent_if_empty=True)

    def _get_selected_group_info(self):
        """Lấy (thread_id, group_name) từ Combobox hiện tại."""
        selected = self.combo_group.get()
        if "[TẤT CẢ" in selected or not selected or "Đang tải" in selected:
            return None, "TẤT CẢ CÁC NHÓM CÔNG TRƯỜNG TỰ ĐỘNG"

        for g in self.groups_data:
            gid = str(g.get("groupId"))
            gname = g.get("name", "")
            if gid in selected or gname in selected:
                return gid, gname

        if "(ID: " in selected:
            gid = selected.split("(ID: ")[1].rstrip(")")
            gname = selected.split(" (ID:")[0]
            return gid, gname

        return None, selected

    def _scan_current_group_now(self, silent_if_empty=False):
        """Quét và phân tích ngay các tin nhắn hiện có của nhóm này."""
        thread_id, group_name = self._get_selected_group_info()
        self._log(f"🔍 Bắt đầu quét tin nhắn hiện có trong nhóm [{group_name}]...")

        found_msgs = []
        daemon_db = Path(r"C:\Users\baotu\.zalo-personal-mcp\zalo.db")
        if daemon_db.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(daemon_db))
                cur = conn.cursor()
                if not thread_id:
                    cur.execute("SELECT id, thread_id, msg_id, sender_name, content, timestamp FROM messages WHERE length(content) > 10 ORDER BY id DESC LIMIT 300")
                else:
                    cur.execute("SELECT id, thread_id, msg_id, sender_name, content, timestamp FROM messages WHERE thread_id = ? AND length(content) > 10 ORDER BY id DESC LIMIT 300", (str(thread_id),))
                found_msgs = cur.fetchall()
                conn.close()
            except Exception as e:
                self._log(f"⚠️ Lỗi đọc bộ đệm tin nhắn: {e}")

        # Thử lấy qua bridge nếu SQLite chưa có
        if not found_msgs and thread_id:
            try:
                msgs = self.bridge.get_recent_messages(thread_id=thread_id, count=50)
                found_msgs = [(0, thread_id, m.get("msgId"), m.get("senderName"), m.get("content"), m.get("timestamp")) for m in msgs if m.get("content")]
            except Exception:
                pass

        if not found_msgs:
            # Kiểm tra xem nhóm này đã có dữ liệu trong SQLite chưa
            existing_items = self.db.search_progress_items(project_name=group_name) if group_name else []
            if existing_items:
                self._log(f"ℹ️ Nhóm [{group_name}]: Đang có {len(existing_items)} hạng mục & tim cọc đã lưu trữ trong CSDL máy tính.")
                self._log(f"   (Chưa phát sinh thêm tin nhắn báo cáo mới nào trên Zalo kể từ lúc mở Bot).")
            else:
                self._log(f"ℹ️ Nhóm [{group_name}] chưa có tin nhắn nào trong bộ nhớ Zalo gần đây.")
                self._log("💡 GỢI Ý ĐỂ ĐỒNG BỘ DỮ LIỆU:")
                self._log("   👉 Cách 1 (Nhanh nhất): Copy tin nhắn báo cáo từ Zalo và bấm nút '📋 DÁN BÁO CÁO CŨ (COPY TỪ ZALO)' để nạp ngay!")
                self._log("   👉 Cách 2: Bất kỳ ai gửi/chuyển tiếp tin nhắn báo cáo vào nhóm trên Zalo, Bot đang chạy sẽ tự động bắt lấy và bóc tách ngay tức thì.")
            
            if not silent_if_empty:
                if existing_items:
                    messagebox.showinfo(
                        "Dữ liệu nhóm Zalo",
                        f"Nhóm [{group_name}] hiện đã lưu trữ sẵn {len(existing_items)} hạng mục trong CSDL hệ thống!\n\n"
                        "- Chưa có tin nhắn báo cáo mới nào phát sinh thêm trên Zalo kể từ lúc bật Bot.\n"
                        "- Bạn có thể bấm sang Tab '🔍 TÌM KIẾM & LỌC DỮ LIỆU' để xem toàn bộ chi tiết.\n"
                        "- Để bổ sung thêm các ca cũ khác: Bấm '📋 DÁN BÁO CÁO CŨ (COPY TỪ ZALO)'."
                    )
                else:
                    messagebox.showinfo(
                        "Thông báo quét nhóm",
                        f"Nhóm [{group_name}] chưa có tin nhắn nào trong bộ nhớ Zalo gần đây.\n\n"
                        "💡 Bạn có thể:\n"
                        "1. Bật Bot giám sát để tự động bắt tin nhắn báo cáo khi có người gửi vào nhóm.\n"
                        "2. Hoặc Copy tin nhắn báo cáo cũ từ Zalo rồi bấm nút '📋 DÁN BÁO CÁO CŨ' để nạp ngay!"
                    )
            return

        self._log(f"🔎 Đã tìm thấy {len(found_msgs)} tin nhắn trong nhóm. Đang kiểm tra cấu trúc báo cáo thi công...")
        imported_count = 0
        for row in reversed(found_msgs):
            _, tid, mid, sname, content, _ = row
            sname = sname or "Kỹ sư"
            if content and self.parser.is_construction_report(content):
                if str(mid) not in self.listener.processed_msg_ids:
                    self._log(f"📊 [BÁO CÁO CA MỚI] Nhận từ @{sname}")
                    res = self.brain.process_incoming_report(content, sender_name=sname, project_name=group_name)
                    self._log(f"   ➔ Đã nạp thành công #{res['report_id']} vào CSDL & Excel sống!")
                    self.listener.processed_msg_ids.add(str(mid))
                    imported_count += 1

        if imported_count > 0:
            auto_push_to_github(f"Auto-update: Quét nạp {imported_count} báo cáo từ nhóm [{group_name}]")
            self._log(f"✅ ĐÃ NẠP THÀNH CÔNG {imported_count} BÁO CÁO TỪ NHÓM [{group_name}]!")
            self._refresh_filter_categories()
            self._do_search()
            messagebox.showinfo("Thành công", f"Đã quét và nạp thành công {imported_count} báo cáo thi công từ nhóm [{group_name}]!\nSố liệu đã được đồng bộ vào CSDL, Excel & Web.")
        else:
            self._log(f"ℹ️ Trong {len(found_msgs)} tin nhắn đã quét, chưa có tin nào mang cấu trúc báo cáo thi công (Ca này/Lũy kế/Tổng TK).")
            self._log("🟢 Bot tiếp tục thường trực: Khi có tin nhắn báo cáo mới gửi vào nhóm, hệ thống sẽ tự động lọc ngay.")
            if not silent_if_empty:
                messagebox.showinfo("Kết quả quét", f"Đã quét {len(found_msgs)} tin nhắn trong nhóm [{group_name}], nhưng không có tin nhắn nào dạng báo cáo thi công.")

    def _quick_paste_report_dialog(self):
        """Mở cửa sổ cho phép người dùng dán (Ctrl+V) tin nhắn báo cáo từ Zalo vào nạp ngay lập tức."""
        win = tk.Toplevel(self.root)
        win.title("📋 Dán Báo Cáo Thi Công Từ Zalo")
        win.geometry("680x580")
        win.minsize(580, 480)
        win.configure(bg="#F4F6F8")

        # Header Box
        h_box = tk.Frame(win, bg="#0E6655", padx=16, pady=12)
        h_box.pack(fill="x")
        tk.Label(h_box, text="📋 NẠP LỊCH SỬ BÁO CÁO CÔNG TRƯỜNG (1 CA HOẶC NHIỀU CA CÙNG LÚC)", font=("Segoe UI", 11, "bold"), bg="#0E6655", fg="#FFFFFF").pack(anchor="w")
        tk.Label(h_box, text="💡 Mẹo: Bạn có thể bôi đen copy NHIỀU TIN NHẮN cùng lúc từ Zalo (hoặc ngăn cách bằng '---') dán vào đây để nạp bức tranh toàn cảnh!", font=("Segoe UI", 9), bg="#0E6655", fg="#D1F2EB").pack(anchor="w", pady=(2, 0))

        # Project name selection
        body = tk.Frame(win, bg="#F4F6F8", padx=16, pady=10)
        body.pack(fill="both", expand=True)

        row_p = tk.Frame(body, bg="#F4F6F8")
        row_p.pack(fill="x", pady=(0, 8))
        tk.Label(row_p, text="Tên Dự án / Gói thầu / Nhóm:", font=("Segoe UI", 9, "bold"), bg="#F4F6F8").pack(side="left")

        current_g = self.combo_group.get()
        g_name = current_g.split(" (ID:")[0].replace("[TẤT CẢ CÁC NHÓM CÔNG TRƯỜNG TỰ ĐỘNG]", "PMU: BĂNG HẠ TẦNG OLP").strip()
        entry_proj = ttk.Entry(row_p, font=("Segoe UI", 10), width=35)
        entry_proj.pack(side="left", padx=8, fill="x", expand=True)
        entry_proj.insert(0, g_name or "PMU: BĂNG HẠ TẦNG OLP")

        row_label = tk.Frame(body, bg="#F4F6F8")
        row_label.pack(fill="x", pady=(4, 2))
        tk.Label(row_label, text="Nội dung báo cáo (Ctrl+V để dán hoặc Chọn File):", font=("Segoe UI", 10, "bold"), bg="#F4F6F8").pack(side="left")

        def choose_file():
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Chọn file sao lưu Zalo (.txt, .json, .csv, .zip)",
                filetypes=[
                    ("Tất cả file hỗ trợ", "*.txt *.json *.csv *.xlsx *.zip"),
                    ("File văn bản (*.txt)", "*.txt"),
                    ("File JSON (*.json)", "*.json"),
                    ("File Excel / CSV (*.xlsx, *.csv)", "*.xlsx *.csv"),
                    ("File nén Zip (*.zip)", "*.zip")
                ],
                parent=win
            )
            if file_path:
                try:
                    p = Path(file_path)
                    content = ""
                    if ".zl" in p.name.lower():
                        messagebox.showwarning(
                            "Định dạng sao lưu Zalo (.zl)",
                            f"File '{p.name}' là bản sao lưu mã hóa toàn bộ tài khoản Zalo của VNG (dung lượng lớn tới ~26GB gồm cả ảnh, video, dữ liệu riêng tư).\n\n"
                            "Máy chủ Zalo mã hóa độc quyền file này nên phần mềm ngoài không thể giải mã trực tiếp.\n\n"
                            "👉 CÁCH LẤY NHANH TIN NHẮN NHÓM 307 (Chỉ mất 10 giây):\n"
                            "1. Trên Zalo PC, mở nhóm 307 HỒ SƠ SẠT LỞ.\n"
                            "2. Chuột phải vào tin nhắn -> 'Chọn nhiều tin nhắn' -> Tick các báo cáo cũ -> Bấm 'Sao chép'.\n"
                            "3. Bấm chuột vào ô màu trắng bên dưới -> Bấm Ctrl+V để Dán -> Bấm '🚀 BÓC TÁCH & NẠP'!",
                            parent=win
                        )
                        return
                    elif p.suffix.lower() == ".txt":
                        content = p.read_text(encoding="utf-8", errors="ignore")
                    elif p.suffix.lower() == ".json":
                        import json
                        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
                        if isinstance(data, list):
                            texts = [d.get("content") or d.get("message") or str(d) for d in data if isinstance(d, dict)]
                            content = "\n---\n".join(texts)
                        elif isinstance(data, dict):
                            texts = [v.get("content") or str(v) for v in data.values() if isinstance(v, dict)]
                            content = "\n---\n".join(texts)
                        else:
                            content = str(data)
                    elif p.suffix.lower() == ".zip":
                        import zipfile
                        if not zipfile.is_zipfile(file_path):
                            raise ValueError(f"File '{p.name}' không phải định dạng ZIP tiêu chuẩn (đây là file sao lưu mã hóa .zl đổi tên).")
                        with zipfile.ZipFile(file_path, 'r') as z:
                            txt_names = [n for n in z.namelist() if n.endswith(('.txt', '.json', '.csv'))]
                            if not txt_names:
                                raise ValueError("Trong file Zip không tìm thấy file văn bản .txt hoặc .json nào chứa tin nhắn.")
                            all_parts = []
                            for n in txt_names:
                                with z.open(n) as f:
                                    all_parts.append(f.read().decode('utf-8', errors='ignore'))
                            content = "\n---\n".join(all_parts)
                    else:
                        content = p.read_text(encoding="utf-8", errors="ignore")

                    if content:
                        txt_input.delete("1.0", tk.END)
                        txt_input.insert("1.0", content)
                        messagebox.showinfo("Đã nạp file", f"Đã đọc thành công nội dung từ file:\n{p.name}\n\nĐộ dài: {len(content)} ký tự. Hãy bấm '🚀 BÓC TÁCH' bên dưới để nạp vào CSDL!", parent=win)
                except Exception as ex:
                    messagebox.showerror("Lỗi đọc file", f"Không thể đọc file: {ex}", parent=win)

        btn_choose = tk.Button(
            row_label,
            text="📂 CHỌN FILE SAO LƯU (.TXT / .JSON / .ZIP)",
            font=("Segoe UI", 9, "bold"),
            bg="#1F4E79",
            fg="#FFFFFF",
            padx=10,
            pady=2,
            cursor="hand2",
            relief="raised",
            command=choose_file
        )
        btn_choose.pack(side="right")

        txt_input = scrolledtext.ScrolledText(body, font=("Consolas", 10), bg="#FFFFFF", fg="#1E293B", wrap="word", relief="groove", bd=1)
        txt_input.pack(fill="both", expand=True, pady=(2, 10))
        txt_input.focus_set()

        def do_import():
            raw_text = txt_input.get("1.0", tk.END).strip()
            if not raw_text:
                messagebox.showwarning("Thông báo", "Vui lòng dán nội dung tin nhắn báo cáo vào ô văn bản trước nhé!", parent=win)
                return

            proj = entry_proj.get().strip() or "PMU: BĂNG HẠ TẦNG OLP"
            blocks = self.parser.split_multiple_reports(raw_text)

            if len(blocks) > 1:
                self._log(f"📦 PHÁT HIỆN BATCH NẠP HÀNG LOẠT: Gồm {len(blocks)} báo cáo ca riêng biệt cho dự án [{proj}]!")
                imported_ids = []
                for idx, block in enumerate(blocks, 1):
                    try:
                        res = self.brain.process_incoming_report(block, sender_name=f"Kỹ sư (Ca {idx})", project_name=proj)
                        rep_id = res['report_id']
                        rep_date = res['parsed'].get('report_date', '-')
                        rep_shift = res['parsed'].get('shift_name', '-')
                        imported_ids.append(rep_id)
                        self._log(f"   ➔ [{idx}/{len(blocks)}] Đã nạp Báo cáo #{rep_id} ({rep_shift} - {rep_date})")
                    except Exception as err:
                        self._log(f"   ⚠️ Lỗi nạp khối {idx}: {err}")

                self._log(f"🎉 ĐÃ HOÀN TẤT ĐỒNG BỘ {len(imported_ids)} BÁO CÁO VÀO CSDL & EXCEL SỐNG!")
                auto_push_to_github(f"Batch-import: Nạp {len(imported_ids)} ca lịch sử cho [{proj}]")
                self._log("   • Đã đồng bộ toàn bộ bức tranh lịch sử lên Web Dashboard.")
                self._refresh_filter_categories()
                self._do_search()
                messagebox.showinfo(
                    "Đồng Bộ Lịch Sử Thành Công",
                    f"🎉 ĐÃ ĐỒNG BỘ THÀNH CÔNG BỨC TRANH TOÀN CẢNH!\n\n"
                    f"• Đã nạp thành công: {len(imported_ids)} báo cáo ca lịch sử.\n"
                    f"• CSDL SQLite đã cập nhật đầy đủ toàn bộ quá trình thi công.\n"
                    f"• File Excel sống đã tính toán lại toàn bộ lũy kế & tỷ lệ hoàn thành.\n"
                    f"• Web Dashboard đã đồng bộ trực tuyến.",
                    parent=win
                )
                win.destroy()
            else:
                self._log(f"📥 Đang bóc tách báo cáo thực tế cho dự án: [{proj}]...")
                try:
                    res = self.brain.process_incoming_report(raw_text, sender_name="Kỹ sư (Nhập Zalo)", project_name=proj)
                    self._log(f"✅ ĐÃ NẠP THÀNH CÔNG BÁO CÁO #{res['report_id']}!")
                    self._log(f"   • Đã cập nhật vào CSDL, Excel & Bảng điều hành HTML.")
                    auto_push_to_github(f"Real-data: Báo cáo #{res['report_id']} cho [{proj}]")
                    self._log("   • Đã đồng bộ trực tuyến lên GitHub Pages.")
                    self._refresh_filter_categories()
                    self._do_search()
                    messagebox.showinfo("Thành công", f"Đã nạp thành công Báo cáo #{res['report_id']}!\nSố liệu đã được tính toán và đồng bộ vào CSDL, Excel & Web.", parent=win)
                    win.destroy()
                except Exception as e:
                    messagebox.showerror("Lỗi", f"Không thể xử lý báo cáo: {e}", parent=win)

        btn_box = tk.Frame(body, bg="#F4F6F8")
        btn_box.pack(fill="x")

        btn_submit = tk.Button(
            btn_box,
            text="🚀 BÓC TÁCH & NẠP VÀO HỆ THỐNG NGAY",
            font=("Segoe UI", 10, "bold"),
            bg="#0E6655",
            fg="#FFFFFF",
            padx=16,
            pady=8,
            cursor="hand2",
            relief="raised",
            command=do_import
        )
        btn_submit.pack(side="left")

        btn_cancel = tk.Button(
            btn_box,
            text="Hủy bỏ",
            font=("Segoe UI", 9),
            bg="#E2E8F0",
            fg="#1E293B",
            padx=14,
            pady=8,
            cursor="hand2",
            relief="flat",
            command=win.destroy
        )
        btn_cancel.pack(side="right")

    # ---------------- Các hàm nền tảng & Zalo ----------------
    def _log(self, text: str):
        now_str = time.strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{now_str}] {text}\n")
        self.txt_log.see(tk.END)

    def _check_zalo_status_async(self):
        def worker():
            status = self.bridge.check_connection()
            if status.get("authenticated", False):
                user = status.get("displayName", "Người dùng Zalo")
                self.lbl_zalo_status.config(text=f"🟢 Đã kết nối: {user}", fg="#2E7A48")
                self._load_zalo_groups()
            else:
                self.lbl_zalo_status.config(text="🔴 Zalo chưa bật hoặc chưa đăng nhập", fg="#B8362A")
        threading.Thread(target=worker, daemon=True).start()

    def _reconnect_zalo(self):
        self._log("Đang kích hoạt Zalo Daemon ngầm...")
        def worker():
            ensure_daemon_running(self.bridge)
            self._check_zalo_status_async()
        threading.Thread(target=worker, daemon=True).start()

    def _load_zalo_groups(self):
        def worker():
            try:
                import httpx
                res = httpx.get(f"{self.bridge.base_url}/groups", timeout=6.0)
                if res.status_code == 200:
                    data = res.json().get("data", [])
                    self.groups_data = data
                    self.group_name_map = {str(g.get("groupId")): g.get("name", "") for g in data}
                    items = ["[TẤT CẢ CÁC NHÓM CÔNG TRƯỜNG TỰ ĐỘNG]"]
                    for g in data:
                        items.append(f"{g.get('name')} (ID: {g.get('groupId')})")
                    self.combo_group["values"] = items
                    # Ưu tiên các nhóm thi công công trình
                    pmu_match = next((i for i in items if any(k in i.upper() for k in ["307", "CẦU", "MỐ", "TRỤ", "CAO TỐC", "THI CÔNG", "TDA2"])), None)
                    if pmu_match:
                        self.combo_group.set(pmu_match)
                    else:
                        self.combo_group.set(items[0])
                    self._log(f"Đã tải {len(data)} nhóm từ tài khoản Zalo.")
            except Exception as e:
                self._log(f"Chưa lấy được danh sách nhóm Zalo: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def _toggle_bot(self):
        if not self.bot_running:
            selected = self.combo_group.get()
            self.bot_running = True
            self.btn_toggle_bot.config(
                text="⏹️ DỪNG BOT GIÁM SÁT REALTIME",
                bg="#B8362A",
                activebackground="#8E2319"
            )
            self.lbl_bot_state.config(text="🟢 Bot Đang Chạy Realtime", fg="#2E7A48")
            self._log(f"🚀 KÍCH HOẠT BOT REALTIME THÀNH CÔNG! Mục tiêu: {selected}")
            self._log("📡 Kênh lắng nghe trực tiếp đã mở: Bất kỳ ai gửi tin nhắn vào nhóm, Bot sẽ nhận diện và bóc tách ngay tức thì!")

            # Quét kiểm tra ngay các tin có sẵn
            threading.Thread(target=lambda: self._scan_current_group_now(silent_if_empty=True), daemon=True).start()

            self.bot_thread = threading.Thread(target=self._bot_realtime_loop, daemon=True)
            self.bot_thread.start()
        else:
            self.bot_running = False
            self.btn_toggle_bot.config(
                text="▶️ BẬT BOT GIÁM SÁT REALTIME (TỰ ĐỘNG BẮT BÁO CÁO ZALO)",
                bg="#0E6655",
                activebackground="#094A3E"
            )
            self.lbl_bot_state.config(text="⚪ Bot đã Dừng", fg="#5A6A80")
            self._log("⏹️ Đã dừng giám sát bot.")

    def _bot_realtime_loop(self):
        """
        Động cơ lắng nghe thời gian thực (Real-time Event Engine).
        Đọc trực tiếp từ cơ sở dữ liệu Zalo với độ trễ < 800ms.
        Bắt ngay lập tức mọi tin nhắn báo cáo từ các nhóm công trường.
        """
        daemon_db_path = Path(r"C:\Users\baotu\.zalo-personal-mcp\zalo.db")
        last_seen_id = 0

        # Lấy max id ban đầu
        if daemon_db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(daemon_db_path))
                cur = conn.cursor()
                cur.execute("SELECT MAX(id) FROM messages")
                row = cur.fetchone()
                if row and row[0]:
                    last_seen_id = int(row[0])
                conn.close()
            except Exception:
                pass

        self._log(f"🟢 [REALTIME ZALO ENGINE] Đang theo dõi trực tiếp từ ID #{last_seen_id}...")
        last_target_desc = ""

        while self.bot_running:
            target_tid, target_tname = self._get_selected_group_info()

            if target_tname != last_target_desc:
                last_target_desc = target_tname
                self._log(f"🎯 [MỤC TIÊU GIÁM SÁT] ➔ {target_tname}")

            # Đọc tin nhắn mới từ daemon SQLite
            if daemon_db_path.exists():
                try:
                    import sqlite3
                    conn = sqlite3.connect(str(daemon_db_path))
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT id, thread_id, msg_id, sender_name, content, timestamp FROM messages WHERE id > ? ORDER BY id ASC LIMIT 20",
                        (last_seen_id,)
                    )
                    rows = cur.fetchall()
                    conn.close()

                    for r in rows:
                        last_seen_id = int(r["id"])
                        msg_tid = str(r["thread_id"])
                        mid = str(r["msg_id"] or r["id"])
                        sname = r["sender_name"] or "Kỹ sư"
                        content = (r["content"] or "").strip()

                        # Xác định xem tin nhắn có thuộc nhóm mục tiêu hay không
                        is_target = False
                        matched_group_name = self.group_name_map.get(msg_tid, f"Nhóm {msg_tid}")

                        if target_tid:
                            # Đang chọn 1 nhóm cụ thể
                            if msg_tid == str(target_tid):
                                is_target = True
                        else:
                            # Đang chọn [TẤT CẢ CÁC NHÓM CÔNG TRƯỜNG TỰ ĐỘNG]
                            keywords = ["307", "CẦU", "MỐ", "TRỤ", "CAO TỐC", "THI CÔNG", "TIẾN ĐỘ", "KCS", "HỒ SƠ", "DỰ ÁN", "PMU", "BÌNH VÀNG", "TDA2", "TUYÊN QUANG", "HÀ GIANG"]
                            if any(k in matched_group_name.upper() for k in keywords):
                                is_target = True

                        if is_target and content:
                            # Kiểm tra xem có phải báo cáo thi công không
                            if self.parser.is_construction_report(content):
                                self._log(f"🎯 [BÁO CÁO CA MỚI PHÁT HIỆN] Từ @{sname} tại nhóm [{matched_group_name}]")
                                res = self.brain.process_incoming_report(content, sender_name=sname, project_name=matched_group_name)
                                self._log(f"   ➔ Đã bóc tách thành công Báo cáo #{res['report_id']}!")
                                self._log(f"   ➔ Số liệu đã ghi vào CSDL SQLite & Excel sống.")

                                # Gửi phản hồi Zalo
                                try:
                                    self.bridge.send_message(res["reply_text"], thread_id=msg_tid)
                                    self._log(f"   ➔ Đã gửi phản hồi xác nhận tự động vào Zalo.")
                                except Exception:
                                    pass

                                # Đồng bộ GitHub Pages
                                auto_push_to_github(f"Realtime: Báo cáo #{res['report_id']} từ @{sname} [{matched_group_name}]")
                                self._log(f"   ➔ 🌐 Đã đồng bộ trực tuyến lên GitHub Pages!")

                                # Cập nhật giao diện
                                self.root.after(0, self._refresh_filter_categories)
                                self.root.after(0, self._do_search)
                            else:
                                # In thông báo tin nhắn thường để người dùng thấy bot hoàn toàn đang sống và nghe thấy
                                short_content = content.replace("\n", " ")
                                if len(short_content) > 60:
                                    short_content = short_content[:60] + "..."
                                self._log(f"💬 [@{sname} - {matched_group_name}]: {short_content}")
                except Exception:
                    pass

            time.sleep(0.8)

    def _open_web_dashboard(self):
        url = "https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/"
        self._log(f"Đang mở Web Dashboard: {url}")
        webbrowser.open(url)

    def _open_excel(self):
        excel_path = self.excel_syncer.excel_path
        if excel_path.exists():
            self._log(f"Đang mở file Excel: {excel_path}")
            os.startfile(str(excel_path))
        else:
            messagebox.showwarning("Thông báo", "File Excel chưa được tạo. Hãy nạp báo cáo từ Zalo trước nhé!")

    def _resync_all_system(self):
        """Đồng bộ hóa lại toàn bộ: CSDL -> Excel -> Web Dashboard GitHub."""
        self._log("⚡ Đang tiến hành đồng bộ hóa lại toàn bộ hệ thống...")
        def worker():
            try:
                # 1. Quét tin nhắn mới trong Zalo nếu có
                thread_id, group_name = self._get_selected_group_info()
                self._scan_current_group_now(silent_if_empty=True)

                # 2. Đồng bộ Excel
                summary = self.db.get_latest_project_summary()
                piles = self.db.get_active_piles()
                self.excel_syncer.sync_to_excel(summary, piles, project_name=group_name)
                self._log("📑 Đã đồng bộ lại toàn bộ số liệu vào file Excel sống.")

                # 3. Đồng bộ GitHub Pages
                ok = auto_push_to_github("Đồng bộ toàn bộ từ Bảng điều khiển")
                if ok:
                    self._log("✅ ĐỒNG BỘ GITHUB PAGES THÀNH CÔNG!")
                
                # 4. Làm mới giao diện
                self.root.after(0, self._refresh_filter_categories)
                self.root.after(0, self._do_search)

                total_items = len(self.db.search_progress_items())
                total_piles = len(self.db.search_piles())
                self._log(f"🎉 ĐỒNG BỘ TOÀN DIỆN HOÀN TẤT! Hiện có {total_items} hạng mục & {total_piles} tim cọc.")
                messagebox.showinfo(
                    "Đồng Bộ Thành Công",
                    f"Đã đồng bộ hóa lại toàn bộ hệ thống thành công!\n\n"
                    f"- File Excel: Đã cập nhật công thức và số liệu mới nhất.\n"
                    f"- Web Dashboard: Đã đồng bộ trực tuyến lên GitHub.\n"
                    f"- Tổng hạng mục đang quản lý: {total_items}\n"
                    f"- Tổng tim cọc hiện trường: {total_piles}"
                )
            except Exception as e:
                self._log(f"⚠️ Lỗi đồng bộ: {e}")
                messagebox.showerror("Lỗi", f"Không thể hoàn tất đồng bộ: {e}")

        threading.Thread(target=worker, daemon=True).start()


def run_app():
    root = tk.Tk()
    app = DataBossControlApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()
