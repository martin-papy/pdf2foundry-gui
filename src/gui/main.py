"""
Main entry point for the PDF2Foundry GUI application.
"""

import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> int:
    """Main application entry point."""
    app = QApplication(sys.argv)

    # Create and show the main window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
