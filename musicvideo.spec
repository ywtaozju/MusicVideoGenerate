# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['C:\\Users\\Vito\\.conda\\envs\\music-video-gen\\Lib\\site-packages'],
    binaries=[],
    datas=[],
    hiddenimports=['mutagen.id3', 'mutagen.mp3', 'mutagen.flac', 'mutagen.wave', 'mutagen.asf', 'mutagen.mp4', 'eyed3'],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/subprocess_hook.py'],
    excludes=['numpy', 'opencv', 'matplotlib', 'scipy', 'pandas', 'PyQt5', 'PyQt6', 'wx'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 添加资源文件和依赖模块
a.datas += [
    ('check_ffmpeg.py', 'check_ffmpeg.py', 'DATA'),
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='歌单视频生成器',
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
