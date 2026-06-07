# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/resources/logo.png', 'app/resources'),
        ('app/resources/logo.icns', 'app/resources'),
    ],
    hiddenimports=[
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.QtNetwork',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cheat-buster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/resources/logo.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Cheat Buster',
)

app = BUNDLE(
    coll,
    name='cheat-buster.app',
    icon='app/resources/logo.icns',
    bundle_identifier='com.cheat-buster.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
