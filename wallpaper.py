"""Wallpaper generation with Pillow."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import YearFlowConfig
from date_utils import DateSnapshot


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TextStyle:
    """Font style details for drawing text."""

    size: int
    color: str


class WallpaperGenerator:
    """Generates the YearFlow minimalist wallpaper."""

    def __init__(self, config: YearFlowConfig) -> None:
        self.config = config
        self.scale = 2

    def generate(self, snapshot: DateSnapshot, quote: str) -> Path:
        """Generate and save the wallpaper image."""
        width, height = self.detect_resolution()
        canvas_width = width * self.scale
        canvas_height = height * self.scale

        image = Image.new("RGB", (canvas_width, canvas_height), self.config.background_color)
        draw = ImageDraw.Draw(image)

        self._draw_layout(draw, canvas_width, canvas_height, snapshot, quote)

        self.config.wallpaper_output_folder.mkdir(parents=True, exist_ok=True)
        output_path = self.config.get_output_path(snapshot.current_date)
        image.save(output_path, "PNG", optimize=True)
        LOGGER.info("Wallpaper generated: %s", output_path)
        
        self._cleanup_old_wallpapers(snapshot.current_date)
        
        return output_path

    def detect_resolution(self) -> tuple[int, int]:
        """Detect the main display resolution, falling back to 4K."""
        try:
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                check=True,
                capture_output=True,
                text=True,
            )
            for line in result.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("Resolution:"):
                    parts = stripped.replace("Resolution:", "").strip().split()
                    width = int(parts[0])
                    height = int(parts[2])
                    LOGGER.info("Resolution detected: %sx%s", width, height)
                    return width, height
        except (subprocess.CalledProcessError, ValueError, IndexError) as error:
            LOGGER.warning("Resolution detection failed: %s", error)

        LOGGER.info(
            "Using default resolution: %sx%s",
            self.config.default_resolution[0],
            self.config.default_resolution[1],
        )
        return self.config.default_resolution

    def _draw_layout(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int,
        snapshot: DateSnapshot,
        quote: str,
    ) -> None:
        margin = int(min(width, height) * 0.075)
        left_x = margin
        right_x = int(width * 0.67)
        top_y = margin
        bottom_y = height - margin

        year_font = self._font(int(height * 0.045))
        days_font = self._font(int(height * 0.14))
        label_font = self._font(int(height * 0.026))
        body_font = self._font(int(height * 0.026))
        small_font = self._font(int(height * 0.020))
        quote_font = self._font(int(height * 0.022))

        draw.text((left_x, top_y), str(snapshot.year), fill=self.config.primary_text_color, font=year_font)

        main_y = int(height * 0.31)
        draw.text(
            (left_x, main_y),
            str(snapshot.days_remaining_year),
            fill=self.config.accent_color,
            font=days_font,
        )
        draw.text(
            (left_x + int(width * 0.008), main_y + int(height * 0.15)),
            "DAYS LEFT",
            fill=self.config.secondary_text_color,
            font=label_font,
        )

        progress_y = main_y + int(height * 0.22)
        if self.config.show_progress_bar:
            self._draw_progress_bar(
                draw,
                left_x,
                progress_y,
                int(width * 0.46),
                int(height * 0.018),
                snapshot.days_completed / snapshot.days_in_year,
            )

        details_y = progress_y + int(height * 0.045)
        completed = f"{snapshot.days_completed} / {snapshot.days_in_year} Days Completed"
        percent = f"{snapshot.progress_percentage}% Complete"
        draw.text((left_x, details_y), completed, fill=self.config.primary_text_color, font=body_font)
        draw.text(
            (left_x, details_y + int(height * 0.04)),
            percent,
            fill=self.config.secondary_text_color,
            font=body_font,
        )

        self._draw_right_panel(draw, right_x, top_y + int(height * 0.18), height, snapshot)

        if self.config.show_quote:
            wrapped_quote = self._wrap_text(f'"{quote}"', quote_font, int(width * 0.5), draw)
            draw.multiline_text(
                (left_x, bottom_y - int(height * 0.10)),
                wrapped_quote,
                fill=self.config.primary_text_color,
                font=quote_font,
                spacing=int(height * 0.010),
            )

        footer = "FOCUS • BUILD • REPEAT"
        footer_bbox = draw.textbbox((0, 0), footer, font=small_font)
        footer_width = footer_bbox[2] - footer_bbox[0]
        draw.text(
            ((width - footer_width) / 2, bottom_y - int(height * 0.02)),
            footer,
            fill=self.config.secondary_text_color,
            font=small_font,
        )

    def _draw_right_panel(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        height: int,
        snapshot: DateSnapshot,
    ) -> None:
        label_font = self._font(int(height * 0.022))
        day_font = self._font(int(height * 0.055))
        date_font = self._font(int(height * 0.028))
        body_font = self._font(int(height * 0.026))

        draw.text((x, y), "TODAY", fill=self.config.accent_color, font=label_font)
        draw.text((x, y + int(height * 0.045)), snapshot.day_name, fill=self.config.primary_text_color, font=day_font)
        date_text = f"{snapshot.month_name} {snapshot.current_date.day}, {snapshot.year}"
        draw.text((x, y + int(height * 0.115)), date_text, fill=self.config.secondary_text_color, font=date_font)

        divider_y = y + int(height * 0.19)
        draw.rounded_rectangle(
            (x, divider_y, x + int(height * 0.32), divider_y + self.scale * 2),
            radius=self.scale,
            fill=self.config.divider_color,
        )

        month_y = divider_y + int(height * 0.045)
        draw.text((x, month_y), "MONTH", fill=self.config.accent_color, font=label_font)
        month_text = f"{snapshot.days_remaining_month} Days Left"
        draw.text((x, month_y + int(height * 0.045)), month_text, fill=self.config.primary_text_color, font=body_font)

    def _draw_progress_bar(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        progress: float,
    ) -> None:
        radius = height // 2
        draw.rounded_rectangle(
            (x, y, x + width, y + height),
            radius=radius,
            fill=self.config.divider_color,
        )
        fill_width = max(height, int(width * progress))
        draw.rounded_rectangle(
            (x, y, x + fill_width, y + height),
            radius=radius,
            fill=self.config.accent_color,
        )

    def _font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        font_path = self.config.font_path
        if not font_path.exists():
            self._download_default_font(font_path)

        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)

        LOGGER.warning("Configured font not found: %s. Falling back to Pillow default.", font_path)
        try:
            return ImageFont.truetype("Helvetica.ttc", size)
        except OSError:
            return ImageFont.load_default()

    def _download_default_font(self, font_path: Path) -> None:
        """Download Inter-Regular.ttf from various candidate URLs if missing."""
        import urllib.request
        
        urls = [
            "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf",
            "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/static/Inter-Regular.ttf",
            "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/Inter-Regular.ttf",
        ]
        
        font_path.parent.mkdir(parents=True, exist_ok=True)
        
        for url in urls:
            try:
                LOGGER.info("Attempting to download Inter-Regular.ttf font from %s...", url)
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    font_path.write_bytes(response.read())
                LOGGER.info("Font downloaded successfully.")
                return
            except Exception as e:
                LOGGER.warning("Failed to download from %s: %s", url, e)
                
        LOGGER.error("All font download attempts failed. Will fallback to system fonts.")

    def _cleanup_old_wallpapers(self, current_date: date) -> None:
        """Delete old wallpaper files to save disk space."""
        try:
            current_filename = f"yearflow-wallpaper-{current_date.isoformat()}.png"
            for file in self.config.wallpaper_output_folder.glob("yearflow-wallpaper-*.png"):
                if file.name != current_filename:
                    file.unlink()
                    LOGGER.info("Deleted old wallpaper: %s", file)
        except Exception as e:
            LOGGER.warning("Failed to clean up old wallpapers: %s", e)

    @staticmethod
    def _wrap_text(
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        max_width: int,
        draw: ImageDraw.ImageDraw,
    ) -> str:
        words = text.split()
        lines: list[str] = []
        current_line = ""

        for word in words:
            candidate = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = candidate
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return "\n".join(lines[:3])
