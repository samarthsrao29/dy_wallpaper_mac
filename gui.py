"""Lightweight settings GUI server for YearFlow."""

from __future__ import annotations

import json
import logging
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import config

LOGGER = logging.getLogger(__name__)


class SettingsHTTPRequestHandler(BaseHTTPRequestHandler):
    """Handles API requests for the YearFlow settings dashboard."""

    def log_message(self, format_str: str, *args: any) -> None:
        # Suppress default server logs to keep stdout clean, log via LOGGER instead
        LOGGER.debug(format_str % args)

    def do_GET(self) -> None:
        """Route GET requests."""
        if self.path == "/":
            self._serve_html()
        elif self.path == "/api/config":
            self._serve_config()
        elif self.path == "/api/fonts":
            self._serve_fonts()
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self) -> None:
        """Route POST requests."""
        if self.path == "/api/config":
            self._handle_save_config()
        elif self.path == "/api/close":
            self._handle_close()
        else:
            self.send_error(404, "Endpoint Not Found")

    def _serve_html(self) -> None:
        """Serve the settings.html dashboard."""
        html_path = config.BASE_DIR / "settings.html"
        if not html_path.exists():
            self.send_error(500, "settings.html template not found")
            return

        try:
            content = html_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as error:
            LOGGER.error("Failed to serve settings.html: %s", error)
            self.send_error(500, "Internal Server Error")

    def _serve_config(self) -> None:
        """Return current config as JSON."""
        if config.IS_FROZEN:
            config_path = config.APP_DATA_DIR / "config.json"
        else:
            config_path = config.BASE_DIR / "config.json"

        try:
            if config_path.exists():
                content = config_path.read_bytes()
            else:
                # If config doesn't exist, serialize current CONFIG object
                serialized = {
                    k: str(v) if isinstance(v, Path) else v
                    for k, v in config.CONFIG.__dict__.items()
                }
                content = json.dumps(serialized, indent=4).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as error:
            LOGGER.error("Failed to read config: %s", error)
            self.send_error(500, "Internal Server Error")

    def _serve_fonts(self) -> None:
        """Return list of scanned font family names."""
        try:
            families = config.scan_mac_fonts()
            sorted_family_names = sorted(list(families.keys()))
            content = json.dumps(sorted_family_names).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as error:
            LOGGER.error("Failed to list system fonts: %s", error)
            self.send_error(500, "Internal Server Error")

    def _handle_save_config(self) -> None:
        """Save received config changes and refresh wallpaper."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            new_settings = json.loads(post_data.decode("utf-8"))
        except Exception as error:
            self.send_error(400, f"Invalid JSON payload: {error}")
            return

        if config.IS_FROZEN:
            config_path = config.APP_DATA_DIR / "config.json"
        else:
            config_path = config.BASE_DIR / "config.json"

        try:
            # Overwrite config file with new settings
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(new_settings, f, indent=4)

            # Reload configuration singleton
            config.CONFIG = config.load_config()

            # Trigger a refresh using the updated config
            from app import YearFlowApp
            app = YearFlowApp()
            app.refresh(force=True)

            response_data = json.dumps({"status": "success"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as error:
            LOGGER.error("Failed to save settings or regenerate wallpaper: %s", error)
            response_data = json.dumps({"status": "error", "error": str(error)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)

    def _handle_close(self) -> None:
        """Shut down the local web server."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "18")
        self.end_headers()
        self.wfile.write(b'{"status":"closed"}')

        LOGGER.info("Shutdown request received. Stopping server...")
        # Shutdown server asynchronously in a separate thread to avoid deadlock
        threading.Thread(target=self.server.shutdown, daemon=True).start()


class SettingsGUIServer:
    """Manages the settings web server lifecycle."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5000) -> None:
        self.host = host
        self.port = port
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the HTTP server on a background thread."""
        try:
            self.server = HTTPServer((self.host, self.port), SettingsHTTPRequestHandler)
            LOGGER.info("Starting settings server on http://%s:%s", self.host, self.port)
            
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            # Automatically open user browser
            webbrowser.open(f"http://{self.host}:{self.port}/")
        except Exception as error:
            LOGGER.exception("Failed to start settings server: %s", error)

    def wait(self) -> None:
        """Wait for the server thread to terminate (after shutdown is triggered)."""
        if self.thread and self.thread.is_alive():
            self.thread.join()
            LOGGER.info("Settings server shut down successfully.")
