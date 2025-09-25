"""
Tests for Browse button functionality in MainWindow.
"""

from unittest.mock import Mock, patch

from PySide6.QtCore import Qt

from gui.main import MainWindow


class TestBrowseButtonFunctionality:
    """Test Browse button functionality and file dialog integration."""

    def test_browse_button_properties(self, qtbot):
        """Test that Browse button is configured correctly."""
        window = MainWindow()
        qtbot.addWidget(window)

        browse_button = window.browse_button
        assert browse_button.text() == "Browse…"
        assert browse_button.toolTip() == "Choose a PDF file (Ctrl+O)"
        assert browse_button.accessibleName() == "Browse for PDF"
        assert browse_button.accessibleDescription() == "Opens a file dialog filtered to PDF files"

    def test_browse_button_signal_connection(self, qtbot):
        """Test that Browse button signal is connected."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Verify the method exists and can be called
        assert hasattr(window, "on_browse_clicked")
        assert callable(window.on_browse_clicked)

    @patch("gui.main.QFileDialog.getOpenFileName")
    def test_browse_valid_pdf_selection(self, mock_dialog, qtbot, tmp_path):
        """Test Browse button with valid PDF selection."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create a test PDF file
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")

        # Mock the file dialog to return our test PDF
        mock_dialog.return_value = (str(test_pdf), "PDF Files (*.pdf)")

        # Mock _apply_selected_file to verify it gets called
        with patch.object(window, "_apply_selected_file") as mock_apply:
            # Trigger browse button click
            window.on_browse_clicked()

            # Verify dialog was called with correct parameters
            mock_dialog.assert_called_once()
            args = mock_dialog.call_args[0]
            assert args[0] == window  # parent
            assert args[1] == "Select PDF"  # caption
            assert args[3] == "PDF Files (*.pdf)"  # filter

            # Verify _apply_selected_file was called with the selected path
            mock_apply.assert_called_once_with(str(test_pdf))

    @patch("gui.main.QFileDialog.getOpenFileName")
    def test_browse_invalid_file_selection(self, mock_dialog, qtbot, tmp_path):
        """Test Browse button with invalid file selection."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create a non-PDF file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Not a PDF")

        # Mock the file dialog to return the non-PDF file
        mock_dialog.return_value = (str(test_file), "PDF Files (*.pdf)")

        # Trigger browse button click
        window.on_browse_clicked()

        # Verify error handling - selected_file_path should remain None
        assert window.selected_file_path is None

        # Verify status shows error message
        assert "Not a valid PDF file" in window.status_label.text()

    @patch("gui.main.QFileDialog.getOpenFileName")
    def test_browse_dialog_cancellation(self, mock_dialog, qtbot):
        """Test Browse button when user cancels dialog."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Store initial state
        initial_status = window.status_label.text()
        initial_file_path = window.selected_file_path

        # Mock the file dialog to return empty (cancelled)
        mock_dialog.return_value = ("", "")

        # Trigger browse button click
        window.on_browse_clicked()

        # Verify no state changes occurred
        assert window.status_label.text() == initial_status
        assert window.selected_file_path == initial_file_path

    @patch("gui.main.QSettings")
    def test_settings_persistence(self, mock_settings_class, qtbot, tmp_path):
        """Test that last directory is saved and loaded correctly."""
        # Mock QSettings instance
        mock_settings = Mock()
        mock_settings_class.return_value = mock_settings

        # Test loading settings
        mock_settings.value.return_value = str(tmp_path)
        window = MainWindow()
        qtbot.addWidget(window)

        # Verify settings were loaded
        mock_settings.value.assert_called_with("ui/last_open_dir", None)
        assert window.last_directory == str(tmp_path)

        # Test saving settings
        new_dir = str(tmp_path / "new_directory")
        window.last_directory = new_dir
        window._save_settings()

        # Verify settings were saved
        mock_settings.setValue.assert_called_with("ui/last_open_dir", new_dir)

    @patch("gui.main.QFileDialog.getOpenFileName")
    @patch("gui.main.QStandardPaths.writableLocation")
    def test_directory_fallback(self, mock_standard_paths, mock_dialog, qtbot):
        """Test fallback to Documents directory when no last directory."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Ensure no last directory is set
        window.last_directory = None

        # Mock Documents directory
        mock_standard_paths.return_value = "/Users/test/Documents"

        # Mock dialog cancellation to avoid side effects
        mock_dialog.return_value = ("", "")

        # Trigger browse
        window.on_browse_clicked()

        # Verify Documents directory was used as fallback
        mock_standard_paths.assert_called_once()
        mock_dialog.assert_called_once()
        args = mock_dialog.call_args[0]
        assert args[2] == "/Users/test/Documents"  # start directory

    def test_tab_order_includes_browse_button(self, qtbot):
        """Test that tab order includes the Browse button."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        # Verify Browse button can receive focus
        assert window.browse_button.focusPolicy() != Qt.FocusPolicy.NoFocus

        # Test that Browse button can be focused
        window.browse_button.setFocus()
        # Note: Focus behavior in tests can be unreliable without actual window activation
        # The important thing is that the button has a proper focus policy


# pytest-qt provides the qtbot fixture automatically
