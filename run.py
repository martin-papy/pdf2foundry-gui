"""
Development runner script for the PySide6 GUI application.
This script allows running the application without installation.
"""

import os
import sys

# Add src directory to Python path for local development
sys.path.insert(0, os.path.abspath("src"))

from gui.main import main

if __name__ == "__main__":
    raise SystemExit(main())
