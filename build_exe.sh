#!/bin/bash

echo "开始在conda环境中构建歌单视频生成器可执行文件..."

# 检查是否存在conda命令
if ! command -v conda &> /dev/null; then
    echo "错误: 未找到conda命令。请确保已安装Anaconda或Miniconda并添加到PATH中。"
    exit 1
fi

# 检查是否存在music-video-gen环境
if ! conda env list | grep -q "music-video-gen"; then
    echo "未找到music-video-gen环境，尝试创建..."
    echo "如果您已经有其他环境用于此项目，请手动运行下面的命令："
    echo "conda activate 您的环境名称"
    echo "python musicvideo_build.py"
    
    # 询问是否创建新环境
    read -p "是否创建新环境music-video-gen? (y/n): " CREATE_ENV
    if [[ $CREATE_ENV == "y" ]]; then
        echo "创建conda环境中..."
        conda env create -f environment.yml
        if [ $? -ne 0 ]; then
            echo "创建环境失败，请检查environment.yml文件。"
            exit 1
        fi
    else
        echo "请手动管理您的conda环境后再运行此脚本。"
        exit 1
    fi
fi

# 激活conda环境
echo "激活conda环境: music-video-gen"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate music-video-gen

if [ $? -ne 0 ]; then
    echo "激活conda环境失败。"
    exit 1
fi

# 运行打包脚本
echo "在conda环境中运行打包脚本..."
python musicvideo_build.py

# 完成后输出信息
echo ""
echo "构建过程已完成。" 