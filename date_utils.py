"""Date calculations used by YearFlow."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DateSnapshot:
    """Computed date values for the current wallpaper."""

    current_date: date
    day_name: str
    month_name: str
    year: int
    day_of_year: int
    days_in_year: int
    days_completed: int
    days_remaining_year: int
    progress_percentage: int
    days_remaining_month: int


class DateCalculator:
    """Calculates calendar values needed by the wallpaper renderer."""

    @staticmethod
    def build(target_date: date | None = None) -> DateSnapshot:
        """Build a complete date snapshot for a given date."""
        current = target_date or date.today()
        days_in_year = 366 if calendar.isleap(current.year) else 365
        day_of_year = current.timetuple().tm_yday
        days_completed = day_of_year - 1
        days_remaining_year = days_in_year - days_completed
        _, days_in_month = calendar.monthrange(current.year, current.month)
        days_remaining_month = days_in_month - (current.day - 1)
        progress_percentage = round((days_completed / days_in_year) * 100)

        return DateSnapshot(
            current_date=current,
            day_name=current.strftime("%A"),
            month_name=current.strftime("%B"),
            year=current.year,
            day_of_year=day_of_year,
            days_in_year=days_in_year,
            days_completed=days_completed,
            days_remaining_year=days_remaining_year,
            progress_percentage=progress_percentage,
            days_remaining_month=days_remaining_month,
        )
