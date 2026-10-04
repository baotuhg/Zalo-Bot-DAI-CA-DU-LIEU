import sys
from pathlib import Path
from database.construction_db import ConstructionDB
from core.report_parser import ConstructionReportParser
from core.excel_syncer import ConstructionExcelSyncer
from core.data_boss_brain import DataBossBrain

SAMPLE_REPORT_FROM_IMAGE = """Báo cáo thi công cuối ca đêm 26/9/2026:
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

def main():
    print("=" * 65)
    print(" 🤖 CHƯƠNG TRÌNH THỬ NGHIỆM BOT 'ĐẠI CA DỮ LIỆU' (CLI MODE)")
    print("    Thu thập & Quản trị Dữ liệu Tiến độ Công trình Tự động")
    print("=" * 65)

    db = ConstructionDB()
    parser = ConstructionReportParser()
    excel_syncer = ConstructionExcelSyncer()
    brain = DataBossBrain(db, excel_syncer, parser)

    print("\n[HỆ THỐNG ĐÃ SẴN SÀNG]")
    print("1. Nạp báo cáo mẫu từ ảnh (Báo cáo thi công cuối ca đêm 26/9/2026)")
    print("2. Xem tổng hợp tiến độ (/tiendo)")
    print("3. Xem cảnh báo & điểm nóng thi công (/canhbao)")
    print("4. Xem tình trạng tim cọc (/coc)")
    print("5. Mở hoặc xuất file Excel sống (/excel)")
    print("6. Nhập báo cáo bất kỳ")
    print("0. Thoát")

    while True:
        try:
            choice = input("\n👉 Nhập lựa chọn hoặc lệnh (/tiendo, /canhbao...): ").strip()
            if choice == "0" or choice.lower() == "exit":
                print("Tạm biệt! 'Đại ca dữ liệu' chúc công trình an toàn & đúng tiến độ! 👷‍♂️")
                break
            elif choice == "1":
                print("\n[Đang nạp báo cáo từ ảnh của kỹ sư Ninh...] 🚀")
                res = brain.process_incoming_report(
                    text=SAMPLE_REPORT_FROM_IMAGE,
                    sender_name="Ninh",
                    project_name="PMU: BĂNG HẠ TẦNG OLP"
                )
                print("\n" + res["reply_text"])
            elif choice in ["2", "/tiendo", "tiến độ", "/baocao"]:
                print("\n" + brain.get_progress_overview())
            elif choice in ["3", "/canhbao", "cảnh báo"]:
                print("\n" + brain.get_risk_and_alerts())
            elif choice in ["4", "/coc", "cọc"]:
                print("\n" + brain.get_active_piles_overview())
            elif choice in ["5", "/excel"]:
                print(f"\n📁 File Excel báo cáo tiến độ nằm tại:\n{excel_syncer.excel_path}")
            elif choice == "/help":
                print("\n" + brain.get_help_message())
            else:
                if parser.is_construction_report(choice):
                    print("\n[Nhận diện báo cáo thi công! Tiến hành xử lý...] 📊")
                    res = brain.process_incoming_report(text=choice, sender_name="Kỹ sư hiện trường")
                    print("\n" + res["reply_text"])
                else:
                    print(f"Nhận tin: '{choice}'")
                    print("Gợi ý: Gõ '1' để nạp báo cáo mẫu, hoặc '/tiendo', '/canhbao', '/coc'.")
        except (KeyboardInterrupt, EOFError):
            break

if __name__ == "__main__":
    main()
