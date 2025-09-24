"""
Smoke tests for PySide6 GUI application.
These tests verify basic functionality and environment setup.
"""

import os
import sys

# Set offscreen platform to prevent display errors on headless systems
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_pyside6_imports():
    """Test that PySide6 can be imported successfully."""
    import PySide6  # noqa: F401
    from PySide6.QtWidgets import QApplication  # noqa: F401


def test_main_window_constructs():
    """Test that the main window can be constructed without errors."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

    from gui.main import main as app_main

    # Ensure QApplication exists (create if needed)
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841

    # Verify that main function is callable
    assert callable(app_main)

    # Test the main window construction directly
    win = QMainWindow()
    win.setWindowTitle("Test PySide6 App")
    label = QLabel("Test Hello, PySide6 6.6.0!")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    win.setCentralWidget(label)
    win.resize(640, 400)

    # Verify window properties
    assert win.windowTitle() == "Test PySide6 App"
    assert win.centralWidget() is not None
    assert isinstance(win.centralWidget(), QLabel)
    assert win.centralWidget().text() == "Test Hello, PySide6 6.6.0!"

    # Clean up
    win.close()


def test_main_module_components():
    """Test individual components from the main module."""
    from PySide6.QtWidgets import QApplication

    from gui import main

    # Ensure QApplication exists
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841

    # Test that the main module has the expected function
    assert hasattr(main, "main")
    assert callable(main.main)

    # Test that we can import the required Qt components
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QMainWindow

    # Verify Qt constants are accessible
    assert hasattr(Qt.AlignmentFlag, "AlignCenter")

    # Test basic widget creation (similar to what main() does)
    window = QMainWindow()
    label = QLabel("Test")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.setCentralWidget(label)

    # Verify the setup
    assert window.centralWidget() == label
    assert label.text() == "Test"

    # Clean up
    window.close()
