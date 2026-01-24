"""Entry point for Whisper Voice Input application."""

import sys
import os
import platform

# Add src directory to path for PyInstaller compatibility
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    _base_path = sys._MEIPASS
    if _base_path not in sys.path:
        sys.path.insert(0, _base_path)


def _setup_logging() -> None:
    """Initialize logging configuration before other imports."""
    try:
        from src.config import configure_logging
    except ImportError:
        from .config import configure_logging

    configure_logging()


def _log_startup_info() -> None:
    """Log application startup information."""
    try:
        from src.config import get_logger
        from src.config.constants import APP_NAME, APP_VERSION
    except ImportError:
        from .config import get_logger
        from .config.constants import APP_NAME, APP_VERSION

    logger = get_logger("main")

    # Log startup banner
    logger.info("=" * 50)
    logger.info("%s v%s starting", APP_NAME, APP_VERSION)
    logger.info("=" * 50)

    # Log system information
    logger.info("Python: %s", sys.version)
    logger.info("Platform: %s %s", platform.system(), platform.release())
    logger.info("Architecture: %s", platform.machine())

    # Log if running as frozen exe
    if getattr(sys, 'frozen', False):
        logger.info("Running as frozen executable")
        logger.debug("Executable path: %s", sys.executable)
    else:
        logger.info("Running from source")


def _setup_exception_handler() -> None:
    """Set up global exception handler for uncaught exceptions."""
    try:
        from src.config import get_logger
    except ImportError:
        from .config import get_logger

    logger = get_logger("main")

    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions by logging them."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow keyboard interrupt to exit normally
            logger.info("Application interrupted by user (KeyboardInterrupt)")
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception


def main() -> int:
    """Run the application.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Initialize logging first
    _setup_logging()
    _log_startup_info()
    _setup_exception_handler()

    # Get logger for this module
    try:
        from src.config import get_logger
    except ImportError:
        from .config import get_logger

    logger = get_logger("main")

    try:
        # Import Qt first to avoid import order issues
        logger.debug("Importing PyQt6")
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt

        # Enable high DPI scaling
        logger.debug("Configuring high DPI scaling")
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Create Qt application
        logger.debug("Creating QApplication")
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
        logger.info("Creating VoiceInputApp instance")
        voice_app = VoiceInputApp(app)

        logger.info("Entering Qt event loop")
        exit_code = voice_app.run()

        logger.info("Application exited with code: %d", exit_code)
        return exit_code

    except Exception as e:
        logger.exception("Fatal error during application startup: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
