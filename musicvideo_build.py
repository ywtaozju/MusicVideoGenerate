#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyInstaller打包脚本 - 歌单视频生成器 (Conda环境版)
"""

import os
import subprocess
import shutil
import sys
import platform

def create_exe():
    print("开始创建歌单视频生成器的可执行文件 (使用Conda环境)...")
    
    # 检查是否在conda环境中
    in_conda = os.environ.get('CONDA_PREFIX') is not None
    if not in_conda:
        print("警告: 当前不在conda环境中运行。建议在conda环境中运行此脚本。")
        response = input("是否继续? (y/n): ")
        if response.lower() != 'y':
            print("退出脚本。请在conda环境中运行。")
            return
    
    # 检查是否安装了PyInstaller
    try:
        import PyInstaller
        print(f"已安装PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("正在安装PyInstaller...")
        subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 确保所有依赖都已安装
    print("安装必要的依赖...")
    subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # 添加缺少的依赖（如果requirements.txt中没有）
    missing_deps = ["mutagen", "eyed3"]
    for dep in missing_deps:
        print(f"安装依赖: {dep}")
        subprocess.call([sys.executable, "-m", "pip", "install", dep])
    
    # 获取conda环境路径，添加到pathex中
    conda_prefix = os.environ.get('CONDA_PREFIX', '')
    pathex = []
    if conda_prefix:
        # 添加conda环境的site-packages路径
        if platform.system() == 'Windows':
            site_packages = os.path.join(conda_prefix, 'Lib', 'site-packages')
        else:
            python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = os.path.join(conda_prefix, 'lib', python_version, 'site-packages')
        
        if os.path.exists(site_packages):
            pathex.append(site_packages)
            print(f"添加conda环境路径: {site_packages}")
    
    # 首先创建runtime_hook来处理ffmpeg的控制台窗口问题
    os.makedirs("hooks", exist_ok=True)
    hook_content = """
# hook用于隐藏子进程的控制台窗口
import subprocess
import sys

# 如果在Windows上，修改subprocess.Popen类，默认添加隐藏控制台窗口的标志
if sys.platform == 'win32':
    # 保存原始的Popen构造函数
    original_popen_init = subprocess.Popen.__init__
    
    # 创建一个新的初始化函数，它会添加隐藏窗口的标志
    def popen_init_no_window(self, *args, **kwargs):
        # 如果没有指定creationflags，添加CREATE_NO_WINDOW标志
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        # 调用原始初始化函数
        original_popen_init(self, *args, **kwargs)
    
    # 替换原始的初始化函数
    subprocess.Popen.__init__ = popen_init_no_window
"""
    
    with open("hooks/subprocess_hook.py", "w", encoding="utf-8") as f:
        f.write(hook_content)
    
    # 创建临时spec文件
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex={pathex},
    binaries=[],
    datas=[],
    hiddenimports=['PIL._tkinter_finder', 'mutagen.id3', 'mutagen.mp3', 'mutagen.flac', 'mutagen.wave', 'mutagen.asf', 'mutagen.mp4', 'eyed3'],
    hookspath=['hooks'],
    hooksconfig={{}},
    runtime_hooks=['hooks/subprocess_hook.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 添加资源文件和依赖模块
a.datas += [
    ('check_ffmpeg.py', 'check_ffmpeg.py', 'DATA'),
    ('lrc_parser.py', 'lrc_parser.py', 'DATA'),
    ('add_lyrics.py', 'add_lyrics.py', 'DATA'),
]

# 如果有自定义图标，可以添加
# a.datas += [('icon.ico', 'icon.ico', 'DATA')]

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
    icon=None,  # 如果有自定义图标，可以设置为'icon.ico'
)
"""
    
    # 写入spec文件
    with open("musicvideo.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    # 创建必要的文件夹
    os.makedirs("dist", exist_ok=True)
    
    # 使用PyInstaller构建可执行文件
    print("开始使用PyInstaller构建可执行文件...")
    if platform.system() == 'Windows':
        # Windows系统上使用shell=True以确保conda环境变量生效
        subprocess.call("pyinstaller musicvideo.spec --clean", shell=True)
    else:
        subprocess.call(["pyinstaller", "musicvideo.spec", "--clean"])
    
    # 复制必要的资源文件夹到dist目录
    resource_folders = ["lyrics", "music", "bg", "bg1", "output"]
    for folder in resource_folders:
        if os.path.exists(folder):
            target_folder = os.path.join("dist", "歌单视频生成器", folder)
            os.makedirs(target_folder, exist_ok=True)
            print(f"创建资源文件夹: {folder}")
    
    print("\n构建完成!")
    print("可执行文件已创建在 dist/歌单视频生成器 目录中")
    print("注意: 您仍然需要确保安装了FFmpeg并添加到系统PATH中才能正常使用程序")

if __name__ == "__main__":
    create_exe() 