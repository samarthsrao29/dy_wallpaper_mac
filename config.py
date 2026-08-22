"""Application configuration for YearFlow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


import sys

BASE_DIR = Path(__file__).resolve().parent

IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    # Use user-specific writable directories for output files when packaged
    APP_DATA_DIR = Path.home() / "Library" / "Application Support" / "YearFlow"
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    WALLPAPER_OUTPUT_FOLDER = Path.home() / "Pictures" / "YearFlow"
    WALLPAPER_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    BACKGROUNDS_FOLDER = WALLPAPER_OUTPUT_FOLDER / "backgrounds"
    BACKGROUNDS_FOLDER.mkdir(parents=True, exist_ok=True)

    LOGS_FOLDER = APP_DATA_DIR / "logs"
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
else:
    WALLPAPER_OUTPUT_FOLDER = BASE_DIR / "generated"
    BACKGROUNDS_FOLDER = BASE_DIR / "backgrounds"
    LOGS_FOLDER = BASE_DIR / "logs"


@dataclass(frozen=True)
class YearFlowConfig:
    """User-configurable settings for wallpaper generation."""

    accent_color: str = "#FF3B30"
    background_color: str = "#0B0D13"  # Deep slate dark
    card_background_color: str = "#131620"  # Slightly lighter card background
    card_border_color: str = "#202433"  # Card border color
    primary_text_color: str = "#FFFFFF"
    secondary_text_color: str = "#7E8494"  # Modern secondary grey
    divider_color: str = "#202433"
    font_family: str = "Inter"
    font_path: Path = BASE_DIR / "fonts" / "Inter-Regular.ttf"
    font_regular_path: Path = BASE_DIR / "fonts" / "Inter-Regular.ttf"
    font_medium_path: Path = BASE_DIR / "fonts" / "Inter-Medium.ttf"
    font_bold_path: Path = BASE_DIR / "fonts" / "Inter-Bold.ttf"
    base_font_size: int = 32
    show_quote: bool = True
    show_progress_bar: bool = True
    show_reminder: bool = True
    reminder_text: str = "Reminder: Check your TO DO list and stay on track!"
    wallpaper_output_folder: Path = WALLPAPER_OUTPUT_FOLDER
    backgrounds_folder: Path = BACKGROUNDS_FOLDER
    background_image_opacity: float = 0.15
    quotes_path: Path = BASE_DIR / "quotes.json"
    logs_folder: Path = LOGS_FOLDER
    default_resolution: tuple[int, int] = (3840, 2160)
    output_filename: str = "yearflow-wallpaper.png"
    gradient_start: str = "#FF453A"  # Red/orange gradient start
    gradient_end: str = "#FF9F0A"  # Red/orange gradient end
    font_scale: float = 1.0
    layout_scale: float = 1.0

    def get_output_path(self, target_date: date) -> Path:
        """Return the full path for the generated wallpaper for a specific date."""
        return self.wallpaper_output_folder / f"yearflow-wallpaper-{target_date.isoformat()}.png"

    @property
    def output_path(self) -> Path:
        """Return the full path for the default generated wallpaper."""
        return self.wallpaper_output_folder / self.output_filename



import json

CONFIG_LOAD_WARNINGS: list[str] = []

import functools
from PIL import ImageFont

@functools.lru_cache(maxsize=1)
def scan_mac_fonts() -> dict[str, dict[str, str]]:
    """Scan macOS font directories and map font family names to style paths."""
    font_dirs = [
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        Path.home() / "Library/Fonts",
        BASE_DIR / "fonts"
    ]
    families = {}
    for folder in font_dirs:
        if not folder.exists() or not folder.is_dir():
            continue
        # Scan files
        for file_path in folder.rglob("*"):
            if file_path.suffix.lower() in (".ttf", ".otf", ".ttc") and file_path.is_file():
                try:
                    font = ImageFont.truetype(str(file_path), 12)
                    family, style = font.getname()
                    if family not in families:
                        families[family] = {}
                    families[family][style] = str(file_path.resolve())
                except Exception:
                    pass
    return families


def load_config() -> YearFlowConfig:
    """Load configuration from JSON file or fall back to defaults."""
    # Define default configurations
    defaults = {
        "accent_color": "#FF3B30",
        "background_color": "#0B0D13",
        "card_background_color": "#131620",
        "card_border_color": "#202433",
        "primary_text_color": "#FFFFFF",
        "secondary_text_color": "#7E8494",
        "divider_color": "#202433",
        "base_font_size": 32,
        "show_quote": True,
        "show_progress_bar": True,
        "show_reminder": True,
        "reminder_text": "Reminder: Check your TO DO list and stay on track!",
        "gradient_start": "#FF453A",
        "gradient_end": "#FF9F0A",
        "default_resolution": [3840, 2160],
        "backgrounds_folder": "",
        "background_image_opacity": 0.15,
        "font_family": "Inter",
        "font_scale": 1.0,
        "layout_scale": 1.0,
    }

    if IS_FROZEN:
        config_path = APP_DATA_DIR / "config.json"
    else:
        config_path = BASE_DIR / "config.json"

    # Auto-generate default config file if it doesn't exist
    if not config_path.exists():
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(defaults, f, indent=4)
        except Exception as e:
            CONFIG_LOAD_WARNINGS.append(f"Failed to auto-create config.json at {config_path}: {e}")

    loaded_settings = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_settings = json.load(f)
            if not isinstance(loaded_settings, dict):
                CONFIG_LOAD_WARNINGS.append("Invalid config.json format: top-level element must be a JSON object.")
                loaded_settings = {}
        except Exception as e:
            CONFIG_LOAD_WARNINGS.append(f"Failed to parse config.json: {e}. Falling back to default settings.")
            loaded_settings = {}

    # Standardize types and extract settings
    resolution = loaded_settings.get("default_resolution", defaults["default_resolution"])
    if isinstance(resolution, list) and len(resolution) == 2:
        try:
            resolution = (int(resolution[0]), int(resolution[1]))
        except ValueError:
            CONFIG_LOAD_WARNINGS.append("Invalid resolution format. Falling back to default resolution.")
            resolution = (3840, 2160)
    else:
        if "default_resolution" in loaded_settings:
            CONFIG_LOAD_WARNINGS.append("Invalid resolution format. Falling back to default resolution.")
        resolution = (3840, 2160)

    def to_path(val: str | None, default_val: Path) -> Path:
        return Path(val) if val else default_val

    # Parse opacity
    opacity_val = loaded_settings.get("background_image_opacity", defaults["background_image_opacity"])
    try:
        opacity = float(opacity_val)
    except (ValueError, TypeError):
        CONFIG_LOAD_WARNINGS.append("Invalid opacity format. Falling back to default opacity 0.15.")
        opacity = 0.15

    # Parse scales
    font_scale_val = loaded_settings.get("font_scale", defaults["font_scale"])
    try:
        font_scale = float(font_scale_val)
    except (ValueError, TypeError):
        CONFIG_LOAD_WARNINGS.append("Invalid font_scale format. Falling back to 1.0.")
        font_scale = 1.0

    layout_scale_val = loaded_settings.get("layout_scale", defaults["layout_scale"])
    try:
        layout_scale = float(layout_scale_val)
    except (ValueError, TypeError):
        CONFIG_LOAD_WARNINGS.append("Invalid layout_scale format. Falling back to 1.0.")
        layout_scale = 1.0

    # Parse backgrounds folder
    bg_folder_str = loaded_settings.get("backgrounds_folder", "")
    if bg_folder_str:
        bg_folder = Path(bg_folder_str)
    else:
        bg_folder = BACKGROUNDS_FOLDER

    # Ensure background directory exists (so user knows where to drop files)
    try:
        bg_folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        CONFIG_LOAD_WARNINGS.append(f"Failed to create backgrounds directory at {bg_folder}: {e}")

    font_family = str(loaded_settings.get("font_family", defaults["font_family"]))

    # Resolve regular, medium, bold paths dynamically
    font_regular_path = BASE_DIR / "fonts" / "Inter-Regular.ttf"
    font_medium_path = BASE_DIR / "fonts" / "Inter-Medium.ttf"
    font_bold_path = BASE_DIR / "fonts" / "Inter-Bold.ttf"

    if font_family != "Inter":
        try:
            families = scan_mac_fonts()
            if font_family in families:
                styles = families[font_family]
                
                # Find regular
                reg_found = None
                for k, v in styles.items():
                    if any(x in k.lower() for x in ("regular", "roman", "light", "w3", "w4", "plain", "normal")):
                        reg_found = Path(v)
                        break
                if not reg_found and styles:
                    reg_found = Path(list(styles.values())[0])
                if reg_found:
                    font_regular_path = reg_found
                    
                # Find bold
                bold_found = None
                for k, v in styles.items():
                    if any(x in k.lower() for x in ("bold", "w7", "w8")):
                        bold_found = Path(v)
                        break
                font_bold_path = bold_found if bold_found else font_regular_path
                
                # Find medium
                med_found = None
                for k, v in styles.items():
                    if any(x in k.lower() for x in ("medium", "semibold", "w5", "w6", "500", "600")):
                        med_found = Path(v)
                        break
                font_medium_path = med_found if med_found else font_regular_path
        except Exception as e:
            CONFIG_LOAD_WARNINGS.append(f"Failed to scan/match fonts for '{font_family}': {e}")

    # Construct the config object
    return YearFlowConfig(
        accent_color=str(loaded_settings.get("accent_color", defaults["accent_color"])),
        background_color=str(loaded_settings.get("background_color", defaults["background_color"])),
        card_background_color=str(loaded_settings.get("card_background_color", defaults["card_background_color"])),
        card_border_color=str(loaded_settings.get("card_border_color", defaults["card_border_color"])),
        primary_text_color=str(loaded_settings.get("primary_text_color", defaults["primary_text_color"])),
        secondary_text_color=str(loaded_settings.get("secondary_text_color", defaults["secondary_text_color"])),
        divider_color=str(loaded_settings.get("divider_color", defaults["divider_color"])),
        gradient_start=str(loaded_settings.get("gradient_start", defaults["gradient_start"])),
        gradient_end=str(loaded_settings.get("gradient_end", defaults["gradient_end"])),
        base_font_size=int(loaded_settings.get("base_font_size", defaults["base_font_size"])),
        show_quote=bool(loaded_settings.get("show_quote", defaults["show_quote"])),
        show_progress_bar=bool(loaded_settings.get("show_progress_bar", defaults["show_progress_bar"])),
        show_reminder=bool(loaded_settings.get("show_reminder", defaults["show_reminder"])),
        reminder_text=str(loaded_settings.get("reminder_text", defaults["reminder_text"])),
        default_resolution=resolution,
        
        # Paths
        font_family=font_family,
        font_path=font_regular_path,
        font_regular_path=font_regular_path,
        font_medium_path=font_medium_path,
        font_bold_path=font_bold_path,
        wallpaper_output_folder=to_path(loaded_settings.get("wallpaper_output_folder"), WALLPAPER_OUTPUT_FOLDER),
        backgrounds_folder=bg_folder,
        background_image_opacity=opacity,
        quotes_path=to_path(loaded_settings.get("quotes_path"), BASE_DIR / "quotes.json"),
        logs_folder=to_path(loaded_settings.get("logs_folder"), LOGS_FOLDER),
        output_filename=str(loaded_settings.get("output_filename", "yearflow-wallpaper.png")),
        font_scale=font_scale,
        layout_scale=layout_scale,
    )


CONFIG = load_config()
