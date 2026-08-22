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
        import time
        if hasattr(self.server, "last_heartbeat"):
            self.server.last_heartbeat = time.time()

        if self.path == "/":
            self._serve_html()
        elif self.path == "/api/config":
            self._serve_config()
        elif self.path == "/api/fonts":
            self._serve_fonts()
        elif self.path == "/api/heartbeat":
            self._serve_heartbeat()
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self) -> None:
        """Route POST requests."""
        import time
        if hasattr(self.server, "last_heartbeat"):
            self.server.last_heartbeat = time.time()

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
        """Return list of curated popular font family names."""
        try:
            families = config.scan_mac_fonts()
            
            # Curate popular/aesthetic font families
            curated_fonts = [
                "Inter",
                "System Font",
                ".New York",
                "Helvetica Neue",
                "Avenir Next",
                "Futura",
                "Optima",
                "Baskerville",
                "Georgia",
                "American Typewriter",
                "Menlo",
                "Ndot 57",
                "Lettera Mono LL",
                "NType 82",
                "Space Grotesk",
                "Mocka",
                "Nagasaki",
                "The Block",
                "Virgil 3 YOFF"
            ]
            
            # Filter to keep only those present on the system/bundle, falling back to all if empty
            available_curated = [font for font in curated_fonts if font in families]
            if not available_curated:
                available_curated = sorted(list(families.keys()))
                
            content = json.dumps(available_curated).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as error:
            LOGGER.error("Failed to list system fonts: %s", error)
            self.send_error(500, "Internal Server Error")
    def _serve_heartbeat(self) -> None:
        """Return heartbeat status."""
        try:
            content = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as error:
            LOGGER.error("Failed to serve heartbeat: %s", error)
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
        import socket
        import time
        # Dynamically find an available port if the default is in use (e.g. macOS AirPlay conflict on 5000)
        base_port = self.port
        for offset in range(20):
            candidate_port = base_port + offset
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((self.host, candidate_port))
                self.port = candidate_port
                break
            except OSError:
                LOGGER.debug("Port %s is busy, trying next...", candidate_port)

        try:
            self.server = HTTPServer((self.host, self.port), SettingsHTTPRequestHandler)
            self.server.last_heartbeat = time.time()
            LOGGER.info("Starting settings server on http://%s:%s", self.host, self.port)
            
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            # Start background heartbeat monitor thread to auto-shutdown when browser tab/window is closed
            def monitor_heartbeat():
                # Allow 25 seconds for the browser to open and load the settings page
                time.sleep(25)
                while self.server:
                    time.sleep(2)
                    if not hasattr(self.server, "last_heartbeat"):
                        continue
                    # Shutdown if no heartbeat received for more than 10 seconds
                    if time.time() - self.server.last_heartbeat > 10:
                        LOGGER.info("No heartbeat received for 10 seconds. Auto-shutting down...")
                        threading.Thread(target=self.server.shutdown, daemon=True).start()
                        break
            
            threading.Thread(target=monitor_heartbeat, daemon=True).start()

            # Automatically open user browser
            webbrowser.open(f"http://localhost:{self.port}/")
        except Exception as error:
            LOGGER.exception("Failed to start settings server: %s", error)

    def wait(self) -> None:
        """Wait for the server thread to terminate (after shutdown is triggered)."""
        if self.thread and self.thread.is_alive():
            self.thread.join()
            LOGGER.info("Settings server shut down successfully.")
