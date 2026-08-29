"""macOS desktop wallpaper integration."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class WallpaperManager:
    """Sets the generated wallpaper as the current macOS desktop picture."""

    def set_wallpaper(self, image_path: Path, force: bool = False) -> None:
        """Set the desktop wallpaper for all spaces using AppleScript/JXA."""
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

        # Use JavaScript for Automation (JXA) to call NSWorkspace Cocoa API directly.
        # This bypasses TCC/Automation permission prompts for Finder / System Events,
        # which are blocked in background launchd execution contexts.
        import json
        jxa_script = (
            "ObjC.import('AppKit');\n"
            f"var url = $.NSURL.fileURLWithPath({json.dumps(str(resolved_path))});\n"
            "var ws = $.NSWorkspace.sharedWorkspace;\n"
            "var screens = $.NSScreen.screens;\n"
            "var success = true;\n"
            "for (var i = 0; i < screens.count; i++) {\n"
            "  var screen = screens.objectAtIndex(i);\n"
            "  var res = ws.setDesktopImageURLForScreenOptionsError(url, screen, $.NSDictionary.dictionary, null);\n"
            "  if (!res) { success = false; }\n"
            "}\n"
            "if (!success) {\n"
            "  throw new Error('Failed to set wallpaper on one or more screens');\n"
            "}"
        )

        success = False
        jxa_success = False
        try:
            subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", jxa_script],
                check=True,
                capture_output=True,
                text=True,
            )
            LOGGER.info("Wallpaper set successfully via JXA/NSWorkspace: %s", resolved_path)
            success = True
            jxa_success = True
        except subprocess.CalledProcessError as error:
            LOGGER.warning("JXA/NSWorkspace failed to set wallpaper: %s. Trying AppleScript fallback...", error.stderr.strip())

        if not success:
            # Fallback to AppleScript System Events
            system_events_script = (
                'tell application "System Events"\n'
                "  repeat with currentDesktop in desktops\n"
                f'    set picture of currentDesktop to "{resolved_path}"\n'
                "  end repeat\n"
                "end tell"
            )
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

        # Only verify the change actually took effect in macOS settings if we had to use AppleScript/Finder fallbacks.
        # JXA (NSWorkspace) operates at a lower level and doesn't require System Events permissions.
        # System Events also has a sync delay which would trigger false warnings.
        if not jxa_success:
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
