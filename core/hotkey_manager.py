import time
import keyboard
import mouse
import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Minimum interval between toggle events to prevent key-repeat bounce
TOGGLE_DEBOUNCE_S = 0.3


class HotkeyManager:
    """
    Manages global input triggers for recording.

    Supports:
    - Keyboard combos (e.g. ctrl+shift+space)
    - Mouse buttons (middle, x, x2)
    - Two modes: push_to_talk (hold) and toggle (press/press)
    """

    def __init__(
        self,
        trigger_type: str = "keyboard",
        trigger_key: str = "ctrl+shift+space",
        trigger_mouse_button: str = "middle",
        mode: str = "push_to_talk",
        on_recording_start: Optional[Callable] = None,
        on_recording_stop: Optional[Callable] = None,
    ):
        self.trigger_type = trigger_type
        self.trigger_key = trigger_key
        self.trigger_mouse_button = trigger_mouse_button
        self.mode = mode
        self.on_recording_start = on_recording_start
        self.on_recording_stop = on_recording_stop

        self._is_active = False
        self._toggle_state = False
        self._registered = False
        self._mouse_hook = None
        self._keyboard_hooks = []  # Hook handlers for keyboard.unhook()
        self._last_toggle_time = 0.0  # For debounce

    def register(self):
        if self._registered:
            self.unregister()

        if self.trigger_type == "keyboard":
            self._register_keyboard()
        else:
            self._register_mouse()

        self._registered = True
        trigger_name = (
            self.trigger_key
            if self.trigger_type == "keyboard"
            else f"mouse:{self.trigger_mouse_button}"
        )
        logger.info(f"Trigger registered: {trigger_name} (mode: {self.mode})")

    def _register_keyboard(self):
        # Parse the combo to get the trigger key and modifiers
        parts = self.trigger_key.lower().split("+")
        trigger = parts[-1]
        modifiers = parts[:-1]

        if self.mode == "push_to_talk":
            h1 = keyboard.on_press_key(
                trigger, lambda e: self._on_key_down(e, modifiers), suppress=True
            )
            h2 = keyboard.on_release_key(
                trigger, lambda e: self._on_key_up(e), suppress=True
            )
            self._keyboard_hooks.extend([h1, h2])
        else:
            # Toggle mode: use on_press_key with debounce.
            # keyboard.add_hotkey fires on every key repeat, causing
            # rapid toggle bounce. on_press_key + debounce prevents this.
            h = keyboard.on_press_key(
                trigger,
                lambda e: self._on_toggle_key(e, modifiers),
                suppress=True,
            )
            self._keyboard_hooks.append(h)

    def _register_mouse(self):
        # Use mouse.hook (not mouse.on_button) because on_button
        # calls callback with no args, but we need the event.
        btn = self.trigger_mouse_button
        if self.mode == "push_to_talk":
            def handler(event):
                if isinstance(event, mouse.ButtonEvent) and event.button == btn:
                    if event.event_type == "down" and not self._is_active:
                        self._is_active = True
                        self._fire_start()
                    elif event.event_type == "up" and self._is_active:
                        self._is_active = False
                        self._fire_stop()
            self._mouse_hook = mouse.hook(handler)
        else:
            def handler(event):
                if isinstance(event, mouse.ButtonEvent) and event.button == btn and event.event_type == "down":
                    self._on_toggle()
            self._mouse_hook = mouse.hook(handler)

    def _check_modifiers(self, modifiers: list[str]) -> bool:
        for mod in modifiers:
            if not keyboard.is_pressed(mod):
                return False
        return True

    def _on_key_down(self, event, modifiers: list[str]):
        if not self._is_active and self._check_modifiers(modifiers):
            self._is_active = True
            self._fire_start()

    def _on_key_up(self, event):
        if self._is_active:
            self._is_active = False
            self._fire_stop()

    def _on_toggle_key(self, event, modifiers: list[str]):
        """Toggle handler for keyboard with debounce to prevent key-repeat bounce."""
        if not self._check_modifiers(modifiers):
            return
        now = time.monotonic()
        if now - self._last_toggle_time < TOGGLE_DEBOUNCE_S:
            return
        self._last_toggle_time = now
        self._on_toggle()

    def _on_toggle(self):
        self._toggle_state = not self._toggle_state
        if self._toggle_state:
            self._fire_start()
        else:
            self._fire_stop()

    def _fire_start(self):
        if self.on_recording_start:
            threading.Thread(target=self.on_recording_start, daemon=True).start()

    def _fire_stop(self):
        if self.on_recording_stop:
            threading.Thread(target=self.on_recording_stop, daemon=True).start()

    def unregister(self):
        # Remove only THIS instance's keyboard hooks (not all global hooks)
        for hook in self._keyboard_hooks:
            try:
                keyboard.unhook(hook)
            except Exception:
                pass
        self._keyboard_hooks = []

        if self._mouse_hook is not None:
            try:
                mouse.unhook(self._mouse_hook)
            except Exception:
                pass
            self._mouse_hook = None
        self._registered = False
        self._is_active = False
        self._toggle_state = False

    def update_trigger(
        self,
        trigger_type: Optional[str] = None,
        trigger_key: Optional[str] = None,
        trigger_mouse_button: Optional[str] = None,
        mode: Optional[str] = None,
    ):
        if trigger_type is not None:
            self.trigger_type = trigger_type
        if trigger_key is not None:
            self.trigger_key = trigger_key
        if trigger_mouse_button is not None:
            self.trigger_mouse_button = trigger_mouse_button
        if mode is not None:
            self.mode = mode
        self.register()
