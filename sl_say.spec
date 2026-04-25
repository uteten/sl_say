# -*- mode: python ; coding: utf-8 -*-
import os
import sys

_icon_icns = 'app/icon.icns'
_icon_ico = 'app/icon.ico'
_mac_icon = _icon_icns if os.path.exists(_icon_icns) else None

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=[('app/icon.ico', 'app')],
    hiddenimports=[
        'edge_tts',
        'aiohttp',
        'certifi',
        'app.config_store',
        'app.startup_form',
        'app.filter_config',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='sl_say',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
    )
    app = BUNDLE(
        exe,
        name='sl_say.app',
        icon=_mac_icon,
        bundle_identifier='com.example.sl_say',
        info_plist={
            'CFBundleName': 'sl_say',
            'CFBundleDisplayName': 'sl_say',
            'CFBundleVersion': '0.1.0',
            'CFBundleShortVersionString': '0.1.0',
            'NSHighResolutionCapable': True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='sl_say',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon=_icon_ico,
        version='version_info.txt',
    )
