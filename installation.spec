# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('ascii_art', 'ascii_art'),
        ('audio', 'audio'),
        ('crafting.json', '.'),
        ('items.json', '.'),
        ('ships.json', '.'),
        ('system_data.json', '.'),
        ('colors.py', '.'),
    ],
    hiddenimports=['pypresence', 'pygame'],
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
    a.binaries,
    a.datas,
    [],
    name='starscape_text_adventure',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
