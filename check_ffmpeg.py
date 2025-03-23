import subprocess
import sys
import os

def check_ffmpeg():
    """
    检查系统中是否安装了FFmpeg
    """
    try:
        # 尝试运行ffmpeg -version命令
        process = subprocess.Popen(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, _ = process.communicate()
        
        if process.returncode == 0:
            # 成功执行，FFmpeg已安装
            version_info = stdout.decode('utf-8', errors='ignore').split('\n')[0]
            print(f"FFmpeg已正确安装: {version_info}")
            return True
        else:
            print("FFmpeg命令执行失败，可能未安装或未添加到PATH中。")
            return False
    
    except FileNotFoundError:
        print("未找到FFmpeg。请确保已安装FFmpeg并添加到系统PATH中。")
        print("下载地址: https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"检查FFmpeg时出错: {str(e)}")
        return False

if __name__ == "__main__":
    if check_ffmpeg():
        print("FFmpeg检查通过。您可以运行歌单视频生成器。")
        print("运行以下命令开始使用: python main.py")
    else:
        print("FFmpeg检查失败。请安装FFmpeg后再使用歌单视频生成器。")
        sys.exit(1) 