"""Entry point for Whisper Voice Input application."""

import sys
import os

# Add src directory to path for PyInstaller compatibility
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    _base_path = sys._MEIPASS
    if _base_path not in sys.path:
        sys.path.insert(0, _base_path)


def main() -> int:
    """Run the application."""
    # Import Qt first to avoid import order issues
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create Qt application
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when windows close

    # Set application info - use try/except for both import styles
    try:
        from src.config.constants import APP_NAME, APP_VERSION
        from src.app import VoiceInputApp
    except ImportError:
        from .config.constants import APP_NAME, APP_VERSION
        from .app import VoiceInputApp

    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Create and run main app
    voice_app = VoiceInputApp(app)
    return voice_app.run()


if __name__ == "__main__":
    sys.exit(main())
