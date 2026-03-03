import ctypes
import ctypes.wintypes as wintypes
import time
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Win32 constants
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Fix 64-bit Windows: ctypes defaults to c_int return type,
# but these functions return pointers/handles (64-bit on x64).
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.OpenClipboard.restype = wintypes.BOOL
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.CloseClipboard.restype = wintypes.BOOL
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
user32.EmptyClipboard.restype = wintypes.BOOL


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


class TextInjector:
    """Injects transcribed text into the currently active Windows application."""

    def __init__(
        self,
        method: str = "clipboard",
        restore_clipboard: bool = True,
        add_trailing_space: bool = True,
    ):
        self.method = method
        self.restore_clipboard = restore_clipboard
        self.add_trailing_space = add_trailing_space
        self._lock = threading.Lock()

    def inject_text(self, text: str, is_rtl: bool = False):
        if not text:
            return

        if self.add_trailing_space and not text.endswith((" ", "\n")):
            text += " "

        with self._lock:
            if self.method in ("clipboard", "streaming"):
                self._inject_via_clipboard(text)
            else:
                self._inject_via_sendinput(text)

    def _inject_via_clipboard(self, text: str):
        old_clipboard = None
        if self.restore_clipboard:
            old_clipboard = self._get_clipboard_text()

        self._set_clipboard_text(text)
        time.sleep(0.05)
        self._send_ctrl_v()
        time.sleep(0.3)

        if self.restore_clipboard and old_clipboard is not None:
            self._set_clipboard_text(old_clipboard)

    def _inject_via_sendinput(self, text: str):
        for char in text:
            for code in self._char_to_utf16(char):
                inputs = (INPUT * 2)()
                # Key down
                inputs[0].type = INPUT_KEYBOARD
                inputs[0].union.ki.wVk = 0
                inputs[0].union.ki.wScan = code
                inputs[0].union.ki.dwFlags = KEYEVENTF_UNICODE
                inputs[0].union.ki.time = 0
                inputs[0].union.ki.dwExtraInfo = None
                # Key up
                inputs[1].type = INPUT_KEYBOARD
                inputs[1].union.ki.wVk = 0
                inputs[1].union.ki.wScan = code
                inputs[1].union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                inputs[1].union.ki.time = 0
                inputs[1].union.ki.dwExtraInfo = None

                user32.SendInput(2, ctypes.pointer(inputs), ctypes.sizeof(INPUT))
            time.sleep(0.005)

    def _char_to_utf16(self, char: str) -> list[int]:
        encoded = char.encode("utf-16-le")
        codes = []
        for i in range(0, len(encoded), 2):
            codes.append(int.from_bytes(encoded[i : i + 2], "little"))
        return codes

    def _get_clipboard_text(self) -> Optional[str]:
        for attempt in range(3):
            try:
                if not user32.OpenClipboard(0):
                    time.sleep(0.05)
                    continue
                try:
                    handle = user32.GetClipboardData(CF_UNICODETEXT)
                    if handle:
                        ptr = kernel32.GlobalLock(handle)
                        if ptr:
                            text = ctypes.wstring_at(ptr)
                            kernel32.GlobalUnlock(handle)
                            return text
                    return None
                finally:
                    user32.CloseClipboard()
            except Exception:
                time.sleep(0.05)
        return None

    def _set_clipboard_text(self, text: str):
        for attempt in range(3):
            try:
                if not user32.OpenClipboard(0):
                    time.sleep(0.05)
                    continue
                try:
                    user32.EmptyClipboard()
                    data = text.encode("utf-16-le") + b"\x00\x00"
                    h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                    ptr = kernel32.GlobalLock(h_mem)
                    ctypes.memmove(ptr, data, len(data))
                    kernel32.GlobalUnlock(h_mem)
                    user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                    return
                finally:
                    user32.CloseClipboard()
            except Exception as e:
                logger.error(f"Clipboard set failed (attempt {attempt + 1}): {e}")
                time.sleep(0.05)

    def _send_ctrl_v(self):
        inputs = (INPUT * 4)()
        # Ctrl down
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].union.ki.wVk = VK_CONTROL
        inputs[0].union.ki.dwFlags = 0
        # V down
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].union.ki.wVk = VK_V
        inputs[1].union.ki.dwFlags = 0
        # V up
        inputs[2].type = INPUT_KEYBOARD
        inputs[2].union.ki.wVk = VK_V
        inputs[2].union.ki.dwFlags = KEYEVENTF_KEYUP
        # Ctrl up
        inputs[3].type = INPUT_KEYBOARD
        inputs[3].union.ki.wVk = VK_CONTROL
        inputs[3].union.ki.dwFlags = KEYEVENTF_KEYUP

        user32.SendInput(4, ctypes.pointer(inputs), ctypes.sizeof(INPUT))
