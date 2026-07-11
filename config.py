"""Application configuration for YearFlow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class YearFlowConfig:
    """User-configurable settings for wallpaper generation."""

    accent_color: str = "#FF3B30"
    background_color: str = "#000000"
    primary_text_color: str = "#FFFFFF"
    secondary_text_color: str = "#888888"
    divider_color: str = "#222222"
    font_path: Path = BASE_DIR / "fonts" / "Inter-Regular.ttf"
    base_font_size: int = 32
    show_quote: bool = True
    show_progress_bar: bool = True
    wallpaper_output_folder: Path = BASE_DIR / "generated"
    quotes_path: Path = BASE_DIR / "quotes.json"
    logs_folder: Path = BASE_DIR / "logs"
    default_resolution: tuple[int, int] = (3840, 2160)
    output_filename: str = "yearflow-wallpaper.png"

    def get_output_path(self, target_date: date) -> Path:
        """Return the full path for the generated wallpaper for a specific date."""
        return self.wallpaper_output_folder / f"yearflow-wallpaper-{target_date.isoformat()}.png"

    @property
    def output_path(self) -> Path:
        """Return the full path for the default generated wallpaper."""
        return self.wallpaper_output_folder / self.output_filename



CONFIG = YearFlowConfig()
