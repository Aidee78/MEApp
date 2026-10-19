# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden_imports = []
hidden_imports += collect_submodules("meapp")
hidden_imports += collect_submodules("dateparser")
hidden_imports += collect_submodules("rapidfuzz")

a = Analysis(
["src/meapp/__main__.py"],
pathex=["src"],
binaries=[],
datas=[],
hiddenimports=hidden_imports,
hookspath=[],
hooksconfig={},
runtime_hooks=[],
excludes=[],
noarchive=False,
optimize=0,
)

pyz = PYZ(
a.pure,
a.zipped_data,
cipher=block_cipher,
)

exe = EXE(
pyz,
a.scripts,
[],
exclude_binaries=True,
name="MEApp",
debug=False,
bootloader_ignore_signals=False,
strip=False,
upx=False,
console=True,
disable_windowed_traceback=False,
argv_emulation=False,
target_arch=None,
codesign_identity=None,
entitlements_file=None,
)

coll = COLLECT(
exe,
a.binaries,
a.zipfiles,
a.datas,
strip=False,
upx=False,
name="MEApp",
)
