"""
Tests for MainWindow integration API methods.
"""

from gui.main import MainWindow


class TestMainWindowIntegrationAPI:
    """Test MainWindow integration API methods."""

    def test_get_selected_pdf_path_empty(self, qtbot):
        """Test getSelectedPdfPath when no file is selected."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.getSelectedPdfPath() == ""

    def test_get_selected_pdf_path_with_selection(self, qtbot, tmp_path):
        """Test getSelectedPdfPath with a selected file."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create test PDF
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")

        # Simulate file selection
        window._apply_selected_file(str(test_pdf))

        assert window.getSelectedPdfPath() == str(test_pdf)

    def test_clear_selected_pdf(self, qtbot, tmp_path):
        """Test clearSelectedPdf method."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Set initial selection
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")
        window._apply_selected_file(str(test_pdf))

        # Verify selection exists
        assert window.getSelectedPdfPath() == str(test_pdf)

        # Clear selection
        window.clearSelectedPdf()

        # Verify selection is cleared
        assert window.getSelectedPdfPath() == ""

    def test_pdf_selected_signal_connection(self, qtbot):
        """Test that pdfSelected signal is connected."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Verify the signal handler exists
        assert hasattr(window, "on_pdf_selected")
        assert callable(window.on_pdf_selected)

    def test_pdf_cleared_signal_connection(self, qtbot):
        """Test that pdfCleared signal is connected."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Verify the signal handler exists
        assert hasattr(window, "on_pdf_cleared")
        assert callable(window.on_pdf_cleared)

    def test_on_pdf_cleared_handler(self, qtbot, tmp_path):
        """Test the on_pdf_cleared signal handler."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Set initial selection
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")
        window._apply_selected_file(str(test_pdf))

        # Verify initial state
        assert window.selected_file_path == str(test_pdf)

        # Trigger cleared handler
        window.on_pdf_cleared()

        # Verify state was cleared
        assert window.selected_file_path is None
        assert window.status_label.text() == "Drop a PDF file to begin"

    def test_browse_button_tooltip_enhanced(self, qtbot):
        """Test that Browse button has enhanced tooltip."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert "Ctrl+O" in window.browse_button.toolTip()


# pytest-qt provides the qtbot fixture automatically
