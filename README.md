# Sub2Speech

Sub2Speech là ứng dụng sử dụng`edge-tts` để chuyển phụ đề/văn bản thành giọng nói. Đồng thời giữ đúng timeline theo phụ đề.
![Photo](https://github.com/vegamu/Sub2Speech/blob/main/src/screen.png?raw=true)

## Phiên bản

- `0.1.0`

## Tính năng chính

- Hỗ trợ cả hai định dạng đầu vào: SRT và TXT.
- **Luồng SRT:** giữ timeline theo từng dòng phụ đề.
- **Luồng TXT:**
- Quản lý nhiều người nói, cho phép gán voice theo danh sách đoạn.
- Tùy chọn lưu audio gốc theo từng dòng phụ đề.

## Bố cục giao diện

- **Top bar (1 hàng):** `Mở file...`, dòng trạng thái gộp (tệp/chế độ/số đoạn), và nút `Trợ giúp`.
- **Workspace:**
  - Bên trái: bảng `Nội dung` kèm nút `Nghe thử dòng đã chọn` ngay phía trên bảng.
  - Bên phải: panel `Chọn giọng đọc` với 2 phần chính `Thiết lập giọng` và `Danh sách người nói`.
- **Bottom bar hợp nhất:**
  - Hàng 1: `Thư mục xuất`, `Chọn...`, tùy chọn `Lưu âm thanh gốc`, và `Xuất MP3`.
  - Hàng 2: trình phát tích hợp (`Phát/Tạm dừng`, `Dừng`, thanh trượt, thời gian `mm:ss / mm:ss`, trạng thái file).
  - Hàng 3: thanh tiến trình (chỉ hiện khi đang xuất).

## Yêu cầu hệ thống

- Windows có thể chạy Python 3.10+.
- Kết nối mạng ổn định khi tổng hợp giọng nói bằng `edge-tts`.
- Có sẵn `ffmpeg` trong môi trường hoặc đi kèm theo cấu hình dự án (dùng để xử lý/ghép audio).

## Khởi động nhanh

### 1) Cài đặt

```bat
setup.bat
```

### 2) Chạy ứng dụng

```bat
run.bat
```

## Quy trình sử dụng

### Luồng SRT (nhiều speaker)

1. Mở file `.srt`.
2. Gán voice cho từng speaker hoặc nhóm đoạn.
3. Dùng chức năng nghe thử để kiểm tra.
4. Nhấn `Xuất MP3`.
5. Nếu có segment lỗi, tiếp tục nhấn `Xuất MP3` để render lại segment lỗi cho đến khi hoàn tất.

### Luồng TXT (một voice cho toàn bộ)

1. Mở file `.txt`.
2. Ứng dụng tự chuyển sang chế độ TXT, bạn chọn voice + `rate`/`volume`/`pitch`.
3. Nghe thử để kiểm tra.
4. Nhấn `Xuất MP3`.

## Xử lý lỗi thường gặp

- `Thiếu voice`: chưa gán giọng cho tất cả segment bắt buộc.
- `No audio was received`: lỗi mạng hoặc dịch vụ `edge-tts` tạm thời, hãy thử xuất lại.
- `ffmpeg error`: kiểm tra log terminal để xem stderr chi tiết.

## Tài liệu bổ sung

- Xem `USER_GUIDE.md` để có hướng dẫn chi tiết cho từng thao tác.

## Tác giả

- `vega`

## Giấy phép

- Dự án phát hành theo giấy phép mã nguồn mở `GNU General Public License v3.0 (GPL-3.0)`.
- Xem đầy đủ trong file `LICENSE` tại thư mục gốc hoặc tại [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html).
