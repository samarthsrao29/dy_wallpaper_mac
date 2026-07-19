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
git clone https://github.com/samarthsrao29/dy_wallpaper_mac.git
cd dy_wallpaper_mac/YearFlow
python3 -m venv .venv
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

## Packaging & Distribution (DMG)

You can package YearFlow as a standalone macOS application inside a `.dmg` installer using the provided automated script.

### 1. Build the DMG
Run the packaging script in your terminal:
```bash
./build_dmg.sh
```
This script compiles the application and produces the installer image at:
```text
dist/YearFlow.dmg
```

### 2. Install on any Mac
1. Double-click the generated `YearFlow.dmg` to mount it.
2. Drag `YearFlow.app` into the **Applications** folder shortcut.
3. Open `YearFlow.app` from your Applications folder.

### 3. Gatekeeper Bypass (For free distribution)
Since the app is built for free (without a $99/year Apple Developer Account), macOS Gatekeeper will block it on other Macs, saying the developer is unidentified.
* **To bypass this:** Right-click (or Control-click) `YearFlow.app` in `/Applications`, click **Open**, and then click **Open** in the warning dialog. (This is only required on the very first launch).
* **Alternative (Terminal command):** Run the following command:
  ```bash
  xattr -cr /Applications/YearFlow.app
  ```

### 4. Zero Configuration (Auto-Scheduling)
Once launched from `/Applications`, the app will automatically:
1. Generate and set your first wallpaper.
2. Write outputs to user-writable folders:
   * Generated wallpapers: `~/Pictures/YearFlow`
   * Logs & Config: `~/Library/Application Support/YearFlow`
3. Configure the `launchd` LaunchAgent to automatically refresh your wallpaper daily at 12:00 AM (and every 10 minutes to catch up if the Mac was asleep). No terminal configuration is required by the end-user.


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

## Safety & Performance

YearFlow is designed to be extremely lightweight and unobtrusive:
* **No Battery/CPU Drain:** The app does not run constantly in the background. macOS's built-in `launchd` service triggers it once at midnight and briefly every 10 minutes to verify. The execution takes less than a second to run and completely exits. It uses 0% CPU and 0 MB RAM when idle.
* **Storage Footprint:** Generated wallpapers alternate between only two files: `yearflow-wallpaper-1.png` and `yearflow-wallpaper-2.png` (~200 KB each), ensuring it never hoards disk space.
* **No Administrator Privileges:** The app runs entirely in user-space, requiring no root permissions. It only asks for standard Automation permissions to tell macOS "System Events" to set the wallpaper.

## How to Uninstall

If you ever want to completely remove YearFlow, follow these steps:

1. **Unload & delete the background scheduler:**
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.yearflow.agent.plist
   rm ~/Library/LaunchAgents/com.yearflow.agent.plist
   ```
2. **Remove the application:**
   Delete `YearFlow.app` from your `/Applications` folder (or move it to Trash).
3. **Clean up generated data and logs:**
   ```bash
   rm -rf ~/Pictures/YearFlow
   rm -rf "~/Library/Application Support/YearFlow"
   ```

## Future Improvements

- Multi-display layout tuning
- Menu bar companion app
- Per-space wallpaper preferences
- User-editable JSON configuration
- Signed and notarized app distribution
