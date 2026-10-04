# 🏗️ ĐẠI CA DỮ LIỆU & BẢNG ĐIỀU HÀNH TIẾN ĐỘ THI CÔNG (CONTECH ZALO BOT)

Hệ sinh thái tự động hóa thu thập, bóc tách và quản trị dữ liệu tiến độ thi công công trình xây dựng (Cầu đường, Hạ tầng kỹ thuật, Dân dụng) qua nhóm chat Zalo và đồng bộ đa kênh (SQLite, Excel PMU sống, Web Dashboard HTML).

---

## 🌟 TÍNH NĂNG VƯỢT TRỘI

1. **Zero-Friction Ingestion (Thu thập không rào cản - Tự động 100%):**
   * Kỹ sư hiện trường chỉ cần gửi tin nhắn báo cáo ca vào nhóm Zalo như thường lệ.
   * Bot tự động nhận diện quy ước **"3 con số vàng"** của ngành xây dựng: `Ca này / Lũy kế / Tổng thiết kế`.
   * Bóc tách chính xác vị trí mố, mã tim cọc và trạng thái thi công (`Cọc M2-1-4: đang khoan`, `Cọc M2-3-6: Hạ ống thổi rửa chuẩn bị đổ bê tông`...).
   * **Cơ chế Realtime Daemon:** Bắt tức thời mọi tin nhắn từ từng kỹ sư trong nhóm qua WebSocket với độ trễ < 0.4s.

2. **Đồng Bộ Đa Kênh Tức Thì (Multi-Sync in < 0.1s):**
   * 🗄️ **CSDL Quan hệ SQLite (`data/construction_data.db`):** Lưu trữ phân cấp chuẩn WBS (Dự án $\rightarrow$ Nhà thầu $\rightarrow$ Báo cáo ca $\rightarrow$ Hạng mục $\rightarrow$ Tim cọc).
   * 📊 **Bảng tính Excel PMU sống (`data/Bao_cao_Tien_do_Thi_cong.xlsx`):** 100% công thức sống, tự tính % và tô màu cảnh báo tiến độ (Xanh $\ge 80\%$, Vàng $40-79\%$, Đỏ $< 40\%$).
   * 🌐 **Bảng điều hành Web (`index.html`):** Tự động cập nhật trực tiếp khối JSON trong thẻ `<script id="td3-data">`, biểu đồ nhân lực, máy móc và danh mục ưu tiên tự nhảy số.

3. **Tương Tác 2 Chiều Trên Zalo (Executive Bot):**
   * Thả Reaction xác nhận (`like`, `heart`) ngay khi nhận tin.
   * Hiệu ứng đang soạn tin (`typing indicator`) và cơ chế chống ban nick Zalo an toàn.
   * Gửi phản hồi báo cáo tóm tắt (Flash Summary) và cảnh báo các điểm nóng cần kiểm tra nghiệm thu.
   * Hỗ trợ các lệnh điều hành nhanh: `/tiendo`, `/canhbao`, `/coc`, `/excel`, `/help`.

4. **Tích hợp GitHub Pages:**
   * Bảng điều hành Web được host miễn phí 100% trên GitHub Pages để toàn bộ Ban điều hành & Chỉ huy công trường xem trực tuyến trên điện thoại:
   * 👉 **Link Web:** [https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/](https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/)

---

## 📂 CẤU TRÚC DỰ ÁN TINH GỌN

```
modest-babbage/
├── CHAY_HE_THONG.bat           # 🚀 [KHUYÊN DÙNG] Khởi động 1-Click All-in-One toàn bộ hệ thống
├── web_control.py              # Máy chủ Web Control Center & REST API nội bộ (cổng 8080)
│
├── 0_CAI_DAT_MOI_TRUONG.bat    # [Tùy chọn] Cài đặt môi trường tự động
├── 1_KET_NOI_ZALO.bat          # [Tùy chọn] Kết nối Zalo Daemon (Quét mã QR)
├── 2_CHAY_BOT_REALTIME.bat      # [Tùy chọn] Khởi động Bot Realtime túc trực 24/7
├── 3_BANG_DIEU_KHIEN.bat       # [Tùy chọn] Mở Bảng điều khiển Desktop Tkinter
├── 4_XEM_WEB_DASHBOARD.bat     # [Tùy chọn] Mở trang Web Dashboard trực tuyến
│
├── index.html                  # Bảng điều hành Web kiêm Trung tâm Quản trị Bot
├── config.py                   # Cấu hình đường dẫn, CSDL, Zalo Daemon URL
├── CHON_NHOM_THEO_DOI.txt       # Cấu hình nhóm mục tiêu (mặc định ALL nhóm thi công)
├── main.py                      # Điểm khởi chạy Python chính thức
├── run_data_boss.py             # Động cơ Bot Realtime Daemon
├── app_control_center.py        # Ứng dụng Desktop Bảng điều khiển giao diện Tkinter
├── sync_github.py               # Module tự động đẩy lên GitHub Pages
├── requirements.txt             # Danh sách thư viện Python
│
├── core/                        # Nhân xử lý logic nghiệp vụ
│   ├── report_parser.py         # Bóc tách ngữ nghĩa báo cáo thi công & tim cọc
│   ├── excel_syncer.py          # Sinh & ghi đè Excel sống WBS
│   ├── html_dashboard_syncer.py # Ghi đè số liệu trực tiếp vào HTML Web
│   └── data_boss_brain.py       # Bộ não điều phối & sinh câu trả lời
│
├── database/                    # Quản trị cơ sở dữ liệu
│   └── construction_db.py       # Quản lý SQLite phân cấp công trình
│
├── zalo/                        # Giao tiếp với Zalo
│   ├── bridge.py                # Cầu nối gửi tin, thả reaction, typing indicator
│   └── data_boss_listener.py    # Bộ lắng nghe và điều hướng sự kiện
│
├── data/                        # Dữ liệu dự án
│   ├── construction_data.db     # CSDL SQLite dự án
│   ├── Bao_cao_Tien_do_Thi_cong.xlsx # File Excel tiến độ sống
│   └── Bang_dieu_hanh_TD3.html  # Bản sao lưu Web Dashboard
│
└── tests/                       # Kiểm thử tự động
    └── test_data_boss.py        # Unit tests bóc tách & đồng bộ
```

---

## 🚀 HƯỚNG DẪN VẬN HÀNH

### 👉 Cách 1: Khởi động 1-Click All-in-One (Khuyên dùng)
Chỉ cần nhấp đúp duy nhất vào:
**`CHAY_HE_THONG.bat`**
* Tự động kiểm tra Python & Node.js, tự khởi tạo `.venv`.
* Tự động kết nối Zalo (hiện mã QR nếu chưa đăng nhập).
* Tự động kích hoạt Bot Realtime và mở ngay Bảng điều hành Web (`http://localhost:8080`) trên trình duyệt:
  - Có sẵn nút bấm **[▶ Khởi động Bot]** / **[⏹ Dừng Bot]**
  - Nút **[📲 Quét mã QR Zalo]**
  - Nút **[⚡ Đồng bộ lên Cloud]** (Tự động Git Push lên GitHub Pages trong 3s, **không cần mở GitHub Desktop**)
  - Nút **[📊 Mở file Excel tiến độ WBS]**

---

### 👉 Cách 2: Vận hành từng bước thủ công (Tùy chọn)
1. **Bước 0: Cài đặt môi trường:** Nhấp đúp `0_CAI_DAT_MOI_TRUONG.bat`.
2. **Bước 1: Kết nối Zalo:** Nhấp đúp `1_KET_NOI_ZALO.bat` (quét mã QR 1 lần duy nhất).
3. **Bước 2: Khởi động Bot Realtime:** Nhấp đúp `2_CHAY_BOT_REALTIME.bat`.
4. **Bước 3: Bảng điều khiển Desktop:** Nhấp đúp `3_BANG_DIEU_KHIEN.bat`.
5. **Bước 4: Xem Web Dashboard:** Nhấp đúp `4_XEM_WEB_DASHBOARD.bat` hoặc truy cập [Web Cloud](https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/).
   * Nhấp đúp file `4_XEM_WEB_DASHBOARD.bat` để mở báo cáo trực tuyến trên trình duyệt: [https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/](https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/).
