# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_dynamic_libs

# Get the project root directory
import sys
from PyInstaller.utils.hooks import copy_metadata, collect_data_files, collect_dynamic_libs

# Get the project root directory
project_root = os.path.abspath('.')

# Data files to include
datas = [
    ('haarcascade_frontalface_default.xml', '.'),
]

# PySide6 ve Qt DLL'lerini topla
qt_dlls = collect_dynamic_libs('PySide6')
pyside_data = collect_data_files('PySide6')
shiboken_data = collect_data_files('shiboken6')

# Metadata ve DLL'leri dahil et (Windows için gerekli)
datas += copy_metadata('replicate')
datas += copy_metadata('PySide6')
datas += copy_metadata('shiboken6')
datas += qt_dlls
datas += pyside_data
datas += shiboken_data

# Hidden imports - replicate ve PySide6 için gerekli modüller
hiddenimports = [
    'cv2',
    'PIL',
    'numpy',
    'requests',
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    'PySide6.QtNetwork',
    'replicate',
    'replicate.__about__',
    'replicate.client',
    'importlib.metadata',
    'importlib.metadata._adapters',
    'importlib.metadata._collections',
    'importlib.metadata._compat',
    'importlib.metadata._functools',
    'importlib.metadata._itertools',
    'importlib.metadata._meta',
    'importlib.metadata._text',
    'importlib.metadata._typing',
    'importlib.metadata._zip',
    'pkg_resources',
    'setuptools',
    'packaging',
    'packaging.version',
    'packaging.specifiers',
    'packaging.requirements',
]

a = Analysis(
    ['desktop_app.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BiyoVes',
    icon=os.path.join(project_root, 'appicon.icns') if sys.platform == 'darwin' else os.path.join(project_root, 'appicon.ico'),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=False,  # Use onedir mode
)