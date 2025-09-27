# PDF2Foundry GUI

A PySide6-based graphical user interface for the PDF2Foundry tool.

## Project Structure

```text
pdf2foundry-gui/
├── src/                    # Source code (src layout)
│   ├── gui/               # GUI components and widgets
│   └── core/              # Backend integration and core logic
├── resources/             # Static assets
│   ├── icons/            # Application and UI icons
│   ├── styles/           # Qt Style Sheets (QSS)
│   └── translations/     # Internationalization files
├── tests/                # Unit and integration tests
├── .venv/                # Virtual environment
└── pyproject.toml        # Project configuration and dependencies
```

## Development Setup

1. Create and activate virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

1. Install dependencies:

   ```bash
   pip install -e .[build]
   ```

1. Run the application:

   ```bash
   python run.py
   # or after installation:
   pdf2foundry-gui
   ```

## Import Paths

The project uses src-layout for clean imports:

- GUI components: `from gui.module import Component`
- Core functionality: `from core.module import Function`

For local development without installation, ensure `src/` is in your Python path or use the provided `run.py` script.

## Requirements

- Python 3.12+
- PySide6 6.9.2
- PyInstaller 6.16.0 (for packaging)

## License

This project is licensed under the GNU GPLv3 - see the [LICENSE](LICENSE) file for details.
