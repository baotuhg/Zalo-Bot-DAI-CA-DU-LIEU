import os
import sys
import time
import sqlite3
import datetime
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

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

def ensure_daemon_running(bridge: ZaloBridge) -> bool:
    """Tự động kiểm tra và khởi động Zalo Daemon ngầm nếu chưa chạy."""
    status = bridge.check_connection()
    if status.get("authenticated", False):
        return True

    print("[Hệ thống] Zalo Daemon chưa bật. Đang tự động kích hoạt ngầm...")
    appdata = os.environ.get("APPDATA", "")
    cli_path = Path(appdata) / "npm" / "node_modules" / "zalo-personal-mcp" / "dist" / "bin" / "cli.js"
    if not cli_path.exists():
        cli_path = Path.home() / "AppData" / "Roaming" / "npm" / "node_modules" / "zalo-personal-mcp" / "dist" / "bin" / "cli.js"
    CREATE_NO_WINDOW = 0x08000000
    try:
        subprocess.Popen(
            ["node", str(cli_path), "daemon", "start"],
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for _ in range(8):
            time.sleep(1.0)
            status = bridge.check_connection()
            if status.get("authenticated", False):
                return True
    except Exception as e:
        print(f"[Cảnh báo] Lỗi kích hoạt Daemon: {e}")
    return False

def async_git_sync(report_id: int, project_name: str):
    """Đẩy cập nhật lên GitHub Pages ngầm không làm chậm bot."""
    def _worker():
        try:
            now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            msg = f"Tự động nạp Báo cáo #{report_id} từ Zalo [{project_name}] lúc {now_str}"
            auto_push_to_github(msg)
        except Exception as e:
            print(f"[Git Sync ngầm] Lỗi: {e}")
    threading.Thread(target=_worker, daemon=True).start()

def main():
    pid_file = BASE_DIR / "data" / "bot.pid"
    try:
        pid_file.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass

    print("=" * 70)
    print(" 🤖 BOT ZALO 'ĐẠI CA DỮ LIỆU' - TRỢ LÝ GIÁM SÁT DỰ ÁN CÔNG TRƯỜNG")
    print("    Hoạt động 100% tự động Realtime như Telegram Bot / 2Anh-Zalo-Bot")
    print("=" * 70)

    bridge = ZaloBridge()
    if not ensure_daemon_running(bridge):
        print("❌ [CHƯA KẾT NỐI ĐƯỢC ZALO]")
        print("👉 Vui lòng chạy file 1_KET_NOI_ZALO.bat để quét mã QR nhé!")
        return

    conn_status = bridge.check_connection()
    user_name = conn_status.get("displayName") or (conn_status.get("user") or {}).get("displayName") or "Chỉ huy"
    own_uid = str(conn_status.get("uid") or (conn_status.get("user") or {}).get("userId") or "")
    print(f"✅ Đã kết nối Zalo thành công! Tài khoản: {user_name} (UID: {own_uid or 'Auto'})", flush=True)

    db = ConstructionDB()
    parser = ConstructionReportParser()
    excel_syncer = ConstructionExcelSyncer()
    html_syncer = HtmlDashboardSyncer()
    brain = DataBossBrain(db, excel_syncer, parser, html_syncer)
    listener = DataBossListener(brain, bridge, bot_name=user_name)

    print(f"📁 Cơ sở dữ liệu: {db.db_path}")
    print(f"📊 Báo cáo Excel: {excel_syncer.excel_path}")
    print(f"🌐 Web Dashboard: https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/")
    print("-" * 70)
    print("🔍 Đang kết nối danh sách nhóm Zalo...")

    # Đọc cấu hình nhóm chỉ định từ CHON_NHOM_THEO_DOI.txt
    config_file = Path(__file__).resolve().parent / "CHON_NHOM_THEO_DOI.txt"
    chosen_keyword = "ALL"
    if config_file.exists():
        for line in config_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                chosen_keyword = line
                break

    group_map: Dict[str, str] = {}
    target_threads: Dict[str, str] = {} # thread_id -> group_name

    try:
        import httpx
        res = httpx.get(f"{bridge.base_url}/groups", timeout=8.0)
        if res.status_code == 200:
            groups = res.json().get("data", [])
            for g in groups:
                gid = str(g.get("groupId"))
                gname = g.get("name", "")
                group_map[gid] = gname

            # Lọc nhóm theo cấu hình
            if chosen_keyword and chosen_keyword.upper() != "ALL":
                # Chỉ theo dõi nhóm chỉ định
                for gid, gname in group_map.items():
                    if chosen_keyword.lower() in gname.lower():
                        target_threads[gid] = gname
                        print(f"  🎯 [KHÓA MỤC TIÊU] '{gname}' (ID: {gid})")
            
            if not target_threads:
                # Quét tự động tất cả các nhóm công trường
                keywords = [
                    "307", "SẠT LỞ", "HỒ SƠ", "CẦU", "MỐ", "TRỤ", "CAO TỐC",
                    "THI CÔNG", "TIẾN ĐỘ", "KCS", "TDA2", "BÌNH VÀNG", "PMU", "DỰ ÁN"
                ]
                for gid, gname in group_map.items():
                    if any(k in gname.upper() for k in keywords):
                        target_threads[gid] = gname
                        print(f"  👉 [TỰ ĐỘNG GIÁM SÁT] '{gname}' (ID: {gid})")
    except Exception as e:
        print(f"Lỗi lấy danh sách nhóm: {e}")

    if not target_threads:
        print("⚠️ Chưa nhận diện được nhóm cụ thể, sẽ giám sát tất cả tin nhắn đến!")

    print("\n" + "=" * 70)
    print(f" 🚀 BOT ĐANG CHẠY REALTIME - GIÁM SÁT {len(target_threads)} NHÓM DỰ ÁN")
    print("    📡 Cơ chế: Bất kỳ kỹ sư nào gửi tin nhắn báo cáo vào nhóm,")
    print("       Bot sẽ lập tức bóc tách, ghi vào SQLite & Excel, và phản hồi Zalo!")
    print("    💡 Nhấn Ctrl + C để dừng bot.")
    print("=" * 70 + "\n")

    daemon_db_path = Path.home() / ".zalo-personal-mcp" / "zalo.db"
    last_seen_id = 0

    # Lấy vị trí tin nhắn hiện tại
    if daemon_db_path.exists():
        try:
            conn = sqlite3.connect(str(daemon_db_path))
            cur = conn.cursor()
            cur.execute("SELECT MAX(id) FROM messages")
            row = cur.fetchone()
            if row and row[0]:
                last_seen_id = int(row[0])
            conn.close()
        except Exception:
            pass

    processed_ids: Set[int] = set()

    try:
        while True:
            # 1. Đọc tin nhắn mới trực tiếp từ SQLite WAL của Daemon (< 400ms độ trễ)
            if daemon_db_path.exists():
                try:
                    conn = sqlite3.connect(str(daemon_db_path), timeout=2.0)
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT id, thread_id, msg_id, sender_name, sender_id, content, timestamp "
                        "FROM messages WHERE id > ? ORDER BY id ASC LIMIT 30",
                        (last_seen_id,)
                    )
                    rows = cur.fetchall()
                    conn.close()

                    for r in rows:
                        row_id = int(r["id"])
                        last_seen_id = max(last_seen_id, row_id)
                        if row_id in processed_ids:
                            continue
                        processed_ids.add(row_id)

                        msg_tid = str(r["thread_id"] or "")
                        mid = str(r["msg_id"] or row_id)
                        sname = r["sender_name"] or "Kỹ sư"
                        sender_uid = str(r["sender_id"] or "")
                        content = (r["content"] or "").strip()

                        # Bỏ qua tin nhắn do chính bot gửi để tránh tự lặp
                        if own_uid and sender_uid == own_uid:
                            continue

                        # Xác định xem tin nhắn có thuộc nhóm mục tiêu hay không
                        matched_group_name = target_threads.get(msg_tid) or group_map.get(msg_tid)
                        
                        is_target = False
                        if target_threads:
                            if msg_tid in target_threads:
                                is_target = True
                        else:
                            # Nếu danh sách trống thì cho phép mọi nhóm công trường
                            is_target = True

                        if not is_target or not content:
                            continue

                        now_str = datetime.datetime.now().strftime("%H:%M:%S")
                        group_display = matched_group_name or f"Nhóm {msg_tid}"
                        print(f"[{now_str}] 📩 [{group_display}] @{sname}: {content[:60]}...")

                        # 2. Xử lý lệnh điều hành hoặc báo cáo thi công
                        msg_dict = {
                            "msgId": mid,
                            "threadId": msg_tid,
                            "senderName": sname,
                            "senderId": sender_uid,
                            "content": content,
                            "isFromBot": False,
                            "projectName": group_display
                        }

                        # Kiểm tra xem có phải báo cáo thi công không
                        if parser.is_construction_report(content):
                            print(f"        ⚡ PHÁT HIỆN BÁO CÁO THI CÔNG! Bắt đầu bóc tách...")
                            bridge.send_typing(msg_tid)
                            bridge.add_reaction(msg_tid, mid, reaction="like")

                            try:
                                res = brain.process_incoming_report(
                                    text=content,
                                    sender_name=sname,
                                    project_name=group_display
                                )
                                report_id = res["report_id"]
                                print(f"        ✅ Nạp thành công Báo cáo #{report_id}!")
                                print(f"        📁 Đã ghi: SQLite (construction_data.db) & Excel sống.")

                                # Gửi phản hồi vào nhóm Zalo
                                bridge.send_message(res["reply_text"], thread_id=msg_tid)
                                print(f"        📤 Đã gửi phản hồi xác nhận vào Zalo nhóm '{group_display}'!")

                                # Tự động đẩy lên Web GitHub Pages ngầm
                                async_git_sync(report_id, group_display)

                            except Exception as parse_err:
                                print(f"        ❌ Lỗi xử lý báo cáo: {parse_err}")
                        else:
                            # Xử lý các lệnh điều hành nhanh (/tiendo, /coc, /help, /excel...)
                            listener.handle_message(msg_dict, project_name=group_display)

                except Exception as loop_err:
                    pass

            time.sleep(0.4)

    except KeyboardInterrupt:
        print("\n[Đại ca dữ liệu] Đã dừng Bot theo lệnh người dùng. Chúc chỉ huy một ngày tốt lành!")
    finally:
        if pid_file.exists():
            try:
                pid_file.unlink()
            except Exception:
                pass

if __name__ == "__main__":
    main()
