"""macOS platform implementation.

Keyboard injection uses Quartz CGEvent (see ``cgevent``) instead of
pynput because pynput-on-Darwin silently drops events in browsers and
Electron apps. Foreground-app detection uses NSWorkspace. Autostart is
implemented via LaunchAgents.
"""
from __future__ import annotations

from typing import Optional

from .. import Platform, PlatformType
from ...logging_setup import get_logger
from ...protocols import TextInsertionProvider
from . import cgevent, startup

log = get_logger("platform.macos")


def configure_accessory_app() -> None:
    """Set NSApplicationActivationPolicyAccessory so the app cannot become
    the active app and never steals keyboard focus from the user's
    foreground window. Qt's QApplication forces Regular policy at startup
    regardless of LSUIElement, so this must be called after QApplication
    is constructed.
    """
    try:
        from AppKit import (
            NSApplication,
            NSApplicationActivationPolicyAccessory,
        )
        app = NSApplication.sharedApplication()
        if app is None:
            log.warning("NSApplication.sharedApplication() returned None")
            return
        before = int(app.activationPolicy())
        ok = bool(app.setActivationPolicy_(NSApplicationActivationPolicyAccessory))
        after = int(app.activationPolicy())
        log.info(
            "Activation policy: before=%d after=%d ok=%s (target=Accessory=%d)",
            before, after, ok, int(NSApplicationActivationPolicyAccessory),
        )
    except Exception as exc:
        log.warning("Failed to set accessory activation policy: %s", exc)


def make_window_non_activating(qwidget) -> None:
    """Reach through Qt to the underlying NSWindow and configure it so
    showing or raising it never activates the app or pulls focus.

    Required because Qt's ``WA_ShowWithoutActivating`` is honored on
    ``show()`` but ``raise_()`` and the first-window-show heuristic on
    macOS still activate the app.
    """
    try:
        import ctypes
        import objc
        from AppKit import (
            NSWindowCollectionBehaviorTransient,
            NSWindowCollectionBehaviorIgnoresCycle,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSFloatingWindowLevel,
        )
        # Force native window creation so winId() returns an NSView pointer.
        qwidget.winId()
        handle = qwidget.windowHandle()
        if handle is None:
            return
        ns_view_ptr = int(qwidget.winId())
        ns_view = objc.objc_object(c_void_p=ctypes.c_void_p(ns_view_ptr))
        ns_window = ns_view.window()
        if ns_window is None:
            return
        ns_window.setCollectionBehavior_(
            NSWindowCollectionBehaviorTransient
            | NSWindowCollectionBehaviorIgnoresCycle
            | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        ns_window.setLevel_(NSFloatingWindowLevel)
        # Most important: panels that don't accept becoming "key" never
        # pull focus from the user's foreground app.
        if hasattr(ns_window, "setCanBecomeKey_"):
            ns_window.setCanBecomeKey_(False)
        ns_window.setHidesOnDeactivate_(False)
    except Exception as exc:
        log.debug("make_window_non_activating failed: %s", exc)


class MacOSPlatform(Platform):
    platform_type = PlatformType.macos

    def create_inserter(
        self,
        restore_clipboard: bool = True,
        use_clipboard: bool = True,
    ) -> TextInsertionProvider:
        from .insertion import MacOSInserter
        return MacOSInserter(
            restore_clipboard=restore_clipboard,
            use_clipboard=use_clipboard,
        )

    def get_foreground_app(self) -> Optional[str]:
        try:
            from AppKit import NSWorkspace
            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            if app is None:
                return None
            return str(app.localizedName())
        except Exception as exc:
            log.debug("get_foreground_app failed: %s", exc)
            return None

    def send_key(self, key: str) -> None:
        keycode = cgevent.keycode_for(key)
        if keycode is None:
            log.warning("Unknown key: %s", key)
            return
        cgevent.post_key(keycode)

    def send_paste(self) -> None:
        cgevent.post_paste()

    def supports_startup(self) -> bool:
        return True

    def is_startup_enabled(self) -> bool:
        return startup.is_enabled()

    def set_startup_enabled(self, enabled: bool) -> bool:
        return startup.enable() if enabled else startup.disable()
