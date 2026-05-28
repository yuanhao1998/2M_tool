# 使用指南

## 快速启动

```bash
python run.py         # 交互式菜单选择功能
```

菜单选项：
1. 钻石识别统计
2. 视觉自动化流程
3. 坐标辅助工具

## 命令行参数

### 主工具 (main.py)

| 参数 | 说明 |
|------|------|
| `--calibrate` | 校准模式：截一张全屏图保存为 `calibrate.png` |
| `--test` | 测试模式：截屏并识别，验证坐标配置是否准确 |
| `--config <path>` | 指定配置文件路径，默认 `config.yaml` |

### 自动化流程 (flows/*.py)

| 选项 | 说明 |
|------|------|
| `main(debug=True)` | 每步打印匹配结果、耗时、坐标 |
| `main(dry_run=True)` | 只验证不点击（安全检查） |
| `main(start_step="name")` | 从指定步骤开始执行 |
| `main(repeat=N)` | 设置循环轮数（覆盖文件中的默认值） |

## 运行模式

### 校准模式

```bash
# 第一步：截取参考图
python main.py --calibrate

# 第二步：打开 GUI 校准工具框选区域
python tools/calibrate_tool.py calibrate.png
```

GUI 操作：
- **鼠标拖拽** — 框选矩形区域
- **滚轮** — 缩放图片
- **Ctrl+拖拽** — 平移图片
- **空格** — 确认当前区域，进入下一步
- **ESC** — 退出

### 测试模式

```bash
python main.py --test
```

生成调试图片：test_fullscreen.png、test_marked.png、test_crop_raw.png、test_crop_processed.png。

### 钻石识别统计

```bash
python flows/diamond_stats.py
# 或通过 run.py 菜单选择
```

### 视觉自动化流程

```bash
# 直接运行
python flows/shop.py        # 商城购买
python flows/delegate.py     # 委托任务
python flows/supply.py       # 补给购买

# 或通过 run.py 菜单选择

# 调试模式
python flows/shop.py --debug
python flows/shop.py --dry-run
```

## 热键

| 按键 | 功能 |
|------|------|
| `F5` | 开始 / 继续 |
| `F6` | 暂停 |
| `F7` | 停止 |
| `ESC` | 退出 |

可在流程文件中自定义热键。

## 编写流程

```python
from automation import AutomationFlow, ImageDir, step

class MyImages(ImageDir):
    path = "images/my_flow"

img = MyImages()

class MyFlow(AutomationFlow):
    def switch_to_next(self):
        self.click(5075, 1138)
        self.wait(3)

    @step(match=img.target, threshold=0.85)
    def do_action(self):
        self.click(100, 200)

    def run(self):
        self.do_action()

if __name__ == "__main__":
    MyFlow().main(repeat=10)
```

## 输出文件

结果自动保存到 `data/` 目录，文件名为 `YYYY-MM-DD_N.json`。

```json
[
  { "cloud_device": "云机-01", "diamonds": 120 },
  { "cloud_device": "云机-02", "diamonds": 85 }
]
```

## 调试

- **OCR 不稳定**：截图自动保存到 `debug_failures/` 目录
- **流程调试**：`pdb.set_trace()` 设置 Python 断点，`python -i flows/shop.py` 交互式 REPL
- **匹配失败**：`--debug` 参数打印每步匹配置信度和坐标信息
- **安全检查**：`--dry-run` 参数只验证不执行点击
