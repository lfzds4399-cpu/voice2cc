# PyInstaller spec for voice2cc Windows build.
# Build:  pyinstaller build_tools/voice2cc.spec --clean --noconfirm
# Output: dist/voice2cc/voice2cc.exe (folder mode — startup is faster than --onefile)
#
# Notes:
#   - We use folder mode because --onefile triggers Win Defender heuristics on unsigned bundles
#     more aggressively, and adds 2-3s startup tax for every launch.
#   - Tk/sounddevice/pynput need their data files; we let PyInstaller auto-collect.

# ruff: noqa
block_cipher = None

a = Analysis(
    ['..\\app.py'],
    pathex=['..', '..\\src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'voice2cc',
        'voice2cc.main',
        'voice2cc.providers.siliconflow',
        'voice2cc.providers.openai',
        'voice2cc.providers.groq',
        'voice2cc.providers.azure',
        'voice2cc.ui.floating',
        'voice2cc.ui.tray',
        'voice2cc.ui.wizard',
        'voice2cc.ui.settings_dialog',
        'pystray._win32',
        'PIL.ImageDraw',
        'sounddevice',
        '_sounddevice',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pandas', 'scipy', 'IPython', 'jupyter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='voice2cc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # window-only — no flashing console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='voice2cc',
)
