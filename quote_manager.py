"""Quote loading and deterministic daily selection."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class QuoteManager:
    """Loads quotes and selects one stable quote per date."""

    def __init__(self, quotes_path: Path) -> None:
        self.quotes_path = quotes_path
        self._quotes: list[str] | None = None

    def get_quote_for_date(self, target_date: date) -> str:
        """Return the deterministic quote for a date."""
        quotes = self._load_quotes()
        if not quotes:
            LOGGER.warning("No quotes found in %s", self.quotes_path)
            return "Focus on today."

        index_seed = int(target_date.strftime("%Y%m%d"))
        return quotes[index_seed % len(quotes)]

    def _load_quotes(self) -> list[str]:
        if self._quotes is not None:
            return self._quotes

        try:
            with self.quotes_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            LOGGER.exception("Quotes file not found: %s", self.quotes_path)
            self._quotes = []
            return self._quotes
        except json.JSONDecodeError:
            LOGGER.exception("Quotes file is not valid JSON: %s", self.quotes_path)
            self._quotes = []
            return self._quotes

        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            LOGGER.error("Quotes file must contain a JSON array of strings.")
            self._quotes = []
            return self._quotes

        self._quotes = data
        return self._quotes
