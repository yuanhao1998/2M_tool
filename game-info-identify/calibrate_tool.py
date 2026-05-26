"""交互式校准工具：在截图上用鼠标框选区域，自动写入 config.yaml。"""

import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk
from ruamel.yaml import YAML




class RegionSelector:
    def __init__(self, image_path: str, config_path: str):
        self.config_path = config_path
        self.regions = {}
        self.current_region = None
        self.start_x = None
        self.start_y = None
        self.step = 0
        self.steps = [
            ("diamond_region", "框选「钻石数量」区域，按空格确认"),
            ("name_region", "框选「云机名称」区域，按空格确认（不需要则直接按空格跳过）"),
            ("next_button", "点击「切换按钮」的位置，按空格确认"),
        ]
        self.rect_id = None
        self.point_id = None

        self.root = tk.Tk()
        self.root.title("校准工具 - 滚轮缩放 拖拽平移 框选区域 空格确认")

        # 获取屏幕大小，窗口最大为屏幕的 90%
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(self.root.winfo_screenwidth(), int(screen_w * 0.9))
        win_h = min(self.root.winfo_screenheight(), int(screen_h * 0.85))

        # 加载原始截图
        self.pil_image = Image.open(image_path)
        self.orig_w = self.pil_image.width
        self.orig_h = self.pil_image.height
        self.scale = 1.0

        if self.orig_w > win_w or self.orig_h > win_h:
            self.scale = min(win_w / self.orig_w, win_h / self.orig_h)

        self._make_photo()
        if self.scale != 1.0:
            self.root.title(f"校准工具 - 已缩放至 {self.scale:.0%} - 滚轮缩放 拖拽平移 空格确认")

        canvas_w = min(self.scaled_w, win_w)
        canvas_h = min(self.scaled_h, win_h)

        # 滚动条容器
        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame, width=canvas_w, height=canvas_h,
                                cursor="cross", scrollregion=(0, 0, self.scaled_w, self.scaled_h))
        self.hbar = tk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.vbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

        self.canvas.grid(row=0, column=0, sticky=tk.NSEW)
        self.hbar.grid(row=1, column=0, sticky=tk.EW)
        self.vbar.grid(row=0, column=1, sticky=tk.NS)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW, tags="bg")

        # 信息栏
        self.info_var = tk.StringVar()
        info = tk.Label(self.root, textvariable=self.info_var, font=("", 14), pady=8)
        info.pack()

        # 提示快捷键
        hint = tk.Label(self.root, text="滚轮缩放 | 鼠标拖拽平移 | 框选区域 | 空格确认 | ESC退出",
                        font=("", 11), fg="gray")
        hint.pack(pady=(0, 4))

        # 绑定事件
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<B2-Motion>", self.on_pan)  # 中键拖拽平移
        self.canvas.bind("<Control-ButtonPress-1>", self.on_pan_start)  # Ctrl+左键平移
        self.canvas.bind("<Control-B1-Motion>", self.on_pan)
        self.root.bind("<MouseWheel>", self.on_zoom)  # macOS 滚轮缩放
        self.root.bind("<space>", self.on_confirm)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self._pan_x = None
        self._pan_y = None
        self._next_step()

    def _next_step(self):
        if self.step >= len(self.steps):
            self._save_and_exit()
            return
        name, hint = self.steps[self.step]
        self.info_var.set(f"步骤 {self.step + 1}/{len(self.steps)}: {hint}")
        self.current_region = name

    # ---- 坐标转换：画布坐标 ↔ 原始图片坐标 ----
    def _to_orig(self, cx, cy):
        """画布坐标转换为原始截图坐标。"""
        return int(cx / self.scale), int(cy / self.scale)

    def _to_canvas(self, ox, oy):
        """原始截图坐标转换为画布坐标。"""
        return ox * self.scale, oy * self.scale

    # ---- 平移 ----
    def on_pan_start(self, event):
        self._pan_x, self._pan_y = event.x, event.y

    def on_pan(self, event):
        if self._pan_x is None:
            return
        dx = self._pan_x - event.x
        dy = self._pan_y - event.y
        self.canvas.xview_scroll(dx, "units")
        self.canvas.yview_scroll(dy, "units")
        self._pan_x, self._pan_y = event.x, event.y

    # ---- 缩放 ----
    def on_zoom(self, event):
        """鼠标滚轮缩放。"""
        factor = 1.1 if event.delta > 0 else 0.9
        new_scale = self.scale * factor
        if new_scale < 0.2 or new_scale > 3.0:
            return
        self.scale = new_scale
        self._rebuild_photo()

    def _make_photo(self):
        """根据当前 scale 生成 tk PhotoImage。"""
        if self.scale == 1.0:
            img = self.pil_image
        else:
            new_w = max(1, int(self.orig_w * self.scale))
            new_h = max(1, int(self.orig_h * self.scale))
            img = self.pil_image.resize((new_w, new_h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)
        self.scaled_w = self.photo.width()
        self.scaled_h = self.photo.height()

    def _rebuild_photo(self):
        self._make_photo()
        self.canvas.delete("all")
        self.canvas.configure(scrollregion=(0, 0, self.scaled_w, self.scaled_h))
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW, tags="bg")
        self.rect_id = None
        self.point_id = None

    # ---- 框选 ----
    def on_press(self, event):
        name, _ = self.steps[self.step]
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self.start_x, self.start_y = self._to_orig(cx, cy)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

    def on_drag(self, event):
        name, _ = self.steps[self.step]
        if name == "next_button":
            return
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        ox, oy = self._to_orig(cx, cy)
        sx, sy = self._to_canvas(self.start_x, self.start_y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            sx, sy, cx, cy,
            outline="red", width=2, dash=(4, 2),
        )

    def on_release(self, event):
        name, _ = self.steps[self.step]
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        ox, oy = self._to_orig(cx, cy)

        if name == "next_button":
            x, y = self.start_x, self.start_y
            if self.point_id:
                for pid in (self.point_id if isinstance(self.point_id, tuple) else [self.point_id]):
                    self.canvas.delete(pid)
            r = max(8, int(10 / self.scale))
            sx, sy = self._to_canvas(x, y)
            pid1 = self.canvas.create_line(sx - r, sy, sx + r, sy, fill="lime", width=2)
            pid2 = self.canvas.create_line(sx, sy - r, sx, sy + r, fill="lime", width=2)
            self.point_id = (pid1, pid2)
            self.regions[name] = (x, y)
        else:
            x1, y1 = self.start_x, self.start_y
            x2, y2 = ox, oy
            left, right = sorted([x1, x2])
            top, bottom = sorted([y1, y2])
            self.regions[name] = (left, top, right, bottom)
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            sl, st = self._to_canvas(left, top)
            sr, sb = self._to_canvas(right, bottom)
            self.rect_id = self.canvas.create_rectangle(
                sl, st, sr, sb,
                outline="lime", width=2,
            )

    def on_confirm(self, event):
        name, _ = self.steps[self.step]
        if name == "name_region" and name not in self.regions:
            self.regions[name] = None
        elif name not in self.regions:
            return
        self.step += 1
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        if self.point_id:
            for pid in (self.point_id if isinstance(self.point_id, tuple) else [self.point_id]):
                self.canvas.delete(pid)
            self.point_id = None
        self._next_step()

    def _save_and_exit(self):
        diamond = self.regions.get("diamond_region")
        name = self.regions.get("name_region")
        btn = self.regions.get("next_button")

        yaml = YAML()
        yaml.preserve_quotes = True
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = yaml.load(f)

        if diamond:
            cfg["capture"]["diamond_region"] = list(diamond)
        if name:
            cfg["capture"]["name_region"] = list(name)
        else:
            cfg["capture"]["name_region"] = None
        if btn:
            cfg["switch"]["next_button"] = list(btn)

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f)

        print(f"坐标已写入 {self.config_path}")
        print(f"  钻石区域: {diamond}")
        print(f"  名称区域: {name}")
        print(f"  切换按钮: {btn}")
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else "calibrate.png"
    cfg = sys.argv[2] if len(sys.argv) > 2 else "config.yaml"
    if not Path(img).exists():
        print(f"错误: 图片 {img} 不存在，请先运行 python main.py --calibrate")
        sys.exit(1)
    RegionSelector(img, cfg).run()
