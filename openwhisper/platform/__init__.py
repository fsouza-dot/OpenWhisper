"""Platform abstraction layer.

This module provides a clean separation between platform-specific code
and the rest of the application. Each platform (Windows, Linux, macOS)
has its own submodule with implementations of the platform protocols.

Usage:
    from openwhisper.platform import get_platform, Platform

    platform = get_platform()
    inserter = platform.create_inserter()
    app_name = platform.get_foreground_app()
"""
from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..protocols import TextInsertionProvider


class PlatformType(str, Enum):
    """Supported operating systems."""
    windows = "windows"
    linux = "linux"
    macos = "macos"


def detect_platform() -> PlatformType:
    """Detect the current operating system."""
    if sys.platform == "win32":
        return PlatformType.windows
    elif sys.platform == "darwin":
        return PlatformType.macos
    elif sys.platform.startswith("linux"):
        return PlatformType.linux
    else:
        # Default to Linux for other Unix-like systems
        return PlatformType.linux


class Platform(ABC):
    """Abstract base class for platform-specific implementations.

    Each platform (Windows, Linux, macOS) provides a concrete implementation
    of this class with platform-specific behavior for:
    - Text insertion (clipboard + paste simulation)
    - Foreground window detection
    - System paths
    """

    platform_type: PlatformType

    @abstractmethod
    def create_inserter(
        self,
        restore_clipboard: bool = True,
        use_clipboard: bool = True,
    ) -> "TextInsertionProvider":
        """Create a platform-specific text insertion provider."""
        ...

    @abstractmethod
    def get_foreground_app(self) -> Optional[str]:
        """Get the name of the currently focused application.

        Returns None if detection fails or is not supported.
        """
        ...

    @abstractmethod
    def send_key(self, key: str) -> None:
        """Send a single keypress (e.g., 'enter', 'tab', 'escape')."""
        ...

    @abstractmethod
    def send_paste(self) -> None:
        """Send Ctrl+V (Windows/Linux) or Cmd+V (macOS)."""
        ...


# Singleton instance
_platform_instance: Optional[Platform] = None


def get_platform() -> Platform:
    """Get the platform instance for the current OS.

    This is a singleton - the same instance is returned on subsequent calls.
    """
    global _platform_instance

    if _platform_instance is not None:
        return _platform_instance

    platform_type = detect_platform()

    if platform_type == PlatformType.windows:
        from .windows import WindowsPlatform
        _platform_instance = WindowsPlatform()
    elif platform_type == PlatformType.linux:
        from .linux import LinuxPlatform
        _platform_instance = LinuxPlatform()
    elif platform_type == PlatformType.macos:
        from .macos import MacOSPlatform
        _platform_instance = MacOSPlatform()
    else:
        raise RuntimeError(f"Unsupported platform: {platform_type}")

    return _platform_instance


def reset_platform() -> None:
    """Reset the platform singleton (mainly for testing)."""
    global _platform_instance
    _platform_instance = None
