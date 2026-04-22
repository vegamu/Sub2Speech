def build_stylesheet() -> str:
    return """
QMainWindow, QWidget {
    background: #f5f7fb;
    color: #0f172a;
    font-size: 12px;
}

QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 4px;
}

QLabel#subtleText {
    color: #475569;
}

QFrame#topBarCard,
QFrame#contentCard,
QFrame#configCard,
QFrame#actionCard,
QFrame#playerCard {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}

QPushButton {
    background: #e2e8f0;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px 12px;
}

QPushButton:hover {
    background: #dbe4ef;
}

QPushButton:disabled {
    color: #94a3b8;
    background: #f1f5f9;
    border-color: #e2e8f0;
}

QPushButton#primaryButton {
    background: #2563eb;
    color: #ffffff;
    border-color: #1d4ed8;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background: #1d4ed8;
}

QLineEdit, QComboBox, QTextEdit {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 5px 8px;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #60a5fa;
}

QTableWidget {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #e2e8f0;
}

QHeaderView::section {
    background: #f8fafc;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    padding: 6px;
    font-weight: 600;
}
"""
