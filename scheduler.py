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
        plist_data["ProgramArguments"] = [
            sys.executable,
            str(self.project_dir / "app.py"),
        ]
        plist_data["WorkingDirectory"] = str(self.project_dir)

        # Create logs directory if it does not exist
        logs_dir = self.project_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        plist_data["StandardOutPath"] = str(logs_dir / "yearflow-launchd.out.log")
        plist_data["StandardErrorPath"] = str(logs_dir / "yearflow-launchd.err.log")

        # Set StartInterval to run hourly to catch up in case computer was asleep
        plist_data["StartInterval"] = 3600

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
