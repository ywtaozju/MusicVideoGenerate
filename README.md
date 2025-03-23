# 歌单视频生成器

这是一个使用Python和ffmpeg制作歌单视频的图形界面工具，它可以批量将音乐文件转换为带有静态图片、歌名和歌词的视频。

## 功能特点

- 批量处理多个音乐文件
- 使用自定义封面图片
- 在视频中显示歌曲名称和艺术家信息
- 自动从音频文件中提取歌词（如果音频包含歌词轨道）
- 用户友好的图形界面
- 实时显示处理进度

## 安装要求

1. Python 3.6或更高版本
2. FFmpeg（需要预先安装并添加到系统PATH中）
3. 必要的Python库（在requirements.txt中列出）

## 安装步骤

### 方法一：使用pip安装

1. 确保已安装FFmpeg并添加到系统PATH中（[下载FFmpeg](https://ffmpeg.org/download.html)）
2. 安装必要的Python库：
   ```
   pip install -r requirements.txt
   ```

### 方法二：使用conda环境（推荐）

1. 确保已安装Anaconda或Miniconda（[下载链接](https://www.anaconda.com/download/)）
2. 使用提供的脚本创建和设置conda环境：

   Windows系统:
   ```
   setup_conda.bat
   ```

   Linux/MacOS系统:
   ```
   chmod +x setup_conda.sh
   ./setup_conda.sh
   ```

3. 脚本将为您创建名为"music-video-gen"的环境，并安装所有必要的依赖项
4. 创建环境后，脚本会检查FFmpeg是否已安装，如果没有安装，您需要手动安装

## 使用方法

1. 如果使用conda环境，首先激活环境：
   ```
   conda activate music-video-gen
   ```

2. 运行程序：
   ```
   python main.py
   ```
   
   或首先检查FFmpeg是否已安装：
   ```
   python check_ffmpeg.py
   ```
   
3. 使用界面选择：
   - 音乐文件（支持mp3、wav、flac等格式）
   - 封面图片（将用作视频的静态背景）
   - 输出目录（生成的视频将保存在此处）
4. 选项设置：
   - 可以选择是否在视频中显示歌词（如果音频文件中包含歌词轨道）
5. 点击"生成视频"按钮开始处理
6. 等待处理完成，进度条会显示当前进度

## 注意事项

- 程序会自动从音频文件中读取标题、艺术家和歌词信息
- 如果音频文件不包含歌词轨道，视频将只显示歌曲名称
- 推荐使用高分辨率图片（至少1920x1080）作为封面，以获得最佳效果
- 处理时间取决于音频文件的长度和数量

## 支持的歌词格式

程序会自动提取音频文件中的歌词轨道。常见的歌词包含形式有：
- MP3文件中的同步歌词（Synchronized Lyrics）
- 包含内嵌字幕轨道的音频文件

## 为音频文件添加歌词

如果您的音频文件没有内置歌词，可以使用项目提供的`add_lyrics.py`工具将LRC或SRT格式的歌词文件添加到音频中：

```
python add_lyrics.py 音频文件.mp3 歌词文件.lrc
```

或者指定输出文件：

```
python add_lyrics.py 音频文件.mp3 歌词文件.lrc -o 输出文件.mp3
```

添加歌词后的音频文件可以直接用于歌单视频生成器，程序将自动检测并显示歌词。

## 故障排除

如果遇到错误：
1. 确保FFmpeg已正确安装并添加到系统PATH
2. 检查音乐文件和图片的格式是否受支持
3. 如果需要显示歌词，确认您的音频文件中确实包含歌词轨道
4. 运行`python check_ffmpeg.py`验证FFmpeg安装是否正确
5. 如果使用conda环境，确保已激活正确的环境：`conda activate music-video-gen` 