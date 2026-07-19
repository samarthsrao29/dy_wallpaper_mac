"""YearFlow command-line entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from config import CONFIG
from date_utils import DateCalculator
from quote_manager import QuoteManager
from scheduler import LaunchAgentScheduler
from wallpaper import WallpaperGenerator
from wallpaper_manager import WallpaperManager


LOGGER = logging.getLogger(__name__)


class YearFlowApp:
    """Coordinates the YearFlow wallpaper lifecycle."""

    def __init__(self) -> None:
        self.config = CONFIG
        self.quote_manager = QuoteManager(self.config.quotes_path)
        self.generator = WallpaperGenerator(self.config)
        self.wallpaper_manager = WallpaperManager()

    def refresh(self, target_date: date | None = None, force: bool = False) -> Path:
        """Generate a fresh wallpaper and set it as the macOS wallpaper."""
        LOGGER.info("YearFlow refresh started")
        snapshot = DateCalculator.build(target_date)

        # Check if a wallpaper was already generated today
        path1 = self.config.wallpaper_output_folder / "yearflow-wallpaper-1.png"
        path2 = self.config.wallpaper_output_folder / "yearflow-wallpaper-2.png"
        
        already_done_today = False
        latest_path = None
        
        existing_mtimes = []
        for p in (path1, path2):
            if p.exists():
                from datetime import datetime
                mtime_date = datetime.fromtimestamp(p.stat().st_mtime).date()
                if mtime_date == snapshot.current_date:
                    existing_mtimes.append((p.stat().st_mtime, p))
                    
        if existing_mtimes:
            latest_path = max(existing_mtimes, key=lambda x: x[0])[1]
            already_done_today = True

        if already_done_today and latest_path and not force:
            LOGGER.info("Wallpaper for %s already exists. Skipping generation.", snapshot.current_date)
            self.wallpaper_manager.set_wallpaper(latest_path)
            LOGGER.info("YearFlow refresh completed (skipped generation)")
            return latest_path

        # Determine the next filename to write (alternating to avoid macOS caching)
        if not path1.exists():
            output_path = path1
        elif not path2.exists():
            output_path = path2
        else:
            mtime1 = path1.stat().st_mtime
            mtime2 = path2.stat().st_mtime
            output_path = path1 if mtime1 < mtime2 else path2

        quote = self.quote_manager.get_quote_for_date(snapshot.current_date)
        wallpaper_path = self.generator.generate(snapshot, quote, output_path=output_path)
        self.wallpaper_manager.set_wallpaper(wallpaper_path)
        LOGGER.info("YearFlow refresh completed")
        return wallpaper_path


def configure_logging() -> None:
    """Configure file and console logging."""
    CONFIG.logs_folder.mkdir(parents=True, exist_ok=True)
    log_path = CONFIG.logs_folder / "yearflow.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description="Generate and set the YearFlow wallpaper.")
    parser.add_argument(
        "--install-agent",
        action="store_true",
        help="Install the launchd LaunchAgent.",
    )
    parser.add_argument(
        "--uninstall-agent",
        action="store_true",
        help="Uninstall the launchd LaunchAgent.",
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Generate wallpaper for a specific date (YYYY-MM-DD format).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force wallpaper regeneration even if it already exists.",
    )
    return parser


def main() -> int:
    """Run YearFlow from the command line."""
    configure_logging()
    args = build_parser().parse_args()

    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        resource_dir = Path(sys._MEIPASS)
    else:
        resource_dir = Path(__file__).resolve().parent

    scheduler = LaunchAgentScheduler(
        project_dir=resource_dir,
        plist_path=resource_dir / "launchd" / "com.yearflow.agent.plist",
    )

    try:
        if args.install_agent:
            scheduler.install()
            return 0
        if args.uninstall_agent:
            scheduler.uninstall()
            return 0

        target_date = None
        if args.date:
            from datetime import datetime
            try:
                target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            except ValueError:
                LOGGER.error("Invalid date format: %s. Use YYYY-MM-DD.", args.date)
                return 1

        # Auto-install/update LaunchAgent when running as a packaged app
        if getattr(sys, "frozen", False):
            try:
                LOGGER.info("YearFlow packaged app detected. Setting up LaunchAgent automatically...")
                scheduler.install()
            except Exception as error:
                LOGGER.warning("Could not automatically configure LaunchAgent: %s", error)

        app = YearFlowApp()
        app.refresh(target_date=target_date, force=args.force)
        return 0
    except Exception:
        LOGGER.exception("YearFlow failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
