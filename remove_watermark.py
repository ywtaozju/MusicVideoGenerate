import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import os
from tkinter import ttk

class WatermarkRemover:
    def __init__(self, root):
        self.root = root
        self.root.title("水印去除工具")
        self.root.geometry("1200x800")
        
        # 初始化变量
        self.original_image = None
        self.current_image = None
        self.mask = None
        self.drawing = False
        self.last_x = None
        self.last_y = None
        self.brush_size = 20
        self.current_mask_positions = []  # 存储当前标记的位置
        
        self.setup_ui()
    
    def setup_ui(self):
        # 创建主框架
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建按钮框架
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # 添加按钮
        tk.Button(button_frame, text="打开图片", command=self.open_image).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="清除标记", command=self.clear_mask).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="去除水印", command=self.remove_watermark).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="保存图片", command=self.save_image).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="批量处理文件夹", command=self.batch_process).pack(side=tk.LEFT, padx=5)
        
        # 创建画笔大小调整框架
        brush_frame = tk.Frame(main_frame)
        brush_frame.pack(fill=tk.X, pady=5)
        
        # 添加画笔大小标签
        tk.Label(brush_frame, text="画笔大小:").pack(side=tk.LEFT, padx=5)
        
        # 添加画笔大小Spinbox
        self.brush_size_var = tk.StringVar(value=str(self.brush_size))
        self.brush_size_spinbox = tk.Spinbox(brush_frame, from_=1, to=50, 
                                           textvariable=self.brush_size_var,
                                           width=5,
                                           command=self.update_brush_size)
        self.brush_size_spinbox.pack(side=tk.LEFT, padx=5)
        
        # 创建画布框架
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建画布
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标事件
        self.canvas.bind("<Button-1>", self.start_drawing)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drawing)
        
        # 添加提示标签
        self.status_label = tk.Label(main_frame, text="请打开一张图片，然后在需要去除水印的区域用鼠标绘制", 
                                   bg="#f0f0f0", pady=5)
        self.status_label.pack(fill=tk.X)
    
    def open_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        if file_path:
            try:
                # 使用numpy读取图片，避免中文路径问题
                self.original_image = np.fromfile(file_path, np.uint8)
                self.original_image = cv2.imdecode(self.original_image, cv2.IMREAD_COLOR)
                if self.original_image is None:
                    raise Exception("无法读取图片")
                
                # 转换颜色空间
                self.original_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2RGB)
                
                # 创建掩码
                self.mask = np.zeros(self.original_image.shape[:2], dtype=np.uint8)
                
                # 显示图片
                self.show_image(self.original_image)
                self.status_label.config(text="请在需要去除水印的区域用鼠标绘制")
                
            except Exception as e:
                messagebox.showerror("错误", f"打开图片时出错: {str(e)}")
    
    def show_image(self, image):
        # 调整图片大小以适应画布
        height, width = image.shape[:2]
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 计算缩放比例
        scale = min(canvas_width/width, canvas_height/height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # 调整图片大小
        resized = cv2.resize(image, (new_width, new_height))
        
        # 转换为PhotoImage
        image = Image.fromarray(resized)
        photo = ImageTk.PhotoImage(image=image)
        
        # 更新画布
        self.canvas.delete("all")
        self.canvas.create_image(canvas_width//2, canvas_height//2, 
                               image=photo, anchor=tk.CENTER)
        
        # 保存引用
        self.canvas.image = photo
    
    def start_drawing(self, event):
        self.drawing = True
        self.last_x = event.x
        self.last_y = event.y
    
    def draw(self, event):
        if self.drawing and self.original_image is not None:
            # 获取画布上的坐标
            x, y = event.x, event.y
            
            # 转换坐标到原始图片尺寸
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            height, width = self.original_image.shape[:2]
            
            # 计算实际坐标
            scale_x = width / canvas_width
            scale_y = height / canvas_height
            img_x = int(x * scale_x)
            img_y = int(y * scale_y)
            
            # 绘制掩码
            cv2.circle(self.mask, (img_x, img_y), self.brush_size, 255, -1)
            
            # 保存标记位置
            self.current_mask_positions.append((img_x, img_y))
            
            # 更新显示
            self.update_preview()
            
            self.last_x = x
            self.last_y = y
    
    def stop_drawing(self, event):
        self.drawing = False
    
    def update_preview(self):
        if self.original_image is not None and self.mask is not None:
            # 创建预览图片
            preview = self.original_image.copy()
            # 在预览图片上显示标记区域
            preview[self.mask == 255] = [255, 0, 0]  # 红色标记
            self.show_image(preview)
    
    def clear_mask(self):
        if self.original_image is not None:
            self.mask = np.zeros(self.original_image.shape[:2], dtype=np.uint8)
            self.current_mask_positions = []  # 清除标记位置
            self.show_image(self.original_image)
            self.status_label.config(text="已清除标记，请重新标记水印区域")
    
    def remove_watermark(self):
        if self.original_image is None or self.mask is None:
            messagebox.showwarning("警告", "请先打开一张图片并标记水印区域")
            return
        
        try:
            # 转换回BGR颜色空间
            image_bgr = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2BGR)
            
            # 使用inpaint算法去除水印
            result = cv2.inpaint(image_bgr, self.mask, 3, cv2.INPAINT_TELEA)
            
            # 转换回RGB颜色空间并显示
            result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
            self.current_image = result_rgb
            self.show_image(result_rgb)
            
            self.status_label.config(text="水印已去除，可以保存图片")
            
        except Exception as e:
            messagebox.showerror("错误", f"去除水印时出错: {str(e)}")
    
    def save_image(self):
        if self.current_image is None:
            messagebox.showwarning("警告", "没有可保存的图片")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG文件", "*.png"), ("JPEG文件", "*.jpg"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                # 转换回BGR颜色空间
                save_image = cv2.cvtColor(self.current_image, cv2.COLOR_RGB2BGR)
                # 使用imencode保存图片
                _, img_encoded = cv2.imencode('.png', save_image)
                img_encoded.tofile(file_path)
                messagebox.showinfo("成功", "图片已保存")
                self.status_label.config(text="图片已保存")
            except Exception as e:
                messagebox.showerror("错误", f"保存图片时出错: {str(e)}")

    def batch_process(self):
        if not self.current_mask_positions:
            messagebox.showwarning("警告", "请先标记水印位置")
            return
            
        # 选择输入文件夹
        input_folder = filedialog.askdirectory(title="选择包含图片的文件夹")
        if not input_folder:
            return
            
        # 选择输出文件夹
        output_folder = filedialog.askdirectory(title="选择保存处理后图片的文件夹")
        if not output_folder:
            return
            
        try:
            # 获取所有支持的图片文件
            supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
            image_files = [f for f in os.listdir(input_folder) 
                         if f.lower().endswith(supported_formats)]
            
            if not image_files:
                messagebox.showwarning("警告", "所选文件夹中没有找到支持的图片文件")
                return
                
            # 创建进度窗口
            progress_window = tk.Toplevel(self.root)
            progress_window.title("处理进度")
            progress_window.geometry("300x150")
            
            progress_label = tk.Label(progress_window, text="正在处理...")
            progress_label.pack(pady=10)
            
            progress_bar = ttk.Progressbar(progress_window, length=200, mode='determinate')
            progress_bar.pack(pady=10)
            
            # 处理每张图片
            total_files = len(image_files)
            for i, image_file in enumerate(image_files):
                # 更新进度
                progress = (i + 1) / total_files * 100
                progress_bar['value'] = progress
                progress_label.config(text=f"正在处理: {image_file} ({i+1}/{total_files})")
                progress_window.update()
                
                # 读取图片
                input_path = os.path.join(input_folder, image_file)
                img_data = np.fromfile(input_path, np.uint8)
                img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                
                if img is None:
                    print(f"无法读取图片: {image_file}")
                    continue
                
                # 创建掩码
                mask = np.zeros(img.shape[:2], dtype=np.uint8)
                
                # 根据原始图片尺寸调整标记位置
                scale_x = img.shape[1] / self.original_image.shape[1]
                scale_y = img.shape[0] / self.original_image.shape[0]
                
                for pos_x, pos_y in self.current_mask_positions:
                    new_x = int(pos_x * scale_x)
                    new_y = int(pos_y * scale_y)
                    cv2.circle(mask, (new_x, new_y), int(self.brush_size * scale_x), 255, -1)
                
                # 去除水印
                result = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
                
                # 保存结果
                output_path = os.path.join(output_folder, f"processed_{image_file}")
                # 使用imencode保存图片
                _, img_encoded = cv2.imencode('.png', result)
                img_encoded.tofile(output_path)
            
            # 关闭进度窗口
            progress_window.destroy()
            
            messagebox.showinfo("成功", f"已处理 {total_files} 张图片")
            self.status_label.config(text=f"批量处理完成，共处理 {total_files} 张图片")
            
        except Exception as e:
            messagebox.showerror("错误", f"批量处理时出错: {str(e)}")
            if 'progress_window' in locals():
                progress_window.destroy()

    def update_brush_size(self):
        """更新画笔大小"""
        try:
            new_size = int(self.brush_size_var.get())
            if new_size < 1:
                new_size = 1
            elif new_size > 50:
                new_size = 50
            self.brush_size = new_size
            self.brush_size_var.set(str(new_size))
        except ValueError:
            # 如果输入无效，恢复原值
            self.brush_size_var.set(str(self.brush_size))

if __name__ == "__main__":
    root = tk.Tk()
    app = WatermarkRemover(root)
    root.mainloop()