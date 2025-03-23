#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
为音频文件添加歌词轨道的工具
这个脚本将LRC或SRT格式的歌词文件作为字幕流添加到音频文件中
"""

import os
import sys
import subprocess
import argparse
import tempfile
import shutil
from check_ffmpeg import check_ffmpeg

def convert_lrc_to_srt(lrc_file, output_file):
    """
    将LRC格式歌词文件转换为SRT格式
    """
    try:
        # 读取LRC文件
        with open(lrc_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # 解析时间标记 [mm:ss.xx]
        import re
        time_pattern = re.compile(r'\[(\d+):(\d+)\.(\d+)\]')
        
        # 存储解析后的歌词
        lyrics = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            matches = time_pattern.findall(line)
            if not matches:
                continue
            
            # 提取歌词文本
            text = time_pattern.sub('', line).strip()
            if not text:
                continue
            
            # 处理每个时间标记
            for match in matches:
                try:
                    minutes = int(match[0])
                    seconds = int(match[1])
                    milliseconds = int(match[2]) * 10  # LRC通常是xx格式，转为xxx毫秒格式
                    
                    # 计算毫秒时间戳
                    time_ms = minutes * 60 * 1000 + seconds * 1000 + milliseconds
                    lyrics.append((time_ms, text))
                except:
                    continue
        
        # 按时间戳排序
        lyrics.sort(key=lambda x: x[0])
        
        # 写入SRT文件
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, (time_ms, text) in enumerate(lyrics):
                # 计算结束时间（下一句歌词时间或当前+3秒）
                if i < len(lyrics) - 1:
                    end_time_ms = lyrics[i+1][0]
                else:
                    end_time_ms = time_ms + 3000  # 最后一行显示3秒
                
                # 格式化SRT时间 (HH:MM:SS,mmm)
                start_time = format_srt_time(time_ms)
                end_time = format_srt_time(end_time_ms)
                
                # 写入SRT条目
                f.write(f"{i+1}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
        
        return True
    
    except Exception as e:
        print(f"转换LRC文件出错: {str(e)}")
        return False

def format_srt_time(ms):
    """
    将毫秒转换为SRT时间格式 (HH:MM:SS,mmm)
    """
    hours = ms // (3600 * 1000)
    ms %= 3600 * 1000
    minutes = ms // (60 * 1000)
    ms %= 60 * 1000
    seconds = ms // 1000
    ms %= 1000
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"

def add_lyrics_to_audio(audio_file, lyrics_file, output_file=None):
    """
    向音频文件添加歌词
    """
    try:
        # 检查FFmpeg是否可用
        if not check_ffmpeg():
            print("未找到FFmpeg，请先安装FFmpeg")
            return False
        
        # 确定输出文件名
        if not output_file:
            base_name = os.path.splitext(audio_file)[0]
            ext = os.path.splitext(audio_file)[1]
            output_file = f"{base_name}_with_lyrics{ext}"
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 检查歌词文件格式并处理
            lyrics_ext = os.path.splitext(lyrics_file)[1].lower()
            srt_file = lyrics_file
            
            # 如果是LRC格式，转换为SRT
            if lyrics_ext == '.lrc':
                srt_file = os.path.join(temp_dir, os.path.basename(lyrics_file).replace('.lrc', '.srt'))
                if not convert_lrc_to_srt(lyrics_file, srt_file):
                    print("转换LRC文件失败")
                    return False
            
            # 添加字幕流到音频
            command = [
                'ffmpeg',
                '-i', audio_file,  # 输入音频
                '-f', 'srt',       # 指定字幕格式
                '-i', srt_file,    # 输入字幕
                '-c:a', 'copy',    # 复制音频流
                '-c:s', 'mov_text', # 字幕编码格式
                '-metadata:s:s:0', 'language=eng', # 设置字幕语言
                '-y',              # 覆盖现有文件
                output_file        # 输出文件
            ]
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            _, stderr = process.communicate()
            
            if process.returncode != 0:
                stderr_text = stderr.decode('utf-8', errors='ignore')
                print(f"添加歌词出错: {stderr_text}")
                return False
            
            print(f"成功添加歌词！输出文件: {output_file}")
            return True
            
    except Exception as e:
        print(f"添加歌词过程中出错: {str(e)}")
        return False

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='为音频文件添加歌词轨道')
    parser.add_argument('audio_file', help='输入的音频文件路径')
    parser.add_argument('lyrics_file', help='歌词文件路径(.lrc或.srt格式)')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.audio_file):
        print(f"错误: 音频文件 '{args.audio_file}' 不存在")
        return 1
    
    if not os.path.exists(args.lyrics_file):
        print(f"错误: 歌词文件 '{args.lyrics_file}' 不存在")
        return 1
    
    # 添加歌词
    if add_lyrics_to_audio(args.audio_file, args.lyrics_file, args.output):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main()) 