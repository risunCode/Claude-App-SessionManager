import sys
import os
import subprocess
import shutil
import psutil
import time
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

try:
    from . import config
except:
    import config

def create_backup(name="claude"):
    source = config.get_source_dir()
    backup_dir = Path(config.get_backup_dir())
    if not os.path.exists(source):
        raise FileNotFoundError(f"Source not found: {source}")
    backup_dir.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup-{name}-{timestamp}"
    shutil.copytree(source, backup_dir / backup_name)
    return backup_name

def list_backups():
    backup_dir = Path(config.get_backup_dir())
    if not backup_dir.exists():
        return []
    backups = []
    for item in backup_dir.iterdir():
        if item.is_dir() and item.name.startswith("backup-"):
            try:
                backups.append({
                    "name": item.name,
                    "created": datetime.fromtimestamp(item.stat().st_ctime),
                    "size": sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                })
            except:
                pass
    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups

def restore_backup(backup_name):
    source = config.get_source_dir()
    backup_path = Path(config.get_backup_dir()) / backup_name
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found")
    if os.path.exists(source):
        shutil.rmtree(source)
    shutil.copytree(backup_path, source)

def delete_backup(backup_name):
    backup_path = Path(config.get_backup_dir()) / backup_name
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found")
    import time
    for i in range(3):
        try:
            shutil.rmtree(backup_path)
            return
        except:
            time.sleep(0.3)
    raise RuntimeError("Cannot delete")

def get_size_str(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def is_claude_running():
    """Check if Claude app is running (match exact image name, exclude self)."""
    self_pid = os.getpid()
    for proc in psutil.process_iter(['name','pid']):
        try:
            if proc.info.get('pid') == self_pid:
                continue
            name = (proc.info.get('name') or '').lower()
            if name == 'claude.exe':
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def iter_claude_procs():
    self_pid = os.getpid()
    for proc in psutil.process_iter(['name','pid']):
        try:
            if proc.info.get('pid') == self_pid:
                continue
            name = (proc.info.get('name') or '').lower()
            if name == 'claude.exe':
                yield proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def terminate_claude(timeout: float = 3.0) -> int:
    """Terminate Claude processes gracefully, then force kill if needed.
    Returns number of processes targeted.
    """
    procs = list(iter_claude_procs())
    if not procs:
        return 0
    # Try graceful terminate
    for p in procs:
        try:
            p.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    psutil.wait_procs(procs, timeout=timeout)
    # Force kill remaining
    remaining = [p for p in procs if p.is_running()]
    for p in remaining:
        try:
            p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    # Fallback to taskkill by image name
    still = [p for p in remaining if p.is_running()]
    if still:
        try:
            subprocess.run(["taskkill","/IM","Claude.exe","/F","/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    time.sleep(0.5)
    return len(procs)

def start_claude():
    """Start Claude app"""
    # Try config path first
    config_path = config.get_claude_path()
    if config_path and os.path.exists(config_path):
        try:
            os.startfile(config_path)
            return True
        except:
            pass
    
    # Fallback to common paths
    claude_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Claude\Claude.exe"),
        os.path.expandvars(r"%APPDATA%\Claude\Claude.exe"),
        r"C:\Program Files\Claude\Claude.exe",
        r"C:\Program Files (x86)\Claude\Claude.exe"
    ]
    for path in claude_paths:
        if os.path.exists(path):
            try:
                subprocess.Popen([path], shell=False)
                return True
            except:
                pass
    return False

class Worker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args
    def run(self):
        try:
            self.finished.emit(self.func(*self.args))
        except Exception as e:
            self.error.emit(str(e))

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Claude Backup Manager")
        self.resize(950, 600)
        self.worker = None
        self.setup_ui()
        self.apply_theme()
        self.log("App started")
        self.load_backups()
        
        # realtime status timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)
        self.update_status()
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        
        menu = self.menuBar()
        fm = menu.addMenu("File")
        a=QAction("Refresh",self);a.setShortcut("F5");a.triggered.connect(self.load_backups);fm.addAction(a)
        fm.addSeparator()
        a=QAction("Exit",self);a.triggered.connect(self.close);fm.addAction(a)
        vm = menu.addMenu("View")
        a=QAction("Open Source",self);a.triggered.connect(lambda: subprocess.run(["explorer", config.get_source_dir()]));vm.addAction(a)
        a=QAction("Open Backup",self);a.triggered.connect(lambda: subprocess.run(["explorer", config.get_backup_dir()]));vm.addAction(a)
        
        top = QWidget()
        top.setObjectName("topbar")
        tl = QVBoxLayout(top)
        tl.setContentsMargins(16,12,16,12)
        tl.setSpacing(8)
        
        s = QHBoxLayout()
        s.setSpacing(8)
        s.addWidget(QLabel("📂 Source"))
        self.src = QLineEdit(config.get_source_dir())
        self.src.setReadOnly(True)
        s.addWidget(self.src, 1)
        sb = QPushButton("Browse")
        sb.setObjectName("sm")
        sb.clicked.connect(self.browse_source)
        s.addWidget(sb)
        sb2 = QPushButton("Open")
        sb2.setObjectName("sm")
        sb2.clicked.connect(lambda: subprocess.run(["explorer", config.get_source_dir()]))
        s.addWidget(sb2)
        tl.addLayout(s)
        
        b = QHBoxLayout()
        b.setSpacing(8)
        b.addWidget(QLabel("💾 Backup"))
        self.bak = QLineEdit(config.get_backup_dir())
        self.bak.setReadOnly(True)
        b.addWidget(self.bak, 1)
        bb = QPushButton("Browse")
        bb.setObjectName("sm")
        bb.clicked.connect(self.browse_backup)
        b.addWidget(bb)
        bb2 = QPushButton("Open")
        bb2.setObjectName("sm")
        bb2.clicked.connect(lambda: subprocess.run(["explorer", config.get_backup_dir()]))
        b.addWidget(bb2)
        tl.addLayout(b)
        
        c = QHBoxLayout()
        c.setSpacing(8)
        c.addWidget(QLabel("🚀 Claude"))
        self.claude = QLineEdit(config.get_claude_path())
        self.claude.setReadOnly(True)
        c.addWidget(self.claude, 1)
        cb = QPushButton("Browse")
        cb.setObjectName("sm")
        cb.clicked.connect(self.browse_claude)
        c.addWidget(cb)
        cb2 = QPushButton("Test")
        cb2.setObjectName("sm")
        cb2.clicked.connect(self.test_claude)
        c.addWidget(cb2)
        tl.addLayout(c)
        
        layout.addWidget(top)
        
        content = QWidget()
        cl = QHBoxLayout(content)
        cl.setContentsMargins(16,16,16,16)
        cl.setSpacing(16)
        
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0,0,0,0)
        ll.setSpacing(8)
        ll.addWidget(QLabel("📋 Available Backups"))
        
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(4)
        self.tbl.setHorizontalHeaderLabels(["Name", "Created", "Size", "Current"])
        self.tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self.ctx_menu)
        self.tbl.doubleClicked.connect(self.open_sel)
        ll.addWidget(self.tbl)
        
        cl.addWidget(left, 2)
        
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0,0,0,0)
        rl.setSpacing(12)
        rl.addWidget(QLabel("⚡ Actions"))
        rl.addWidget(QLabel("New Backup"))
        self.name = QLineEdit("claude")
        rl.addWidget(self.name)
        cb = QPushButton("✓ Create")
        cb.setObjectName("success")
        cb.clicked.connect(self.do_create)
        rl.addWidget(cb)
        rl.addSpacing(20)
        # Tip: use right-click on the table
        tip = QLabel("Tip: Right-click a backup row to Restore / Open / Delete")
        tip.setWordWrap(True)
        rl.addWidget(tip)
        rl.addSpacing(16)
        
        # Claude status card
        status_card = QGroupBox("Claude Status")
        sl = QVBoxLayout(status_card)
        self.status_label = QLabel("Detecting…")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sl.addWidget(self.status_label)
        self.stop_btn = QPushButton("Terminate Claude")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self.stop_claude)
        sl.addWidget(self.stop_btn)
        rl.addWidget(status_card)
        rl.addStretch()
        
        cl.addWidget(right, 1)
        
        layout.addWidget(content, 1)
        
        log_w = QWidget()
        log_w.setObjectName("logbar")
        logl = QVBoxLayout(log_w)
        logl.setContentsMargins(16,8,16,8)
        logl.setSpacing(4)
        logl.addWidget(QLabel("📝 Activity Log"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        self.log_text.setObjectName("logtext")
        logl.addWidget(self.log_text)
        
        layout.addWidget(log_w)
    
    def log(self, msg):
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    def load_backups(self):
        self.log("Loading...")
        self.tbl.setRowCount(0)
        try:
            bs = list_backups()
            cur = None
            try:
                cur = config.get_current_backup()
            except Exception:
                cur = None
            self.tbl.setRowCount(len(bs))
            for i, b in enumerate(bs):
                self.tbl.setItem(i, 0, QTableWidgetItem(b["name"]))
                d = QTableWidgetItem(b["created"].strftime("%Y-%m-%d %H:%M"))
                d.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl.setItem(i, 1, d)
                s = QTableWidgetItem(get_size_str(b["size"]))
                s.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl.setItem(i, 2, s)
                ctext = "Current" if cur and b["name"] == cur else ""
                c = QTableWidgetItem(ctext)
                c.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tbl.setItem(i, 3, c)
            self.log(f"✓ {len(bs)} backup(s)")
        except Exception as e:
            self.log(f"✗ {e}")
    
    def do_create(self):
        n = self.name.text().strip() or "claude"
        if not n.replace("-","").replace("_","").isalnum():
            QMessageBox.warning(self, "Invalid", "Letters, numbers, - _ only")
            return
        self.log(f"Creating '{n}'...")
        self.worker = Worker(create_backup, n)
        self.worker.finished.connect(self.on_create_ok)
        self.worker.error.connect(self.on_err)
        self.worker.start()
    
    def on_create_ok(self, name):
        self.log(f"✓ {name}")
        QMessageBox.information(self, "Success", f"Created:\n{name}")
        self.load_backups()
    
    def do_restore(self):
        r = self.tbl.currentRow()
        if r < 0:
            QMessageBox.warning(self, "No Selection", "Select a backup")
            return
        n = self.tbl.item(r, 0).text()
        
        # single-prompt flow
        if is_claude_running():
            reply = QMessageBox.question(
                self,
                "Claude is Running",
                "Claude is currently running. Close Claude now and continue restore?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.log("✗ Restore cancelled (Claude running)")
                return
            self.log("Closing Claude...")
            count = terminate_claude()
            if count > 0:
                self.log(f"✓ Claude terminated ({count})")
                time.sleep(0.5)
            else:
                self.log("⚠ No Claude process found")
        else:
            if QMessageBox.question(self, "Restore", f"Restore '{n}'? This will replace current data.") != QMessageBox.StandardButton.Yes:
                return
        
        self.log(f"Restoring '{n}'...")
        self.worker = Worker(restore_backup, n)
        self.worker.finished.connect(lambda: self.on_restore_ok(n))
        self.worker.error.connect(self.on_err)
        self.worker.start()
    
    def on_restore_ok(self, n):
        # mark current backup
        try:
            config.set_current_backup(n)
        except Exception:
            pass
        self.log(f"✓ Restored: {n}")
        self.load_backups()
        
        # Ask to restart Claude (no extra success popups)
        reply = QMessageBox.question(
            self,
            "Restore Complete",
            "Restore successful. Start Claude now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.log("Starting Claude...")
            start_claude()
    
    def do_delete(self):
        r = self.tbl.currentRow()
        if r < 0:
            QMessageBox.warning(self, "No Selection", "Select a backup")
            return
        n = self.tbl.item(r, 0).text()
        if QMessageBox.question(self, "Delete", f"Delete '{n}'?\n\nCannot be undone!") != QMessageBox.StandardButton.Yes:
            return
        self.log(f"Deleting '{n}'...")
        self.worker = Worker(delete_backup, n)
        self.worker.finished.connect(lambda: self.on_delete_ok(n))
        self.worker.error.connect(self.on_err)
        self.worker.start()
    
    def on_delete_ok(self, n):
        self.log(f"✓ Deleted: {n}")
        QMessageBox.information(self, "Success", "Deleted!")
        self.load_backups()
    
    def on_err(self, e):
        self.log(f"✗ {e}")
        QMessageBox.critical(self, "Error", e)
    
    def update_status(self):
        running = is_claude_running()
        if running:
            self.status_label.setText("Claude is Running")
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("Claude is Stopped")
            self.stop_btn.setEnabled(False)
    
    def stop_claude(self):
        if is_claude_running():
            self.log("Terminating Claude...")
            count = terminate_claude()
            self.log(f"✓ Terminated {count} process(es)")
            self.update_status()
        else:
            self.log("No Claude process running")
    
    def browse_source(self):
        p = QFileDialog.getExistingDirectory(self, "Select Source", config.get_source_dir())
        if p:
            config.set_source_dir(p)
            self.src.setText(p)
            self.log(f"Source: {p}")
    
    def browse_backup(self):
        p = QFileDialog.getExistingDirectory(self, "Select Backup", config.get_backup_dir())
        if p:
            config.set_backup_dir(p)
            self.bak.setText(p)
            self.log(f"Backup: {p}")
            self.load_backups()
    
    def browse_claude(self):
        p, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Claude Executable/Shortcut", 
            config.get_claude_path(),
            "Executables (*.exe *.lnk);;All Files (*.*)"
        )
        if p:
            config.set_claude_path(p)
            self.claude.setText(p)
            self.log(f"Claude path: {p}")
    
    def test_claude(self):
        self.log("Testing Claude path...")
        if start_claude():
            self.log("✓ Claude start invoked")
        else:
            self.log("✗ Failed to start Claude")
            QMessageBox.warning(self, "Error", "Could not start Claude\n\nCheck the path in config")
    
    def open_sel(self):
        r = self.tbl.currentRow()
        if r >= 0:
            n = self.tbl.item(r, 0).text()
            subprocess.run(["explorer", str(Path(config.get_backup_dir()) / n)])
            self.log(f"Opened: {n}")
    
    def ctx_menu(self, pos):
        if self.tbl.itemAt(pos):
            m = QMenu(self)
            m.addAction("🔄 Restore", self.do_restore)
            m.addAction("📂 Open", self.open_sel)
            m.addSeparator()
            m.addAction("🗑 Delete", self.do_delete)
            m.exec(self.tbl.mapToGlobal(pos))
    
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow,QWidget{background:#1a1a1a;color:#e0e0e0;font-family:'Segoe UI';font-size:10pt}
            QWidget#topbar{background:#252525;border-bottom:2px solid #3b82f6}
            QWidget#logbar{background:#1f1f1f;border-top:1px solid #333}
            QLabel{color:#e0e0e0}
            QLineEdit{background:#2d2d2d;color:#e0e0e0;border:1px solid #404040;border-radius:4px;padding:6px}
            QLineEdit:read-only{background:#252525;color:#888}
            QTextEdit#logtext{background:#0d0d0d;color:#888;border:1px solid #333;border-radius:4px;font-family:'Consolas';font-size:9pt}
            QPushButton{padding:10px;border-radius:6px;font-weight:bold;background:#2d2d2d;color:#e0e0e0;border:1px solid #404040}
            QPushButton:hover{background:#3a3a3a}
            QPushButton#sm{padding:6px 12px;font-size:9pt}
            QPushButton#success{background:#10b981;color:white;border:none}
            QPushButton#success:hover{background:#059669}
            QPushButton#primary{background:#3b82f6;color:white;border:none}
            QPushButton#primary:hover{background:#2563eb}
            QPushButton#danger{background:#ef4444;color:white;border:none}
            QPushButton#danger:hover{background:#dc2626}
            QGroupBox{border:1px solid #333;border-radius:6px;margin-top:12px}
            QGroupBox::title{subcontrol-origin: margin; left:10px; padding:0 4px}
            QTableWidget{background:#1a1a1a;alternate-background-color:#252525;border:1px solid #333;gridline-color:#2d2d2d}
            QTableWidget::item{padding:8px}
            QTableWidget::item:selected{background:#3b82f6;color:white}
            QHeaderView::section{background:#2d2d2d;color:#e0e0e0;padding:8px;border:none;border-bottom:2px solid #3b82f6;font-weight:bold}
            QMenuBar{background:#252525;color:#e0e0e0;border-bottom:1px solid #333;padding:4px}
            QMenuBar::item{padding:6px 12px}
            QMenuBar::item:selected{background:#3b82f6}
            QMenu{background:#2d2d2d;color:#e0e0e0;border:1px solid #404040}
            QMenu::item{padding:6px 30px 6px 10px}
            QMenu::item:selected{background:#3b82f6}
            QScrollBar:vertical{background:#1a1a1a;width:12px}
            QScrollBar::handle:vertical{background:#404040;border-radius:6px}
            QScrollBar::handle:vertical:hover{background:#555}
        """)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = App()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
