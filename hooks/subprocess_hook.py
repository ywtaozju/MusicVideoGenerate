
# hook用于隐藏子进程的控制台窗口
import subprocess
import sys

# 如果在Windows上，修改subprocess.Popen类，默认添加隐藏控制台窗口的标志
if sys.platform == 'win32':
    # 保存原始的Popen构造函数
    original_popen_init = subprocess.Popen.__init__
    
    # 创建一个新的初始化函数，它会添加隐藏窗口的标志
    def popen_init_no_window(self, *args, **kwargs):
        # 如果没有指定creationflags，添加CREATE_NO_WINDOW标志
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        
        # 调用原始初始化函数
        original_popen_init(self, *args, **kwargs)
    
    # 替换原始的初始化函数
    subprocess.Popen.__init__ = popen_init_no_window
