#!/bin/bash

echo "正在为歌单视频生成器创建conda环境..."

# 检查是否安装了conda
if ! command -v conda &> /dev/null; then
    echo "错误: 未找到conda。请先安装Anaconda或Miniconda。"
    echo "您可以从 https://www.anaconda.com/download/ 下载。"
    exit 1
fi

# 创建新的conda环境
echo "创建名为music-video-gen的新环境..."
conda env create -f environment.yml

if [ $? -ne 0 ]; then
    echo "创建环境时出错，请检查environment.yml文件。"
    exit 1
fi

echo "环境已成功创建！"

# 激活环境并验证FFmpeg
echo "正在验证FFmpeg..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate music-video-gen
python check_ffmpeg.py

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️警告: FFmpeg未安装或未添加到PATH。"
    echo "请从 https://ffmpeg.org/download.html 下载并安装FFmpeg，"
    echo "并确保将其添加到系统PATH中。"
    echo ""
fi

echo ""
echo "设置已完成! 从现在开始，请使用以下命令来使用此程序:"
echo ""
echo "  conda activate music-video-gen"
echo "  python main.py"
echo ""
echo "如果需要添加歌词到音频文件，可以使用:"
echo "  python add_lyrics.py 音频文件.mp3 歌词文件.lrc"
echo "" 