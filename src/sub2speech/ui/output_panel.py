from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from sub2speech.utils.i18n import tr, translator


class OutputPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setObjectName("outputPathEdit")
        self.output_label = QLabel()
        self.save_original_checkbox = QCheckBox()
        self.export_button = QPushButton()
        self.export_button.setObjectName("primaryButton")
        self.browse_btn = QPushButton()
        self.browse_btn.clicked.connect(self.choose_output_dir)
        self.export_button.setMinimumWidth(120)
        self.browse_btn.setMinimumWidth(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_edit, 1)
        layout.addWidget(self.browse_btn)
        layout.addStretch(1)
        layout.addWidget(self.save_original_checkbox)
        layout.addWidget(self.export_button)
        translator.language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, tr("output.choose_dialog_title"))
        if directory:
            self.output_edit.setText(directory)

    def retranslate_ui(self) -> None:
        self.output_label.setText(tr("output.dir_label"))
        self.save_original_checkbox.setText(tr("output.save_original"))
        self.export_button.setText(tr("output.export"))
        self.browse_btn.setText(tr("output.browse"))
