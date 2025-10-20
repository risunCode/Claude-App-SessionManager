import json
from pathlib import Path
import os
import sys

DEBUG = False

# Resolve app directory (works for dev and PyInstaller onefile)
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent.parent

CONFIG_FILE = APP_DIR / "config.json"

# Auto-detect current username
CURRENT_USER = os.getenv('USERNAME') or os.getenv('USER') or 'LovelyLova'

# Default backup directory resolver

def _documents_dir() -> Path:
    onedrive = os.getenv('OneDrive')
    if onedrive:
        d = Path(onedrive) / 'Documents'
        if d.exists():
            return d
    return Path.home() / 'Documents'


def _default_backup_dir() -> Path:
    if getattr(sys, 'frozen', False):
        # EXE build: store under Documents/BackupClaude
        return _documents_dir() / 'BackupClaude'
    # Dev: store inside project folder
    return APP_DIR / 'backup'

DEFAULT_CONFIG = {
    "source_dir": rf"C:\Users\{CURRENT_USER}\AppData\Roaming\Claude\Network",
    "backup_dir": str(_default_backup_dir()),
    "claude_path": rf"C:\Users\{CURRENT_USER}\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Anthropic\Claude.lnk",
    "current_backup": ""
}

def load_config():
    """Load configuration from file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ensure backup_dir exists
                Path(config.get("backup_dir", DEFAULT_CONFIG["backup_dir"])).mkdir(exist_ok=True, parents=True)
                return config
        except Exception as e:
            if DEBUG:
                print(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        if DEBUG:
            print(f"Error saving config: {e}")
        return False

def get_source_dir():
    """Get source directory from config"""
    config = load_config()
    return config.get("source_dir", DEFAULT_CONFIG["source_dir"])

def get_backup_dir():
    """Get backup directory from config"""
    config = load_config()
    return config.get("backup_dir", DEFAULT_CONFIG["backup_dir"])

def set_source_dir(path):
    """Set source directory in config"""
    config = load_config()
    config["source_dir"] = path
    return save_config(config)

def set_backup_dir(path):
    """Set backup directory in config"""
    config = load_config()
    config["backup_dir"] = path
    # Create directory if it doesn't exist
    Path(path).mkdir(exist_ok=True, parents=True)
    return save_config(config)

def get_claude_path():
    """Get Claude executable/shortcut path from config"""
    config = load_config()
    return config.get("claude_path", DEFAULT_CONFIG["claude_path"])

def set_claude_path(path):
    """Set Claude executable/shortcut path in config"""
    config = load_config()
    config["claude_path"] = path
    return save_config(config)

def get_current_backup():
    """Get the last restored/active backup name"""
    config = load_config()
    return config.get("current_backup", DEFAULT_CONFIG["current_backup"]) or ""

def set_current_backup(name: str):
    """Set the last restored/active backup name"""
    config = load_config()
    config["current_backup"] = name or ""
    return save_config(config)
