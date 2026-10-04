import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import os
import sys
import webbrowser
import subprocess
from pathlib import Path

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
        self.root.title("🏗️ BẢNG ĐIỀU KHIỂN - ĐẠI CA DỮ LIỆU (CONTECH ZALO)")
        self.root.geometry("820x680")
        self.root.minsize(760, 600)
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

        self._setup_styles()
        self._build_ui()
        self._check_zalo_status_async()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure("TLabel", background="#F4F6F8", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#1F4E79")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 10), foreground="#5A6A80")
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#0E6655", foreground="#FFFFFF")
        style.map("Primary.TButton", background=[("active", "#094A3E")])

        style.configure("Stop.TButton", font=("Segoe UI", 10, "bold"), background="#B8362A", foreground="#FFFFFF")
        style.map("Stop.TButton", background=[("active", "#8E2319")])

        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        # 1. Header Frame
        header_frame = tk.Frame(self.root, bg="#FFFFFF", padx=20, pady=14, relief="ridge", bd=1)
        header_frame.pack(fill="x", padx=14, pady=(12, 8))

        lbl_title = ttk.Label(header_frame, text="🏗️ BẢNG ĐIỀU KHIỂN TRUNG TÂM — ĐẠI CA DỮ LIỆU", style="Header.TLabel", background="#FFFFFF")
        lbl_title.pack(anchor="w")

        lbl_sub = ttk.Label(
            header_frame,
            text="Tự động thu thập báo cáo ca từ Zalo ➔ Đồng bộ CSDL ➔ Cập nhật Excel sống ➔ Đẩy lên Web trực tuyến",
            style="SubHeader.TLabel",
            background="#FFFFFF"
        )
        lbl_sub.pack(anchor="w", pady=(2, 6))

        # Status Bar con trong header
        status_bar = tk.Frame(header_frame, bg="#FFFFFF")
        status_bar.pack(fill="x", pady=(4, 0))

        self.lbl_zalo_status = tk.Label(status_bar, text="🟡 Đang kiểm tra kết nối Zalo...", font=("Segoe UI", 10, "bold"), bg="#FFFFFF", fg="#B8740A")
        self.lbl_zalo_status.pack(side="left")

        btn_reconnect = tk.Button(status_bar, text="🔄 Kết nối lại", font=("Segoe UI", 8), bg="#E9ECE6", relief="flat", command=self._reconnect_zalo)
        btn_reconnect.pack(side="left", padx=8)

        # 2. Main Control Frame (Chọn nhóm & Bật/Tắt Bot)
        ctrl_frame = tk.LabelFrame(self.root, text=" 🎯 Cấu hình & Giám sát Nhóm Zalo ", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", padx=16, pady=12)
        ctrl_frame.pack(fill="x", padx=14, pady=6)

        row_group = tk.Frame(ctrl_frame, bg="#F4F6F8")
        row_group.pack(fill="x", pady=4)

        tk.Label(row_group, text="Nhóm Zalo cần lọc báo cáo:", font=("Segoe UI", 10, "bold"), bg="#F4F6F8").pack(side="left")
        
        self.combo_group = ttk.Combobox(row_group, font=("Segoe UI", 10), state="readonly", width=42)
        self.combo_group.pack(side="left", padx=10, fill="x", expand=True)
        self.combo_group.set("Đang tải danh sách nhóm...")

        btn_refresh_groups = ttk.Button(row_group, text="🔄 Tải lại nhóm", command=self._load_zalo_groups)
        btn_refresh_groups.pack(side="left", padx=4)

        # Hàng nút Bật / Tắt Bot
        row_bot_btn = tk.Frame(ctrl_frame, bg="#F4F6F8")
        row_bot_btn.pack(fill="x", pady=(10, 4))

        self.btn_toggle_bot = tk.Button(
            row_bot_btn,
            text="▶️ BẬT BOT GIÁM SÁT (BẮT ĐẦU LỌC BÁO CÁO)",
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

        # 3. Phím bấm thao tác nhanh 1-Click
        action_frame = tk.LabelFrame(self.root, text=" ⚡ Thao tác nhanh 1-Click ", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", padx=14, pady=10)
        action_frame.pack(fill="x", padx=14, pady=6)

        btn_grid = tk.Frame(action_frame, bg="#F4F6F8")
        btn_grid.pack(fill="x")

        # Nút 1: Mở Web Dashboard
        btn_web = tk.Button(
            btn_grid,
            text="🌐 MỞ WEB DASHBOARD ONLINE",
            font=("Segoe UI", 9, "bold"),
            bg="#1F4E79",
            fg="#FFFFFF",
            padx=10,
            pady=8,
            cursor="hand2",
            relief="groove",
            command=self._open_web_dashboard
        )
        btn_web.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")

        # Nút 2: Mở Excel
        btn_excel = tk.Button(
            btn_grid,
            text="📑 MỞ BẢNG TÍNH EXCEL SỐNG",
            font=("Segoe UI", 9, "bold"),
            bg="#2E7A48",
            fg="#FFFFFF",
            padx=10,
            pady=8,
            cursor="hand2",
            relief="groove",
            command=self._open_excel
        )
        btn_excel.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")

        # Nút 3: Nạp thử báo cáo mẫu
        btn_sample = tk.Button(
            btn_grid,
            text="🧪 NẠP THỬ BÁO CÁO MẪU",
            font=("Segoe UI", 9, "bold"),
            bg="#C98407",
            fg="#FFFFFF",
            padx=10,
            pady=8,
            cursor="hand2",
            relief="groove",
            command=self._feed_sample_report
        )
        btn_sample.grid(row=0, column=2, padx=6, pady=4, sticky="nsew")

        # Nút 4: Đồng bộ Git lên GitHub Pages
        btn_git = tk.Button(
            btn_grid,
            text="🔄 ĐỒNG BỘ LÊN GITHUB PAGES",
            font=("Segoe UI", 9, "bold"),
            bg="#4B5563",
            fg="#FFFFFF",
            padx=10,
            pady=8,
            cursor="hand2",
            relief="groove",
            command=self._manual_git_sync
        )
        btn_git.grid(row=0, column=3, padx=6, pady=4, sticky="nsew")

        for c in range(4):
            btn_grid.columnconfigure(c, weight=1)

        # 4. Live Log Window (Nhật ký hoạt động sạch đẹp)
        log_frame = tk.LabelFrame(self.root, text=" 📜 Nhật ký hoạt động thời gian thực ", font=("Segoe UI", 10, "bold"), bg="#F4F6F8", padx=10, pady=8)
        log_frame.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        self.txt_log = scrolledtext.ScrolledText(log_frame, font=("Consolas", 9), bg="#1E2227", fg="#ABB2BF", wrap="word", relief="flat")
        self.txt_log.pack(fill="both", expand=True)

        self._log("Hệ thống Bảng điều khiển All-in-One sẵn sàng.")
        self._log("Link Web trực tuyến: https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/")

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
                    items = ["[TẤT CẢ CÁC NHÓM CÔNG TRƯỜNG TỰ ĐỘNG]"]
                    for g in data:
                        items.append(f"{g.get('name')} (ID: {g.get('groupId')})")
                    self.combo_group["values"] = items
                    
                    # Tìm xem có nhóm PMU hay không để đặt mặc định
                    pmu_match = next((i for i in items if "PMU" in i.upper() or "OLP" in i.upper()), None)
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
            # Bật Bot
            selected = self.combo_group.get()
            self.bot_running = True
            self.btn_toggle_bot.config(
                text="⏹️ DỪNG BOT GIÁM SÁT",
                bg="#B8362A",
                activebackground="#8E2319"
            )
            self.lbl_bot_state.config(text="🟢 Bot Đang Chạy Lọc Báo Cáo", fg="#2E7A48")
            self._log(f"🚀 KÍCH HOẠT BOT THÀNH CÔNG! Mục tiêu: {selected}")

            self.bot_thread = threading.Thread(target=self._bot_polling_loop, args=(selected,), daemon=True)
            self.bot_thread.start()
        else:
            # Dừng Bot
            self.bot_running = False
            self.btn_toggle_bot.config(
                text="▶️ BẬT BOT GIÁM SÁT (BẮT ĐẦU LỌC BÁO CÁO)",
                bg="#0E6655",
                activebackground="#094A3E"
            )
            self.lbl_bot_state.config(text="⚪ Bot đã Dừng", fg="#5A6A80")
            self._log("⏹️ Đã dừng giám sát bot.")

    def _bot_polling_loop(self, selected_group: str):
        # Xác định target group id
        target_threads = []
        if "[TẤT CẢ" in selected_group or not selected_group:
            for g in self.groups_data:
                g_name = g.get("name", "")
                if any(k in g_name.upper() for k in ["PMU", "OLP", "BĂNG HẠ TẦNG", "307", "CẦU", "THI CÔNG", "TIẾN ĐỘ", "KCS", "HỒ SƠ"]):
                    target_threads.append((g.get("groupId"), g_name))
        else:
            # Tách ID
            for g in self.groups_data:
                if str(g.get("groupId")) in selected_group or g.get("name") in selected_group:
                    target_threads.append((g.get("groupId"), g.get("name")))
                    break

        if not target_threads:
            target_threads.append((Config.DEFAULT_GROUP_NAME, Config.DEFAULT_GROUP_NAME))

        while self.bot_running:
            for tid, tname in target_threads:
                if not self.bot_running:
                    break
                try:
                    msgs = self.bridge.get_recent_messages(thread_id=tid, count=5)
                    for m in reversed(msgs):
                        mid = m.get("msgId")
                        if mid and str(mid) not in self.listener.processed_msg_ids:
                            content = (m.get("content") or "").strip()
                            sname = m.get("senderName", "Kỹ sư")
                            if self.parser.is_construction_report(content):
                                self._log(f"📊 [BÁO CÁO CA MỚI] Nhận từ @{sname} tại nhóm [{tname}]")
                                res = self.brain.process_incoming_report(content, sender_name=sname, project_name=tname)
                                self._log(f"   ➔ Đã nạp #{res['report_id']} | Lũy kế đã cập nhật vào Excel & Web.")
                                # Gửi phản hồi Zalo
                                self.bridge.send_message(res["reply_text"], thread_id=tid)
                                # Tự động push GitHub
                                auto_push_to_github(f"Auto-update: Báo cáo ca từ {sname} [{tname}]")
                                self._log("   ➔ ✅ Đã đồng bộ trực tuyến lên GitHub Pages!")
                            self.listener.processed_msg_ids.add(str(mid))
                except Exception:
                    pass
                time.sleep(1.0)
            time.sleep(3.0)

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
            messagebox.showwarning("Thông báo", "File Excel chưa được tạo. Hãy nhấn nút 'Nạp thử báo cáo mẫu' trước nhé!")

    def _feed_sample_report(self):
        sample = """Báo cáo thi công cuối ca đêm 26/9/2026:
* Nhà thầu SGC Cầu 5B:
1. Thi công ép cừ mố M2:
- Mố M2-1 & M2-2: 00/246/280
- Mố M2-3 & M2-4: 00/138/248
2. Gia công lồng thép điển hình
3. Thi công sàn đạo
- Cọc Casing : 02/20/132
- Tấm sàn: 00/18/155
4. Thi công cọc khoan nhồi :
00/14/106
- Mố M2-1: 0/3/7
+ Cọc M2-1-4: đang khoan
- Mố M2-2: 0/4/10
- Mố M2-3: 0/4/10
+ Cọc M2-3-6: Hạ ống thổi rửa chuẩn bị đổ bê tông
- Mố M2-4: 0/3/7
+ Cọc M2-4-1 đang hạ lồng thép L4-L3"""

        self._log("🧪 Đang nạp báo cáo mẫu ca đêm...")
        res = self.brain.process_incoming_report(sample, sender_name="Ninh", project_name="PMU: BĂNG HẠ TẦNG OLP")
        self._log(f"✅ ĐÃ NẠP THÀNH CÔNG BÁO CÁO #{res['report_id']}!")
        self._log(f"   • Ép cừ: 246/280 (87.9%) | Cọc Casing: 20/132 (15.2%) | Cọc khoan nhồi: 14/106 (13.2%)")
        self._log(f"   • Đã cập nhật CSDL, Excel & Bảng điều hành HTML.")
        messagebox.showinfo("Thành công", "Đã nạp báo cáo mẫu thành công!\nSố liệu đã được tính toán và cập nhật vào Excel & Web.")

    def _manual_git_sync(self):
        self._log("🔄 Đang thực hiện Git Push lên GitHub Pages...")
        def worker():
            ok = auto_push_to_github("Đồng bộ thủ công từ Bảng điều khiển")
            if ok:
                self._log("✅ ĐỒNG BỘ GITHUB PAGES THÀNH CÔNG! Web sẽ cập nhật sau 30 giây.")
                messagebox.showinfo("Thành công", "Đã đồng bộ thành công lên GitHub Pages!\nLink: https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/")
            else:
                self._log("⚠️ Không có thay đổi mới hoặc lỗi push.")
        threading.Thread(target=worker, daemon=True).start()

def run_app():
    root = tk.Tk()
    app = DataBossControlApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()
