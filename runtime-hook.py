import os
import sys

# PyInstaller tarafından oluşturulan _MEIPASS değişkenini kontrol et
if hasattr(sys, '_MEIPASS'):
    # Qt plugin dizinini ayarla
    plugin_path = os.path.join(sys._MEIPASS, 'PySide6', 'plugins')
    if os.path.exists(plugin_path):
        os.environ['QT_PLUGIN_PATH'] = plugin_path

    # Qt DLL dizinini PATH'e ekle
    pyside_path = os.path.join(sys._MEIPASS, 'PySide6')
    if os.path.exists(pyside_path):
        if 'PATH' in os.environ:
            os.environ['PATH'] = f"{pyside_path}{os.pathsep}{os.environ['PATH']}"
        else:
            os.environ['PATH'] = pyside_path
