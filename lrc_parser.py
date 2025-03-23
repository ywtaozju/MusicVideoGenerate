import re
import os

class LRCParser:
    """
    简单的LRC歌词文件解析器
    """
    def __init__(self, lrc_file=None):
        self.lyrics = []
        self.time_mapping = {}
        
        if lrc_file and os.path.exists(lrc_file):
            self.parse_file(lrc_file)
    
    def parse_file(self, lrc_file):
        """
        解析LRC文件并提取时间戳和歌词
        """
        try:
            with open(lrc_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 如果读取失败，尝试不同的编码
            if not lines:
                with open(lrc_file, 'r', encoding='gbk') as f:
                    lines = f.readlines()
            
            self.parse_lines(lines)
            return True
        except Exception as e:
            print(f"解析歌词文件时出错: {str(e)}")
            return False
    
    def parse_lines(self, lines):
        """
        解析LRC格式的行
        """
        # 正则表达式匹配时间标签 [mm:ss.xx]
        time_pattern = re.compile(r'\[(\d+):(\d+)\.(\d+)\]')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找所有时间标签
            matches = time_pattern.findall(line)
            if not matches:
                continue
            
            # 提取歌词文本（删除所有时间标签）
            lyric = time_pattern.sub('', line).strip()
            
            # 如果有歌词内容，将其存储在时间映射中
            if lyric:
                for match in matches:
                    try:
                        minutes = int(match[0])
                        seconds = int(match[1])
                        milliseconds = int(match[2])
                        
                        # 将时间转换为毫秒
                        time_ms = minutes * 60 * 1000 + seconds * 1000 + milliseconds * 10
                        
                        self.time_mapping[time_ms] = lyric
                        self.lyrics.append((time_ms, lyric))
                    except:
                        continue
        
        # 按时间戳排序
        self.lyrics.sort(key=lambda x: x[0])
    
    def get_subtitle_file(self, output_file):
        """
        生成SRT字幕文件
        """
        if not self.lyrics:
            return None
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, (time_ms, lyric) in enumerate(self.lyrics):
                    # SRT格式: 序号, 开始时间 --> 结束时间, 歌词文本
                    start_time = self._ms_to_srt_time(time_ms)
                    
                    # 计算结束时间（下一句歌词的时间或当前时间+5秒）
                    if i < len(self.lyrics) - 1:
                        end_time = self._ms_to_srt_time(self.lyrics[i+1][0])
                    else:
                        end_time = self._ms_to_srt_time(time_ms + 5000)  # 最后一句显示5秒
                    
                    f.write(f"{i+1}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{lyric}\n\n")
            
            return output_file
        except Exception as e:
            print(f"生成字幕文件时出错: {str(e)}")
            return None
    
    def _ms_to_srt_time(self, ms):
        """
        将毫秒转换为SRT时间格式 (HH:MM:SS,MMM)
        """
        hours = ms // (3600 * 1000)
        ms %= 3600 * 1000
        minutes = ms // (60 * 1000)
        ms %= 60 * 1000
        seconds = ms // 1000
        ms %= 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}" 