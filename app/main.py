import sys
import traceback
import ctypes

def _msgbox(title, text):
    try:
        ctypes.windll.user32.MessageBoxW(None, str(text), str(title), 0x00000010)
    except Exception:
        pass

try:
    # Prefer absolute import for PyInstaller compatibility
    try:
        from app.gui import main
    except ImportError:
        from gui import main

    if __name__ == "__main__":
        main()
except ImportError as e:
    _msgbox("Import Error", f"{e}\n\nMake sure dependencies are bundled. (PyQt6)")
    sys.exit(1)
except Exception as e:
    tb = traceback.format_exc()
    _msgbox("Fatal Error", f"{e}\n\n{tb}")
    sys.exit(1)
