# 📖 CẨM NANG HƯỚNG DẪN SỬ DỤNG TRỌN GÓI
# BOT ZALO "ĐẠI CA DỮ LIỆU" - QUẢN TRỊ TIẾN ĐỘ THI CÔNG CÔNG TRÌNH

> **Dành cho Ban chỉ huy công trường, Kỹ sư hiện trường & Quản lý dự án**  
> Hệ thống tự động thu thập báo cáo qua Zalo, bóc tách tim cọc, cập nhật CSDL SQLite, xuất bảng tính Excel sống và đồng bộ Web Dashboard trực tuyến.

---

## ❓ VÌ SAO HỆ THỐNG CẦN CẢ PYTHON VÀ NODE.JS?

Rất nhiều kỹ sư thắc mắc: *"Tại sao phải cài cả Python và Node.js? Có thể bỏ 1 trong 2 được không?"*

Câu trả lời nằm ở **đặc thù kỹ thuật của Zalo**:
1. **Node.js (Lớp giao tiếp Zalo):** Zalo **không có API công khai** cho tài khoản cá nhân. Trong cộng đồng lập trình (kể cả các dự án nổi tiếng như `2anh-zalo-bot`), thư viện duy nhất kết nối ổn định với máy chủ Zalo là `zca-js` – được viết bằng **JavaScript chạy trên Node.js**. Node.js đóng vai trò như "chiếc tai nghe và cái miệng" của Bot: lắng nghe tin nhắn từ nhóm Zalo và gửi phản hồi.
2. **Python (Lớp bộ não nghiệp vụ xây dựng):** Python là ngôn ngữ số 1 về xử lý ngôn ngữ tự nhiên, bóc tách báo cáo công trường theo quy ước "3 con số vàng" (`Ca này / Lũy kế / Thiết kế`), phân loại tim cọc, quản lý CSDL quan hệ WBS và xuất file Excel sống 100% công thức (`openpyxl`).

👉 **Tóm lại:**  
* **Node.js:** Bắt buộc phải có để Bot đăng nhập và nhận/gửi tin nhắn Zalo.  
* **Python:** Bắt buộc phải có để phân tích dữ liệu, ghi file Excel và chạy Bảng điều khiển Desktop.

---

## 🛠️ ĐIỀU KIỆN TIÊN QUYẾT (CHỈ CẦN CÀI 1 LẦN TRÊN MÁY TÍNH)

Trước khi khởi chạy hệ thống lần đầu, máy tính của bạn cần có 2 phần mềm nền tảng miễn phí sau:

| Phần mềm | Phiên bản khuyến nghị | Link tải chính thức | Lưu ý quan trọng khi cài đặt |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10, 3.11 hoặc 3.12 | [https://www.python.org/downloads/](https://www.python.org/downloads/) | ⚠️ **BẮT BUỘC TÍCH CHỌN:** Ô vuông `[x] Add python.exe to PATH` ở ngay màn hình cài đặt đầu tiên! |
| **Node.js** | Bản LTS (18 hoặc 20 trở lên) | [https://nodejs.org/](https://nodejs.org/) | Chọn bản **LTS (Recommended for Most Users)**, tải về bấm Next liên tục để cài mặc định. |

---

## 🚀 KHỞI ĐỘNG 1-CLICK ALL-IN-ONE (KHUYÊN DÙNG NHẤT)

Khi bạn hoặc kỹ sư tải file ZIP về từ GitHub, chỉ cần làm đúng **1 thao tác duy nhất**:

👉 **Nhấp đúp chuột vào file: `CHAY_HE_THONG.bat`**
1. **Tự động 100%:** Kiểm tra Python, tự tạo `.venv`, tự cài đặt thư viện cần thiết.
2. **Tự động kết nối Zalo:** Nếu chưa từng đăng nhập, cửa sổ quét mã QR sẽ tự động bật lên để bạn quét một lần duy nhất.
3. **Tự động khởi động Bot Realtime & Mở Bảng điều hành Web:**
   * Trình duyệt tự mở trang: `http://localhost:8080`.
   * Giao diện Bảng điều hành tích hợp sẵn **Trung Tâm Bot & Zalo**:
     - Nút **[▶ Bật / ⏹ Tắt Bot Realtime]** trực quan.
     - Nút **[📲 Quét mã QR Zalo]**.
     - Nút **[⚡ Đồng bộ lên Cloud ngay]**: Bấm 1 click là đẩy dữ liệu lên GitHub Pages trong 3 giây, **loại bỏ hoàn toàn việc phải mở GitHub Desktop**!
     - Nút **[📊 Mở file Excel tiến độ WBS]**.

---

## 🛠️ QUY TRÌNH TỪNG BƯỚC THỦ CÔNG (TÙY CHỌN DÀNH CHO KỸ SƯ MUỐN TÁCH RỜI)

Nếu bạn muốn chạy từng thành phần độc lập:

### 🔹 Bước 0: Cài đặt môi trường tự động
* Nhấp đúp chuột vào file: **`0_CAI_DAT_MOI_TRUONG.bat`**
* Màn hình sẽ tự động:
  1. Kiểm tra Python trên máy.
  2. Tự động tạo thư mục môi trường ảo `.venv`.
  3. Tự động tải và cài đặt toàn bộ thư viện cần thiết (`httpx`, `openpyxl`, `python-dotenv`).
  4. Kiểm tra Node.js và công cụ kết nối Zalo.
* *Khi thấy thông báo "CHÚC MỪNG! HỆ THỐNG ĐÃ ĐƯỢC THIẾT LẬP HOÀN TOÀN TỰ ĐỘNG!" là hoàn tất.*

---

### 🔹 Bước 1: Kết nối tài khoản Zalo (Quét mã QR)
* Nhấp đúp chuột vào file: **`1_KET_NOI_ZALO.bat`**
* Màn hình terminal sẽ hiển thị một mã QR kết nối:
  1. Mở ứng dụng **Zalo trên điện thoại**.
  2. Bấm vào biểu tượng **Quét mã QR** (góc trên bên phải màn hình Zalo).
  3. Hướng camera vào màn hình máy tính và bấm **Đăng nhập / Xác nhận** trên điện thoại.
* Terminal sẽ báo: `DANG NHAP ZALO THANH CONG!` và tự động khởi chạy tiến trình Daemon ngầm.

---

### 🔹 Bước 2: Bật Bot Realtime tự hành 24/7 (Khuyên dùng)
* Nhấp đúp chuột vào file: **`2_CHAY_BOT_REALTIME.bat`**
* Bot sẽ khởi động và hiện danh sách các nhóm công trường đang được giám sát (ví dụ: `307 HỒ SƠ SẠT LỞ`, `Cao tốc TQ-HG (Kỹ thuật)`...).
* **Cách Bot hoạt động từ thời điểm này:**
  * Bạn và các kỹ sư cứ nhắn tin báo cáo ca vào nhóm Zalo bình thường.
  * **Từng người nhắn vào:** Bot sẽ tự động nhận diện báo cáo, bóc tách tim cọc, cập nhật CSDL SQLite, cập nhật bảng tính Excel, thả reaction 👍 và gửi tin nhắn phản hồi xác nhận trực tiếp vào nhóm!
  * **Bạn không cần bấm chuột, không cần copy-paste, không cần chạm vào máy tính!**

---

### 🔹 Bước 3: Mở Bảng điều khiển Quản lý & Lọc Excel (Khi cần tra cứu)
* Nhấp đúp chuột vào file: **`3_BANG_DIEU_KHIEN.bat`**
* Giao diện đồ họa Desktop sẽ hiện ra với đầy đủ các tính năng:
  * **Tab Tìm kiếm & Báo cáo:** Lọc theo dự án, theo nhóm Zalo, theo hạng mục (cọc khoan nhồi, đào đắp, bê tông...) hoặc theo từ khóa.
  * **Nút "Xuất Excel Kết Quả":** Xuất các dòng vừa lọc ra file Excel riêng để in ấn/báo cáo.
  * **Nút "Mở File Excel Tiến Độ":** Mở ngay file Excel tổng hợp sống (`Bao_cao_Tien_do_Thi_cong.xlsx`) với đầy đủ công thức WBS và tô màu cảnh báo tiến độ.
  * **Nút "Đồng Bộ Toàn Bộ":** Quét lại toàn bộ và đồng bộ dữ liệu lên Web Dashboard GitHub.

---

### 🔹 Bước 4: Xem Web Dashboard trên điện thoại & máy tính
* Nhấp đúp chuột vào file: **`4_XEM_WEB_DASHBOARD.bat`**
* Hoặc truy cập trực tiếp bằng điện thoại qua đường link GitHub Pages:
  👉 **[https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/](https://baotuhg.github.io/Zalo-Bot-DAI-CA-DU-LIEU/)**
* Bảng điều hành hiển thị biểu đồ nhân lực, thiết bị, tiến độ tim cọc và nhật trình thi công công trường trực quan.

---

## 💬 CÁC LỆNH ĐIỀU HÀNH BOT TRỰC TIẾP TRÊN ZALO

Bất kỳ thành viên nào trong nhóm Zalo cũng có thể tương tác với Bot bằng các câu lệnh nhanh:

| Lệnh | Ý nghĩa | Phản hồi của Bot |
| :--- | :--- | :--- |
| `/tiendo` hoặc `tiến độ` | Xem tổng hợp tiến độ toàn dự án | Bot tóm tắt tỷ lệ hoàn thành các hạng mục lớn và cảnh báo chậm tiến độ |
| `/coc` hoặc `tim cọc` | Xem tình trạng tim cọc hiện trường | Liệt kê các tim cọc đang khoan, đang thổi rửa, hạ lồng thép hoặc chờ đổ bê tông |
| `/canhbao` | Xem điểm nghẽn thi công | Cảnh báo các mũi thi công chậm hoặc các khâu xung yếu cần nghiệm thu |
| `/excel` | Kiểm tra file Excel | Cung cấp thông tin tình trạng đồng bộ của file Excel sống |
| `/help` hoặc `hướng dẫn` | Xem trợ giúp | Hướng dẫn cách bắn báo cáo ca và danh sách lệnh |
| `@Đại ca` hoặc `đại ca ơi` | Gọi bot | Bot chào và xác nhận sẵn sàng tiếp nhận dữ liệu |

---

## 🎯 CÁCH SOẠN BÁO CÁO ĐỂ BOT BÓC TÁCH CHUẨN XÁC 100%

Bot được huấn luyện nhận diện chuẩn ngữ nghĩa công trường Việt Nam. Kỹ sư chỉ cần nhắn theo cấu trúc quen thuộc:

```text
Báo cáo thi công ca ngày 04/10/2026:
* Nhà thầu: SGC Cầu 5B
1. Thi công ép cừ mố M2: 00/246/280 cừ
2. Thi công cọc khoan nhồi: 00/14/106 cọc
- Mố M2-1: Cọc M2-1-4: đang khoan
- Mố M2-3: Cọc M2-3-6: Hạ ống thổi rửa chuẩn bị đổ bê tông
- Mố M2-4: Cọc M2-4-1: đang hạ lồng thép L4-L3
3. Nhân lực: 18 người, Thiết bị: 2 máy khoan, 1 cẩu 25T
Thời tiết: Nắng tốt
```

* Quy ước "3 con số": `Ca này / Lũy kế / Tổng thiết kế` (Ví dụ: `00/246/280`).
* Bot tự động nhận diện số lượng, tính % hoàn thành và cập nhật trạng thái từng cọc.

---

## ❓ CÁC SỰ CỐ THƯỜNG GẶP & CÁCH XỬ LÝ (FAQ)

### 1. Bấm vào file `.bat` bị hiện cửa sổ đen rồi tắt ngay?
* **Nguyên nhân:** Máy tính của bạn chưa cài đặt Python hoặc chưa tích ô `Add python.exe to PATH`.
* **Cách xử lý:** Vào [python.org](https://www.python.org/downloads/) tải Python, khi cài nhớ tích chọn ô `Add python.exe to PATH`. Sau đó chạy file `0_CAI_DAT_MOI_TRUONG.bat`.

### 2. Báo lỗi `Windows cannot find pythonw.exe`?
* **Cách xử lý:** Chạy file `0_CAI_DAT_MOI_TRUONG.bat`. File này sẽ tự động tạo thư mục `.venv` và cài đầy đủ thư viện giúp bạn.

### 3. Bot báo `Chưa kết nối được Zalo`?
* **Nguyên nhân:** Phiên đăng nhập Zalo đã hết hạn hoặc chưa quét mã QR.
* **Cách xử lý:** Chạy file `1_KET_NOI_ZALO.bat` và lấy điện thoại quét lại mã QR một lần nữa.

### 4. Muốn đổi nhóm theo dõi hoặc chỉ theo dõi 1 nhóm duy nhất?
* Mở file **`CHON_NHOM_THEO_DOI.txt`**:
  * Để chữ `ALL`: Bot sẽ tự động quét và theo dõi tất cả các nhóm công trường (`307`, `SẠT LỞ`, `CẦU`, `CAO TỐC`...).
  * Điền chính xác tên nhóm (ví dụ: `307 HỒ SƠ SẠT LỞ`): Bot sẽ chỉ tập trung duy nhất vào nhóm đó.
