"""
Shared fixtures for InputValidator tests.
"""

import pytest
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QApplication, QLineEdit

from core.errors import ValidationError
from gui.validation.input_validator import InputValidator


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class MockValidator(QValidator):
    """Mock validator for testing."""

    def __init__(self, should_accept=True):
        super().__init__()
        self.should_accept = should_accept

    def validate(self, input_text, pos):
        if self.should_accept:
            return QValidator.State.Acceptable, input_text, pos
        else:
            return QValidator.State.Invalid, input_text, pos


class MockCallableValidator:
    """Mock callable validator for testing."""

    def __init__(self, should_accept=True, error_message="Invalid input"):
        self.should_accept = should_accept
        self.error_message = error_message

    def __call__(self, value):
        if not self.should_accept:
            raise ValidationError("test_field", "INVALID", self.error_message, value)
        return True


class MockExternalSource:
    """Mock external validation source for testing."""

    def __init__(self):
        self.is_valid = True
        self.error_message = ""

    def set_validation_result(self, is_valid, error_message=""):
        self.is_valid = is_valid
        self.error_message = error_message


@pytest.fixture
def mock_validator():
    """Mock QValidator that accepts all input."""
    return MockValidator(should_accept=True)


@pytest.fixture
def mock_invalid_validator():
    """Mock QValidator that rejects all input."""
    return MockValidator(should_accept=False)


@pytest.fixture
def mock_callable_validator():
    """Mock callable validator that accepts all input."""
    return MockCallableValidator(should_accept=True)


@pytest.fixture
def mock_invalid_callable_validator():
    """Mock callable validator that rejects all input."""
    return MockCallableValidator(should_accept=False)


@pytest.fixture
def mock_external_source():
    """Mock external validation source."""
    return MockExternalSource()


@pytest.fixture
def sample_line_edit():
    """Sample QLineEdit for testing."""
    return QLineEdit()


@pytest.fixture
def input_validator():
    """InputValidator instance for testing."""
    return InputValidator()
