from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


class OutputPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setObjectName("outputPathEdit")
        self.save_original_checkbox = QCheckBox("Lưu âm thanh gốc theo từng dòng phụ đề")
        self.export_button = QPushButton("Xuất MP3")
        self.export_button.setObjectName("primaryButton")
        self.preview_button = QPushButton("Nghe thử dòng phụ đề")
        self.browse_btn = QPushButton("Chọn thư mục")
        self.browse_btn.clicked.connect(self.choose_output_dir)
        self.preview_button.setMinimumWidth(150)
        self.export_button.setMinimumWidth(120)
        self.browse_btn.setMinimumWidth(120)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(QLabel("Thư mục xuất"))
        row.addWidget(self.output_edit, 1)
        row.addWidget(self.browse_btn)
        row.addWidget(self.preview_button)
        row.addWidget(self.export_button)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addLayout(row)
        layout.addWidget(self.save_original_checkbox)

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất")
        if directory:
            self.output_edit.setText(directory)
