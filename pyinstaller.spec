# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

project_root = os.path.abspath('.')

# Data files to include inside the build
# (destination paths are relative to the application root at runtime)
datas = []
# Haar cascade xml
datas.append((os.path.join(project_root, 'haarcascade_frontalface_default.xml'), '.'))
# MODNet checkpoint
datas.append((os.path.join(project_root, 'MODNet', 'pretrained', 'modnet_photographic_portrait_matting.ckpt'), os.path.join('MODNet', 'pretrained')))

# Hidden imports that PyInstaller may miss
hiddenimports = []
hiddenimports += collect_submodules('cv2')
hiddenimports += collect_submodules('PIL')
hiddenimports += collect_submodules('torch')
hiddenimports += collect_submodules('numpy')

block_cipher = None


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
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BiyoVes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
