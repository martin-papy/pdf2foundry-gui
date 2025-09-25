"""
Tests for DragDropLabel widget.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from gui.widgets.drag_drop import DragDropLabel


@pytest.fixture
def app():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def widget(app):
    """Create DragDropLabel widget for testing."""
    return DragDropLabel()


class TestDragDropLabelInitialization:
    """Test DragDropLabel initialization and setup."""

    def test_initial_state(self, widget):
        """Test widget is properly initialized."""
        assert widget.acceptDrops() is True
        assert widget._current_state == DragDropLabel.STATE_NORMAL
        assert widget.accessibleName() == "PDF file drop zone"
        assert "Drop a PDF file here" in widget.accessibleDescription()

    def test_initial_appearance(self, widget):
        """Test initial visual appearance."""
        assert "📄 Drop a PDF or use Browse" in widget.text()
        assert "Supported: .pdf files only" in widget.text()

    def test_size_hints(self, widget):
        """Test size hints are reasonable."""
        size_hint = widget.sizeHint()
        min_size_hint = widget.minimumSizeHint()

        assert size_hint.width() >= 400
        assert size_hint.height() >= 200
        assert min_size_hint.width() >= 300
        assert min_size_hint.height() >= 150


class TestDragDropLabelStates:
    """Test visual state management."""

    def test_set_state_normal(self, widget):
        """Test setting normal state."""
        widget._set_state(DragDropLabel.STATE_NORMAL)
        assert widget._current_state == DragDropLabel.STATE_NORMAL
        assert "palette(mid)" in widget.styleSheet()  # Palette-aware border color

    def test_set_state_hover(self, widget):
        """Test setting hover state."""
        widget._set_state(DragDropLabel.STATE_HOVER)
        assert widget._current_state == DragDropLabel.STATE_HOVER
        assert "palette(highlight)" in widget.styleSheet()  # Palette-aware hover border
        assert "Drop your PDF file here" in widget.text()

    def test_set_state_reject(self, widget):
        """Test setting reject state."""
        widget._set_state(DragDropLabel.STATE_REJECT)
        assert widget._current_state == DragDropLabel.STATE_REJECT
        assert "#d32f2f" in widget.styleSheet()  # Error border color

    def test_state_transitions(self, widget):
        """Test state transitions update appearance."""
        initial_style = widget.styleSheet()

        widget._set_state(DragDropLabel.STATE_HOVER)
        hover_style = widget.styleSheet()
        assert hover_style != initial_style

        widget._set_state(DragDropLabel.STATE_REJECT)
        reject_style = widget.styleSheet()
        assert reject_style != hover_style
        assert reject_style != initial_style


class TestDragDropLabelDragEvents:
    """Test drag and drop event handling."""

    def test_drag_enter_valid_pdf(self, widget, tmp_path):
        """Test drag enter with valid PDF file."""
        # Create a test PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        # Mock the validation functions to return valid result
        with (
            patch("gui.widgets.drag_drop.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.drag_drop.validate_single_pdf_source") as mock_validate,
        ):
            mock_extract.return_value = [pdf_file]
            mock_validate.return_value = (pdf_file, None)

            # Create mock drag enter event
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(str(pdf_file))])

            event = Mock(spec=QDragEnterEvent)
            event.mimeData.return_value = mime_data

            # Test drag enter
            widget.dragEnterEvent(event)

            # Should accept and change to hover state
            event.acceptProposedAction.assert_called_once()
            assert widget._current_state == DragDropLabel.STATE_HOVER

    def test_drag_enter_invalid_file(self, widget, tmp_path):
        """Test drag enter with invalid file."""
        # Create a test non-PDF file
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("text content")

        # Mock the validation functions to return invalid result
        with (
            patch("gui.widgets.drag_drop.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.drag_drop.validate_single_pdf_source") as mock_validate,
        ):
            mock_extract.return_value = [txt_file]
            mock_validate.return_value = (None, "File is not a PDF (detected: .txt). Please select a PDF file.")

            # Create mock drag enter event
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(str(txt_file))])

            event = Mock(spec=QDragEnterEvent)
            event.mimeData.return_value = mime_data

            # Test drag enter
            widget.dragEnterEvent(event)

            # Should reject and show error
            event.ignore.assert_called_once()
            assert widget._current_state == DragDropLabel.STATE_REJECT
            assert "File is not a PDF" in widget.text()

    def test_drag_enter_no_urls(self, widget):
        """Test drag enter with no URLs."""
        mime_data = QMimeData()
        mime_data.setText("some text")  # No URLs

        event = Mock(spec=QDragEnterEvent)
        event.mimeData.return_value = mime_data

        widget.dragEnterEvent(event)

        event.ignore.assert_called_once()
        assert widget._current_state == DragDropLabel.STATE_REJECT

    def test_drag_move_with_urls(self, widget):
        """Test drag move with URLs."""
        mime_data = QMimeData()
        mime_data.setUrls([QUrl("file:///test.pdf")])

        event = Mock(spec=QDragMoveEvent)
        event.mimeData.return_value = mime_data

        widget.dragMoveEvent(event)

        event.acceptProposedAction.assert_called_once()

    def test_drag_move_without_urls(self, widget):
        """Test drag move without URLs."""
        mime_data = QMimeData()
        mime_data.setText("text")

        event = Mock(spec=QDragMoveEvent)
        event.mimeData.return_value = mime_data

        widget.dragMoveEvent(event)

        event.ignore.assert_called_once()

    def test_drag_leave(self, widget):
        """Test drag leave event."""
        # Set to hover state first
        widget._set_state(DragDropLabel.STATE_HOVER)

        event = Mock(spec=QDragLeaveEvent)
        widget.dragLeaveEvent(event)

        # Should return to normal state
        assert widget._current_state == DragDropLabel.STATE_NORMAL
        event.accept.assert_called_once()


class TestDragDropLabelDropEvents:
    """Test drop event handling."""

    def test_drop_valid_pdf(self, widget, tmp_path):
        """Test dropping a valid PDF file."""
        # Create a test PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf content")

        # Mock the validation functions
        with (
            patch("gui.widgets.drag_drop.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.drag_drop.validate_single_pdf_source") as mock_validate,
        ):
            mock_extract.return_value = [pdf_file]
            mock_validate.return_value = (pdf_file, None)

            # Create mock drop event
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(str(pdf_file))])

            event = Mock(spec=QDropEvent)
            event.mimeData.return_value = mime_data

            # Connect signal to capture emission
            signal_received = []
            widget.fileAccepted.connect(lambda path: signal_received.append(path))

            # Test drop
            widget.dropEvent(event)

            # Should accept and emit signal
            event.acceptProposedAction.assert_called_once()
            assert len(signal_received) == 1
            assert signal_received[0] == str(pdf_file)
            assert "✅ PDF Selected" in widget.text()
            assert pdf_file.name in widget.text()

    def test_drop_invalid_file(self, widget, tmp_path):
        """Test dropping an invalid file."""
        # Create a test non-PDF file
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("text content")

        # Mock the validation functions
        with (
            patch("gui.widgets.drag_drop.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.drag_drop.validate_single_pdf_source") as mock_validate,
        ):
            mock_extract.return_value = [txt_file]
            mock_validate.return_value = (None, "File is not a PDF")

            # Create mock drop event
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(str(txt_file))])

            event = Mock(spec=QDropEvent)
            event.mimeData.return_value = mime_data

            # Connect signal to capture emission
            signal_received = []
            widget.fileRejected.connect(lambda msg: signal_received.append(msg))

            # Test drop
            widget.dropEvent(event)

            # Should reject and emit error signal
            event.ignore.assert_called_once()
            assert len(signal_received) == 1
            assert "File is not a PDF" in signal_received[0]
            assert widget._current_state == DragDropLabel.STATE_REJECT
            assert "❌" in widget.text()

    def test_drop_multiple_files(self, widget, tmp_path):
        """Test dropping multiple files."""
        # Create test PDF files
        pdf1 = tmp_path / "test1.pdf"
        pdf2 = tmp_path / "test2.pdf"
        pdf1.write_text("fake pdf 1")
        pdf2.write_text("fake pdf 2")

        # Mock the validation functions
        with (
            patch("gui.widgets.drag_drop.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.drag_drop.validate_single_pdf_source") as mock_validate,
        ):
            mock_extract.return_value = [pdf1, pdf2]
            mock_validate.return_value = (None, "Multiple files provided (2). Please select only one PDF file.")

            # Create mock drop event
            mime_data = QMimeData()
            mime_data.setUrls([QUrl.fromLocalFile(str(pdf1)), QUrl.fromLocalFile(str(pdf2))])

            event = Mock(spec=QDropEvent)
            event.mimeData.return_value = mime_data

            # Connect signal to capture emission
            signal_received = []
            widget.fileRejected.connect(lambda msg: signal_received.append(msg))

            # Test drop
            widget.dropEvent(event)

            # Should reject with multiple files message
            event.ignore.assert_called_once()
            assert len(signal_received) == 1
            assert "Multiple files provided" in signal_received[0]

    def test_drop_exception_handling(self, widget):
        """Test drop event exception handling."""
        # Mock extract function to raise exception
        with patch("gui.widgets.drag_drop.extract_local_paths_from_mimedata", side_effect=Exception("Test error")):
            mime_data = QMimeData()
            mime_data.setUrls([QUrl("file:///test.pdf")])

            event = Mock(spec=QDropEvent)
            event.mimeData.return_value = mime_data

            # Connect signal to capture emission
            signal_received = []
            widget.fileRejected.connect(lambda msg: signal_received.append(msg))

            # Test drop
            widget.dropEvent(event)

            # Should handle exception gracefully
            event.ignore.assert_called_once()
            assert len(signal_received) == 1
            assert "Error processing file" in signal_received[0]


class TestDragDropLabelPublicMethods:
    """Test public methods for external control."""

    def test_reset(self, widget):
        """Test reset method."""
        # Change to different state
        widget._set_state(DragDropLabel.STATE_HOVER)
        assert widget._current_state == DragDropLabel.STATE_HOVER

        # Reset
        widget.reset()
        assert widget._current_state == DragDropLabel.STATE_NORMAL

    def test_set_file_selected(self, widget, tmp_path):
        """Test set_file_selected method."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_text("fake pdf")

        widget.set_file_selected(str(pdf_file))

        assert widget._current_state == DragDropLabel.STATE_NORMAL
        assert "✅ PDF Selected" in widget.text()
        assert "test.pdf" in widget.text()
        assert "Ready to convert" in widget.text()

    def test_set_error(self, widget):
        """Test set_error method."""
        error_msg = "Custom error message"

        # Connect signal to capture emission
        signal_received = []
        widget.fileRejected.connect(lambda msg: signal_received.append(msg))

        widget.set_error(error_msg)

        assert widget._current_state == DragDropLabel.STATE_REJECT
        assert error_msg in widget.text()
        assert len(signal_received) == 1
        assert signal_received[0] == error_msg


class TestDragDropLabelAccessibility:
    """Test accessibility features."""

    def test_keyboard_navigation(self, widget):
        """Test keyboard accessibility."""
        # Test that widget can receive focus
        assert widget.focusPolicy() == Qt.FocusPolicy.StrongFocus

        # Test accessibility properties
        assert widget.accessibleName() == "PDF file drop zone"
        assert "Drop a PDF file here" in widget.accessibleDescription()

    def test_keyboard_events(self, widget):
        """Test keyboard event handling."""
        # Mock key press event
        from PySide6.QtGui import QKeyEvent

        # Test Enter key (should trigger file browser if connected)
        enter_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier)

        # This should not crash (actual file browser trigger would be handled by parent)
        widget.keyPressEvent(enter_event)

        # Test Space key
        space_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
        widget.keyPressEvent(space_event)

        # Test other keys (should call parent)
        other_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        widget.keyPressEvent(other_event)


class TestDragDropLabelEnhancements:
    """Test enhanced functionality and integration API."""

    def test_object_name_set(self, widget):
        """Test that object name is set for CSS styling."""
        assert widget.objectName() == "dragZone"

    def test_new_signals_exist(self, widget):
        """Test that new signals are available."""
        # Test signal existence
        assert hasattr(widget, "pdfSelected")
        assert hasattr(widget, "pdfCleared")

    def test_selected_pdf_path_tracking(self, widget, tmp_path):
        """Test PDF path tracking functionality."""
        # Initially no selection
        assert widget.selectedPdfPath() == ""

        # Set a file selection
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")

        widget.set_file_selected(str(test_pdf))
        assert widget.selectedPdfPath() == str(test_pdf)

        # Clear selection
        widget.clearSelectedPdf()
        assert widget.selectedPdfPath() == ""

    def test_pdf_cleared_signal_emission(self, widget):
        """Test that pdfCleared signal is emitted correctly."""
        # Set initial selection
        widget._selected_pdf_path = "/some/path.pdf"

        # Connect signal to capture emissions
        pdf_cleared_calls = []
        widget.pdfCleared.connect(lambda: pdf_cleared_calls.append(True))

        # Clear selection
        widget.clearSelectedPdf()

        # Verify signal was emitted
        assert len(pdf_cleared_calls) == 1
        assert widget.selectedPdfPath() == ""

    def test_enhanced_styling_methods(self, widget):
        """Test that enhanced styling methods exist."""
        # Test that styling methods exist
        assert hasattr(widget, "_get_base_stylesheet")
        assert hasattr(widget, "_get_hover_stylesheet")
        assert hasattr(widget, "_get_reject_stylesheet")
        assert hasattr(widget, "_update_cursor")

        # Test that they return strings
        assert isinstance(widget._get_base_stylesheet(), str)
        assert isinstance(widget._get_hover_stylesheet(), str)
        assert isinstance(widget._get_reject_stylesheet(), str)

    def test_tooltip_set(self, widget):
        """Test that tooltip is properly set."""
        assert widget.toolTip() == "Drop a PDF file here. Only .pdf files are accepted."

    def test_accessibility_updates_on_selection(self, widget, tmp_path):
        """Test that accessibility description updates when file is selected."""
        # Initial state
        initial_desc = widget.accessibleDescription()
        assert "Drop a PDF file here" in initial_desc

        # Select a file
        test_pdf = tmp_path / "test_document.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\ntest content")

        widget.set_file_selected(str(test_pdf))

        # Check that description was updated
        updated_desc = widget.accessibleDescription()
        assert "test_document.pdf" in updated_desc

        # Clear selection
        widget.clearSelectedPdf()

        # Check that description was reset
        reset_desc = widget.accessibleDescription()
        assert "Drop a PDF file here" in reset_desc
