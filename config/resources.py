"""Resource path resolution — works both in development and PyInstaller bundle."""
import sys
import os


def get_resource_path(relative_path: str) -> str:
    """Return absolute path to a bundled resource.

    In a PyInstaller onedir build, data files live under sys._MEIPASS.
    In development, they live relative to the project root.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    # Project root is one level above this file (config/)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, relative_path)


ICON_PATH = get_resource_path(os.path.join("assets", "icon.ico"))
