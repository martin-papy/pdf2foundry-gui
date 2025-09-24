"""
Tests for DragDropLabel widget.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from gui.widgets import DragDropLabel


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
        assert "Drag and drop a PDF file here" in widget.accessibleDescription()

    def test_initial_appearance(self, widget):
        """Test initial visual appearance."""
        assert "📂 Drag & Drop your PDF here" in widget.text()
        assert "OR" in widget.text()
        assert "Browse button" in widget.text()

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
        assert "#cccccc" in widget.styleSheet()  # Normal border color

    def test_set_state_hover(self, widget):
        """Test setting hover state."""
        widget._set_state(DragDropLabel.STATE_HOVER)
        assert widget._current_state == DragDropLabel.STATE_HOVER
        assert "#0078d4" in widget.styleSheet()  # Hover border color
        assert "Drop your PDF file here" in widget.text()

    def test_set_state_reject(self, widget):
        """Test setting reject state."""
        widget._set_state(DragDropLabel.STATE_REJECT)
        assert widget._current_state == DragDropLabel.STATE_REJECT
        assert "#d13438" in widget.styleSheet()  # Reject border color

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
            patch("gui.widgets.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.validate_single_pdf_source") as mock_validate,
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
            patch("gui.widgets.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.validate_single_pdf_source") as mock_validate,
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
            patch("gui.widgets.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.validate_single_pdf_source") as mock_validate,
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
            patch("gui.widgets.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.validate_single_pdf_source") as mock_validate,
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
            patch("gui.widgets.extract_local_paths_from_mimedata") as mock_extract,
            patch("gui.widgets.validate_single_pdf_source") as mock_validate,
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
        with patch("gui.widgets.extract_local_paths_from_mimedata", side_effect=Exception("Test error")):
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
        assert "Drag and drop a PDF file here" in widget.accessibleDescription()

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
