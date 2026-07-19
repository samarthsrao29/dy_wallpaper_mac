"""launchd scheduling helpers for YearFlow."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class LaunchAgentScheduler:
    """Installs and removes the YearFlow LaunchAgent."""

    def __init__(self, project_dir: Path, plist_path: Path) -> None:
        self.project_dir = project_dir
        self.plist_path = plist_path
        self.launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        self.installed_plist = self.launch_agents_dir / plist_path.name

    def install(self) -> None:
        """Install and load the LaunchAgent dynamically resolving paths and python interpreter."""
        import sys
        import plistlib

        self.launch_agents_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.plist_path, "rb") as file:
                plist_data = plistlib.load(file)
        except Exception as error:
            LOGGER.warning("Could not read plist file: %s. Using default agent template.", error)
            plist_data = {
                "Label": "com.yearflow.agent",
                "RunAtLoad": True,
                "StartCalendarInterval": {"Hour": 0, "Minute": 0},
            }

        # Update paths dynamically using current workspace and environment
        is_frozen = getattr(sys, "frozen", False)
        if is_frozen:
            # When frozen, sys.executable points to the packaged YearFlow binary
            plist_data["ProgramArguments"] = [sys.executable]
            app_data_dir = Path.home() / "Library" / "Application Support" / "YearFlow"
            plist_data["WorkingDirectory"] = str(app_data_dir)
            logs_dir = app_data_dir / "logs"
        else:
            plist_data["ProgramArguments"] = [
                sys.executable,
                str(self.project_dir / "app.py"),
            ]
            plist_data["WorkingDirectory"] = str(self.project_dir)
            logs_dir = self.project_dir / "logs"

        # Create logs directory if it does not exist
        logs_dir.mkdir(parents=True, exist_ok=True)

        plist_data["StandardOutPath"] = str(logs_dir / "yearflow-launchd.out.log")
        plist_data["StandardErrorPath"] = str(logs_dir / "yearflow-launchd.err.log")

        # Set StartInterval to run every 10 minutes to catch up in case computer was asleep
        plist_data["StartInterval"] = 600

        # Avoid reload loop: check if plist already exists and has identical key fields
        if self.installed_plist.exists():
            try:
                with open(self.installed_plist, "rb") as file:
                    current_plist = plistlib.load(file)
                if (current_plist.get("ProgramArguments") == plist_data["ProgramArguments"] and
                        current_plist.get("WorkingDirectory") == plist_data["WorkingDirectory"]):
                    LOGGER.info("LaunchAgent is already installed and up to date at: %s", self.installed_plist)
                    return
            except Exception as error:
                LOGGER.warning("Could not verify existing plist: %s. Re-installing.", error)

        with open(self.installed_plist, "wb") as file:
            plistlib.dump(plist_data, file)

        # Unload if already loaded, then load again
        subprocess.run(["launchctl", "unload", str(self.installed_plist)], check=False)
        subprocess.run(["launchctl", "load", str(self.installed_plist)], check=True)
        LOGGER.info("LaunchAgent installed and loaded at: %s", self.installed_plist)

    def uninstall(self) -> None:
        """Unload and remove the LaunchAgent."""
        subprocess.run(["launchctl", "unload", str(self.installed_plist)], check=False)
        if self.installed_plist.exists():
            self.installed_plist.unlink()
        LOGGER.info("LaunchAgent uninstalled: %s", self.installed_plist)
