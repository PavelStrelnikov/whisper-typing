import sys
import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_logging():
    log_dir = Path.home() / "AppData" / "Roaming" / "WhisperTyping"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "whisper-typing.log"

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler (rotating, 5 MB max, keep 3 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting WhisperTyping...")

    try:
        from ui.app import Application

        app = Application()
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
