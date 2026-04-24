English content is below.

# HƯỚNG DẪN SỬ DỤNG - Sub2Speech v1.0

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
  - `Mở file...`
  - Nút đổi ngôn ngữ (`EN`/`VIE`) nằm bên trái nút `Trợ giúp`
  - `Trợ giúp`
  - Dòng trạng thái gộp: tên tệp, chế độ xử lý, số segment
- **Workspace:**
  - Trái: bảng `Nội dung` và nút `Nghe thử dòng đã chọn` ngay trên bảng
  - Phải: panel `Chọn giọng đọc` gồm:
    - `Thiết lập giọng`
    - `Danh sách người nói`
  - Có thể double-click trực tiếp vào một dòng trong bảng `Nội dung` để nghe thử nhanh
- **Bottom:**
  - Hàng xuất: `Thư mục xuất`, `Chọn...`, `Lưu audio gốc theo từng dòng phụ đề`, `Xuất MP3`
  - Hàng player: `Phát/Tạm dừng`, `Dừng`, thanh trượt, thời gian phát, trạng thái file
  - Hàng tiến trình: chỉ hiện khi đang export
- **Logs:** Runtime logs được ghi vào thư mục `logs/` cạnh `Sub2Speech.exe` (xoay theo ngày, giữ 7 bản).

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
- Hiển thị thời lượng theo định dạng `mm:ss / mm:ss`.

## 8. Các tham số giọng đọc

- `Rate`: tốc độ đọc, ví dụ `+10%`, `-10%`.
- `Volume`: âm lượng, ví dụ `+0%`, `-10%`.
- `Pitch`: cao độ, ví dụ `+0Hz`, `+20Hz`.

## 9. Trợ giúp và thông tin trong ứng dụng

- Nút `Trợ giúp` mở cửa sổ tích hợp:
  - Hướng dẫn thao tác nhanh
  - Mẹo chỉnh tham số giọng đọc
  - Thông tin phiên bản, công nghệ và cấu hình ứng dụng

## 10. Mẹo sử dụng hiệu quả

- Với file SRT dài, nên nghe thử một vài đoạn đại diện trước khi xuất toàn bộ.
- Nếu mạng chập chờn, ưu tiên xuất theo từng lần và retry segment lỗi để tiết kiệm thời gian.
- Bật tùy chọn lưu audio gốc theo dòng khi cần hậu kỳ từng câu riêng lẻ.

---

# USER GUIDE - Sub2Speech v1.0

## 1. Introduction

Sub2Speech converts subtitles/text to speech using `edge-tts`, suitable for language-learning audio, text-reading podcasts, or basic voice-over workflows.

## 2. Setup and Launch

1. Run `setup.bat` to create `.venv` and install dependencies.
2. Run `run.bat` to start the application.

## 3. General Workflow

1. Open an SRT/TXT file.
2. Choose voice and speech options.
3. Preview output.
4. Select output folder.
5. Export MP3.

## 3.1 UI Layout

- **Top bar:**
  - `Open file...`
  - Language switch button (`EN`/`VIE`) placed left of `Help`
  - `Help`
  - Combined status line: file name, processing mode, segment count
- **Workspace:**
  - Left: `Content` table and `Preview selected line` button
  - Right: `Voice selection` panel including:
    - `Voice setup`
    - `Speaker list`
  - Double-click a row in `Content` to preview quickly
- **Bottom:**
  - Export row: `Output folder`, `Browse...`, `Save original audio per subtitle line`, `Export MP3`
  - Player row: `Play/Pause`, `Stop`, slider, play time, file status
  - Progress row: visible only during export
- **Logs:** Runtime logs are written to `logs/` next to `Sub2Speech.exe` (rotated daily, keeps the last 7 files).

## 4. SRT Guide

1. Use the right panel to assign voices by speaker or segment range.
2. Enter segment ranges, for example: `1-5,8,10`.
3. Preview before full export.
4. Click `Export MP3`.

## 5. TXT Guide

1. The app switches to TXT mode automatically.
2. No manual speaker or segment list setup required.
3. Choose one voice + `rate`/`volume`/`pitch` for whole content.
4. The app splits content into chunks (max 500 words/chunk), renders sequentially, then merges.

## 6. Retry Failed Segments

- If some segments fail during synthesis:
  - The app records failed segment indexes.
  - Click `Export MP3` again to regenerate only failed segments.
  - When no failure remains, the final output file is generated automatically.

## 7. Built-in Player

- Both preview audio and exported audio can be played in-app.
- Supports time slider, `Play/Pause`, `Stop`.
- Displays duration in `mm:ss / mm:ss` format.

## 8. Speech Parameters

- `Rate`: speaking speed, for example `+10%`, `-10%`.
- `Volume`: loudness, for example `+0%`, `-10%`.
- `Pitch`: tone, for example `+0Hz`, `+20Hz`.

## 9. Help and In-app Information

- `Help` opens an integrated dialog:
  - Quick operation guide
  - Speech parameter tips
  - Version, technology stack, and app configuration info

## 10. Usage Tips

- For long SRT files, preview representative segments before full export.
- If network is unstable, export iteratively and retry only failed segments.
- Enable original-audio saving when you need per-line post-processing.
