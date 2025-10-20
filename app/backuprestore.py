import os
import shutil
from datetime import datetime
from pathlib import Path

# Source and backup directories
SOURCE_DIR = r"C:\Users\LovelyLova\AppData\Roaming\Claude\Network"
BACKUP_DIR = Path(__file__).parent.parent / "backup"

def create_backup(name="claude"):
    """Create a full backup of the Claude Network folder"""
    if not os.path.exists(SOURCE_DIR):
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")
    
    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Generate backup folder name with datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup-{name}-{timestamp}"
    backup_path = BACKUP_DIR / backup_name
    
    # Copy the entire directory
    shutil.copytree(SOURCE_DIR, backup_path)
    
    return backup_name

def list_backups():
    """List all available backups"""
    if not BACKUP_DIR.exists():
        return []
    
    backups = []
    for item in BACKUP_DIR.iterdir():
        if item.is_dir() and item.name.startswith("backup-"):
            backups.append({
                "name": item.name,
                "path": str(item),
                "created": datetime.fromtimestamp(item.stat().st_ctime),
                "size": sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
            })
    
    # Sort by creation time, newest first
    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups

def restore_backup(backup_name):
    """Restore a backup to the Claude Network folder"""
    backup_path = BACKUP_DIR / backup_name
    
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_name}")
    
    # Create parent directory if it doesn't exist
    parent_dir = Path(SOURCE_DIR).parent
    try:
        parent_dir.mkdir(exist_ok=True, parents=True)
    except Exception as e:
        raise RuntimeError(f"Failed to create target directory: {e}")
    
    # Remove existing Network folder
    if os.path.exists(SOURCE_DIR):
        try:
            shutil.rmtree(SOURCE_DIR)
        except Exception as e:
            raise RuntimeError(f"Failed to remove existing folder: {e}")
    
    # Copy backup to source location
    try:
        shutil.copytree(backup_path, SOURCE_DIR)
    except Exception as e:
        raise RuntimeError(f"Failed to restore backup: {e}")
    
    return True

def delete_backup(backup_name):
    """Delete a backup"""
    BACKUP_DIR = get_backup_dir()
    
    backup_path = BACKUP_DIR / backup_name
    
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_name}")
    
    # Try to remove with retry for locked files
    import time
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            shutil.rmtree(backup_path)
            return True
        except PermissionError as e:
            if attempt < max_attempts - 1:
                time.sleep(0.5)
                continue
            else:
                raise RuntimeError(f"Cannot delete backup (in use or locked): {backup_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to delete backup: {e}")

def get_backup_size_str(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
