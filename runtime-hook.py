import os# runtime-hook.py

import sysimport os

import sys

# PyInstaller tarafından oluşturulan _MEIPASS değişkenini kontrol et

if hasattr(sys, '_MEIPASS'):# PyInstaller'ın onefile modunda oluşturduğu geçici dizin

    # Qt plugin dizinini ayarla# sys._MEIPASS, programın çalıştığı geçici klasörün yolunu verir.

    qt_plugin_path = os.path.join(sys._MEIPASS, 'PySide6', 'plugins')if hasattr(sys, '_MEIPASS'):

    if os.path.exists(qt_plugin_path):    # Qt'nin eklentileri (platforms, styles, etc.) bulabilmesi için

        os.environ['QT_PLUGIN_PATH'] = qt_plugin_path    # QT_PLUGIN_PATH environment değişkenini ayarla.

    # PySide6'nın eklentileri genellikle PySide6/plugins altında olur.

    # Qt DLL dizinini PATH'e ekle    plugin_path = os.path.join(sys._MEIPASS, 'PySide6', 'plugins')

    qt_bin_path = os.path.join(sys._MEIPASS, 'PySide6')    os.environ['QT_PLUGIN_PATH'] = plugin_path

    if os.path.exists(qt_bin_path):    

        if 'PATH' in os.environ:    # Bazı durumlarda Qt'nin kendi dosyalarını da bulması gerekebilir.

            os.environ['PATH'] = qt_bin_path + os.pathsep + os.environ['PATH']    # Bu yüzden PySide6 klasörünü de yola eklemek faydalı olabilir.

        else:    pyside_path = os.path.join(sys._MEIPASS, 'PySide6')

            os.environ['PATH'] = qt_bin_path    os.environ['PATH'] = f"{pyside_path}{os.pathsep}{os.environ['PATH']}"
