# HƯỚNG DẪN SỬ DỤNG - Sub2Speech v0.0.1

## 1. Giới thiệu

Sub2Speech là ứng dụng chuyển phụ đề/văn bản thành giọng nói bằng `edge-tts`, phù hợp để tạo audio học ngoại ngữ, podcast đọc văn bản, hoặc voice-over cơ bản.

## 2. Cài đặt và khởi động

1. Chạy `setup.bat` để tạo môi trường `.venv` và cài thư viện cần thiết.
2. Chạy `run.bat` để mở ứng dụng.

## 3. Luồng sử dụng tổng quát

1. Mở file SRT/TXT.
2. Chọn voice và tham số giọng đọc.
3. Nghe thử (Preview).
4. Chọn thư mục xuất.
5. Xuất MP3.

## 3.1 Bố cục giao diện

- **Top bar:**
  - `Chọn file phụ đề/văn bản`
  - `Trợ giúp`
  - `Thông tin`
  - Dòng trạng thái file, mode, số segment
- **Workspace:**
  - Trái: bảng `Nội dung`
  - Phải: panel `Chọn giọng đọc` (thiết lập Voice + ánh xạ Speaker)
- **Bottom:**
  - `Thư mục xuất`, `Chọn thư mục`, `Nghe thử dòng phụ đề`, `Xuất MP3`
  - Tùy chọn `Lưu audio gốc theo từng dòng phụ đề`
  - Player tích hợp ở hàng dưới

## 4. Hướng dẫn với file SRT

1. Panel bên phải cho phép gán voice theo người nói hoặc nhóm đoạn.
2. Có thể nhập range đoạn, ví dụ: `1-5,8,10`.
3. Dùng Preview để kiểm tra trước khi xuất hàng loạt.
4. Nhấn `Xuất MP3` để bắt đầu render.

## 5. Hướng dẫn với file TXT

1. Ứng dụng tự chuyển sang TXT mode.
2. Không cần tạo người nói hay danh sách đoạn thủ công.
3. Chọn 1 voice + `rate`/`volume`/`pitch` cho toàn bộ nội dung.
4. Ứng dụng tự chia nội dung thành nhiều đoạn (tối đa 500 từ/đoạn), render tuần tự và ghép kết quả.

## 6. Render lại segment lỗi (Retry)

- Nếu một số segment lỗi trong quá trình tạo giọng:
  - Ứng dụng ghi nhận danh sách segment lỗi.
  - Nhấn `Xuất MP3` thêm lần nữa để chỉ render lại segment lỗi.
  - Khi không còn lỗi, ứng dụng sẽ xuất file cuối hoàn chỉnh.

## 7. Trình phát tích hợp

- Cả audio preview và audio đã xuất đều phát trực tiếp trong ứng dụng.
- Hỗ trợ thanh trượt thời gian, `Play/Pause`, `Stop`.

## 8. Các tham số giọng đọc

- `Rate`: tốc độ đọc, ví dụ `+10%`, `-10%`.
- `Volume`: âm lượng, ví dụ `+0%`, `-10%`.
- `Pitch`: cao độ, ví dụ `+0Hz`, `+20Hz`.

## 9. Trợ giúp và thông tin trong ứng dụng

- Nút `Trợ giúp`: mở hướng dẫn nhanh trong app.
- Nút `Thông tin`: hiển thị phiên bản và thông tin hệ thống ứng dụng.

## 10. Mẹo sử dụng hiệu quả

- Với file SRT dài, nên nghe thử một vài đoạn đại diện trước khi xuất toàn bộ.
- Nếu mạng chập chờn, ưu tiên xuất theo từng lần và retry segment lỗi để tiết kiệm thời gian.
- Bật tùy chọn lưu audio gốc theo dòng khi cần hậu kỳ từng câu riêng lẻ.
