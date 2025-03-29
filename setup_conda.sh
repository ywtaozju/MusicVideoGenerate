#!/bin/bash

echo "歌单视频生成器 - 环境配置工具"
echo "=============================="
echo

# 检查conda是否安装
if ! command -v conda &> /dev/null
then
    echo "错误: 未找到conda。请确保已安装Anaconda或Miniconda，并将其添加到PATH中。"
    exit 1
fi

echo "正在创建精简的conda环境..."
conda env create -f environment.yml

if [ $? -ne 0 ]; then
    echo "创建环境失败，尝试更新现有环境..."
    conda env update -f environment.yml
    if [ $? -ne 0 ]; then
        echo "环境更新失败。"
        exit 1
    fi
fi

echo
echo "环境设置完成！"
echo
echo "使用说明:"
echo "1. 激活环境: conda activate music-video-min"
echo "2. 运行程序: python main.py"
echo
echo "提示: 本程序需要安装FFmpeg，请确保FFmpeg已添加到系统PATH中"

# 使脚本可执行
chmod +x add_lyrics.py 