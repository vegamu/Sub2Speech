from __future__ import annotations

from PySide6.QtCore import QObject, Signal

LANG_VI = "vi"
LANG_EN = "en"

STRINGS: dict[str, dict[str, str]] = {
    LANG_VI: {
        "top.open_file": "Mở file...",
        "top.help": "Trợ giúp",
        "top.lang_toggle_to_en": "EN",
        "top.lang_toggle_to_vi": "VIE",
        "status.no_file": "Chưa chọn file. Bấm 'Mở file...' để bắt đầu.",
        "status.file_info": "Tệp: {file}  •  {mode}  •  Đoạn: {count}",
        "status.mode_txt": "Chế độ TXT: áp dụng một cấu hình giọng cho toàn bộ nội dung",
        "status.mode_srt": "Chế độ SRT: gán giọng theo người nói hoặc nhóm đoạn",
        "status.mode_unknown": "Chế độ chưa xác định",
        "section.content": "Nội dung",
        "section.voice": "Chọn giọng đọc",
        "section.voice_setup": "Thiết lập giọng",
        "section.speaker_list": "Danh sách người nói",
        "table.idx": "#",
        "table.time": "Thời gian",
        "table.content": "Nội dung",
        "table.speaker": "Người nói",
        "table.voice": "Giọng",
        "speaker.name_label": "Tên người nói",
        "speaker.range_label": "Danh sách đoạn",
        "speaker.language_label": "Ngôn ngữ",
        "speaker.voice_label": "Giọng đọc",
        "speaker.rate_label": "Tốc độ",
        "speaker.volume_label": "Âm lượng",
        "speaker.pitch_label": "Cao độ",
        "speaker.voice_options_label": "Tùy chỉnh giọng",
        "speaker.add_btn": "Thêm/Cập nhật vào Danh sách người nói",
        "speaker.remove_btn": "Xóa",
        "speaker.preview_btn": "Nghe thử giọng",
        "speaker.preview_sample_text": "Xin chào, đây là giọng đọc mẫu.",
        "speaker.txt_mode_hint": "Chế độ TXT: chỉ cần chọn giọng và tham số, áp dụng cho toàn bộ đoạn.",
        "speaker.warn_title": "Cảnh báo",
        "speaker.warn_empty_name": "Tên người nói không được để trống",
        "speaker.warn_no_voice": "Chưa chọn giọng đọc",
        "speaker.overlap_title": "Cảnh báo trùng đoạn",
        "speaker.overlap_msg": "Đoạn bị gán nhiều người nói: {items}",
        "language.group.Tiếng Việt": "Tiếng Việt",
        "language.group.Tiếng Anh (Tất cả)": "Tiếng Anh (Tất cả)",
        "language.group.Tiếng Nhật": "Tiếng Nhật",
        "language.group.Tiếng Trung": "Tiếng Trung",
        "language.group.Tiếng Hàn": "Tiếng Hàn",
        "language.group.Tiếng Pháp": "Tiếng Pháp",
        "language.group.Tiếng Nga": "Tiếng Nga",
        "output.dir_label": "Thư mục xuất",
        "output.browse": "Chọn...",
        "output.save_original": "Lưu âm thanh gốc theo từng dòng phụ đề",
        "output.export": "Xuất MP3",
        "output.export_retry": "Xuất lại MP3",
        "output.choose_dialog_title": "Chọn thư mục xuất",
        "player.play": "Phát",
        "player.pause": "Tạm dừng",
        "player.stop": "Dừng",
        "player.status_idle": "Trình phát: Chưa phát",
        "player.status_playing": "Trình phát: {name}",
        "subtitle.preview_btn": "Nghe thử dòng đã chọn",
        "subtitle.warn_select_row": "Hãy chọn 1 dòng phụ đề để nghe thử",
        "subtitle.warn_no_voice": "Dòng này chưa có giọng đọc",
        "dlg.error_title": "Lỗi",
        "dlg.warn_title": "Cảnh báo",
        "dlg.done_title": "Hoàn tất",
        "dlg.export_done": "Đã xuất audio: {path}",
        "dlg.export_incomplete_title": "Tạo audio chưa hoàn tất",
        "dlg.export_incomplete_msg": "Các segment sau bị lỗi và đã được bỏ qua:\n{items}\n\nHãy chỉnh lại voice/tham số nếu cần, sau đó bấm 'Xuất lại MP3' để tạo lại segment lỗi. Khi không còn lỗi hệ thống sẽ tự render file cuối.",
        "dlg.missing_voice_title": "Thiếu voice",
        "dlg.missing_voice_msg": "Các đoạn chưa có voice: {items}",
        "dlg.preview_error_title": "Lỗi preview",
        "dlg.no_input": "Chưa có dữ liệu đầu vào",
        "dlg.no_output_dir": "Vui lòng chọn thư mục xuất",
        "dlg.open_input_title": "Chọn file phụ đề hoặc văn bản",
        "dlg.open_input_filter": "Subtitle/Text (*.srt *.txt)",
        "tip.export": "Xuất file âm thanh MP3 192 kbps.",
        "tip.export_retry": "Tạo lại các segment bị lỗi ở lần xuất trước. Khi không còn lỗi, hệ thống sẽ tự render file MP3 hoàn chỉnh.",
        "tip.preview_row": "Nghe thử dòng phụ đề đang chọn.",
        "tip.rate": "Tốc độ đọc. Ví dụ: +10% hoặc -15%.",
        "tip.volume": "Âm lượng đọc. Ví dụ: +0% hoặc -10%.",
        "tip.pitch": "Cao độ giọng. Ví dụ: +0Hz hoặc +20Hz.",
        "help.dialog_title": "Hướng dẫn sử dụng",
        "help.html_body": "<h3>Hướng dẫn nhanh</h3>{quick_guide_image}<ol><li>Bấm <b>Mở file...</b> để nạp dữ liệu.</li><li>Nếu là <b>SRT</b>: gán giọng theo người nói/đoạn.</li><li>Nếu là <b>TXT</b>: chỉ cần chọn 1 giọng và tham số đọc.</li><li>Dùng <b>Preview</b> để nghe thử trước khi xuất.</li><li>Chọn thư mục xuất và bấm <b>Xuất MP3</b>.</li><li>Nếu có segment lỗi, bấm xuất lại để tạo lại segment lỗi.</li></ol><h4>Mẹo tham số</h4><ul><li>Rate: +10% / -10%</li><li>Volume: +0% / -10%</li><li>Pitch: +0Hz / +20Hz</li></ul><h4>Thông tin ứng dụng</h4><p><b>Sub2Speech</b> là công cụ chuyển nội dung SRT/TXT thành âm thanh MP3 dành cho quy trình sản xuất nội dung. Ứng dụng hỗ trợ preview trong app, xử lý retry segment lỗi và lưu cấu hình ổn định theo phiên làm việc.</p><ul><li>Phiên bản: <b>{version}</b></li><li>Tác giả: <b>vega</b></li><li>Công nghệ: PySide6, edge-tts, ffmpeg</li><li>Giấy phép: <b>GNU GPL v3</b> (<a href='https://www.gnu.org/licenses/gpl-3.0.html'>Chi tiết</a>)</li><li>Tệp cấu hình: {settings_path}</li><li>Thư mục xuất mặc định: {output_dir}</li></ul><p>Phần mềm tự do phát hành theo GNU GPL v3. Xem thêm trong file LICENSE đi kèm.</p>",
    },
    LANG_EN: {
        "top.open_file": "Open file...",
        "top.help": "Help",
        "top.lang_toggle_to_en": "EN",
        "top.lang_toggle_to_vi": "VIE",
        "status.no_file": "No file selected. Click 'Open file...' to start.",
        "status.file_info": "File: {file}  •  {mode}  •  Segments: {count}",
        "status.mode_txt": "TXT mode: apply one voice profile for the entire content",
        "status.mode_srt": "SRT mode: assign voices by speaker or segment range",
        "status.mode_unknown": "Unknown mode",
        "section.content": "Content",
        "section.voice": "Voice selection",
        "section.voice_setup": "Voice setup",
        "section.speaker_list": "Speaker list",
        "table.idx": "#",
        "table.time": "Time",
        "table.content": "Content",
        "table.speaker": "Speaker",
        "table.voice": "Voice",
        "speaker.name_label": "Speaker name",
        "speaker.range_label": "Segment ranges",
        "speaker.language_label": "Language",
        "speaker.voice_label": "Voice",
        "speaker.rate_label": "Rate",
        "speaker.volume_label": "Volume",
        "speaker.pitch_label": "Pitch",
        "speaker.voice_options_label": "Voice options",
        "speaker.add_btn": "Add/Update in Speaker list",
        "speaker.remove_btn": "Delete",
        "speaker.preview_btn": "Preview voice",
        "speaker.preview_sample_text": "Hello, this is a sample voice.",
        "speaker.txt_mode_hint": "TXT mode: choose voice and options once for all segments.",
        "speaker.warn_title": "Warning",
        "speaker.warn_empty_name": "Speaker name must not be empty",
        "speaker.warn_no_voice": "Please select a voice",
        "speaker.overlap_title": "Overlap warning",
        "speaker.overlap_msg": "Segments assigned to multiple speakers: {items}",
        "language.group.Tiếng Việt": "Vietnamese",
        "language.group.Tiếng Anh (Tất cả)": "English (All)",
        "language.group.Tiếng Nhật": "Japanese",
        "language.group.Tiếng Trung": "Chinese",
        "language.group.Tiếng Hàn": "Korean",
        "language.group.Tiếng Pháp": "French",
        "language.group.Tiếng Nga": "Russian",
        "output.dir_label": "Output folder",
        "output.browse": "Browse...",
        "output.save_original": "Save original audio per subtitle line",
        "output.export": "Export MP3",
        "output.export_retry": "Retry MP3 Export",
        "output.choose_dialog_title": "Select output folder",
        "player.play": "Play",
        "player.pause": "Pause",
        "player.stop": "Stop",
        "player.status_idle": "Player: Idle",
        "player.status_playing": "Player: {name}",
        "subtitle.preview_btn": "Preview selected line",
        "subtitle.warn_select_row": "Please select a subtitle line to preview",
        "subtitle.warn_no_voice": "No voice assigned for this line",
        "dlg.error_title": "Error",
        "dlg.warn_title": "Warning",
        "dlg.done_title": "Done",
        "dlg.export_done": "Audio exported: {path}",
        "dlg.export_incomplete_title": "Audio generation incomplete",
        "dlg.export_incomplete_msg": "The following segments failed and were skipped:\n{items}\n\nPlease adjust voice/options if needed, then click 'Retry MP3 Export' to regenerate failed segments. When all failed segments are resolved, the app will render the final output file automatically.",
        "dlg.missing_voice_title": "Missing voice",
        "dlg.missing_voice_msg": "Segments without voice: {items}",
        "dlg.preview_error_title": "Preview error",
        "dlg.no_input": "No input data yet",
        "dlg.no_output_dir": "Please choose an output folder",
        "dlg.open_input_title": "Select subtitle or text file",
        "dlg.open_input_filter": "Subtitle/Text (*.srt *.txt)",
        "tip.export": "Export MP3 audio file at 192 kbps.",
        "tip.export_retry": "Retry only failed segments from previous export. When no failure remains, the app will render a complete final MP3.",
        "tip.preview_row": "Preview currently selected subtitle line.",
        "tip.rate": "Speech rate. Example: +10% or -15%.",
        "tip.volume": "Speech volume. Example: +0% or -10%.",
        "tip.pitch": "Speech pitch. Example: +0Hz or +20Hz.",
        "help.dialog_title": "User Guide",
        "help.html_body": "<h3>Quick guide</h3>{quick_guide_image}<ol><li>Click <b>Open file...</b> to load input data.</li><li>For <b>SRT</b>: assign voice by speaker/segments.</li><li>For <b>TXT</b>: pick one voice and speech options.</li><li>Use <b>Preview</b> before export.</li><li>Select output folder then click <b>Export MP3</b>.</li><li>If segments fail, retry export to regenerate only failed segments.</li></ol><h4>Parameter tips</h4><ul><li>Rate: +10% / -10%</li><li>Volume: +0% / -10%</li><li>Pitch: +0Hz / +20Hz</li></ul><h4>Application info</h4><p><b>Sub2Speech</b> converts SRT/TXT content into MP3 audio for content production workflows. The app supports in-app preview, failed-segment retry, and persistent settings per session.</p><ul><li>Version: <b>{version}</b></li><li>Author: <b>vega</b></li><li>Tech stack: PySide6, edge-tts, ffmpeg</li><li>License: <b>GNU GPL v3</b> (<a href='https://www.gnu.org/licenses/gpl-3.0.html'>Details</a>)</li><li>Settings file: {settings_path}</li><li>Default output folder: {output_dir}</li></ul><p>This software is free software licensed under GNU GPL v3. See bundled LICENSE for details.</p>",
    },
}


class Translator(QObject):
    language_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._language = LANG_VI

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        target = language if language in (LANG_VI, LANG_EN) else LANG_VI
        if target == self._language:
            return
        self._language = target
        self.language_changed.emit(self._language)

    def tr(self, key: str, **kwargs: object) -> str:
        text = STRINGS.get(self._language, {}).get(key) or STRINGS[LANG_VI].get(key) or key
        if kwargs:
            return text.format(**kwargs)
        return text


translator = Translator()


def tr(key: str, **kwargs: object) -> str:
    return translator.tr(key, **kwargs)
