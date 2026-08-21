"""macOS desktop wallpaper integration."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class WallpaperManager:
    """Sets the generated wallpaper as the current macOS desktop picture."""

    def set_wallpaper(self, image_path: Path, force: bool = False) -> None:
        """Set the desktop wallpaper for all spaces using AppleScript."""
        resolved_path = image_path.expanduser().resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Wallpaper image does not exist: {resolved_path}")

        # Check if the wallpaper is already set to the target path to avoid redundant updates
        if not force:
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

        # Try setting via System Events first (supports multiple displays)
        system_events_script = (
            'tell application "System Events"\n'
            "  repeat with currentDesktop in desktops\n"
            f'    set picture of currentDesktop to "{resolved_path}"\n'
            "  end repeat\n"
            "end tell"
        )

        success = False
        try:
            subprocess.run(
                ["osascript", "-e", system_events_script],
                check=True,
                capture_output=True,
                text=True,
            )
            LOGGER.info("Wallpaper set command sent via System Events: %s", resolved_path)
            success = True
        except subprocess.CalledProcessError as error:
            LOGGER.warning("System Events failed to set wallpaper: %s. Trying Finder fallback...", error.stderr.strip())

        # If System Events fails or silently ignores it, fallback to Finder
        if not success:
            finder_script = f'tell application "Finder" to set desktop picture to POSIX file "{resolved_path}"'
            try:
                subprocess.run(
                    ["osascript", "-e", finder_script],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                LOGGER.info("Wallpaper changed via Finder: %s", resolved_path)
                success = True
            except subprocess.CalledProcessError as finder_error:
                LOGGER.error("Failed to set wallpaper via Finder: %s", finder_error.stderr.strip())
                raise

        # Verify the change actually took effect in macOS settings
        try:
            verify_result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get picture of every desktop'],
                check=True,
                capture_output=True,
                text=True,
            )
            new_paths = [p.strip() for p in verify_result.stdout.strip().split(",") if p.strip()]
            if new_paths and not any(p == str(resolved_path) for p in new_paths):
                LOGGER.warning(
                    "macOS did not update the wallpaper path to %s. "
                    "Current paths are: %s. "
                    "This is likely due to missing Automation/TCC permissions. "
                    "Please check 'System Settings -> Privacy & Security -> Automation' and ensure Terminal and YearFlow are allowed to control Finder and System Events.",
                    resolved_path, new_paths
                )
                # Try Finder fallback as a last resort in case System Events ran but failed silently
                finder_script = f'tell application "Finder" to set desktop picture to POSIX file "{resolved_path}"'
                subprocess.run(["osascript", "-e", finder_script], check=True, capture_output=True)
                LOGGER.info("Attempted last-resort Finder force update: %s", resolved_path)
        except Exception as error:
            LOGGER.warning("Could not verify wallpaper change: %s", error)
