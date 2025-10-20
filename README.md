# Claude Backup Manager

Manage Claude session backups on Windows with a fast, minimal PyQt app.

- Create and restore backups of Claude Network data
- Right‑click actions on backups: Restore, Open in Explorer, Delete
- Realtime status card: Claude is Running/Stopped + Stop button
- Marks the currently active (last restored) backup
- Auto‑detects Claude path (.lnk in Start Menu) per current user
- Single prompt to close Claude if restoring while running
- Portable: stores config.json and backup/ next to the EXE

## Download / Portable Usage

- Download the portable EXE (ClaudeBackupManager.exe) from Releases and run it
- First run creates config.json and backup/ next to the EXE
- No Python required
- Windows 10/11 supported

## Features

- Create Backup: backs up the entire Claude Network folder
- List Backups: shows name, created time, and size; marks Current
- Restore Backup: replaces current data; prompts once to close Claude if running
- Delete Backup: removes a selected backup (with confirmation)
- Open Backup: opens the selected backup folder in Explorer
- Paths: Source, Backup, and Claude (.exe/.lnk) are configurable; defaults auto‑detected
- Realtime Claude Status: see running/stopped; click Stop to terminate Claude safely

## Quick Start (from source)

```powershell path=null start=null
# one‑click build (creates portable EXE under dist/)
./build.bat

# cleanup build artifacts
./clean.bat
```

Manual build via PyInstaller:

```powershell path=null start=null
# create venv (optional)
python -m venv venv
./venv/Scripts/pip install -r requirements.txt

# build one-file, no console
./venv/Scripts/pyinstaller --noconfirm --clean --onefile --noconsole \
  --optimize=2 --name ClaudeBackupManager app/main.py
```

Run in dev mode (requires Python):

```powershell path=null start=null
./venv/Scripts/python -m app.main
```

## Usage

- New Backup: set name (letters/numbers/-/_) and click ✓ Create
- Available Backups: right‑click a row → Restore / Open / Delete
- Current column shows the last restored (active) backup
- Claude Status card: view status and Stop Claude
- After a successful restore, optionally start Claude again (no extra success popups)

## Configuration

A config.json is created next to the EXE (or repo root in dev). Example:

```json path=null start=null
{
  "source_dir": "C:\\Users\\<YOU>\\AppData\\Roaming\\Claude\\Network",
  "backup_dir": "<APP_DIR>\\backup",
  "claude_path": "C:\\Users\\<YOU>\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Anthropic\\Claude.lnk",
  "current_backup": "backup-claude-20251020_101530"
}
```

- source_dir: Claude Network folder
- backup_dir: where backups are stored (default: next to EXE)
- claude_path: executable/shortcut for launching Claude (browse to change)
- current_backup: auto‑updated after restore

## Requirements

- Runtime: none (portable EXE bundles Python + dependencies)
- Build: Python 3.8+, PyQt6, psutil, PyInstaller (installed via requirements.txt)

## Troubleshooting

- Restore fails or is partial: ensure Claude is stopped (use Stop button) and try again
- "Could not find Claude": set Claude path via Browse (supports .exe or .lnk)
- Permission denied when deleting: close any Explorer windows in that backup and retry
- Running as Administrator may be needed in locked environments

## License

MIT (or project’s chosen license).