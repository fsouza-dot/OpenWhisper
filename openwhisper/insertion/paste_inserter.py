"""Cross-app text insertion via the clipboard + synthesized Ctrl+V.

Works in every Windows app because it only touches the clipboard and
posts virtual key events. We optionally save and restore the user's
previous clipboard contents so their copy buffer isn't clobbered.

`press_key` is used by command-mode actions (press_enter, press_tab,
press_escape, delete_last).
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import pyperclip
from pynput.keyboard import Controller, Key, KeyCode

from ..errors import InsertionFailed
from ..logging_setup import get_logger

log = get_logger("insertion")


# Map friendly names → pynput Key values. Anything not in this map is
# treated as a single-char key.
_NAMED_KEYS: dict[str, Key] = {
    "enter": Key.enter,
    "return": Key.enter,
    "tab": Key.tab,
    "escape": Key.esc,
    "esc": Key.esc,
    "space": Key.space,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "home": Key.home,
    "end": Key.end,
}


class PasteboardInserter:
    def __init__(self, restore_clipboard: bool = True) -> None:
        self.restore_clipboard = restore_clipboard
        self._keyboard = Controller()
        self._lock = threading.Lock()

    # -------------------------------------------------- TextInsertionProvider

    def insert(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            log.info("insert: starting (%d chars)", len(text))
            previous: Optional[str] = None
            if self.restore_clipboard:
                try:
                    previous = pyperclip.paste()
                except Exception as exc:  # pragma: no cover
                    log.debug("Could not read previous clipboard: %s", exc)

            try:
                pyperclip.copy(text)
            except Exception as exc:
                raise InsertionFailed(f"Clipboard write failed: {exc}") from exc
            log.info("insert: clipboard write ok")

            # The hotkey that triggered us was likely Alt+Space (or similar).
            # By the time we get here the user has lifted the keys, but on
            # some setups Windows still has Alt "logically" held — synthetic
            # Ctrl+V then becomes Ctrl+Alt+V, which does nothing useful and
            # may even open the system menu. Force-release common modifiers
            # and wait a beat before pasting.
            self._force_release_modifiers()
            time.sleep(0.05)

            try:
                self._send_paste()
            except Exception as exc:
                raise InsertionFailed(f"Could not synthesize Ctrl+V: {exc}") from exc
            log.info("insert: paste sent")

            if previous is not None:
                # Let the target app actually consume the paste event before
                # we restore the clipboard.
                def _restore() -> None:
                    time.sleep(0.25)
                    try:
                        pyperclip.copy(previous)
                    except Exception as exc:  # pragma: no cover
                        log.debug("Clipboard restore failed: %s", exc)
                threading.Thread(target=_restore, daemon=True).start()

    def press_key(self, key_name: str) -> None:
        key = _NAMED_KEYS.get(key_name.lower())
        if key is None:
            if len(key_name) == 1:
                key = KeyCode.from_char(key_name)
            else:
                raise InsertionFailed(f"Unknown key: {key_name}")
        try:
            self._keyboard.press(key)
            self._keyboard.release(key)
        except Exception as exc:
            raise InsertionFailed(f"Could not press {key_name}: {exc}") from exc

    # -------------------------------------------------------- internals

    def _send_paste(self) -> None:
        """Post Ctrl+V via Windows SendInput.

        We bypass pynput here because pynput's Controller tracks modifier
        state internally and can get confused by the global hotkey listener
        (e.g. after releasing Alt+Space, Alt sometimes stays 'logically
        held'). SendInput talks directly to the OS input queue, so whatever
        pynput thinks is held is irrelevant.
        """
        import ctypes
        from ctypes import wintypes

        VK_CONTROL = 0x11
        VK_V = 0x56
        KEYEVENTF_KEYUP = 0x0002
        INPUT_KEYBOARD = 1

        # ULONG_PTR is pointer-sized (4 on 32-bit, 8 on 64-bit). ctypes.wintypes
        # does not export it directly on all Python versions, so use c_size_t.
        ULONG_PTR = ctypes.c_size_t

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            ]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            ]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD),
            ]

        class _INPUTunion(ctypes.Union):
            # All three variants must be present so the union is sized to
            # the largest (MOUSEINPUT on 64-bit = 32 bytes). If we omit
            # MOUSEINPUT, SendInput returns GetLastError=87 on 64-bit.
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT),
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("u", _INPUTunion)]

        user32 = ctypes.windll.user32
        user32.SendInput.argtypes = [
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        ]
        user32.SendInput.restype = wintypes.UINT

        def _make(vk: int, up: bool) -> "INPUT":
            ev = INPUT()
            ev.type = INPUT_KEYBOARD
            ev.u.ki = KEYBDINPUT(
                wVk=vk,
                wScan=0,
                dwFlags=KEYEVENTF_KEYUP if up else 0,
                time=0,
                dwExtraInfo=0,
            )
            return ev

        events = (INPUT * 4)(
            _make(VK_CONTROL, up=False),
            _make(VK_V, up=False),
            _make(VK_V, up=True),
            _make(VK_CONTROL, up=True),
        )
        sent = user32.SendInput(4, events, ctypes.sizeof(INPUT))
        if sent != 4:
            raise InsertionFailed(
                f"SendInput rejected some events ({sent}/4). "
                f"GetLastError={ctypes.windll.kernel32.GetLastError()} "
                f"(sizeof INPUT={ctypes.sizeof(INPUT)})"
            )

    def _force_release_modifiers(self) -> None:
        """Fire a KEYUP for every common modifier in case the hotkey left
        one stuck. KEYUP on an already-released key is a no-op, so this is
        safe to call unconditionally."""
        try:
            import ctypes
            from ctypes import wintypes
            KEYEVENTF_KEYUP = 0x0002
            user32 = ctypes.windll.user32
            for vk in (0x12, 0x11, 0x10, 0x5B, 0x5C):  # Alt, Ctrl, Shift, LWin, RWin
                user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        except Exception as exc:  # pragma: no cover
            log.debug("Modifier release failed: %s", exc)
