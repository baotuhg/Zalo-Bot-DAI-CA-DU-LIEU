"""
Điểm khởi động chính của Hệ thống Bot Zalo "Đại ca dữ liệu"
Giám sát & Quản trị Tiến độ Thi công Công trình Tự động.

Sử dụng:
  python main.py          -> Chạy Bot Realtime Daemon (bắt báo cáo tự động từ các nhóm Zalo)
  python main.py --gui    -> Mở Bảng điều khiển Quản lý & Lọc Excel
"""

import sys
import os

def main():
    if "--gui" in sys.argv or "--app" in sys.argv:
        import app_control_center
        # Khởi chạy giao diện Tkinter
        app_control_center.main()
    else:
        import run_data_boss
        run_data_boss.main()

if __name__ == "__main__":
    main()
