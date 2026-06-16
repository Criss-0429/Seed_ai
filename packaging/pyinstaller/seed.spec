# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['../../build_entry.py'],
    pathex=['../..'],
    binaries=[],
    datas=[('../../seed/ui/surface', 'seed/ui/surface'), ('../../assets', 'assets')],
    hiddenimports=['tiktoken_ext.openai_public'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SEED',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='../../assets/seed.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='SEED',
)
