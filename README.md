# 🏗️ ĐẠI CA DỮ LIỆU & BẢNG ĐIỀU HÀNH TIẾN ĐỘ THI CÔNG (CONTECH ZALO BOT)

Hệ sinh thái tự động hóa thu thập, bóc tách và quản trị dữ liệu tiến độ thi công công trình xây dựng (Cầu đường, Hạ tầng kỹ thuật, Dân dụng) qua nhóm chat Zalo và đồng bộ đa kênh (SQLite, Excel PMU, Web Dashboard HTML).

---

## 🌟 TÍNH NĂNG VƯỢT TRỘI

1. **Zero-Friction Ingestion (Thu thập không rào cản):**
   * Kỹ sư hiện trường chỉ cần gửi tin nhắn báo cáo ca như thường lệ (Ví dụ: `Báo cáo thi công cuối ca đêm 26/9/2026: Nhà thầu SGC Cầu 5B: Ép cừ mố M2: 00/246/280...`).
   * Bot tự động nhận diện quy ước **"3 con số vàng"** của ngành xây dựng: `Ca này / Lũy kế / Tổng thiết kế`.
   * Bóc tách chính xác vị trí mố, mã tim cọc và trạng thái thi công (`Cọc M2-1-4: đang khoan`, `Cọc M2-3-6: Hạ ống thổi rửa chuẩn bị đổ bê tông`...).

2. **Đồng Bộ Đa Kênh Tức Thì (Multi-Sync in < 0.1s):**
   * 🗄️ **CSDL Quan hệ SQLite (`construction_data.db`):** Lưu trữ phân cấp chuẩn WBS (Dự án $\rightarrow$ Nhà thầu $\rightarrow$ Báo cáo ca $\rightarrow$ Hạng mục $\rightarrow$ Tim cọc).
   * 📊 **Bảng tính Excel PMU sống (`Bao_cao_Tien_do_Thi_cong.xlsx`):** 100% công thức sống, tự tính % và tô màu cảnh báo tiến độ (Xanh $\ge 80\%$, Vàng $40-79\%$, Đỏ $< 40\%$).
   * 🌐 **Bảng điều hành Web (`index.html`):** Tự động cập nhật trực tiếp khối JSON trong thẻ `<script id="td3-data">`, biểu đồ nhân lực, máy móc và danh mục ưu tiên tự nhảy số.

3. **Tương Tác 2 Chiều Trên Zalo (Executive Bot):**
   * Thả Reaction xác nhận (`like`, `heart`, `rocket`) ngay khi nhận tin.
   * Hiệu ứng đang soạn tin (`typing indicator`) và cơ chế chống ban nick Zalo an toàn.
   * Gửi phản hồi báo cáo tóm tắt (Flash Summary) và cảnh báo các điểm nóng cần kiểm tra nghiệm thu.
   * Hỗ trợ các lệnh điều hành: `/tiendo`, `/canhbao`, `/coc`, `/excel`, `/help`.

4. **Tích hợp GitHub Pages:**
   * File `index.html` được thiết kế chuẩn Single-Page App, cho phép host miễn phí 100% trên GitHub Pages để toàn bộ Ban điều hành xem trực tuyến trên điện thoại.

---

## 📂 CẤU TRÚC THƯ MỤC

```
modest-babbage/
├── index.html                   # Bảng điều hành TĐ3 (Giao diện Web dùng cho GitHub Pages)
├── config.py                    # Cấu hình hệ thống, Zalo Daemon URL, tên nhóm dự án
├── .gitignore                   # Loại trừ file mật (.env, .venv, *.db)
├── requirements.txt             # Thư viện Python cần thiết
│
├── core/
│   ├── report_parser.py         # Bộ bóc tách ngữ nghĩa báo cáo thi công công trường
│   ├── excel_syncer.py          # Bộ sinh và đồng bộ Bảng tính Excel WBS sống
│   ├── html_dashboard_syncer.py # Bộ ghi đè dữ liệu tự động vào Bảng điều hành HTML
│   └── data_boss_brain.py       # Bộ não điều hành & phân tích cảnh báo tiến độ
│
├── database/
│   ├── construction_db.py       # SQLite Quản lý tiến độ công trình (WBS Relational)
│   └── db_manager.py            # SQLite Quản lý học tập (Gia sư Jerryhg)
│
├── zalo/
│   ├── bridge.py                # Cầu nối gửi tin, gửi ảnh, thả cảm xúc qua Zalo Daemon
│   ├── data_boss_listener.py    # Lắng nghe & điều phối nhóm Zalo công trường
│   └── listener.py              # Lắng nghe nhóm gia sư
│
├── data/
│   ├── Bang_dieu_hanh_TD3.html  # Bản sao lưu Bảng điều hành
│   ├── Bao_cao_Tien_do_Thi_cong.xlsx # File Excel tự động cập nhật
│   └── construction_data.db     # CSDL SQLite (tự sinh khi chạy)
│
├── cli_data_boss.py             # Chế độ chạy thử nghiệm dòng lệnh (CLI Test)
├── run_data_boss.py             # Điểm chạy 24/7 kết nối Zalo Daemon
├── sync_github.py               # Tự động commit và đẩy lên GitHub Pages
└── tests/
    └── test_data_boss.py        # Bộ kiểm thử tự động (Unit Tests)
```

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY

### 1. Kích hoạt môi trường & Cài đặt thư viện
```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Chạy thử nghiệm ngay trên Terminal (CLI Mode)
Bạn có thể thử nghiệm khả năng bóc tách và đồng bộ dữ liệu ngay lập tức:
```powershell
python cli_data_boss.py
# hoặc: python main.py --boss
```
*Nhấn phím `1` để nạp ngay nội dung từ bức ảnh báo cáo ca mẫu, hoặc gõ `/tiendo`, `/canhbao`, `/coc`.*

### 3. Vận hành Bot Zalo tự động 24/7
1. Đảm bảo Zalo Personal Daemon đang chạy trên cổng `3712`.
2. Khởi chạy bot:
```powershell
python run_data_boss.py
# hoặc: python main.py --databoss
```
*Bot sẽ tự động bắt mọi tin nhắn báo cáo từ các nhóm công trường, nạp vào CSDL, cập nhật Excel và Bảng điều hành HTML.*

### 4. Tự động đồng bộ lên GitHub Pages
Mỗi khi dữ liệu cập nhật, bạn có thể chạy:
```powershell
python sync_github.py
```
*Toàn bộ Dashboard trực tuyến trên GitHub Pages sẽ được làm mới chỉ sau 30 giây.*

---

## 🛡️ BẢN QUYỀN & GIẤY PHÉP
Phát triển bởi đội ngũ kỹ sư công nghệ xây dựng (AEC / ConTech Việt Nam).
Giấy phép: MIT License.
