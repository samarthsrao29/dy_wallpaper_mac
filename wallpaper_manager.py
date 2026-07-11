"""macOS desktop wallpaper integration."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class WallpaperManager:
    """Sets the generated wallpaper as the current macOS desktop picture."""

    def set_wallpaper(self, image_path: Path) -> None:
        """Set the desktop wallpaper for all spaces using AppleScript."""
        resolved_path = image_path.expanduser().resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Wallpaper image does not exist: {resolved_path}")

        script = (
            'tell application "System Events"\n'
            "  repeat with currentDesktop in desktops\n"
            f'    set picture of currentDesktop to "{resolved_path}"\n'
            "  end repeat\n"
            "end tell"
        )

        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
            )
            LOGGER.info("Wallpaper changed: %s", resolved_path)
        except subprocess.CalledProcessError as error:
            LOGGER.error("Failed to set wallpaper: %s", error.stderr.strip())
            raise
