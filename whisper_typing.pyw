"""
WhisperTyping - Windowless launcher.
Run this with pythonw.exe to start without a console window.
All logs go to %APPDATA%/WhisperTyping/whisper-typing.log
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import setup_logging, main

if __name__ == "__main__":
    main()
