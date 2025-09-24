"""
Main entry point for the PySide6 GUI application.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


def main() -> int:
    """Main application entry point."""
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("PySide6 App")
    label = QLabel("Hello, PySide6 6.6.0!")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    win.setCentralWidget(label)
    win.resize(640, 400)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
