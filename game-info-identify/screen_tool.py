"""截图坐标辅助工具：查看坐标、裁剪参考图、生成 YAML 动作片段。

用法:
  1. 截全屏图: python -c "from PIL import ImageGrab; ImageGrab.grab().save('screen.png')"
  2. 打开工具: python screen_tool.py screen.png

操作:
  鼠标悬停  → 实时显示物理像素坐标
  拖拽框选  → 显示区域坐标，按 R 保存裁剪图为参考图，按 C 复制坐标
  滚轮      → 缩放
  Ctrl+拖拽 → 平移
  Space     → 取当前坐标作为点击目标，生成 YAML 动作片段
  ESC       → 退出
"""

import sys
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk


class ScreenTool:
    def __init__(self, image_path: str):
        self.root = tk.Tk()
        self.root.title(f"坐标工具 — {Path(image_path).name} — 滚轮缩放 Ctrl+拖拽平移")

        self.pil_image = Image.open(image_path)
        self.orig_w = self.pil_image.width
        self.orig_h = self.pil_image.height
        self.scale = 1.0

        # 窗口大小
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = min(screen_w, int(screen_w * 0.9))
        win_h = min(screen_h, int(screen_h * 0.85))

        if self.orig_w > win_w or self.orig_h > win_h:
            self.scale = min(win_w / self.orig_w, win_h / self.orig_h)

        self._make_photo()

        canvas_w = min(self.scaled_w, win_w)
        canvas_h = min(self.scaled_h, win_h)

        frame = tk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(frame, width=canvas_w, height=canvas_h,
                                cursor="cross",
                                scrollregion=(0, 0, self.scaled_w, self.scaled_h))
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
        self.info_var = tk.StringVar(value="悬停查看坐标 | 拖拽框选 → R保存参考图 | Space 取点击坐标 → 生成YAML")
        tk.Label(self.root, textvariable=self.info_var, font=("", 13), pady=6).pack()

        # 操作提示
        tk.Label(self.root,
                 text="R=保存参考图  C=复制区域坐标  T=复制点击坐标  Space=生成YAML  ESC=退出",
                 font=("", 11), fg="gray").pack(pady=(0, 2))

        # 坐标输入栏：粘贴 [l,t,r,b] 回车高亮并定位
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=(0, 4))
        tk.Label(input_frame, text="坐标:", font=("", 11)).pack(side=tk.LEFT)
        self.coord_entry = tk.Entry(input_frame, width=40, font=("", 11))
        self.coord_entry.pack(side=tk.LEFT, padx=(4, 4))
        self.coord_entry.bind("<Return>", self._on_coord_enter)
        tk.Label(input_frame, text="例: [100,200,300,400]", font=("", 10), fg="gray").pack(side=tk.LEFT)

        # 选中状态
        self.start_x = self.start_y = None
        self.rect_id = None
        self.point_id = None

        # 事件绑定
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Control-ButtonPress-1>", self.on_pan_start)
        self.canvas.bind("<Control-B1-Motion>", self.on_pan)
        # macOS 滚轮：同时绑定 root 和 canvas，兼容不同 Tk 版本
        self.root.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.root.bind("<Button-4>", lambda e: self._zoom_step(1.1))
        self.root.bind("<Button-5>", lambda e: self._zoom_step(0.9))
        self.canvas.bind("<Button-4>", lambda e: self._zoom_step(1.1))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_step(0.9))
        self.root.bind("<r>", lambda e: self._save_crop())
        self.root.bind("<c>", lambda e: self._copy_region())
        self.root.bind("<t>", lambda e: self._copy_click())
        self.root.bind("<space>", lambda e: self._gen_click_action())
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self._pan_x = self._pan_y = None
        self._saved_region = None   # 最近一次框选区域 (left, top, right, bottom)
        self._last_click = None     # 最近一次点击坐标 (x, y)

    # ---- 坐标转换 ----
    def _to_orig(self, cx, cy):
        return int(cx / self.scale), int(cy / self.scale)

    def _to_canvas(self, ox, oy):
        return ox * self.scale, oy * self.scale

    # ---- 缩放 ----
    def on_zoom(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self._zoom_step(factor)

    def _zoom_step(self, factor):
        new_scale = self.scale * factor
        if new_scale < 0.2 or new_scale > 3.0:
            return
        self.scale = new_scale
        self._rebuild_photo()

    def _make_photo(self):
        if self.scale == 1.0:
            img = self.pil_image
        else:
            nw = max(1, int(self.orig_w * self.scale))
            nh = max(1, int(self.orig_h * self.scale))
            img = self.pil_image.resize((nw, nh), Image.LANCZOS)
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

    # ---- 鼠标交互 ----
    def on_move(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        ox, oy = self._to_orig(cx, cy)
        self.info_var.set(f"坐标: ({ox}, {oy})  — 悬停查看 | 拖拽框选 | R/C/Space 操作")

    def on_press(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self.start_x, self.start_y = self._to_orig(cx, cy)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

    def on_drag(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        ox, oy = self._to_orig(cx, cy)
        sx, sy = self._to_canvas(self.start_x, self.start_y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(sx, sy, cx, cy,
                                                     outline="lime", width=2)

    def on_release(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        ox, oy = self._to_orig(cx, cy)
        x1, y1 = self.start_x, self.start_y
        x2, y2 = ox, oy
        left, right = sorted([x1, x2])
        top, bottom = sorted([y1, y2])

        if abs(x2 - x1) < 5 and abs(y2 - y1) < 5:
            # 点击行为：记录坐标
            self._last_click = (self.start_x, self.start_y)
            self._draw_point(self.start_x, self.start_y)
            self.info_var.set(f"点击坐标: ({self.start_x}, {self.start_y}) — 按 T 复制坐标，按 Space 生成 YAML")
            self._saved_region = None
        else:
            # 框选行为：记录区域
            self._saved_region = (left, top, right, bottom)
            self._last_click = None
            self.info_var.set(f"区域: [{left}, {top}, {right}, {bottom}]  "
                              f"({right - left}x{bottom - top}) — 按R保存参考图，按C复制坐标")

    def _draw_point(self, x, y):
        if self.point_id:
            for pid in (self.point_id if isinstance(self.point_id, tuple) else [self.point_id]):
                self.canvas.delete(pid)
        r = max(8, int(10 / self.scale))
        sx, sy = self._to_canvas(x, y)
        p1 = self.canvas.create_line(sx - r, sy, sx + r, sy, fill="red", width=2)
        p2 = self.canvas.create_line(sx, sy - r, sx, sy + r, fill="red", width=2)
        self.point_id = (p1, p2)

    # ---- 操作 ----
    def _save_crop(self):
        if not self._saved_region:
            self.info_var.set("请先拖拽框选区域")
            return
        left, top, right, bottom = self._saved_region
        crop = self.pil_image.crop((left, top, right, bottom))

        out_dir = Path("images")
        out_dir.mkdir(exist_ok=True)

        # 自动命名
        n = 1
        while (out_dir / f"ref_{n}.png").exists():
            n += 1
        path = out_dir / f"ref_{n}.png"
        crop.save(path)
        self.info_var.set(f"已保存参考图: {path}")

    def _copy_region(self):
        if not self._saved_region:
            self.info_var.set("请先拖拽框选区域")
            return
        left, top, right, bottom = self._saved_region
        text = f"[{left}, {top}, {right}, {bottom}]"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.info_var.set(f"已复制到剪贴板: {text}")

    def _copy_click(self):
        if not self._last_click:
            self.info_var.set("请先点击取坐标")
            return
        x, y = self._last_click
        text = f"[{x}, {y}]"
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.info_var.set(f"已复制点击坐标到剪贴板: {text}")

    def _on_coord_enter(self, event):
        """粘贴坐标后回车：高亮矩形区域并缩放到合适大小。"""
        raw = self.coord_entry.get().strip()
        try:
            parts = [int(x.strip()) for x in raw.strip("[]()").split(",")]
            if len(parts) != 4:
                raise ValueError
            left, top, right, bottom = parts
        except (ValueError, TypeError):
            self.info_var.set("格式错误，示例: [100,200,300,400]")
            return

        # 检查坐标合理性
        if left >= right or top >= bottom:
            self.info_var.set(f"坐标无效: ({left},{top},{right},{bottom})")
            return

        self._saved_region = (left, top, right, bottom)
        w, h = right - left, bottom - top

        # 先缩放到合适大小（会重建画布），再画高亮框
        self._fit_region(left, top, w, h)
        self._draw_rect(left, top, right, bottom)
        self.info_var.set(f"定位到 [{left}, {top}, {right}, {bottom}]  ({w}x{h})")

    def _draw_rect(self, left, top, right, bottom):
        """在画布上绘制绿色高亮矩形。"""
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        sl, st = self._to_canvas(left, top)
        sr, sb = self._to_canvas(right, bottom)
        self.rect_id = self.canvas.create_rectangle(sl, st, sr, sb, outline="lime", width=3)

    def _fit_region(self, x, y, w, h):
        """调整缩放和滚动，使指定区域在画布中可见。"""
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return

        # 计算合适的缩放比
        margin = 0.85
        scale_x = canvas_w / max(w, 1) * margin
        scale_y = canvas_h / max(h, 1) * margin
        self.scale = min(scale_x, scale_y, 3.0)
        self._rebuild_photo()

        # 滚动使区域居中
        cx = (x + w / 2) * self.scale
        cy = (y + h / 2) * self.scale
        self.canvas.xview_moveto(max(0, (cx - canvas_w / 2) / self.scaled_w))
        self.canvas.yview_moveto(max(0, (cy - canvas_h / 2) / self.scaled_h))

    def _gen_click_action(self):
        """生成 YAML 动作片段并打印到终端。"""
        if self._saved_region:
            # 框选了区域 → 生成 match_click
            ref = ""
            idx = 1
            while (Path("images") / f"ref_{idx}.png").exists():
                idx += 1
            if idx > 1:
                ref = f"images/ref_{idx - 1}.png"

            left, top, right, bottom = self._saved_region
            cx = (left + right) // 2
            cy = (top + bottom) // 2

            snippet = f"""
- action: match_click
  name: ""
  match_region: [{left}, {top}, {right}, {bottom}]
  reference: "{ref or 'images/xxx.png'}"
  threshold: 0.85
  target: [{cx}, {cy}]
  max_retries: 30
  interval: 1
  wait_after: 1
"""
        elif self._last_click:
            x, y = self._last_click
            snippet = f"""
- action: click
  name: ""
  target: [{x}, {y}]
  wait_after: 1
"""
        else:
            self.info_var.set("请先框选区域或点击取坐标")
            return

        print("\n" + "=" * 50)
        print("复制以下内容到 plans/*.yaml:")
        print("=" * 50)
        print(snippet)
        self.info_var.set("已生成 YAML 片段（见终端输出）")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    img = sys.argv[1] if len(sys.argv) > 1 else "screen.png"
    if not Path(img).exists():
        print(f"错误: 图片 {img} 不存在")
        print("请先截图: python -c \"from PIL import ImageGrab; ImageGrab.grab().save('screen.png')\"")
        sys.exit(1)
    ScreenTool(img).run()
