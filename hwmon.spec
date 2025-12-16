# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for HW Monitor."""

from PyInstaller.utils.hooks import collect_submodules

hwmon_modules = collect_submodules('hwmon')

excludes = [
    # Network/crypto
    'ssl', '_ssl', 'hashlib', '_hashlib',
    'email', 'http', 'urllib', 'ftplib', 'smtplib', 'imaplib', 'poplib',
    'xmlrpc', 'html', 'xml',
    # Testing/debugging
    'unittest', 'pytest', 'doctest', 'pdb', 'profile', 'cProfile',
    # Unused stdlib
    'sqlite3', 'asyncio', 'concurrent', 'multiprocessing',
    'logging', 'argparse', 'getopt', 'optparse',
    'pydoc', 'tarfile', 'gzip',
    'csv', 'configparser', 'json',  # if not using these
    'decimal', 'fractions', 'statistics',
    'calendar', 'gettext', 'locale',
    # Platform-specific
    'curses', 'readline', 'rlcompleter',
    # Tkinter extras
    'tkinter.tix', 'tkinter.scrolledtext',
]

a = Analysis(
    ['hwmon/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hwmon_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='hwmon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
