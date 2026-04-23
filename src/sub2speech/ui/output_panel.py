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
        self.browse_btn = QPushButton("Chọn...")
        self.browse_btn.clicked.connect(self.choose_output_dir)
        self.export_button.setMinimumWidth(120)
        self.browse_btn.setMinimumWidth(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Thư mục xuất"))
        layout.addWidget(self.output_edit, 1)
        layout.addWidget(self.browse_btn)
        layout.addStretch(1)
        layout.addWidget(self.save_original_checkbox)
        layout.addWidget(self.export_button)

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục xuất")
        if directory:
            self.output_edit.setText(directory)
