@echo off
echo 正在为歌单视频生成器创建conda环境...

REM 检查是否安装了conda
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到conda。请先安装Anaconda或Miniconda。
    echo 您可以从 https://www.anaconda.com/download/ 下载。
    pause
    exit /b 1
)

REM 创建新的conda环境
echo 创建名为music-video-gen的新环境...
call conda env create -f environment.yml

if %errorlevel% neq 0 (
    echo 创建环境时出错，请检查environment.yml文件。
    pause
    exit /b 1
)

echo 环境已成功创建！

REM 激活环境并验证FFmpeg
echo 正在验证FFmpeg...
call conda activate music-video-gen
python check_ffmpeg.py

if %errorlevel% neq 0 (
    echo.
    echo ⚠️警告: FFmpeg未安装或未添加到PATH。
    echo 请从 https://ffmpeg.org/download.html 下载并安装FFmpeg，
    echo 并确保将其添加到系统PATH中。
    echo.
)

echo.
echo 设置已完成! 从现在开始，请使用以下命令来使用此程序:
echo.
echo   conda activate music-video-gen
echo   python main.py
echo.
echo 如果需要添加歌词到音频文件，可以使用:
echo   python add_lyrics.py 音频文件.mp3 歌词文件.lrc
echo.

pause 