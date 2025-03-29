import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from PIL import Image, ImageTk, ImageDraw, ImageFont
import json
import tempfile
import uuid
import math
from check_ffmpeg import check_ffmpeg
import re
import urllib.request
import urllib.parse
import urllib.error
import html
from io import BytesIO
# 导入mutagen库用于读取MP3的ID3标签
try:
    from mutagen.id3 import ID3
    from mutagen.mp3 import MP3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("警告: mutagen库未安装，某些MP3元数据功能将受限")

# 导入eyed3库作为备用
try:
    import eyed3
    EYED3_AVAILABLE = True
except ImportError:
    EYED3_AVAILABLE = False
    print("警告: eyed3库未安装，某些MP3标签功能将受限")

import queue
import time

class MusicVideoGenerator:
    def __init__(self, root):
        self.root = root
        
        # 添加鉴权验证
        if not self.verify_authority():
            return
            
        self.root.title("歌单视频生成器")
        self.root.geometry("850x650")
        self.root.minsize(800, 600)  # 设置最小窗口大小
        self.root.configure(bg="#f0f0f0")
        
        self.music_files = []
        self.music_item_frames = []  # 初始化音乐项目框架列表
        self.image_file = ""
        self.image_folder = ""  # 添加图片文件夹路径
        self.image_files = []   # 添加图片文件列表
        self.current_image_index = 0  # 当前使用的图片索引
        self.overlay_image = ""  # 叠加图片路径
        self.output_dir = ""
        self.lyrics_folder = ""  # 歌词文件夹路径
        self.merge_mode = True  # 合并模式标志
        self.use_gpu = False    # 是否使用GPU加速
        self.is_generating = False  # 添加标志跟踪是否正在生成视频
        self.ffmpeg_process = None  # 添加变量存储FFmpeg进程
        
        # 添加字体大小设置
        self.title_font_size = tk.IntVar(value=28)  # 标题字体大小
        self.lyrics_font_size = tk.IntVar(value=24)  # 歌词字体大小
        self.playlist_font_size = tk.IntVar(value=24)  # 播放列表字体大小
        
        # 添加用于跟踪处理时间的变量
        self.start_time = 0
        self.elapsed_time = 0
        self.timer_running = False
        
        # 检查FFmpeg是否安装
        if not check_ffmpeg():
            messagebox.showerror("错误", "未检测到FFmpeg。请安装FFmpeg并确保其在系统PATH中。")
            self.root.destroy()
            return
        
        # 检查是否支持GPU加速
        self.check_gpu_support()
        
        # 创建默认歌词文件夹
        self.create_default_lyrics_folder()
        
        self.setup_ui()
        
        # 添加进度更新队列
        self.progress_queue = queue.Queue()
        # 添加进度更新标志
        self.processing = False
        # 开始进度更新线程
        self.start_progress_monitor()
    
    def verify_authority(self):
        """验证程序使用权限"""
        try:
            # 请求授权文件
            response = urllib.request.urlopen("https://file-1301801484.cos.ap-nanjing.myqcloud.com/Authority/MusicVideoGenerate.txt", timeout=10)
            content = response.read().decode("utf-8").strip()
            
            # 检查权限
            if content == "ok":
                return True
            else:
                # 显示授权信息
                messagebox.showinfo("授权信息", content)
                self.root.destroy()
                return False
                
        except Exception as e:
            # 网络错误或其他异常
            messagebox.showinfo("网络错误", "无法连接到授权服务器，请检查网络连接后重试。")
            self.root.destroy()
            return False
    
    def create_default_lyrics_folder(self):
        """创建默认的歌词文件夹"""
        try:
            # 在当前工作目录下创建lyrics文件夹
            default_lyrics_folder = os.path.join(os.getcwd(), "lyrics")
            if not os.path.exists(default_lyrics_folder):
                os.makedirs(default_lyrics_folder)
            
            self.lyrics_folder = default_lyrics_folder
            print(f"歌词文件夹设置为: {self.lyrics_folder}")
        except Exception as e:
            print(f"创建默认歌词文件夹时出错: {str(e)}")
    
    def check_gpu_support(self):
        """检查系统是否支持GPU加速（NVIDIA NVENC）"""
        try:
            # 使用ffmpeg -encoders命令检查是否支持NVENC
            command = [
                'ffmpeg',
                '-encoders'
            ]
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, _ = process.communicate()
            stdout_text = stdout.decode('utf-8', errors='ignore')
            
            # 检查输出中是否包含NVENC相关的编码器
            if 'h264_nvenc' in stdout_text:
                self.use_gpu = True
                print("已检测到NVIDIA GPU加速支持")
            else:
                self.use_gpu = False
                print("未检测到GPU加速支持，将使用CPU编码")
        
        except Exception as e:
            print(f"检查GPU支持时出错: {str(e)}")
            self.use_gpu = False
    
    def setup_ui(self):
        # 创建主框架，使用滚动条确保所有内容都可以访问
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建带滚动条的画布
        self.main_canvas = tk.Canvas(main_frame, bd=0, highlightthickness=0)
        main_scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.main_canvas.yview)
        
        # 配置画布
        self.main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        # 放置画布和滚动条
        main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建内容框架
        self.content_frame = tk.Frame(self.main_canvas, bg="#f0f0f0")
        self.main_canvas_window = self.main_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        
        # 绑定调整大小事件
        self.content_frame.bind("<Configure>", self.on_content_configure)
        self.main_canvas.bind("<Configure>", self.on_main_canvas_configure)
        
        # 绑定鼠标滚轮事件
        self.main_canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        
        # 选择音乐文件
        music_frame = tk.LabelFrame(self.content_frame, text="选择音乐文件", bg="#f0f0f0", font=("Arial", 12))
        music_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 创建一个带颜色标签的Frame来代替Listbox
        self.music_list_frame = tk.Frame(music_frame)
        self.music_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建一个Canvas和Scrollbar
        self.music_canvas = tk.Canvas(self.music_list_frame, bd=0, highlightthickness=0)
        self.music_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(self.music_list_frame, orient=tk.VERTICAL, command=self.music_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.music_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 创建一个Frame作为Canvas的窗口
        self.music_items_frame = tk.Frame(self.music_canvas, bg="#ffffff")
        self.music_canvas_window = self.music_canvas.create_window((0, 0), window=self.music_items_frame, anchor="nw")
        
        # 绑定调整大小事件
        self.music_items_frame.bind("<Configure>", self.on_frame_configure)
        self.music_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # 传统的Listbox作为备用（不可见）
        self.music_list = tk.Listbox(music_frame, width=70, height=10)
        
        music_btn_frame = tk.Frame(music_frame, bg="#f0f0f0")
        music_btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # 第一行：添加音乐
        btn_row1 = tk.Frame(music_btn_frame, bg="#f0f0f0")
        btn_row1.pack(fill=tk.X, pady=(0, 5))
        
        add_music_btn = tk.Button(btn_row1, text="添加音乐", command=self.add_music, bg="#4CAF50", fg="white", font=("Arial", 10), width=30)
        add_music_btn.pack(padx=2, pady=2)
        
        # 第二行：上移和下移
        btn_row2 = tk.Frame(music_btn_frame, bg="#f0f0f0")
        btn_row2.pack(fill=tk.X, pady=(0, 5))
        
        move_up_btn = tk.Button(btn_row2, text="上移", command=self.move_up, bg="#2196F3", fg="white", font=("Arial", 10), width=15)
        move_up_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        move_down_btn = tk.Button(btn_row2, text="下移", command=self.move_down, bg="#2196F3", fg="white", font=("Arial", 10), width=15)
        move_down_btn.pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        
        # 第三行：移除选中音乐和清空所有
        btn_row3 = tk.Frame(music_btn_frame, bg="#f0f0f0")
        btn_row3.pack(fill=tk.X, pady=(0, 5))
        
        remove_music_btn = tk.Button(btn_row3, text="移除选中音乐", command=self.remove_music, bg="#f44336", fg="white", font=("Arial", 10), width=15)
        remove_music_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        clear_all_btn = tk.Button(btn_row3, text="清空所有音乐", command=self.clear_music_list, bg="#FF5722", fg="white", font=("Arial", 10), width=15)
        clear_all_btn.pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        
        # 第四行：添加歌词和检查歌词
        btn_row4 = tk.Frame(music_btn_frame, bg="#f0f0f0")
        btn_row4.pack(fill=tk.X)
        
        add_lyrics_btn = tk.Button(btn_row4, text="添加歌词", command=self.add_lyrics_to_selected, bg="#9C27B0", fg="white", font=("Arial", 10), width=15)
        add_lyrics_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        check_lyrics_btn = tk.Button(btn_row4, text="检查歌词", command=self.check_selected_lyrics, bg="#FF9800", fg="white", font=("Arial", 10), width=15)
        check_lyrics_btn.pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)
        
        # 选择封面图片
        image_frame = tk.LabelFrame(self.content_frame, text="选择背景图片文件夹", bg="#f0f0f0", font=("Arial", 12))
        image_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.image_label = tk.Label(image_frame, text="未选择背景图片文件夹", bg="#f0f0f0", anchor=tk.W, justify=tk.LEFT, padx=10, wraplength=600)
        self.image_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        select_image_btn = tk.Button(image_frame, text="选择文件夹", command=self.select_image, bg="#2196F3", fg="white", font=("Arial", 10), width=15)
        select_image_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # 添加叠加图片选择
        overlay_frame = tk.LabelFrame(self.content_frame, text="选择背景叠加图片", bg="#f0f0f0", font=("Arial", 12))
        overlay_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 创建左侧区域用于显示预览图和文件路径
        overlay_left_frame = tk.Frame(overlay_frame, bg="#f0f0f0")
        overlay_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.overlay_label = tk.Label(overlay_left_frame, text="未选择叠加图片", bg="#f0f0f0", anchor=tk.CENTER, justify=tk.CENTER, padx=10, wraplength=600)
        self.overlay_label.pack(fill=tk.BOTH, expand=True)
        
        # 创建右侧按钮区域
        overlay_right_frame = tk.Frame(overlay_frame, bg="#f0f0f0")
        overlay_right_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        
        select_overlay_btn = tk.Button(overlay_right_frame, text="选择图片", command=self.select_overlay, bg="#673AB7", fg="white", font=("Arial", 10), width=15)
        select_overlay_btn.pack(side=tk.RIGHT)
        
        # 添加清除按钮
        clear_overlay_btn = tk.Button(overlay_right_frame, text="清除图片", command=self.clear_overlay, bg="#F44336", fg="white", font=("Arial", 10), width=15)
        clear_overlay_btn.pack(side=tk.RIGHT, padx=5)
        
        # 选择输出目录和文件名
        output_frame = tk.LabelFrame(self.content_frame, text="选择输出位置", bg="#f0f0f0", font=("Arial", 12))
        output_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.output_label = tk.Label(output_frame, text="未选择输出目录", bg="#f0f0f0")
        self.output_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=10)
        
        select_output_btn = tk.Button(output_frame, text="选择目录", command=self.select_output, bg="#FF9800", fg="white", font=("Arial", 10), width=15)
        select_output_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        # 输出文件名和导出数量
        output_settings_frame = tk.Frame(output_frame, bg="#f0f0f0")
        output_settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 文件名输入
        filename_frame = tk.Frame(output_settings_frame, bg="#f0f0f0")
        filename_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(filename_frame, text="输出文件名:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        
        self.output_filename = tk.StringVar(value="歌单视频")
        filename_entry = tk.Entry(filename_frame, textvariable=self.output_filename, width=30)
        filename_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        tk.Label(filename_frame, text=".mp4", bg="#f0f0f0").pack(side=tk.LEFT)
        
        # 导出数量输入
        count_frame = tk.Frame(output_settings_frame, bg="#f0f0f0")
        count_frame.pack(side=tk.RIGHT)
        
        tk.Label(count_frame, text="导出数量:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        
        self.export_count = tk.IntVar(value=1)
        count_spinbox = tk.Spinbox(count_frame, from_=1, to=10, textvariable=self.export_count, width=5)
        count_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 选项设置
        options_frame = tk.LabelFrame(self.content_frame, text="设置选项", bg="#f0f0f0", font=("Arial", 12))
        options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 显示歌词选项
        self.show_lyrics_var = tk.BooleanVar(value=True)
        show_lyrics_check = tk.Checkbutton(options_frame, text="显示歌词（如果音频文件包含）", 
                                         variable=self.show_lyrics_var, bg="#f0f0f0")
        show_lyrics_check.pack(anchor=tk.W, padx=10, pady=5)
        
        # GPU加速选项
        self.gpu_acceleration_var = tk.BooleanVar(value=self.use_gpu)
        gpu_check = tk.Checkbutton(options_frame, text="使用GPU加速处理（需要NVIDIA显卡）", 
                                 variable=self.gpu_acceleration_var, bg="#f0f0f0")
        gpu_check.pack(anchor=tk.W, padx=10, pady=5)
        
        # 如果系统不支持GPU加速，禁用该选项
        if not self.use_gpu:
            gpu_check.config(state=tk.DISABLED)
            
        # 添加字体大小设置
        font_size_frame = tk.LabelFrame(options_frame, text="字体大小设置", bg="#f0f0f0", padx=10, pady=5)
        font_size_frame.pack(fill=tk.X, padx=10, pady=5, anchor=tk.W)
        
        # 标题字体大小设置
        title_font_frame = tk.Frame(font_size_frame, bg="#f0f0f0")
        title_font_frame.pack(fill=tk.X, pady=2)
        tk.Label(title_font_frame, text="标题字体大小:", bg="#f0f0f0", width=15, anchor=tk.W).pack(side=tk.LEFT)
        title_font_spinbox = tk.Spinbox(title_font_frame, from_=12, to=48, textvariable=self.title_font_size, width=5)
        title_font_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 播放列表字体大小设置
        playlist_font_frame = tk.Frame(font_size_frame, bg="#f0f0f0")
        playlist_font_frame.pack(fill=tk.X, pady=2)
        tk.Label(playlist_font_frame, text="播放列表字体大小:", bg="#f0f0f0", width=15, anchor=tk.W).pack(side=tk.LEFT)
        playlist_font_spinbox = tk.Spinbox(playlist_font_frame, from_=12, to=48, textvariable=self.playlist_font_size, width=5)
        playlist_font_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 歌词字体大小设置
        lyrics_font_frame = tk.Frame(font_size_frame, bg="#f0f0f0")
        lyrics_font_frame.pack(fill=tk.X, pady=2)
        tk.Label(lyrics_font_frame, text="歌词字体大小:", bg="#f0f0f0", width=15, anchor=tk.W).pack(side=tk.LEFT)
        lyrics_font_spinbox = tk.Spinbox(lyrics_font_frame, from_=12, to=48, textvariable=self.lyrics_font_size, width=5)
        lyrics_font_spinbox.pack(side=tk.LEFT, padx=5)
            
        # 进度条
        progress_frame = tk.Frame(self.content_frame, bg="#f0f0f0")
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(fill=tk.X, padx=10, pady=5)
        
        # 添加一个状态和耗时信息的框架
        status_time_frame = tk.Frame(progress_frame, bg="#f0f0f0")
        status_time_frame.pack(fill=tk.X, padx=10)
        
        self.status_label = tk.Label(status_time_frame, text="就绪", bg="#f0f0f0")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 添加耗时显示标签
        time_frame = tk.Frame(status_time_frame, bg="#f0f0f0")
        time_frame.pack(side=tk.RIGHT)
        
        # 当前视频耗时标签
        self.current_time_label = tk.Label(time_frame, text="当前耗时: 00:00:00", bg="#f0f0f0")
        self.current_time_label.pack(side=tk.TOP, padx=10, pady=2, anchor=tk.E)
        
        # 总耗时标签
        self.total_time_label = tk.Label(time_frame, text="总耗时: 00:00:00", bg="#f0f0f0")
        self.total_time_label.pack(side=tk.BOTTOM, padx=10, pady=2, anchor=tk.E)
        
        # 添加导出进度显示标签
        export_progress_frame = tk.Frame(progress_frame, bg="#f0f0f0")
        export_progress_frame.pack(fill=tk.X, padx=10)
        
        self.export_progress_label = tk.Label(export_progress_frame, text="", bg="#f0f0f0")
        self.export_progress_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 生成按钮
        self.generate_btn = tk.Button(self.content_frame, text="生成视频", command=self.start_generation, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"))
        self.generate_btn.pack(fill=tk.X, padx=10, pady=20)
    
    def on_content_configure(self, event):
        """当内容框架大小变化时调整滚动区域"""
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
    
    def on_main_canvas_configure(self, event):
        """当主画布大小变化时调整内容框架宽度"""
        # 更新内容框架的宽度以匹配画布宽度
        self.main_canvas.itemconfig(self.main_canvas_window, width=event.width)
    
    def on_mousewheel(self, event):
        """鼠标滚轮事件处理"""
        self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def on_frame_configure(self, event):
        """当音乐列表框架大小变化时调整Canvas的滚动区域"""
        self.music_canvas.configure(scrollregion=self.music_canvas.bbox("all"))
    
    def on_canvas_configure(self, event):
        """当Canvas大小变化时调整窗口大小"""
        self.music_canvas.itemconfig(self.music_canvas_window, width=event.width)
    
    def add_music(self):
        files = filedialog.askopenfilenames(
            title="选择音乐文件",
            filetypes=[("音频文件", "*.mp3 *.flac *.wav *.m4a *.aac *.wma"), 
                      ("MP3文件", "*.mp3"),
                      ("FLAC文件", "*.flac"),
                      ("WAV文件", "*.wav"),
                      ("M4A文件", "*.m4a"),
                      ("AAC文件", "*.aac"),
                      ("WMA文件", "*.wma"),
                      ("所有文件", "*.*")]
        )
        if files:
            for file in files:
                if file not in self.music_files:
                    self.music_files.append(file)
                    
                    # 检查是否有歌词
                    has_lyrics = self.check_lyrics_exist(file)
                    
                    # 添加到后台Listbox（用于保持一致性）
                    self.music_list.insert(tk.END, os.path.basename(file))
                    
                    # 在UI中创建新的音乐项目
                    self.add_music_item_to_ui(file, len(self.music_files) - 1, has_lyrics)
    
    def add_music_item_to_ui(self, music_file, index, has_lyrics):
        """在UI中添加一个音乐项目"""
        # 创建一个帧来包含音乐项目
        item_frame = tk.Frame(self.music_items_frame, bd=1, relief=tk.RIDGE, padx=5, pady=5)
        item_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # 添加序号标签
        index_label = tk.Label(item_frame, text=f"{index + 1}.", width=3)
        index_label.pack(side=tk.LEFT, padx=2)
        
        # 添加歌词状态指示器
        if has_lyrics:
            lyrics_indicator = tk.Label(item_frame, text="歌词", bg="#4CAF50", fg="white", 
                                      font=("Arial", 8), padx=5, pady=1)
        else:
            lyrics_indicator = tk.Label(item_frame, text="无歌词", bg="#f44336", fg="white", 
                                      font=("Arial", 8), padx=5, pady=1)
        lyrics_indicator.pack(side=tk.LEFT, padx=5)
        
        # 添加文件名标签
        filename_label = tk.Label(item_frame, text=os.path.basename(music_file), anchor=tk.W)
        filename_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 保存引用以便后续更新
        item_frame.index = index
        item_frame.music_file = music_file
        item_frame.filename_label = filename_label
        item_frame.lyrics_indicator = lyrics_indicator
        
        # 添加选择事件
        def select_item(event, idx=index):
            self.select_music_item(idx)
        
        item_frame.bind("<Button-1>", select_item)
        filename_label.bind("<Button-1>", select_item)
        
        # 保存对所有项目的引用
        if not hasattr(self, 'music_item_frames'):
            self.music_item_frames = []
        
        # 确保列表长度足够
        while len(self.music_item_frames) <= index:
            self.music_item_frames.append(None)
        
        self.music_item_frames[index] = item_frame
    
    def select_music_item(self, index):
        """选择一个音乐项目"""
        # 清除所有项目的选择状态
        for item in self.music_item_frames:
            if item:
                item.config(bg="#f0f0f0")
                for widget in item.winfo_children():
                    if not isinstance(widget, tk.Label) or widget != item.lyrics_indicator:
                        widget.config(bg="#f0f0f0")
        
        # 设置选中项目的背景色
        if 0 <= index < len(self.music_item_frames) and self.music_item_frames[index]:
            self.music_item_frames[index].config(bg="#e0e0e0")  # 选中背景为浅灰色
            for widget in self.music_item_frames[index].winfo_children():
                if not isinstance(widget, tk.Label) or widget != self.music_item_frames[index].lyrics_indicator:
                    widget.config(bg="#e0e0e0")
            
            # 同步Listbox选择
            self.music_list.selection_clear(0, tk.END)
            self.music_list.selection_set(index)
    
    def update_music_list_ui(self):
        """更新整个音乐列表UI"""
        # 清空当前列表
        for widget in self.music_items_frame.winfo_children():
            widget.destroy()
        
        # 清空引用列表
        self.music_item_frames = []
        
        # 重新检查所有音乐的歌词状态并添加到UI
        for i, music_file in enumerate(self.music_files):
            has_lyrics = self.check_lyrics_exist(music_file)
            self.add_music_item_to_ui(music_file, i, has_lyrics)
    
    def remove_music(self):
        try:
            selection = self.music_list.curselection()
            if selection:
                index = selection[0]
                del self.music_files[index]
                self.music_list.delete(index)
                self.update_music_list_ui()
        except Exception as e:
            messagebox.showerror("错误", f"移除音乐时出错: {str(e)}")
    
    def move_up(self):
        try:
            selection = self.music_list.curselection()
            if selection and selection[0] > 0:
                index = selection[0]
                # 交换列表中的项目
                self.music_files[index], self.music_files[index-1] = self.music_files[index-1], self.music_files[index]
                # 更新显示
                self.update_music_list_ui()
                # 更新选择
                self.select_music_item(index - 1)
        except Exception as e:
            messagebox.showerror("错误", f"上移音乐时出错: {str(e)}")
    
    def move_down(self):
        try:
            selection = self.music_list.curselection()
            if selection and selection[0] < len(self.music_files) - 1:
                index = selection[0]
                # 交换列表中的项目
                self.music_files[index], self.music_files[index+1] = self.music_files[index+1], self.music_files[index]
                # 更新显示
                self.update_music_list_ui()
                # 更新选择
                self.select_music_item(index + 1)
        except Exception as e:
            messagebox.showerror("错误", f"下移音乐时出错: {str(e)}")
    
    def select_image(self):
        # 修改为选择图片文件夹
        folder = filedialog.askdirectory(title="选择背景图片文件夹")
        if folder:
            # 保存文件夹路径
            self.image_folder = folder
            
            # 搜索文件夹中的所有图片文件
            self.image_files = []
            supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
            for file in sorted(os.listdir(folder)):
                if file.lower().endswith(supported_formats):
                    self.image_files.append(os.path.join(folder, file))
            
            # 检查是否找到了图片
            if not self.image_files:
                messagebox.showwarning("警告", "所选文件夹中没有找到支持的图片文件！")
                return
            
            # 重置当前图片索引并设置第一张图片为当前图片
            self.current_image_index = 0
            self.image_file = self.image_files[0] if self.image_files else ""
            
            # 更新UI显示，只显示文件夹路径和图片数量
            self.image_label.config(text=f"已选择背景图片文件夹: {folder} (包含 {len(self.image_files)} 张图片)", image="", compound=tk.NONE)
            self.image_label.image = None
    
    def select_overlay(self):
        """选择叠加背景图片"""
        file = filedialog.askopenfilename(
            title="选择背景叠加图片",
            filetypes=(("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif"), ("所有文件", "*.*"))
        )
        if file:
            self.overlay_image = file
            try:
                # 创建预览图片
                img = Image.open(file)
                # 计算预览图片大小，保持比例但限制最大高度为150
                width, height = img.size
                ratio = width / height
                preview_height = 150
                preview_width = int(preview_height * ratio)
                
                # 如果预览宽度太大，则限制宽度并重新计算高度
                if preview_width > 300:
                    preview_width = 300
                    preview_height = int(preview_width / ratio)
                
                img = img.resize((preview_width, preview_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # 更新UI显示预览图片
                self.overlay_label.config(image=photo, compound=tk.TOP)
                self.overlay_label.image = photo
                
                # 在预览图片下方显示文件路径
                self.overlay_label.config(text=f"已选择叠加图片: {file}")
            except Exception as e:
                messagebox.showerror("错误", f"加载叠加图片时出错: {str(e)}")
    
    def clear_overlay(self):
        """清除叠加背景图片"""
        self.overlay_image = ""
        self.overlay_label.config(text="未选择叠加图片", image="", compound=tk.NONE)
        self.overlay_label.image = None
    
    def select_output(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir = directory
            self.output_label.config(text=directory)
    
    def start_generation(self):
        """开始生成视频"""
        # 如果已经在生成，不做任何操作
        if self.is_generating:
            return
            
        if not self.music_files:
            messagebox.showwarning("警告", "请先添加音乐文件！")
            return
        
        if not self.image_files:
            messagebox.showwarning("警告", "请先选择包含图片的文件夹！")
            return
        
        if not self.output_dir:
            messagebox.showwarning("警告", "请先选择输出目录！")
            return
        
        # 获取导出数量
        export_count = self.export_count.get()
        if export_count < 1:
            messagebox.showwarning("警告", "导出数量必须大于0！")
            return
        
        # 检查是否有足够的歌曲进行排列组合
        import math
        # 计算歌曲的可能排列数
        num_songs = len(self.music_files)
        factorial = math.factorial(num_songs)
        
        # 对于两首歌曲的特殊处理
        if num_songs == 2 and export_count > factorial:
            response = messagebox.askyesno("确认", 
                           f"您只有2首歌曲，最多只能生成2个不同顺序的视频。\n\n"
                           f"是否继续并生成{factorial}个视频？")
            if response:
                export_count = factorial
                # 更新导出数量显示
                self.export_count.set(factorial)
            else:
                return
        # 对于一般情况的处理
        elif num_songs >= 3 and export_count > factorial:
            response = messagebox.askyesno("确认", 
                           f"导出数量({export_count})超过了可能的歌曲排列组合数量({factorial})，"
                           f"无法保证所有视频顺序不重复。\n\n是否继续并生成{factorial}个视频？")
            if response:
                export_count = factorial
                # 更新导出数量显示
                self.export_count.set(factorial)
            else:
                return
        # 对于只有1首歌曲的情况
        elif num_songs == 1 and export_count > 1:
            response = messagebox.askyesno("确认", 
                           "您只有1首歌曲，无法生成多个不同顺序的视频。\n\n"
                           "是否继续并只生成1个视频？")
            if response:
                export_count = 1
                # 更新导出数量显示
                self.export_count.set(1)
            else:
                return
        
        # 设置生成标志
        self.is_generating = True
        
        # 将生成按钮更改为停止按钮
        self.generate_btn.config(text="停止生成", command=self.stop_generation, bg="#f44336")
        
        # 更新状态
        self.status_label.config(text="正在生成视频...")
        
        # 开始生成视频（使用线程防止界面冻结）
        threading.Thread(target=lambda: self.generate_multiple_videos(export_count), daemon=True).start()
    
    def generate_multiple_videos(self, count):
        """生成多个视频，第一个保持原顺序，之后的随机打乱"""
        # 确保设置生成标志
        self.is_generating = True
        
        # 保存原始音乐文件列表和当前索引
        self.original_music_files = self.music_files.copy()
        self.current_video_index = 0
        self.total_video_count = count
        self.original_filename = self.output_filename.get()
        
        # 重置图片索引，从第一张图片开始
        self.current_image_index = 0
        
        # 初始化总耗时
        self.total_process_time = 0
        self.total_start_time = time.time()  # 记录总处理开始时间
        
        # 跟踪已生成的歌曲顺序，防止重复
        self.generated_orders = []
        # 保存原始顺序的哈希值
        self.generated_orders.append(self.get_order_hash(self.original_music_files))
        
        # 如果只有两首歌曲，并且需要生成第二个视频，提前计算出颠倒顺序
        if len(self.original_music_files) == 2 and count > 1:
            # 创建反序列表，用于第二个视频
            self.reversed_music_files = self.original_music_files.copy()
            self.reversed_music_files.reverse()
        
        # 更新导出进度显示
        self.root.after(0, lambda idx=0, tot=count: self.export_progress_label.configure(
            text=f"导出进度: {idx}/{tot} 视频完成"))
        
        # 更新总耗时显示
        self.root.after(0, lambda: self.total_time_label.configure(text=f"总耗时: 00:00:00"))
        
        # 开始第一个视频生成
        self.generate_next_video()
    
    def get_order_hash(self, file_list):
        """获取歌曲顺序的哈希值，用于检查重复"""
        # 使用文件路径作为唯一标识
        order_str = "".join(file_list)
        import hashlib
        return hashlib.md5(order_str.encode()).hexdigest()
    
    def generate_next_video(self):
        """生成下一个视频"""
        try:
            # 检查是否已完成所有视频生成或者是否请求停止
            if self.current_video_index >= self.total_video_count or not self.is_generating:
                # 所有视频已生成完成或请求停止，恢复原始列表
                self.music_files = self.original_music_files.copy()
                # 恢复原始文件名
                self.output_filename.set(self.original_filename)
                # 恢复生成按钮状态
                self.root.after(0, lambda: self.generate_btn.config(text="生成视频", command=self.start_generation, state=tk.NORMAL, bg="#4CAF50"))
                # 更新状态和导出进度
                if not self.is_generating:
                    self.root.after(0, lambda: self.status_label.configure(text=f"已停止视频生成"))
                else:
                    self.root.after(0, lambda: self.status_label.configure(text=f"已完成所有 {self.total_video_count} 个视频生成"))
                    
                self.root.after(0, lambda cur=self.current_video_index, tot=self.total_video_count: self.export_progress_label.configure(
                    text=f"导出进度: {cur}/{tot} 视频完成"))
                    
                # 重置生成标志
                self.is_generating = False
                return
            
            # 设置文件名
            if self.total_video_count > 1:
                new_filename = f"{self.original_filename}_{self.current_video_index + 1}"
                self.output_filename.set(new_filename)
            
            # 处理不同的歌曲排序
            if self.current_video_index > 0:
                # 只有两首歌曲的特殊情况处理
                if len(self.original_music_files) == 2:
                    # 直接使用提前准备好的反序列表
                    self.music_files = self.reversed_music_files.copy()
                    # 更新状态
                    self.root.after(0, lambda idx=self.current_video_index+1, total=self.total_video_count: 
                                self.status_label.configure(text=f"正在生成第 {idx}/{total} 个视频 (反序顺序)..."))
                # 三首及以上歌曲的随机排序处理
                else:
                    import random
                    max_attempts = 100  # 最大尝试次数，防止无限循环
                    attempts = 0
                    
                    while attempts < max_attempts:
                        # 复制原始列表并打乱
                        self.music_files = self.original_music_files.copy()
                        random.shuffle(self.music_files)
                        
                        # 检查是否生成了新的顺序
                        current_hash = self.get_order_hash(self.music_files)
                        if current_hash not in self.generated_orders:
                            # 找到新顺序，保存并跳出循环
                            self.generated_orders.append(current_hash)
                            break
                        
                        attempts += 1
                    
                    # 更新状态，提示是否找到了不重复的顺序
                    if attempts < max_attempts:
                        self.root.after(0, lambda idx=self.current_video_index+1, total=self.total_video_count: 
                                    self.status_label.configure(text=f"正在生成第 {idx}/{total} 个视频 (随机顺序)..."))
                    else:
                        # 无法找到不重复的顺序，提示用户并停止生成
                        error_msg = "无法生成更多不重复的歌曲顺序，已停止处理"
                        print(error_msg)
                        self.root.after(0, lambda: self.status_label.configure(text=f"发生错误: {error_msg}"))
                        self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
                        
                        # 恢复原始设置和按钮状态
                        self.music_files = self.original_music_files.copy()
                        self.output_filename.set(self.original_filename)
                        self.root.after(0, lambda: self.generate_btn.config(text="生成视频", state=tk.NORMAL, bg="#4CAF50"))
                        return
            else:
                # 第一次使用原始顺序
                self.music_files = self.original_music_files.copy()
                # 更新状态
                self.root.after(0, lambda: self.status_label.configure(text=f"正在生成第 1/{self.total_video_count} 个视频 (原始顺序)..."))
            
            # 为当前视频选择图片
            if self.image_files:
                # 选择当前索引对应的图片
                self.image_file = self.image_files[self.current_image_index % len(self.image_files)]
                # 增加图片索引，为下一个视频准备
                self.current_image_index += 1
                # 如果索引超出范围，重新开始
                if self.current_image_index >= len(self.image_files):
                    self.current_image_index = 0
            
            # 开始生成当前视频
            threading.Thread(target=lambda: self.generate_combined_video(self.on_video_complete), daemon=True).start()
            
            # 增加索引，准备下一个视频
            self.current_video_index += 1
            
        except Exception as e:
            error_msg = str(e)
            print(f"生成多个视频时出错: {error_msg}")
            self.root.after(0, lambda: self.status_label.configure(text=f"发生错误: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"生成多个视频时出错: {error_msg}"))
            
            # 恢复生成按钮状态
            self.root.after(0, lambda: self.generate_btn.config(text="生成视频", state=tk.NORMAL, bg="#4CAF50"))
            
            # 恢复原始设置
            self.music_files = self.original_music_files.copy()
            self.output_filename.set(self.original_filename)
    
    def on_video_complete(self):
        """视频完成后的回调"""
        # 更新导出进度显示
        self.root.after(0, lambda idx=self.current_video_index, tot=self.total_video_count: self.export_progress_label.configure(
            text=f"导出进度: {idx}/{tot} 视频完成"))
        # 继续生成下一个视频
        self.generate_next_video()
    
    def start_progress_monitor(self):
        """启动进度监控线程，定期检查队列中的进度更新并应用到UI"""
        def update_progress():
            while True:
                if not self.processing:
                    # 如果没有正在处理，则休眠一会再检查
                    time.sleep(0.1)
                    continue
                
                # 更新当前视频耗时显示
                if self.timer_running:
                    current_time = time.time()
                    self.elapsed_time = current_time - self.start_time
                    elapsed_str = self.format_elapsed_time(self.elapsed_time)
                    self.root.after(0, lambda t=elapsed_str: self.current_time_label.configure(text=f"当前耗时: {t}"))
                    
                    # 更新总耗时显示（如果在批量处理模式下）
                    if hasattr(self, 'total_start_time'):
                        total_elapsed = current_time - self.total_start_time
                        total_elapsed_str = self.format_elapsed_time(total_elapsed)
                        self.root.after(0, lambda t=total_elapsed_str: self.total_time_label.configure(text=f"总耗时: {t}"))
                
                try:
                    # 非阻塞方式获取队列中的进度更新
                    progress_info = self.progress_queue.get_nowait()
                    stage = progress_info.get('stage', '')
                    progress = progress_info.get('progress', 0)
                    message = progress_info.get('message', '')
                    
                    # 根据处理阶段和进度更新UI
                    if stage == 'audio':
                        # 音频合并阶段 (0-33%)
                        value = progress * 0.33
                        self.root.after(0, lambda v=value: self.progress.configure(value=v))
                    elif stage == 'video':
                        # 视频生成阶段 (33-100%)
                        value = 0.33 + progress * 0.67
                        self.root.after(0, lambda v=value: self.progress.configure(value=v))
                    
                    # 更新状态消息
                    if message:
                        self.root.after(0, lambda m=message: self.status_label.configure(text=m))
                        
                    self.progress_queue.task_done()
                except queue.Empty:
                    # 队列为空，稍等再检查
                    time.sleep(0.1)
        
        # 创建并启动进度监控线程
        progress_thread = threading.Thread(target=update_progress, daemon=True)
        progress_thread.start()
    
    def parse_ffmpeg_progress(self, line, duration):
        """解析FFmpeg输出行，提取进度信息"""
        # 寻找时间信息
        time_match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
        if time_match:
            hours, minutes, seconds, msec = map(int, time_match.groups())
            current_time = hours * 3600 + minutes * 60 + seconds + msec / 100
            # 计算百分比进度 (0-1范围)
            return min(current_time / duration, 1.0) if duration else 0
        return None
    
    def run_ffmpeg_with_progress(self, command, stage, total_duration, message_prefix):
        """运行FFmpeg命令并报告进度"""
        try:
            # 使用subprocess.Popen来获取实时输出
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                text=True
            )
            
            # 存储进程引用以便可以在需要时终止
            self.ffmpeg_process = process
            
            # 读取错误输出（FFmpeg将进度信息输出到stderr）
            for line in process.stderr:
                # 如果已经请求停止处理，则终止循环
                if not self.is_generating:
                    break
                    
                # 解析进度
                progress = self.parse_ffmpeg_progress(line, total_duration)
                if progress is not None:
                    # 将进度信息放入队列
                    percentage = int(progress * 100)
                    self.progress_queue.put({
                        'stage': stage,
                        'progress': progress,
                        'message': f"{message_prefix} ({percentage}%)"
                    })
            
            # 等待进程完成或终止它
            if not self.is_generating and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
                # 如果进程未能在超时时间内终止，则强制终止
                if process.poll() is None:
                    process.kill()
            else:
                process.wait()
                
            self.ffmpeg_process = None
            return process.returncode
        except Exception as e:
            print(f"FFmpeg执行错误: {str(e)}")
            self.ffmpeg_process = None
            return -1
            
    def stop_generation(self):
        """停止视频生成过程"""
        if not self.is_generating:
            return
            
        # 设置标志以停止处理
        self.is_generating = False
        
        # 终止当前FFmpeg进程（如果有）
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                self.ffmpeg_process.terminate()
                # 给进程一些时间来优雅地关闭
                self.ffmpeg_process.wait(timeout=5)
                # 如果进程未能在超时时间内终止，则强制终止
                if self.ffmpeg_process.poll() is None:
                    self.ffmpeg_process.kill()
            except Exception as e:
                print(f"终止FFmpeg进程时出错: {str(e)}")
        
        # 重置计时器
        self.timer_running = False
        
        # 更新UI
        self.root.after(0, lambda: self.status_label.configure(text="已停止视频生成"))
        self.root.after(0, lambda: self.generate_btn.config(text="生成视频", command=self.start_generation, state=tk.NORMAL, bg="#4CAF50"))
        
        # 如果处于批量生成模式，则恢复原始设置
        if hasattr(self, 'original_music_files'):
            self.music_files = self.original_music_files.copy()
            if hasattr(self, 'original_filename'):
                self.output_filename.set(self.original_filename)
    
    def generate_combined_video(self, callback=None):
        try:
            # 标记处理开始
            self.processing = True
            
            # 如果已经请求停止，直接返回
            if not self.is_generating:
                self.processing = False
                return
            
            # 开始计时
            self.start_time = time.time()
            self.timer_running = True
            
            # 设置进度条最大值为1（0-100%）
            self.root.after(0, lambda: self.progress.configure(maximum=1.0))
            self.root.after(0, lambda: self.progress.configure(value=0.0))
            
            # 创建临时工作目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # 使用root.after确保在UI线程中更新界面
                self.root.after(0, lambda: self.status_label.configure(text="步骤1/4: 分析音频文件..."))
                
                # 1. 分析所有音频文件，获取时长信息
                music_info = []
                current_time = 0
                total_duration = 0
                
                for music_file in self.music_files:
                    # 检查是否请求停止
                    if not self.is_generating:
                        self.processing = False
                        return
                        
                    # 提取音频元数据
                    title, artist, duration = self.extract_audio_info(music_file)
                    total_duration += duration
                    
                    # 使用更好的显示名称（标题+艺术家）
                    display_name = title
                    if artist:
                        display_name = f"{artist} - {title}"
                    
                    # 确保display_name不包含文件扩展名
                    display_name = os.path.splitext(display_name)[0]
                    
                    # 检查歌词文件
                    has_lyrics = False
                    lyrics_path = None
                    
                    # 1. 检查是否有同名的.lrc文件
                    base_name = os.path.splitext(music_file)[0]
                    lrc_file = base_name + '.lrc'
                    if os.path.exists(lrc_file):
                        has_lyrics = True
                        lyrics_path = lrc_file
                    
                    # 2. 如果没有同名文件，检查歌词文件夹中是否有对应的歌词文件
                    if not has_lyrics and self.lyrics_folder and os.path.exists(self.lyrics_folder):
                        # 获取音频文件名（不含路径和扩展名）
                        audio_filename = os.path.basename(music_file)
                        filename_no_ext = os.path.splitext(audio_filename)[0]
                        
                        # 检查歌词文件夹中是否存在对应的歌词文件
                        lrc_path = os.path.join(self.lyrics_folder, filename_no_ext + ".lrc")
                        if os.path.exists(lrc_path):
                            has_lyrics = True
                            lyrics_path = lrc_path
                        
                        # 如果文件名包含艺术家和歌曲名信息（如"艺术家-歌曲名"格式）
                        if not has_lyrics and '-' in filename_no_ext:
                            artist_name, song_title = filename_no_ext.split('-', 1)
                            artist_name = artist_name.strip()
                            song_title = song_title.strip()
                            
                            # 检查可能的歌词文件名格式
                            possible_names = [
                                f"{artist_name} - {song_title}.lrc",
                                f"{song_title}.lrc",
                                f"{artist_name}-{song_title}.lrc"
                            ]
                            
                            for lrc_name in possible_names:
                                lrc_path = os.path.join(self.lyrics_folder, lrc_name)
                                if os.path.exists(lrc_path):
                                    has_lyrics = True
                                    lyrics_path = lrc_path
                                    break
                    
                    # 计算时间点
                    start_time = current_time
                    end_time = start_time + duration
                    
                    # 时间格式化 (HH:MM:SS)
                    start_time_fmt = self.format_time(start_time)
                    
                    music_info.append({
                        'file': music_file,
                        'title': title,
                        'artist': artist,
                        'duration': duration,
                        'start_time': start_time,
                        'start_time_fmt': start_time_fmt,
                        'display_name': display_name,
                        'has_lyrics': has_lyrics,
                        'lyrics_path': lyrics_path
                    })
                    
                    current_time = end_time
                
                # 更新进度队列，表示分析完成
                self.progress_queue.put({
                    'stage': 'audio',
                    'progress': 0.1,
                    'message': "步骤2/4: 生成带歌单的视频..."
                })
                
                # 2. 生成包含歌单的背景图
                img_with_playlist = os.path.join(temp_dir, "background_with_playlist.png")
                self.create_image_with_playlist(music_info, img_with_playlist)
                
                # 确保输出目录存在
                output_file = os.path.join(self.output_dir, f"{self.output_filename.get()}.mp4")
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                # 更新进度队列，表示准备合并音频
                self.progress_queue.put({
                    'stage': 'audio',
                    'progress': 0.2,
                    'message': "步骤2/4: 准备合并音频文件..."
                })
                
                # 根据音频类型进行处理
                # 首先将所有非MP3格式转换为MP3格式
                converted_files = []
                for i, info in enumerate(music_info):
                    source_file = info['file']
                    file_ext = os.path.splitext(source_file)[1].lower()
                    
                    # 如果文件不是MP3格式，需要先转换
                    if file_ext != '.mp3':
                        print(f"转换音频文件: {os.path.basename(source_file)}")
                        temp_mp3 = os.path.join(temp_dir, f"temp_{i}.mp3")
                        
                        # 使用FFmpeg转换音频格式
                        convert_command = [
                            'ffmpeg',
                            '-i', source_file,
                            '-vn',  # 不处理视频流
                            '-ar', '44100',  # 设置采样率
                            '-ac', '2',  # 设置声道数
                            '-b:a', '192k',  # 设置比特率
                            '-y',
                            temp_mp3
                        ]
                        
                        try:
                            # 执行转换命令
                            process = subprocess.Popen(
                                convert_command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                            
                            _, stderr = process.communicate()
                            
                            if process.returncode != 0:
                                print(f"转换音频错误: {stderr.decode('utf-8', errors='ignore')}")
                                raise Exception(f"转换音频文件失败: {os.path.basename(source_file)}")
                            
                            # 使用转换后的文件
                            converted_files.append((i, temp_mp3))
                            
                        except Exception as e:
                            print(f"转换音频出错: {str(e)}")
                            raise Exception(f"转换音频文件失败: {os.path.basename(source_file)}")
                
                # 更新音乐信息中的文件路径
                for idx, temp_file in converted_files:
                    music_info[idx]['file'] = temp_file
                
                # 创建合并音频的列表文件
                audio_list_file = os.path.join(temp_dir, "audio_list.txt")
                with open(audio_list_file, 'w', encoding='utf-8') as f:
                    for info in music_info:
                        # 确保文件路径格式正确（对于Windows和Unix系统）
                        if os.name == 'nt':  # Windows系统
                            file_path = info['file'].replace('\\', '\\\\')
                        else:
                            file_path = info['file']
                        f.write(f"file '{file_path}'\n")
                
                temp_audio = os.path.join(temp_dir, "combined_audio.mp3")
                
                # 合并音频
                try:
                    # 运行音频合并命令
                    audio_command = [
                        'ffmpeg',
                        '-f', 'concat',
                        '-safe', '0',
                        '-i', audio_list_file,
                        '-c:a', 'libmp3lame',
                        '-q:a', '4',
                        '-y',
                        temp_audio
                    ]
                    
                    print(f"执行合并音频命令: {' '.join(audio_command)}")
                    
                    # 运行音频合并并监控进度
                    audio_result = self.run_ffmpeg_with_progress(
                        audio_command, 
                        'audio', 
                        total_duration, 
                        "步骤2/4: 合并音频文件"
                    )
                    
                    if audio_result != 0:
                        raise Exception("合并音频文件失败")
                    
                    # 更新进度，表示音频合并完成
                    self.progress_queue.put({
                        'stage': 'audio',
                        'progress': 1.0,
                        'message': "步骤3/4: 处理歌词字幕..."
                    })
                    
                    # 3. 如果有歌词，将LRC文件转换为字幕文件
                    subtitle_file = None
                    if self.show_lyrics_var.get() and any(info['has_lyrics'] for info in music_info):
                        # 将字幕文件保存到固定位置，避免路径问题
                        subtitle_file = os.path.join(temp_dir, "lyrics.srt")
                        self.convert_lrc_to_subtitle(music_info, subtitle_file)
                    else:
                        self.progress_queue.put({
                            'stage': 'video',
                            'progress': 0.0,
                            'message': "步骤3/4: 跳过字幕处理(无歌词)..."
                        })
                    
                    # 4. 创建视频
                    self.progress_queue.put({
                        'stage': 'video',
                        'progress': 0.1,
                        'message': "步骤4/4: 生成最终视频..."
                    })
                    
                    # 确保输出路径正确处理
                    safe_output_file = output_file.replace('\\', '/')
                    video_creation_success = False
                    
                    # 如果有字幕，使用两步法：先创建带字幕的临时视频
                    if subtitle_file and os.path.exists(subtitle_file) and os.name == 'nt':
                        # 步骤1：创建带字幕的临时视频
                        temp_video_with_sub = os.path.join(temp_dir, "temp_with_sub.mp4")
                        
                        # 切换到临时目录
                        old_cwd = os.getcwd()
                        os.chdir(temp_dir)
                        
                        try:
                            # 获取用户设置的字体大小
                            font_size = self.lyrics_font_size.get()
                            
                            # 使用相对路径
                            sub_command = [
                                'ffmpeg',
                                '-loop', '1',
                                '-i', img_with_playlist,
                                '-i', temp_audio,
                                '-vf', f'subtitles=lyrics.srt:force_style=\'FontSize={font_size}\'',
                                '-c:v', 'h264_nvenc' if self.gpu_acceleration_var.get() and self.use_gpu else 'libx264',
                                '-preset', 'p7' if self.gpu_acceleration_var.get() and self.use_gpu else 'medium',
                                '-crf', '23',
                                '-c:a', 'aac',
                                '-b:a', '192k',
                                '-pix_fmt', 'yuv420p',
                                '-shortest',
                                '-y',
                                temp_video_with_sub
                            ]
                            
                            print(f"执行创建带字幕的临时视频命令: {' '.join(sub_command)}")
                            
                            # 运行带字幕的视频生成并监控进度
                            video_result = self.run_ffmpeg_with_progress(
                                sub_command, 
                                'video', 
                                total_duration, 
                                "步骤4/4: 生成带字幕的临时视频"
                            )
                            
                            if video_result != 0:
                                print(f"创建带字幕的临时视频错误")
                                temp_video_with_sub = None
                        finally:
                            # 恢复工作目录
                            os.chdir(old_cwd)
                            
                        # 步骤2：复制临时视频到最终位置
                        if temp_video_with_sub and os.path.exists(temp_video_with_sub):
                            self.progress_queue.put({
                                'stage': 'video',
                                'progress': 0.9,
                                'message': "步骤4/4: 完成视频处理..."
                            })
                            
                            # 直接复制视频文件
                            copy_command = [
                                'ffmpeg',
                                '-i', temp_video_with_sub,
                                '-c', 'copy',
                                '-y',
                                safe_output_file
                            ]
                            
                            print(f"执行复制最终视频命令: {' '.join(copy_command)}")
                            
                            process = subprocess.Popen(
                                copy_command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                            
                            _, stderr = process.communicate()
                            
                            if process.returncode != 0:
                                print(f"复制最终视频错误: {stderr.decode('utf-8', errors='ignore')}")
                                raise Exception("生成视频失败")
                            
                            video_creation_success = True
                    
                    # 如果前面的步骤没有成功，尝试标准视频生成
                    if not video_creation_success:
                        # 创建临时视频文件
                        temp_video = os.path.join(temp_dir, "temp_video.mp4")
                        
                        # 创建标准视频（无字幕或非Windows系统）
                        video_command = [
                            'ffmpeg',
                            '-loop', '1',
                            '-i', img_with_playlist,
                            '-i', temp_audio,
                            '-c:v', 'h264_nvenc' if self.gpu_acceleration_var.get() and self.use_gpu else 'libx264',
                            '-preset', 'p7' if self.gpu_acceleration_var.get() and self.use_gpu else 'medium',
                            '-crf', '23',
                            '-c:a', 'aac',
                            '-b:a', '192k',
                            '-pix_fmt', 'yuv420p',
                            '-shortest',
                            '-y'
                        ]
                        
                        # 如果是非Windows系统且有字幕文件，添加字幕滤镜
                        if subtitle_file and os.path.exists(subtitle_file) and os.name != 'nt':
                            # 添加字体大小设置
                            font_size = self.lyrics_font_size.get()
                            video_command.extend([
                                '-vf', f"subtitles='{subtitle_file}':force_style='FontSize={font_size}'"
                            ])
                        
                        # 添加临时输出文件
                        video_command.append(temp_video)
                        
                        print(f"执行创建视频命令: {' '.join(video_command)}")
                        
                        # 使用进度监控运行视频生成命令
                        video_result = self.run_ffmpeg_with_progress(
                            video_command, 
                            'video', 
                            total_duration, 
                            "步骤4/4: 生成临时视频"
                        )
                        
                        if video_result != 0:
                            raise Exception("生成临时视频失败")
                            
                        # 复制临时视频到最终位置
                        self.progress_queue.put({
                            'stage': 'video',
                            'progress': 0.9,
                            'message': "步骤4/4: 完成视频处理..."
                        })
                        
                        copy_command = [
                            'ffmpeg',
                            '-i', temp_video,
                            '-c', 'copy',
                            '-y',
                            safe_output_file
                        ]
                        
                        print(f"执行复制最终视频命令: {' '.join(copy_command)}")
                        
                        process = subprocess.Popen(
                            copy_command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        
                        _, stderr = process.communicate()
                        
                        if process.returncode != 0:
                            print(f"复制最终视频错误: {stderr.decode('utf-8', errors='ignore')}")
                            raise Exception("生成视频失败")
                    
                    # 最终完成处理
                    self.progress_queue.put({
                        'stage': 'video',
                        'progress': 1.0,
                        'message': "完成! 已生成合并视频"
                    })
                    
                    # 使用root.after确保在UI线程中更新界面
                    self.root.after(0, lambda: self.progress.configure(value=1.0))
                    self.root.after(0, lambda: self.status_label.configure(text=f"完成! 已生成合并视频"))
                    
                    # 弹出成功消息
                    completed_msg = f"已成功生成合并视频!\n保存位置: {output_file}"
                    # 使用单独的after调用来确保弹窗显示，给予足够的时间让UI更新
                    self.root.after(100, lambda msg=completed_msg: messagebox.showinfo("成功", msg))
                
                except Exception as e:
                    error_msg = str(e)
                    print(f"处理错误: {error_msg}")
                    # 使用root.after确保在UI线程中更新界面
                    self.root.after(0, lambda: self.status_label.configure(text=f"发生错误: {error_msg}"))
                    self.root.after(0, lambda: messagebox.showerror("错误", f"生成视频时出错: {error_msg}"))
        
        except Exception as e:
            error_msg = str(e)
            print(f"处理错误: {error_msg}")
            # 使用root.after确保在UI线程中更新界面
            self.root.after(0, lambda: self.status_label.configure(text=f"发生错误: {error_msg}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"生成视频时出错: {error_msg}"))
        finally:
            # 标记处理结束
            self.processing = False
            self.timer_running = False
            
            # 计算当前视频的耗时
            if self.start_time > 0:
                video_time = time.time() - self.start_time
                video_time_str = self.format_elapsed_time(video_time)
                
                # 更新当前视频耗时显示
                self.root.after(0, lambda t=video_time_str: self.current_time_label.configure(text=f"当前耗时: {t}"))
                
                # 如果在批量处理模式下，更新总耗时
                if hasattr(self, 'total_start_time'):
                    total_elapsed = time.time() - self.total_start_time
                    total_elapsed_str = self.format_elapsed_time(total_elapsed)
                    self.root.after(0, lambda t=total_elapsed_str: self.total_time_label.configure(text=f"总耗时: {t}"))
            
            # 如果是单独生成视频模式，恢复生成按钮状态
            if callback is None:
                self.root.after(0, lambda: self.generate_btn.config(text="生成视频", state=tk.NORMAL, bg="#4CAF50"))
            else:
                # 调用回调函数处理下一个视频
                self.root.after(100, callback)
    
    def extract_audio_info(self, audio_file):
        """提取音频文件的元数据"""
        title = os.path.basename(audio_file)
        artist = ""
        duration = 0
        
        try:
            # 根据文件扩展名选择不同的处理方法
            ext = os.path.splitext(audio_file)[1].lower()
            
            if ext == '.mp3':
                # 处理MP3文件
                audio = MP3(audio_file)
                
                # 尝试读取ID3标签
                if audio.tags:
                    # 尝试获取标题
                    if 'TIT2' in audio.tags:
                        title = str(audio.tags['TIT2'])
                    
                    # 尝试获取艺术家
                    if 'TPE1' in audio.tags:
                        artist = str(audio.tags['TPE1'])
                
                # 获取持续时间（秒）
                duration = audio.info.length
                
            elif ext == '.flac':
                # 处理FLAC文件
                from mutagen.flac import FLAC
                audio = FLAC(audio_file)
                
                # 尝试获取标题
                if 'title' in audio:
                    title = audio['title'][0]
                
                # 尝试获取艺术家
                if 'artist' in audio:
                    artist = audio['artist'][0]
                
                # 获取持续时间（秒）
                duration = audio.info.length
                
            elif ext == '.wav':
                # 处理WAV文件
                from mutagen.wave import WAVE
                audio = WAVE(audio_file)
                
                # WAV文件可能没有元数据，直接使用文件名作为标题
                # 获取持续时间（秒）
                duration = audio.info.length
            
            elif ext == '.wma':
                # 处理WMA文件
                from mutagen.asf import ASF
                audio = ASF(audio_file)
                
                # 尝试获取标题
                if 'Title' in audio:
                    title = str(audio['Title'][0])
                
                # 尝试获取艺术家
                if 'Author' in audio:
                    artist = str(audio['Author'][0])
                
                # 获取持续时间（秒）
                duration = audio.info.length
                
            elif ext in ['.m4a', '.aac']:
                # 处理M4A/AAC文件
                from mutagen.mp4 import MP4
                audio = MP4(audio_file)
                
                # 尝试获取标题
                if '\xa9nam' in audio:
                    title = audio['\xa9nam'][0]
                
                # 尝试获取艺术家
                if '\xa9ART' in audio:
                    artist = audio['\xa9ART'][0]
                
                # 获取持续时间（秒）
                duration = audio.info.length
                
            else:
                # 对于不支持的格式，使用FFmpeg获取时长
                import subprocess
                command = [
                    'ffmpeg', 
                    '-i', audio_file,
                    '-f', 'null',
                    '-'
                ]
                
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                _, stderr = process.communicate()
                
                # 从输出中解析持续时间
                duration_match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", stderr)
                if duration_match:
                    hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
                    duration = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
            
            # 如果没有提取到标题，使用文件名（不包含扩展名）
            if not title or title == "None":
                title = os.path.splitext(os.path.basename(audio_file))[0]
            
            # 如果文件名是 "艺术家-歌曲名" 格式，尝试提取
            if not artist and "-" in title:
                parts = title.split("-", 1)
                if len(parts) == 2:
                    artist = parts[0].strip()
                    title = parts[1].strip()
            
        except Exception as e:
            print(f"提取音频信息时出错: {str(e)}")
            # 如果出错，使用文件名（不包含扩展名）作为标题
            title = os.path.splitext(os.path.basename(audio_file))[0]
            
            # 尝试使用FFmpeg获取时长
            try:
                import subprocess
                command = [
                    'ffmpeg', 
                    '-i', audio_file,
                    '-f', 'null',
                    '-'
                ]
                
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                _, stderr = process.communicate()
                
                # 从输出中解析持续时间
                duration_match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", stderr)
                if duration_match:
                    hours, minutes, seconds, centiseconds = map(int, duration_match.groups())
                    duration = hours * 3600 + minutes * 60 + seconds + centiseconds / 100
            except:
                # 如果FFmpeg也失败，使用默认值
                duration = 0
        
        return title, artist, duration
    
    def format_time(self, seconds):
        """将秒数格式化为时:分:秒格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def create_image_with_playlist(self, music_info, output_path):
        try:
            # 打开原始图片
            img = Image.open(self.image_file)
            
            # 确保图片是1080p (1920x1080)
            if img.size != (1920, 1080):
                img = img.resize((1920, 1080), Image.LANCZOS)
            
            # 如果有叠加图片，处理叠加效果
            if self.overlay_image and os.path.exists(self.overlay_image):
                try:
                    # 打开叠加图片
                    overlay = Image.open(self.overlay_image)
                    # 将叠加图片调整为相同大小
                    overlay = overlay.resize((1920, 1080), Image.LANCZOS)
                    
                    # 确保叠加图片有Alpha通道，如果没有则添加
                    if overlay.mode != 'RGBA':
                        overlay = overlay.convert('RGBA')
                    
                    # 如果背景图片没有Alpha通道，添加一个
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    # 叠加图片
                    img = Image.alpha_composite(img, overlay)
                    
                    # 转回RGB模式，因为有些处理需要RGB模式
                    img = img.convert('RGB')
                except Exception as e:
                    print(f"处理叠加图片时出错: {str(e)}")
                    # 如果叠加过程出错，继续使用原始图片
            
            # 创建绘图对象
            draw = ImageDraw.Draw(img)
            
            # 左侧区域的宽度和位置
            panel_width = 1800  # 增加到接近视频宽度(1920)，留出一些边距
            x_start = 20  # 从左侧开始
            
            # 加载字体
            try:
                if os.name == 'nt':  # Windows
                    title_font_path = "C:\\Windows\\Fonts\\simhei.ttf"  # 黑体
                    time_font_path = "C:\\Windows\\Fonts\\simhei.ttf"   # 黑体
                else:  # Linux/Mac
                    title_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                    time_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                
                if os.path.exists(title_font_path) and os.path.exists(time_font_path):
                    # 使用用户设置的字体大小
                    title_font_size = self.title_font_size.get()
                    playlist_font_size = self.playlist_font_size.get()
                    
                    title_font = ImageFont.truetype(title_font_path, title_font_size)
                    playlist_font = ImageFont.truetype(time_font_path, playlist_font_size)
                else:
                    title_font = ImageFont.load_default()
                    playlist_font = ImageFont.load_default()
            except Exception as e:
                print(f"加载字体时出错: {str(e)}")
                title_font = ImageFont.load_default()
                playlist_font = ImageFont.load_default()
            
            # 为文本添加阴影效果以增强可读性
            shadow_offset = 2
            shadow_color = "black"
            
            # 调整标题位置，根据字体大小调整
            title_font_size = self.title_font_size.get()
            title_y = 30
            divider_y = title_y + title_font_size + 20  # 分隔线位置随标题字体大小调整
            
            # 添加标题
            title_text = "歌曲列表"
            # 添加阴影效果
            draw.text((x_start + shadow_offset, title_y + shadow_offset), title_text, 
                    fill=shadow_color, font=title_font)
            # 添加主文本
            draw.text((x_start, title_y), title_text, fill="white", font=title_font)
            
            # 绘制分隔线 (带阴影)
            draw.line([(x_start + shadow_offset, divider_y + shadow_offset), (x_start + panel_width + shadow_offset, divider_y + shadow_offset)], 
                    fill=shadow_color, width=2)
            draw.line([(x_start, divider_y), (x_start + panel_width, divider_y)], fill="white", width=2)
            
            # 添加歌曲列表，起始位置也随字体大小调整
            y_position = divider_y + 40
            
            # 计算动态间距，根据字体大小调整
            font_size = self.playlist_font_size.get()
            number_width = 40 * (font_size / 24)  # 序号宽度根据字体大小调整
            time_width = 100 * (font_size / 24)   # 时间宽度根据字体大小调整
            line_height = max(40, font_size * 1.6)  # 减小行高，但保持最小高度为40像素
            
            for i, info in enumerate(music_info):
                # 歌曲序号 (带阴影)
                number_text = f"{i+1}."
                draw.text((x_start + shadow_offset, y_position + shadow_offset), number_text, 
                       fill=shadow_color, font=playlist_font)
                draw.text((x_start, y_position), number_text, fill="white", font=playlist_font)
                
                # 歌曲开始时间 (带阴影)
                time_x = x_start + number_width
                time_text = info['start_time_fmt']
                draw.text((time_x + shadow_offset, y_position + shadow_offset), time_text, 
                       fill=shadow_color, font=playlist_font)
                draw.text((time_x, y_position), time_text, 
                       fill="#00FFFF", font=playlist_font)  # 青色显示时间
                
                # 歌曲名称
                name_x = x_start + number_width + time_width
                # 如果歌曲名称过长，进行裁剪
                display_name = info['display_name']
                
                # 确保歌曲名称不包含文件扩展名
                display_name = os.path.splitext(display_name)[0]
                
                max_width = panel_width - (number_width + time_width + 20)  # 动态计算最大宽度
                
                if draw.textlength(display_name, font=playlist_font) > max_width:
                    # 裁剪歌曲名称使其适应区域宽度
                    while draw.textlength(display_name + "...", font=playlist_font) > max_width and len(display_name) > 1:
                        display_name = display_name[:-1]
                    display_name += "..."
                
                # 添加文字阴影效果
                draw.text((name_x + shadow_offset, y_position + shadow_offset), display_name, 
                       fill=shadow_color, font=playlist_font)
                # 添加主文本
                draw.text((name_x, y_position), display_name, 
                       fill="white", font=playlist_font)
                
                y_position += line_height
            
            # 保存处理后的图片
            img.save(output_path)
            
        except Exception as e:
            raise Exception(f"处理图片时出错: {str(e)}")
    
    def check_lyrics_exist(self, audio_file):
        """检查音频文件是否包含歌词"""
        try:
            print(f"\n开始检查歌词: {os.path.basename(audio_file)}")
            
            # 1. 检查是否有同名的.lrc文件
            base_name = os.path.splitext(audio_file)[0]
            lrc_file = base_name + '.lrc'
            if os.path.exists(lrc_file):
                print(f"找到外部LRC文件: {lrc_file}")
                return True
            
            # 2. 检查歌词文件夹中是否有对应的歌词文件
            if self.lyrics_folder and os.path.exists(self.lyrics_folder):
                # 获取音频文件名（不含路径和扩展名）
                audio_filename = os.path.basename(audio_file)
                filename_no_ext = os.path.splitext(audio_filename)[0]
                
                # 检查歌词文件夹中可能的歌词文件名
                possible_names = [
                    f"{filename_no_ext}.lrc",
                    f"{filename_no_ext}.LRC"
                ]
                
                # 如果文件名包含艺术家和歌曲名信息（如"艺术家-歌曲名"格式）
                if '-' in filename_no_ext:
                    artist, title = filename_no_ext.split('-', 1)
                    artist = artist.strip()
                    title = title.strip()
                    
                    possible_names.extend([
                        f"{artist} - {title}.lrc",
                        f"{title}.lrc",
                        f"{artist}-{title}.lrc"
                    ])
                
                # 检查所有可能的文件名
                for lrc_name in possible_names:
                    lrc_path = os.path.join(self.lyrics_folder, lrc_name)
                    if os.path.exists(lrc_path):
                        print(f"在歌词文件夹中找到对应歌词: {lrc_path}")
                        return True
            
            print(f"没有找到歌词: {audio_file}")
            return False
        except Exception as e:
            print(f"检查歌词时出错: {str(e)}")
            return False
         

    def parse_lrc_content(self, lrc_content):
        """解析LRC格式的歌词内容"""
        lyrics = []
        
        if not lrc_content or len(lrc_content.strip()) < 10:  # 太短的内容可能不是歌词
            return None
        
        try:
            # 解析各种可能的时间标记格式
            # 标准LRC: [mm:ss.xx]
            time_pattern1 = r'\[(\d+):(\d+)\.(\d+)\](.*)'
            # 简化格式: [mm:ss]
            time_pattern2 = r'\[(\d+):(\d+)\](.*)'
            # 其他可能的格式: (mm:ss)
            time_pattern3 = r'\((\d+):(\d+)\)(.*)'
            
            lines_with_time = 0  # 计数包含时间标记的行数
            
            for line in lrc_content.split('\n'):
                match1 = re.search(time_pattern1, line)
                match2 = re.search(time_pattern2, line)
                match3 = re.search(time_pattern3, line)
                
                if match1:
                    minutes = int(match1.group(1))
                    seconds = int(match1.group(2))
                    centiseconds = int(match1.group(3))
                    text = match1.group(4).strip()
                    
                    time_in_seconds = minutes * 60 + seconds + centiseconds / 100
                    lines_with_time += 1
                elif match2:
                    minutes = int(match2.group(1))
                    seconds = int(match2.group(2))
                    text = match2.group(3).strip()
                    
                    time_in_seconds = minutes * 60 + seconds
                    lines_with_time += 1
                elif match3:
                    minutes = int(match3.group(1))
                    seconds = int(match3.group(2))
                    text = match3.group(3).strip()
                    
                    time_in_seconds = minutes * 60 + seconds
                    lines_with_time += 1
                else:
                    continue  # 跳过没有时间标记的行
                
                if text:  # 只添加有内容的歌词
                    lyrics.append({
                        'time': time_in_seconds,
                        'text': text
                    })
            
            # 如果大部分行都有时间标记，说明这是歌词
            if lines_with_time > 5 or (lines_with_time > 0 and lines_with_time / len(lrc_content.split('\n')) > 0.3):
                return sorted(lyrics, key=lambda x: x['time'])  # 按时间排序
        
        except Exception as e:
            print(f"解析歌词内容时出错: {str(e)}")
        
        # 如果未找到足够的歌词行，返回None
        return lyrics if lyrics else None

    def check_selected_lyrics(self):
        """检查选中歌曲的歌词并显示调试信息"""
        try:
            selection = self.music_list.curselection()
            if not selection:
                messagebox.showinfo("提示", "请先选择一首音乐")
                return
                
            index = selection[0]
            music_file = self.music_files[index]
            
            # 创建日志捕获器
            class LogCapture:
                def __init__(self):
                    self.log = []
                    
                def write(self, message):
                    self.log.append(message)
                    
                def flush(self):
                    pass
                    
                def get_log(self):
                    return ''.join(self.log)
            
            # 捕获日志输出
            old_stdout = sys.stdout
            log_capture = LogCapture()
            sys.stdout = log_capture
            
            try:
                # 运行检查
                has_lyrics = self.check_lyrics_exist(music_file)
                
                # 添加检查结果
                if has_lyrics:
                    log_capture.log.append("\n\n结果: 文件包含歌词")
                else:
                    log_capture.log.append("\n\n结果: 文件不包含歌词")
                    
                # 创建一个带滚动条的文本查看窗口
                result_window = tk.Toplevel(self.root)
                result_window.title(f"歌词检查结果: {os.path.basename(music_file)}")
                result_window.geometry("800x600")
                
                frame = tk.Frame(result_window)
                frame.pack(fill=tk.BOTH, expand=True)
                
                scrollbar = tk.Scrollbar(frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                text_area = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
                text_area.pack(fill=tk.BOTH, expand=True)
                
                scrollbar.config(command=text_area.yview)
                
                # 插入日志内容
                text_area.insert(tk.END, log_capture.get_log())
                text_area.config(state=tk.DISABLED)  # 设置为只读
                
                # 添加关闭按钮
                close_btn = tk.Button(result_window, text="关闭", command=result_window.destroy, 
                                    bg="#f44336", fg="white", font=("Arial", 10), width=15)
                close_btn.pack(pady=10)
                
            finally:
                # 恢复标准输出
                sys.stdout = old_stdout
                
        except Exception as e:
            messagebox.showerror("错误", f"检查歌词时出错: {str(e)}")
            # 确保标准输出被恢复
            if 'old_stdout' in locals():
                sys.stdout = old_stdout

    def add_lyrics_to_selected(self):
        """为选定的音乐添加LRC歌词文件"""
        try:
            selection = self.music_list.curselection()
            if not selection:
                messagebox.showinfo("提示", "请先选择一首音乐")
                return
                
            index = selection[0]
            music_file = self.music_files[index]
            
            # 选择LRC文件
            lrc_file = filedialog.askopenfilename(
                title="选择LRC歌词文件",
                filetypes=(("LRC歌词文件", "*.lrc"), ("文本文件", "*.txt"), ("所有文件", "*.*"))
            )
            
            if not lrc_file:
                return  # 用户取消选择
            
            # 提供两种选项：直接复制到音乐文件旁边或复制到歌词文件夹
            option_window = tk.Toplevel(self.root)
            option_window.title("选择保存位置")
            option_window.geometry("400x150")
            option_window.transient(self.root)  # 设置为父窗口的临时窗口
            option_window.grab_set()  # 模态窗口
            
            # 标签
            tk.Label(option_window, text="请选择保存歌词文件的位置:", font=("Arial", 12)).pack(pady=10)
            
            # 选项变量
            save_option = tk.IntVar(value=1)
            
            # 选项1: 保存到音乐文件旁边
            tk.Radiobutton(option_window, text="保存到音乐文件旁边", variable=save_option, value=1).pack(anchor=tk.W, padx=20)
            
            # 选项2: 保存到歌词文件夹（如果已经设置）
            lyrics_folder_option = tk.Radiobutton(option_window, text=f"保存到歌词文件夹: {self.lyrics_folder}", variable=save_option, value=2)
            lyrics_folder_option.pack(anchor=tk.W, padx=20)
            
            # 如果未设置歌词文件夹，禁用第二个选项
            if not self.lyrics_folder:
                lyrics_folder_option.config(state=tk.DISABLED)
                save_option.set(1)  # 默认选择第一个选项
            
            # 按钮框架
            btn_frame = tk.Frame(option_window)
            btn_frame.pack(pady=10)
            
            # 确认和取消按钮
            confirm_btn = tk.Button(btn_frame, text="确定", command=lambda: save_lyrics(save_option.get()), bg="#4CAF50", fg="white", width=10)
            confirm_btn.pack(side=tk.LEFT, padx=10)
            
            cancel_btn = tk.Button(btn_frame, text="取消", command=option_window.destroy, bg="#f44336", fg="white", width=10)
            cancel_btn.pack(side=tk.LEFT, padx=10)
            
            def save_lyrics(option):
                try:
                    if option == 1:
                        # 保存到音乐文件旁边
                        target_lrc = os.path.splitext(music_file)[0] + ".lrc"
                    else:
                        # 保存到歌词文件夹
                        music_filename = os.path.basename(music_file)
                        filename_no_ext = os.path.splitext(music_filename)[0]
                        target_lrc = os.path.join(self.lyrics_folder, filename_no_ext + ".lrc")
                    
                    # 如果目标文件已存在，询问是否覆盖
                    if os.path.exists(target_lrc):
                        if not messagebox.askyesno("确认", f"歌词文件 {os.path.basename(target_lrc)} 已存在，是否覆盖?"):
                            option_window.destroy()
                            return
                    
                    # 复制歌词文件
                    import shutil
                    shutil.copy2(lrc_file, target_lrc)
                    
                    # 更新UI
                    self.update_music_list_ui()
                    # 重新选择之前选中的项目
                    self.select_music_item(index)
                    
                    messagebox.showinfo("成功", f"已成功添加歌词文件到 {os.path.basename(music_file)}")
                    option_window.destroy()
                    
                except Exception as e:
                    messagebox.showerror("错误", f"添加歌词时出错: {str(e)}")
                    option_window.destroy()
                
        except Exception as e:
            messagebox.showerror("错误", f"添加歌词时出错: {str(e)}")
    
    def has_lyrics(self, music_file):
        """检查音乐文件是否有歌词，支持同名lrc文件和歌词文件夹中的歌词"""
        try:
            # 1. 检查是否有同名的.lrc文件
            base_name = os.path.splitext(music_file)[0]
            lrc_file = base_name + '.lrc'
            if os.path.exists(lrc_file):
                return True
            
            # 2. 检查歌词文件夹中是否有对应的歌词文件
            if self.lyrics_folder and os.path.exists(self.lyrics_folder):
                # 获取音频文件名（不含路径和扩展名）
                audio_filename = os.path.basename(music_file)
                filename_no_ext = os.path.splitext(audio_filename)[0]
                
                # 检查歌词文件夹中是否存在对应的歌词文件
                lrc_path = os.path.join(self.lyrics_folder, filename_no_ext + ".lrc")
                if os.path.exists(lrc_path):
                    return True
                
                # 如果文件名包含艺术家和歌曲名信息（如"艺术家-歌曲名"格式）
                if '-' in filename_no_ext:
                    artist, title = filename_no_ext.split('-', 1)
                    artist = artist.strip()
                    title = title.strip()
                    
                    # 检查可能的歌词文件名格式
                    possible_names = [
                        f"{artist} - {title}.lrc",
                        f"{title}.lrc",
                        f"{artist}-{title}.lrc"
                    ]
                    
                    for lrc_name in possible_names:
                        lrc_path = os.path.join(self.lyrics_folder, lrc_name)
                        if os.path.exists(lrc_path):
                            return True
            
            return False
        except Exception as e:
            print(f"检查歌词存在性时出错: {str(e)}")
            return False

    def convert_lrc_to_subtitle(self, music_info, output_srt):
        """将LRC歌词文件转换为SRT字幕文件"""
        try:
            with open(output_srt, 'w', encoding='utf-8') as srt_file:
                subtitle_index = 1
                
                # 添加字体大小设置
                srt_file.write("1\n")
                srt_file.write("00:00:00,000 --> 00:00:00,000\n")
                srt_file.write(f"<font size=\"{self.lyrics_font_size.get()}\">\n\n")
                
                for info in music_info:
                    if not info['has_lyrics'] or not info['lyrics_path']:
                        continue
                    
                    # 读取LRC文件
                    lrc_content = ""
                    try:
                        # 尝试不同的编码读取LRC文件
                        encodings = ['utf-8', 'gbk', 'big5', 'latin1']
                        for encoding in encodings:
                            try:
                                with open(info['lyrics_path'], 'r', encoding=encoding) as f:
                                    lrc_content = f.read()
                                    break
                            except UnicodeDecodeError:
                                continue
                    except Exception as e:
                        print(f"读取歌词文件出错: {str(e)}")
                        continue
                    
                    if not lrc_content:
                        continue
                    
                    # 解析LRC内容
                    lyrics_data = self.parse_lrc_content(lrc_content)
                    if not lyrics_data:
                        continue
                    
                    # 歌曲起始时间（秒）
                    song_start_time = info['start_time']
                    
                    # 将LRC转换为SRT格式
                    for i in range(len(lyrics_data)):
                        lyric = lyrics_data[i]
                        
                        # 计算字幕开始和结束时间
                        start_time = song_start_time + lyric['time']
                        
                        # 确定字幕结束时间（使用下一句歌词的开始时间，或者使用当前歌词开始时间加上默认显示时间）
                        if i < len(lyrics_data) - 1:
                            end_time = song_start_time + lyrics_data[i+1]['time']
                        else:
                            # 如果是当前歌曲的最后一句歌词，结束时间为当前时间+5秒
                            end_time = start_time + 5
                        
                        # 确保字幕结束时间不超过歌曲结束时间
                        song_end_time = song_start_time + info['duration']
                        if end_time > song_end_time:
                            end_time = song_end_time
                        
                        # 格式化时间为SRT格式：00:00:00,000
                        start_time_str = self.format_time_srt(start_time)
                        end_time_str = self.format_time_srt(end_time)
                        
                        # 如果歌词为空，则跳过
                        if not lyric['text'].strip():
                            continue
                        
                        # 写入SRT条目，添加字体大小标签
                        srt_file.write(f"{subtitle_index}\n")
                        srt_file.write(f"{start_time_str} --> {end_time_str}\n")
                        srt_file.write(f"{lyric['text']}\n\n")
                        
                        subtitle_index += 1
            
            return True
        except Exception as e:
            print(f"转换歌词到字幕时出错: {str(e)}")
            return False
    
    def format_time_srt(self, seconds):
        """将秒数格式化为SRT时间格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds_part = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds_part:02d},{milliseconds:03d}"

    def format_elapsed_time(self, seconds):
        """格式化已用时间为 HH:MM:SS 格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def clear_music_list(self):
        """清空已选择的所有音乐文件"""
        if not self.music_files:
            return
            
        # 确认是否清空
        response = messagebox.askyesno("确认", "确定要清空所有已选择的歌曲吗？")
        if not response:
            return
            
        # 清空列表
        self.music_files = []
        self.music_list.delete(0, tk.END)
        
        # 清空UI
        for widget in self.music_items_frame.winfo_children():
            widget.destroy()
        
        # 清空引用列表
        self.music_item_frames = []
        
        # 更新UI状态
        self.status_label.config(text="已清空所有歌曲")

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicVideoGenerator(root)
    root.mainloop() 