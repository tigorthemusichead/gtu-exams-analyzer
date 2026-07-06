STYLESHEET = """
QWidget {
    background-color: #F7F7FF;
    color: #1E1B4B;
    font-size: 13px;
}

QLabel {
    background-color: transparent;
    color: #1E1B4B;
}

QLineEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #D4D4F4;
    border-radius: 7px;
    padding: 8px 12px;
    font-size: 13px;
    color: #1E1B4B;
    min-height: 18px;
}

QLineEdit:focus {
    border-color: #7C3AED;
}

QLineEdit:read-only {
    background-color: #EDEDFF;
    color: #6B7280;
}

QPushButton {
    background-color: #7C3AED;
    color: #FFFFFF;
    border: none;
    border-radius: 7px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #6D28D9;
}

QPushButton:pressed {
    background-color: #5B21B6;
}

QPushButton:disabled {
    background-color: #C4B5FD;
    color: #EDE9FE;
}

QPushButton[role="secondary"] {
    background-color: transparent;
    color: #7C3AED;
    border: 1.5px solid #7C3AED;
}

QPushButton[role="secondary"]:hover {
    background-color: #EDE9FE;
}

QPushButton[role="secondary"]:pressed {
    background-color: #DDD6FE;
}

QPushButton[role="danger"] {
    background-color: #DC2626;
}

QPushButton[role="danger"]:hover {
    background-color: #B91C1C;
}

QPushButton[role="danger"]:pressed {
    background-color: #991B1B;
}

QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #DDD8FF;
    border-radius: 10px;
}

QFrame#divider {
    background-color: #E0E0F8;
    border: none;
}

QMessageBox {
    background-color: #F7F7FF;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""
