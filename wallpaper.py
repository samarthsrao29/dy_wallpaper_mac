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

    def generate(self, snapshot: DateSnapshot, quote: str, output_path: Path | None = None) -> Path:
        """Generate and save the wallpaper image."""
        width, height = self.detect_resolution()
        canvas_width = width * self.scale
        canvas_height = height * self.scale

        image = Image.new("RGB", (canvas_width, canvas_height), self.config.background_color)
        draw = ImageDraw.Draw(image)
        self.image = image

        self._draw_layout(draw, canvas_width, canvas_height, snapshot, quote)

        self.config.wallpaper_output_folder.mkdir(parents=True, exist_ok=True)
        if not output_path:
            output_path = self.config.get_output_path(snapshot.current_date)
        image.save(output_path, "PNG", optimize=True)
        LOGGER.info("Wallpaper generated: %s", output_path)
        
        self._cleanup_old_wallpapers(output_path)
        
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
        margin_x = int(width * 0.075)
        margin_y = int(height * 0.08)
        left_x = margin_x
        top_y = margin_y
        bottom_y = height - margin_y

        right_width = int(width * 0.325)
        right_x = width - margin_x - right_width

        # ----------------------------------------------------
        # LEFT COLUMN
        # ----------------------------------------------------
        # 1. Year Header (Calendar Icon + "YYYY")
        year_header_y = top_y
        badge_sz = int(height * 0.055)
        icon_sz = int(height * 0.038)
        
        self._draw_card(draw, left_x, year_header_y, badge_sz, badge_sz, radius=int(badge_sz * 0.25))
        icon_offset = (badge_sz - icon_sz) // 2
        self._draw_icon(draw, "calendar", left_x + icon_offset, year_header_y + icon_offset, icon_sz, self.config.accent_color)
        
        year_font = self._font(int(height * 0.035), weight="Bold")
        year_text = str(snapshot.year)
        year_bbox = draw.textbbox((0, 0), year_text, font=year_font)
        th_year = year_bbox[3] - year_bbox[1]
        y_offset_year = year_bbox[1]
        draw.text(
            (left_x + badge_sz + int(width * 0.015), year_header_y + int((badge_sz - th_year) / 2) - y_offset_year),
            year_text,
            fill=self.config.primary_text_color,
            font=year_font,
        )

        # 2. Countdown Title
        countdown_y = year_header_y + int(height * 0.11)
        subtitle_font = self._font(int(height * 0.018), weight="Medium")
        draw.text(
            (left_x, countdown_y),
            "COUNTDOWN TO SUCCESS",
            fill=self.config.secondary_text_color,
            font=subtitle_font,
        )

        # 3. Big countdown number (solid red)
        big_num_y = countdown_y + int(height * 0.02)
        big_num_font = self._font(int(height * 0.165), weight="Bold")
        days_rem_str = str(snapshot.days_remaining_year)
        draw.text(
            (left_x, big_num_y),
            days_rem_str,
            fill=self.config.accent_color,
            font=big_num_font,
        )

        # 4. DAYS LEFT label
        days_left_y = big_num_y + int(height * 0.20)
        days_left_font = self._font(int(height * 0.022), weight="Bold")
        draw.text(
            (left_x, days_left_y),
            "DAYS LEFT",
            fill=self.config.secondary_text_color,
            font=days_left_font,
        )

        # 5. Progress Bar
        progress_y = days_left_y + int(height * 0.05)
        bar_w = int(width * 0.44)
        bar_h = int(height * 0.020)
        progress_val = snapshot.days_completed / snapshot.days_in_year
        self._draw_progress_bar(draw, left_x, progress_y, bar_w, bar_h, progress_val)

        # 6. Stats section
        stats_y = progress_y + int(height * 0.05)
        circle_sz = int(height * 0.055)
        stat_icon_sz = int(height * 0.028)
        stat_title_font = self._font(int(height * 0.020), weight="Bold")
        stat_sub_font = self._font(int(height * 0.017), weight="Medium")

        # Left Stat: Completed / In Year
        draw.ellipse(
            (left_x, stats_y, left_x + circle_sz, stats_y + circle_sz),
            fill=self.config.card_background_color,
            outline=self.config.accent_color,
            width=max(2, self.scale)
        )
        stat_offset = (circle_sz - stat_icon_sz) // 2
        self._draw_icon(draw, "checkmark", left_x + stat_offset, stats_y + stat_offset, stat_icon_sz, self.config.accent_color)
        
        completed_text = f"{snapshot.days_completed} / {snapshot.days_in_year}"
        draw.text(
            (left_x + circle_sz + int(width * 0.012), stats_y + int(height * 0.003)),
            completed_text,
            fill=self.config.primary_text_color,
            font=stat_title_font,
        )
        draw.text(
            (left_x + circle_sz + int(width * 0.012), stats_y + int(height * 0.028)),
            "Days Completed",
            fill=self.config.secondary_text_color,
            font=stat_sub_font,
        )

        # Vertical Divider
        divider_x = left_x + int(width * 0.22)
        divider_h = int(height * 0.05)
        draw.line(
            (divider_x, stats_y + int(height * 0.003), divider_x, stats_y + int(height * 0.003) + divider_h),
            fill=self.config.divider_color,
            width=max(1, self.scale)
        )

        # Right Stat: Percentage Complete
        pct_badge_x = left_x + int(width * 0.24)
        draw.ellipse(
            (pct_badge_x, stats_y, pct_badge_x + circle_sz, stats_y + circle_sz),
            fill=self.config.card_background_color,
            outline=self.config.card_border_color,
            width=max(1, self.scale)
        )
        self._draw_icon(draw, "chart", pct_badge_x + stat_offset, stats_y + stat_offset, stat_icon_sz, self.config.accent_color)
        
        pct_text = f"{snapshot.progress_percentage}%"
        draw.text(
            (pct_badge_x + circle_sz + int(width * 0.012), stats_y + int(height * 0.003)),
            pct_text,
            fill=self.config.primary_text_color,
            font=stat_title_font,
        )
        draw.text(
            (pct_badge_x + circle_sz + int(width * 0.012), stats_y + int(height * 0.028)),
            "Complete",
            fill=self.config.secondary_text_color,
            font=stat_sub_font,
        )

        # 7. Quote Panel
        if self.config.show_quote:
            quote_panel_y = stats_y + int(height * 0.09)
            panel_w = int(width * 0.44)
            panel_h = int(height * 0.11)
            
            self._draw_card(draw, left_x, quote_panel_y, panel_w, panel_h, radius=int(height * 0.015))
            
            q_badge_sz = int(height * 0.055)
            q_badge_x = left_x + int(width * 0.015)
            q_badge_y = quote_panel_y + (panel_h - q_badge_sz) // 2
            self._draw_quote_badge(draw, q_badge_x, q_badge_y, q_badge_sz)
            
            quote_font = self._font(int(height * 0.020), weight="Medium")
            max_text_w = panel_w - q_badge_sz - int(width * 0.055)
            wrapped_quote = self._wrap_text(quote, quote_font, max_text_w, draw)
            
            quote_bbox = draw.multiline_textbbox((0, 0), wrapped_quote, font=quote_font, spacing=int(height * 0.006))
            th_quote = quote_bbox[3] - quote_bbox[1]
            y_offset_quote = quote_bbox[1]
            
            draw.multiline_text(
                (q_badge_x + q_badge_sz + int(width * 0.015), quote_panel_y + (panel_h - th_quote) // 2 - y_offset_quote),
                wrapped_quote,
                fill=self.config.primary_text_color,
                font=quote_font,
                spacing=int(height * 0.006),
            )

        # 8. Reminder Panel
        if self.config.show_reminder:
            panel_w = int(width * 0.44)
            panel_h = int(height * 0.11)
            if self.config.show_quote:
                reminder_panel_y = stats_y + int(height * 0.09) + panel_h + int(height * 0.02)
            else:
                reminder_panel_y = stats_y + int(height * 0.09)
            
            self._draw_card(draw, left_x, reminder_panel_y, panel_w, panel_h, radius=int(height * 0.015))
            
            r_badge_sz = int(height * 0.055)
            r_badge_x = left_x + int(width * 0.015)
            r_badge_y = reminder_panel_y + (panel_h - r_badge_sz) // 2
            self._draw_reminder_badge(draw, r_badge_x, r_badge_y, r_badge_sz)
            
            reminder_font = self._font(int(height * 0.020), weight="Medium")
            max_text_w = panel_w - r_badge_sz - int(width * 0.055)
            wrapped_reminder = self._wrap_text(self.config.reminder_text, reminder_font, max_text_w, draw)
            
            reminder_bbox = draw.multiline_textbbox((0, 0), wrapped_reminder, font=reminder_font, spacing=int(height * 0.006))
            th_reminder = reminder_bbox[3] - reminder_bbox[1]
            y_offset_reminder = reminder_bbox[1]
            
            draw.multiline_text(
                (r_badge_x + r_badge_sz + int(width * 0.015), reminder_panel_y + (panel_h - th_reminder) // 2 - y_offset_reminder),
                wrapped_reminder,
                fill=self.config.primary_text_color,
                font=reminder_font,
                spacing=int(height * 0.006),
            )

        # ----------------------------------------------------
        # RIGHT COLUMN
        # ----------------------------------------------------
        card_x = right_x
        card_w = right_width

        # Card 1: Today
        card1_y = top_y
        card1_h = int(height * 0.30)
        self._draw_card(draw, card_x, card1_y, card_w, card1_h, radius=int(height * 0.015))
        
        today_badge_x = card_x + int(width * 0.02)
        today_badge_y = card1_y + int(height * 0.03)
        self._draw_card(draw, today_badge_x, today_badge_y, badge_sz, badge_sz, radius=int(badge_sz * 0.25))
        self._draw_icon(draw, "calendar", today_badge_x + icon_offset, today_badge_y + icon_offset, icon_sz, self.config.accent_color)
        
        label_font = self._font(int(height * 0.018), weight="Bold")
        label_bbox = draw.textbbox((0, 0), "TODAY", font=label_font)
        th_label = label_bbox[3] - label_bbox[1]
        y_offset_label = label_bbox[1]
        draw.text(
            (today_badge_x + badge_sz + int(width * 0.01), today_badge_y + int((badge_sz - th_label) / 2) - y_offset_label),
            "TODAY",
            fill=self.config.accent_color,
            font=label_font,
        )

        day_font = self._font(int(height * 0.052), weight="Bold")
        day_text = snapshot.day_name
        draw.text(
            (card_x + int(width * 0.02), today_badge_y + badge_sz + int(height * 0.02)),
            day_text,
            fill=self.config.primary_text_color,
            font=day_font,
        )

        date_font = self._font(int(height * 0.022), weight="Medium")
        date_text = f"{snapshot.month_name} {snapshot.current_date.day}, {snapshot.year}"
        draw.text(
            (card_x + int(width * 0.02), today_badge_y + badge_sz + int(height * 0.085)),
            date_text,
            fill=self.config.secondary_text_color,
            font=date_font,
        )

        divider_y_today = card1_y + card1_h - int(height * 0.04)
        draw.line(
            (card_x + int(width * 0.02), divider_y_today, card_x + card_w - int(width * 0.02), divider_y_today),
            fill=self.config.divider_color,
            width=max(1, self.scale)
        )

        # Card 2: This Month
        card2_y = card1_y + card1_h + int(height * 0.03)
        card2_h = int(height * 0.24)
        self._draw_card(draw, card_x, card2_y, card_w, card2_h, radius=int(height * 0.015))

        month_badge_x = card_x + int(width * 0.02)
        month_badge_y = card2_y + int(height * 0.03)
        self._draw_card(draw, month_badge_x, month_badge_y, badge_sz, badge_sz, radius=int(badge_sz * 0.25))
        self._draw_icon(draw, "clock", month_badge_x + icon_offset, month_badge_y + icon_offset, icon_sz, self.config.accent_color)
        
        draw.text(
            (month_badge_x + badge_sz + int(width * 0.01), month_badge_y + int((badge_sz - th_label) / 2) - y_offset_label),
            "THIS MONTH",
            fill=self.config.accent_color,
            font=label_font,
        )

        days_rem_month_str = str(snapshot.days_remaining_month)
        draw.text(
            (card_x + int(width * 0.02), month_badge_y + badge_sz + int(height * 0.015)),
            days_rem_month_str,
            fill=self.config.primary_text_color,
            font=day_font,
        )
        draw.text(
            (card_x + int(width * 0.02), month_badge_y + badge_sz + int(height * 0.075)),
            "Days Left",
            fill=self.config.secondary_text_color,
            font=date_font,
        )

        import calendar
        _, days_in_month = calendar.monthrange(snapshot.year, snapshot.current_date.month)
        month_ratio = snapshot.days_remaining_month / days_in_month
        
        ring_sz = int(height * 0.105)
        ring_x = card_x + card_w - ring_sz - int(width * 0.025)
        ring_y = month_badge_y + badge_sz - int(height * 0.01)
        ring_thick = int(height * 0.018)
        self._draw_donut_chart(
            draw,
            ring_x,
            ring_y,
            ring_sz,
            ring_thick,
            month_ratio,
            bg_color=self.config.divider_color,
            fg_color=self.config.accent_color
        )

        # ----------------------------------------------------
        # FOOTER Section (Glowing red flare + Target/Building/Refresh footer)
        # ----------------------------------------------------
        glow_w = int(width * 0.35)
        gx0 = (width - glow_w) // 2
        gx1 = (width + glow_w) // 2
        gy = bottom_y - int(height * 0.045)

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.line((gx0, gy, gx1, gy), fill=(255, 69, 58, 30), width=max(12, self.scale * 8))
        overlay_draw.line((gx0, gy, gx1, gy), fill=(255, 69, 58, 80), width=max(6, self.scale * 4))
        overlay_draw.line((gx0, gy, gx1, gy), fill=(255, 69, 58, 200), width=max(2, self.scale * 2))
        self.image.paste(overlay, (0, 0), mask=overlay)

        foot_font = self._font(int(height * 0.018), weight="Bold")
        foot_icon_sz = int(height * 0.022)
        bullet_text = "     •     "
        
        bbox_focus = draw.textbbox((0, 0), "FOCUS", font=foot_font)
        w_focus = bbox_focus[2] - bbox_focus[0]
        
        bbox_build = draw.textbbox((0, 0), "BUILD", font=foot_font)
        w_build = bbox_build[2] - bbox_build[0]
        
        bbox_repeat = draw.textbbox((0, 0), "REPEAT", font=foot_font)
        w_repeat = bbox_repeat[2] - bbox_repeat[0]
        
        bbox_bullet = draw.textbbox((0, 0), bullet_text, font=foot_font)
        w_bullet = bbox_bullet[2] - bbox_bullet[0]
        
        spacing = int(width * 0.008)
        w_item1 = foot_icon_sz + spacing + w_focus
        w_item2 = foot_icon_sz + spacing + w_build
        w_item3 = foot_icon_sz + spacing + w_repeat
        
        total_footer_w = w_item1 + w_bullet + w_item2 + w_bullet + w_item3
        cur_x = (width - total_footer_w) // 2
        foot_y = bottom_y - int(height * 0.01)

        text_h_offset = bbox_focus[1]
        th_foot = bbox_focus[3] - bbox_focus[1]

        self._draw_icon(draw, "target", cur_x, foot_y - foot_icon_sz // 2, foot_icon_sz, self.config.accent_color)
        draw.text(
            (cur_x + foot_icon_sz + spacing, foot_y - th_foot // 2 - text_h_offset),
            "FOCUS",
            fill=self.config.secondary_text_color,
            font=foot_font,
        )
        cur_x += w_item1

        draw.text(
            (cur_x, foot_y - th_foot // 2 - text_h_offset),
            bullet_text,
            fill=self.config.divider_color,
            font=foot_font,
        )
        cur_x += w_bullet

        self._draw_icon(draw, "building", cur_x, foot_y - foot_icon_sz // 2, foot_icon_sz, self.config.accent_color)
        draw.text(
            (cur_x + foot_icon_sz + spacing, foot_y - th_foot // 2 - text_h_offset),
            "BUILD",
            fill=self.config.secondary_text_color,
            font=foot_font,
        )
        cur_x += w_item2

        draw.text(
            (cur_x, foot_y - th_foot // 2 - text_h_offset),
            bullet_text,
            fill=self.config.divider_color,
            font=foot_font,
        )
        cur_x += w_bullet

        self._draw_icon(draw, "refresh", cur_x, foot_y - foot_icon_sz // 2, foot_icon_sz, self.config.accent_color)
        draw.text(
            (cur_x + foot_icon_sz + spacing, foot_y - th_foot // 2 - text_h_offset),
            "REPEAT",
            fill=self.config.secondary_text_color,
            font=foot_font,
        )

    def _draw_quote_badge(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
        draw.ellipse((x, y, x + size, y + size), fill=self.config.card_background_color, outline=self.config.card_border_color, width=max(1, self.scale))
        font = self._font(int(size * 1.2), weight="Bold")
        text = "“"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        cx = x + (size - tw) / 2 - bbox[0]
        cy = y + (size - th) / 2 - bbox[1] + int(size * 0.15)
        draw.text((cx, cy), text, fill=self.config.accent_color, font=font)

    def _draw_reminder_badge(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
        draw.ellipse((x, y, x + size, y + size), fill=self.config.card_background_color, outline=self.config.card_border_color, width=max(1, self.scale))
        icon_sz = int(size * 0.5)
        offset = (size - icon_sz) // 2
        self._draw_icon(draw, "clipboard", x + offset, y + offset, icon_sz, self.config.accent_color)

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

    def _draw_card(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        radius: int,
    ) -> None:
        """Draw a card panel with a subtle border."""
        draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius=radius,
            fill=self.config.card_background_color,
        )
        draw.rounded_rectangle(
            (x, y, x + w, y + h),
            radius=radius,
            outline=self.config.card_border_color,
            width=max(1, self.scale),
        )

    def _draw_donut_chart(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        size: int,
        thickness: int,
        progress: float,
        bg_color: str,
        fg_color: str,
    ) -> None:
        """Draw a circular progress ring (donut chart)."""
        start_angle = -90
        end_angle = -90 + (progress * 360)
        draw.ellipse(
            (x, y, x + size, y + size),
            outline=bg_color,
            width=thickness,
        )
        if progress > 0.001:
            draw.arc(
                (x, y, x + size, y + size),
                start=int(start_angle),
                end=int(end_angle),
                fill=fg_color,
                width=thickness,
            )

    def _draw_icon(self, draw: ImageDraw.ImageDraw, icon_type: str, x: int, y: int, size: int, color: str) -> None:
        """Draw custom vector-like icons geometrically."""
        w, h = size, size
        if icon_type == "calendar":
            draw.rounded_rectangle((x, y + h * 0.15, x + w, y + h), radius=size * 0.12, outline=color, width=max(2, self.scale))
            draw.line((x + w * 0.25, y, x + w * 0.25, y + h * 0.25), fill=color, width=max(2, self.scale))
            draw.line((x + w * 0.75, y, x + w * 0.75, y + h * 0.25), fill=color, width=max(2, self.scale))
            draw.line((x, y + h * 0.4, x + w, y + h * 0.4), fill=color, width=max(2, self.scale))
            dot_size = max(1, self.scale)
            for r in range(2):
                for c in range(3):
                    dx = x + w * (0.22 + c * 0.28)
                    dy = y + h * (0.55 + r * 0.22)
                    draw.ellipse((dx - dot_size, dy - dot_size, dx + dot_size, dy + dot_size), fill=color)

        elif icon_type == "checkmark":
            pts = [
                (x + w * 0.25, y + h * 0.5),
                (x + w * 0.45, y + h * 0.7),
                (x + w * 0.75, y + h * 0.3)
            ]
            draw.line(pts[0:2], fill=color, width=max(3, self.scale * 2), joint="round")
            draw.line(pts[1:3], fill=color, width=max(3, self.scale * 2), joint="round")

        elif icon_type == "chart":
            draw.rounded_rectangle((x + w * 0.2, y + h * 0.55, x + w * 0.35, y + h * 0.8), radius=self.scale, fill=color)
            draw.rounded_rectangle((x + w * 0.42, y + h * 0.3, x + w * 0.57, y + h * 0.8), radius=self.scale, fill=color)
            draw.rounded_rectangle((x + w * 0.65, y + h * 0.45, x + w * 0.8, y + h * 0.8), radius=self.scale, fill=color)

        elif icon_type == "clock":
            draw.ellipse((x, y, x + w, y + h), outline=color, width=max(2, self.scale))
            cx, cy = x + w / 2, y + h / 2
            draw.line((cx, cy, cx + w * 0.22, cy), fill=color, width=max(2, self.scale))
            draw.line((cx, cy, cx, cy - h * 0.3), fill=color, width=max(2, self.scale))

        elif icon_type == "target":
            cx, cy = x + w / 2, y + h / 2
            draw.ellipse((x, y, x + w, y + h), outline=color, width=max(2, self.scale))
            draw.ellipse((cx - w * 0.25, cy - h * 0.25, cx + w * 0.25, cy + h * 0.25), outline=color, width=max(2, self.scale))
            draw.ellipse((cx - w * 0.08, cy - h * 0.08, cx + w * 0.08, cy + h * 0.08), fill=color)

        elif icon_type == "building":
            draw.rounded_rectangle((x + w * 0.3, y + h * 0.15, x + w * 0.7, y + h * 0.85), radius=self.scale, fill=color)
            window_color = self.config.card_background_color
            for r in range(3):
                for c in range(2):
                    wx = x + w * (0.38 + c * 0.16)
                    wy = y + h * (0.28 + r * 0.18)
                    draw.rectangle((wx, wy, wx + w * 0.08, wy + h * 0.1), fill=window_color)

        elif icon_type == "refresh":
            draw.arc((x, y, x + w, y + h), start=0, end=270, fill=color, width=max(2, self.scale))
            ax = x + w / 2
            ay = y
            arrow_pts = [
                (ax, ay - h * 0.1),
                (ax + w * 0.15, ay),
                (ax, ay + h * 0.1)
            ]
            draw.polygon(arrow_pts, fill=color)

        elif icon_type == "clipboard":
            draw.rounded_rectangle(
                (x + w * 0.22, y + h * 0.25, x + w * 0.78, y + h * 0.92),
                radius=max(2, int(w * 0.06)),
                outline=color,
                width=max(2, self.scale)
            )
            draw.rounded_rectangle(
                (x + w * 0.38, y + h * 0.12, x + w * 0.62, y + h * 0.27),
                radius=max(1, int(w * 0.04)),
                outline=color,
                width=max(2, self.scale),
                fill=self.config.card_background_color
            )
            line_width = max(1, self.scale)
            cx = x + w * 0.32
            cy = y + h * 0.44
            draw.line(
                [(cx, cy + h * 0.04), (cx + w * 0.04, cy + h * 0.08), (cx + w * 0.10, cy - h * 0.02)],
                fill=color,
                width=max(2, self.scale)
            )
            draw.line((cx + w * 0.15, cy + h * 0.04, cx + w * 0.38, cy + h * 0.04), fill=color, width=line_width)
            
            cx2 = x + w * 0.32
            cy2 = y + h * 0.60
            draw.rectangle((cx2, cy2, cx2 + w * 0.08, cy2 + h * 0.08), outline=color, width=line_width)
            draw.line((cx2 + w * 0.15, cy2 + h * 0.04, cx2 + w * 0.38, cy2 + h * 0.04), fill=color, width=line_width)
            
            cx3 = x + w * 0.32
            cy3 = y + h * 0.76
            draw.rectangle((cx3, cy3, cx3 + w * 0.08, cy3 + h * 0.08), outline=color, width=line_width)
            draw.line((cx3 + w * 0.15, cy3 + h * 0.04, cx3 + w * 0.38, cy3 + h * 0.04), fill=color, width=line_width)

    def _draw_gradient_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        xy: tuple[int, int],
        start_color: str,
        end_color: str,
    ) -> None:
        """Render text with a vertical gradient fill."""
        bbox = draw.textbbox((0, 0), text, font=font)
        x0, y0, x1, y1 = bbox
        tw = x1 - x0
        th = y1 - y0
        
        if tw <= 0 or th <= 0:
            draw.text(xy, text, fill=start_color, font=font)
            return

        mask = Image.new("L", (tw + 10, th + 10), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((-x0 + 5, -y0 + 5), text, fill=255, font=font)
        
        c1 = self._parse_color(start_color)
        c2 = self._parse_color(end_color)
        gradient = Image.new("RGB", (tw + 10, th + 10))
        pixels = gradient.load()
        for y_idx in range(th + 10):
            factor = y_idx / max(1, th + 9)
            r = int(c1[0] + (c2[0] - c1[0]) * factor)
            g = int(c1[1] + (c2[1] - c1[1]) * factor)
            b = int(c1[2] + (c2[2] - c1[2]) * factor)
            for x_idx in range(tw + 10):
                pixels[x_idx, y_idx] = (r, g, b)
                
        px = xy[0] + x0 - 5
        py = xy[1] + y0 - 5
        self.image.paste(gradient, (px, py), mask=mask)

    def _parse_color(self, hex_str: str) -> tuple[int, int, int]:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 3:
            hex_str = "".join(c * 2 for c in hex_str)
        return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)

    def _font(self, size: int, weight: str = "Regular") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if weight == "Bold":
            font_path = self.config.font_bold_path
        elif weight == "Medium":
            font_path = self.config.font_medium_path
        else:
            font_path = self.config.font_regular_path

        if not font_path.exists():
            self._download_font(font_path, weight)

        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)

        # Fallback to other weights if the specific one is missing
        fallback_path = self.config.font_regular_path
        if fallback_path.exists():
            return ImageFont.truetype(str(fallback_path), size)

        LOGGER.warning("Configured font %s not found. Falling back to system fonts.", font_path)
        
        sys_font = "Helvetica.ttc"
        if weight == "Bold":
            sys_font = "HelveticaNeue-Bold"
        elif weight == "Medium":
            sys_font = "HelveticaNeue-Medium"
            
        try:
            return ImageFont.truetype(sys_font, size)
        except OSError:
            try:
                return ImageFont.truetype("Helvetica.ttc", size)
            except OSError:
                return ImageFont.load_default()

    def _download_font(self, font_path: Path, weight: str) -> None:
        """Download Inter font family weight from raw sources."""
        import urllib.request
        
        weight_mapping = {
            "Regular": "Inter_400Regular.ttf",
            "Medium": "Inter_500Medium.ttf",
            "Bold": "Inter_700Bold.ttf"
        }
        filename = weight_mapping.get(weight, "Inter_400Regular.ttf")
        
        urls = [
            f"https://cdn.jsdelivr.net/npm/@expo-google-fonts/inter/{filename}",
            f"https://raw.githubusercontent.com/google/fonts/main/ofl/inter/static/Inter-{weight}.ttf",
            f"https://github.com/google/fonts/raw/main/ofl/inter/static/Inter-{weight}.ttf",
        ]
        if weight == "Regular":
            urls.append("https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf")

        font_path.parent.mkdir(parents=True, exist_ok=True)
        
        for url in urls:
            try:
                LOGGER.info("Attempting to download Inter-%s.ttf font from %s...", weight, url)
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    font_path.write_bytes(response.read())
                LOGGER.info("Font Inter-%s downloaded successfully.", weight)
                return
            except Exception as e:
                LOGGER.warning("Failed to download from %s: %s", url, e)
                
        LOGGER.error("All download attempts for Inter-%s failed.", weight)

    def _cleanup_old_wallpapers(self, current_path: Path) -> None:
        """Delete old wallpaper files to save disk space."""
        try:
            for file in self.config.wallpaper_output_folder.glob("yearflow-wallpaper-*.png"):
                if file.resolve() != current_path.resolve():
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
