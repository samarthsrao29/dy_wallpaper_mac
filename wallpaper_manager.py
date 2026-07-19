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

        # Check if the wallpaper is already set to the target path to avoid redundant updates
        try:
            check_result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get picture of every desktop'],
                check=True,
                capture_output=True,
                text=True,
            )
            current_paths = [p.strip() for p in check_result.stdout.strip().split(",") if p.strip()]
            if current_paths and all(p == str(resolved_path) for p in current_paths):
                LOGGER.info("Wallpaper is already set correctly to: %s. Skipping update.", resolved_path)
                return
        except Exception as error:
            LOGGER.warning("Could not check current wallpaper: %s. Proceeding to set it.", error)

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
