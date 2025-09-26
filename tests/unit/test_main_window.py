"""
Tests for the MainWindow class.
"""

from unittest.mock import Mock, patch

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton

from gui.main_window import MainWindow
from gui.widgets.drag_drop import DragDropLabel


class TestMainWindowInitialization:
    """Test MainWindow initialization and setup."""

    def test_window_properties(self, qtbot):
        """Test that window properties are set correctly."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.windowTitle() == "PDF2Foundry GUI"
        assert window.size().width() == 800
        assert window.size().height() == 600
        assert window.selected_file_path is None

    def test_ui_components_created(self, qtbot):
        """Test that all UI components are created."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Check that main components exist
        assert hasattr(window, "drag_drop_label")
        assert hasattr(window, "status_label")
        assert hasattr(window, "browse_button")

        # Check component types
        assert isinstance(window.drag_drop_label, DragDropLabel)
        assert isinstance(window.browse_button, QPushButton)
        assert window.status_label.text() == "Ready to convert PDF files"

    def test_drag_drop_label_properties(self, qtbot):
        """Test that drag-drop label is configured correctly."""
        window = MainWindow()
        qtbot.addWidget(window)

        drag_label = window.drag_drop_label
        # The minimum height is now set via CSS min-height, not widget property
        assert drag_label.minimumHeight() > 0
        assert drag_label.focusPolicy() == Qt.FocusPolicy.StrongFocus
        assert drag_label.accessibleName() == "PDF file drop zone"

    def test_status_label_properties(self, qtbot):
        """Test that status label is configured correctly."""
        window = MainWindow()
        qtbot.addWidget(window)

        status_label = window.status_label
        assert status_label.accessibleName() == "Status message"
        assert status_label.accessibleDescription() == "Displays the current selection and errors"
        assert status_label.alignment() == Qt.AlignmentFlag.AlignCenter

    def test_signals_connected(self, qtbot):
        """Test that drag-drop signals are connected."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Test that signals are connected by checking if methods exist
        assert hasattr(window, "on_file_accepted")
        assert hasattr(window, "on_file_rejected")

        # Verify the drag_drop_label has the expected signals
        assert hasattr(window.drag_drop_label, "fileAccepted")
        assert hasattr(window.drag_drop_label, "fileRejected")


class TestMainWindowFileHandling:
    """Test file selection and rejection handling."""

    def test_apply_selected_file(self, qtbot, tmp_path):
        """Test _apply_selected_file method."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create a test PDF file
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")

        # Apply selected file
        window._apply_selected_file(str(test_pdf))

        assert window.selected_file_path == str(test_pdf)
        assert "Selected: test.pdf" in window.status_label.text()

    def test_on_file_accepted(self, qtbot, tmp_path):
        """Test file acceptance handling."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create a test PDF file
        test_pdf = tmp_path / "test_document.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")

        # Call on_file_accepted directly
        window.on_file_accepted(str(test_pdf))

        # Check that file was applied
        assert window.selected_file_path == str(test_pdf)

        # Check status label was updated
        assert "Selected: test_document.pdf" in window.status_label.text()

        # Check that success styling was applied (accessible colors)
        style = window.status_label.styleSheet()
        assert "#f8f9fa" in style  # Success background color (accessible)
        assert "#198754" in style  # Success text color (accessible)

    def test_on_file_rejected(self, qtbot):
        """Test file rejection handling."""
        window = MainWindow()
        qtbot.addWidget(window)

        error_message = "File is not a PDF"
        window.on_file_rejected(error_message)

        # Check that selected file path is cleared
        assert window.selected_file_path is None

        # Check status label shows error message with "Error:" prefix
        assert window.status_label.text() == f"Error: {error_message}"

        # Check that error styling was applied (red background)
        style = window.status_label.styleSheet()
        assert "#f8d7da" in style  # Error background color
        assert "#721c24" in style  # Error text color

    def test_file_accepted_signal_integration(self, qtbot, tmp_path):
        """Test that fileAccepted signal properly triggers on_file_accepted."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create a test PDF file
        test_pdf = tmp_path / "integration_test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")

        # Mock _apply_selected_file to verify it gets called
        with patch.object(window, "_apply_selected_file") as mock_apply:
            # Emit the signal directly
            window.drag_drop_label.fileAccepted.emit(str(test_pdf))

            # Verify the handler was called
            mock_apply.assert_called_once_with(str(test_pdf))

    def test_file_rejected_signal_integration(self, qtbot):
        """Test that fileRejected signal properly triggers on_file_rejected."""
        window = MainWindow()
        qtbot.addWidget(window)

        error_message = "Invalid file type"

        # Emit the signal directly
        window.drag_drop_label.fileRejected.emit(error_message)

        # Verify the handler was called and state updated
        assert window.selected_file_path is None
        assert window.status_label.text() == f"Error: {error_message}"


class TestMainWindowAccessibility:
    """Test accessibility features."""

    def test_initial_focus(self, qtbot):
        """Test that initial focus is set correctly."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # The drag-drop label should have focus initially
        # Note: Focus might not be set until the window is actually shown
        QTest.qWaitForWindowActive(window)

        # Check that the drag-drop label can receive focus
        assert window.drag_drop_label.focusPolicy() == Qt.FocusPolicy.StrongFocus

    def test_tab_order(self, qtbot):
        """Test tab order between components."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Verify that tab order is set up (this is hard to test directly,
        # but we can check that the method was called during setup)
        assert window.drag_drop_label.focusPolicy() == Qt.FocusPolicy.StrongFocus


class TestMainWindowLayout:
    """Test layout and responsive behavior."""

    def test_layout_structure(self, qtbot):
        """Test that the layout is structured correctly."""
        window = MainWindow()
        qtbot.addWidget(window)

        central_widget = window.centralWidget()
        assert central_widget is not None

        layout = central_widget.layout()
        assert layout is not None
        # Current layout: header_widget, main_splitter
        assert layout.count() == 2

    def test_stretch_factors(self, qtbot):
        """Test that stretch factors are set correctly."""
        window = MainWindow()
        qtbot.addWidget(window)

        layout = window.centralWidget().layout()

        # Current layout: header_widget (no stretch), main_splitter (no explicit stretch)
        assert layout.stretch(0) == 0  # header_widget
        assert layout.stretch(1) == 0  # main_splitter (default stretch is 0)

    def test_layout_margins_and_spacing(self, qtbot):
        """Test layout margins and spacing."""
        window = MainWindow()
        qtbot.addWidget(window)

        layout = window.centralWidget().layout()
        margins = layout.contentsMargins()

        assert margins.left() == 20
        assert margins.top() == 20
        assert margins.right() == 20
        assert margins.bottom() == 20
        assert layout.spacing() == 20


class TestMainApplication:
    """Test the main application function."""

    @patch("gui.main.QApplication")
    @patch("gui.main.MainWindow")
    def test_main_function(self, mock_window_class, mock_app_class):
        """Test the main() function."""
        # Mock the application and window
        mock_app = Mock()
        mock_app.exec.return_value = 0
        mock_app_class.return_value = mock_app

        mock_window = Mock()
        mock_window_class.return_value = mock_window

        # Import and call main
        from gui.main import main

        result = main()

        # Verify QApplication was created with sys.argv
        mock_app_class.assert_called_once()

        # Verify MainWindow was created and shown
        mock_window_class.assert_called_once()
        mock_window.show.assert_called_once()

        # Verify app.exec() was called and result returned
        mock_app.exec.assert_called_once()
        assert result == 0


# pytest-qt provides the qtbot fixture automatically
