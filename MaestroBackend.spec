# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/python/maestro_backend.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pkg_resources.py2_warn', 'flask_cors', 'werkzeug', 'jinja2', 'itsdangerous', 'click', 'markupsafe'],
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('v', None, 'OPTION')],
    exclude_binaries=True,
    name='MaestroBackend',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MaestroBackend',
)
app = BUNDLE(
    coll,
    name='MaestroBackend.app',
    icon=None,
    bundle_identifier=None,
)
