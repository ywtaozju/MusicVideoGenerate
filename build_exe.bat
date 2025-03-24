@echo off
echo 开始在conda环境中构建歌单视频生成器可执行文件...

REM 检查是否存在conda环境
call conda --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到conda命令。请确保已安装Anaconda或Miniconda并添加到PATH中。
    pause
    exit /b 1
)

REM 检查是否存在music-video-gen环境
call conda env list | findstr "music-video-gen" > nul
if %ERRORLEVEL% NEQ 0 (
    echo 未找到music-video-gen环境，尝试创建...
    echo 如果您已经有其他环境用于此项目，请手动运行下面的命令：
    echo conda activate 您的环境名称
    echo python musicvideo_build.py
    
    REM 询问是否创建新环境
    set /p CREATE_ENV=是否创建新环境music-video-gen? (y/n): 
    if /i "%CREATE_ENV%"=="y" (
        echo 创建conda环境中...
        call conda env create -f environment.yml
        if %ERRORLEVEL% NEQ 0 (
            echo 创建环境失败，请检查environment.yml文件。
            pause
            exit /b 1
        )
    ) else (
        echo 请手动管理您的conda环境后再运行此脚本。
        pause
        exit /b 1
    )
)

REM 激活conda环境
echo 激活conda环境: music-video-gen
call conda activate music-video-gen

if %ERRORLEVEL% NEQ 0 (
    echo 激活conda环境失败。
    pause
    exit /b 1
)

REM 运行打包脚本
echo 在conda环境中运行打包脚本...
python musicvideo_build.py

REM 完成后暂停
echo.
echo 构建过程已完成。
pause 