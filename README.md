# YearFlow

YearFlow is a minimalist macOS utility that generates a fresh typography-only desktop wallpaper every day and sets it as the current wallpaper.

It is fully offline, uses Pillow for rendering, and uses `launchd` instead of cron for automatic daily refreshes.

## Screenshots

Add screenshots here after generating your first wallpaper.

## Requirements

- macOS
- Python 3.13
- Pillow
- PyInstaller, for packaging only

## Installation

```bash
cd /Users/samarthrao/LocalFiles/wallpaper/YearFlow
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `python3.13` is not on your path, install Python 3.13 first or replace the command with the correct interpreter path.

## Running

Generate and set the wallpaper immediately:

```bash
python app.py
```

The generated image is written to:

```text
generated/yearflow-wallpaper.png
```

Logs are written to:

```text
logs/yearflow.log
```

## launchd Setup

Install the LaunchAgent:

```bash
python app.py --install-agent
```

This copies `launchd/com.yearflow.agent.plist` to:

```text
~/Library/LaunchAgents/com.yearflow.agent.plist
```

The agent runs:

- At login
- Every day at exactly 12:00 AM

Uninstall the LaunchAgent:

```bash
python app.py --uninstall-agent
```

You can also inspect the job manually:

```bash
launchctl list | grep yearflow
```

## Packaging

Create a standalone macOS app with PyInstaller:

```bash
pyinstaller \
  --windowed \
  --name YearFlow \
  --add-data "quotes.json:." \
  --add-data "fonts:fonts" \
  app.py
```

The packaged app will be created under:

```text
dist/YearFlow.app
```

Double-clicking the app regenerates and sets the current wallpaper. For LaunchAgent use with a packaged app, update `ProgramArguments` in the plist to point to the executable inside `dist/YearFlow.app/Contents/MacOS/YearFlow`.

## Folder Structure

```text
YearFlow/
  app.py
  wallpaper.py
  scheduler.py
  config.py
  quote_manager.py
  date_utils.py
  wallpaper_manager.py
  quotes.json
  fonts/
    Inter-Regular.ttf
  generated/
  launchd/
    com.yearflow.agent.plist
  README.md
  requirements.txt
```

## Configuration

Edit `config.py` to customize:

- Accent color
- Background color
- Font path
- Base font size
- Quote visibility
- Progress bar visibility
- Wallpaper output folder

## Troubleshooting

If the wallpaper does not change, run `python app.py` from Terminal and check `logs/yearflow.log`.

If macOS blocks wallpaper changes, open System Settings and confirm Terminal or the packaged app has the required automation permissions.

If the LaunchAgent does not run, confirm the plist path is correct and run:

```bash
launchctl unload ~/Library/LaunchAgents/com.yearflow.agent.plist
launchctl load ~/Library/LaunchAgents/com.yearflow.agent.plist
```

If the Inter font is unavailable, YearFlow falls back to a system font. Place `Inter-Regular.ttf` in `fonts/` for the intended typography.

## Future Improvements

- Multi-display layout tuning
- Menu bar companion app
- Per-space wallpaper preferences
- User-editable JSON configuration
- Signed and notarized app distribution
