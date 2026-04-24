English content is below.

# Sub2Speech

Sub2Speech là ứng dụng sử dụng `edge-tts` để chuyển phụ đề/văn bản thành giọng nói, đồng thời giữ đúng timeline theo phụ đề.
![Photo](https://github.com/vegamu/Sub2Speech/blob/main/src/screen.png?raw=true)

## Phiên bản

- `0.2.0`

## Tính năng chính

- Hỗ trợ cả hai định dạng đầu vào: SRT và TXT.
- **Luồng SRT:** giữ timeline theo từng dòng phụ đề.
- **Luồng TXT:** áp dụng một cấu hình giọng cho toàn bộ nội dung.
- Quản lý nhiều người nói, cho phép gán voice theo danh sách đoạn.
- Tùy chọn lưu audio gốc theo từng dòng phụ đề.
- Runtime logs được ghi vào thư mục `logs/` cạnh `Sub2Speech.exe` (xoay theo ngày, giữ 7 bản).

## Bố cục giao diện

- **Top bar (1 hàng):** `Mở file...`, dòng trạng thái gộp (tệp/chế độ/số đoạn), nút đổi ngôn ngữ (`EN`/`VIE`), và nút `Trợ giúp`.
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
- `ffmpeg error`: kiểm tra file log trong thư mục `logs/` để xem chi tiết.

## Tài liệu bổ sung

- Xem `USER_GUIDE.md` để có hướng dẫn chi tiết cho từng thao tác.

## Tác giả

- `vega`

## Giấy phép

- Dự án phát hành theo giấy phép mã nguồn mở `GNU General Public License v3.0 (GPL-3.0)`.
- Xem đầy đủ trong file `LICENSE` tại thư mục gốc hoặc tại [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html).

---

# Sub2Speech (English)

Sub2Speech uses `edge-tts` to convert subtitles/text into speech while preserving subtitle timing.
![Photo](https://github.com/vegamu/Sub2Speech/blob/main/src/screen.png?raw=true)

## Version

- `0.2.0`

## Main Features

- Supports both input formats: SRT and TXT.
- **SRT flow:** preserves timeline line by line.
- **TXT flow:** applies one voice profile to the whole content.
- Multi-speaker management with segment-range voice mapping.
- Optional original-audio export per subtitle line.
- Runtime logs are written to `logs/` next to `Sub2Speech.exe` (rotated daily, keeps the last 7 files).

## UI Layout

- **Top bar (single row):** `Open file...`, combined status line (file/mode/segments), language switch (`EN`/`VIE`), and `Help`.
- **Workspace:**
  - Left: `Content` table with `Preview selected line` button above it.
  - Right: `Voice selection` panel with `Voice setup` and `Speaker list`.
- **Unified bottom bar:**
  - Row 1: `Output folder`, `Browse...`, `Save original audio`, and `Export MP3`.
  - Row 2: built-in player (`Play/Pause`, `Stop`, slider, `mm:ss / mm:ss`, file status).
  - Row 3: progress bar (visible only during export).

## System Requirements

- Windows with Python 3.10+.
- Stable internet connection for `edge-tts` synthesis.
- `ffmpeg` available in environment or bundled by project config (for audio processing/merging).

## Quick Start

### 1) Install

```bat
setup.bat
```

### 2) Run the app

```bat
run.bat
```

## Usage Workflow

### SRT flow (multiple speakers)

1. Open an `.srt` file.
2. Assign voice by speaker or segment range.
3. Use preview to validate.
4. Click `Export MP3`.
5. If segments fail, click `Export MP3` again to retry failed segments until completion.

### TXT flow (single voice)

1. Open a `.txt` file.
2. App switches to TXT mode; pick voice + `rate`/`volume`/`pitch`.
3. Preview for quality check.
4. Click `Export MP3`.

## Troubleshooting

- `Missing voice`: voice not assigned for required segments.
- `No audio was received`: temporary network/service issue; retry export.
- `ffmpeg error`: inspect log files in `logs/` for details.

## Additional Documentation

- See `USER_GUIDE.md` for detailed operation instructions.

## Author

- `vega`

## License

- Released under `GNU General Public License v3.0 (GPL-3.0)`.
- See full text in `LICENSE` or [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html).
