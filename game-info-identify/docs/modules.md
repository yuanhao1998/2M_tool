# 模块说明

## main.py — 主入口

校准与测试工具。

**主要功能：**
- 解析命令行参数（`--calibrate`, `--test`, `--config`）
- 校准模式：截全屏图供坐标校准
- 测试模式：截屏裁剪钻石区域进行 OCR 识别，输出调试图片

**关键函数：**
- `calibrate(cfg)` — 截全屏图保存为 calibrate.png
- `test_ocr(cfg)` — 截屏 → 裁剪 → OCR，输出 4 张调试图片
- `load_config(path)` — 使用 ruamel.yaml 安全加载配置文件

---

## core/capture.py — 截图模块

全屏截图与区域裁剪的薄封装。

| 函数 | 说明 |
|------|------|
| `fullscreen_screenshot()` | 截取 macOS 全屏，返回 PIL Image |
| `crop_region(image, region)` | 从全屏图中裁剪 `(left, top, right, bottom)` 区域 |

---

## ocr_engine.py — OCR 识别模块

基于 EasyOCR 深度学习模型的图像识别，包含预处理、数字提取、文字提取、稳定采样。

**预处理：**
- `preprocess(image)` — 小文字（高度 < 30px）3× 放大

**数字识别：**
- `extract_digits(image)` — EasyOCR 白名单识别 + 宽图空间聚类验证
- `_extract_by_cluster(image)` — 用 bounding box 获取字符位置，按间距聚类，取最大簇
- `recognize_diamond(image)` — 单次数字识别
- `recognize_diamond_stable(capture)` — 多次采样比对，一致才采信，不一致则多数投票

**文字识别：**
- `extract_text(image)` — EasyOCR 通用文字识别，用于云机名称

**调试：**
- `_save_debug(captures, samples, best, index)` — 识别不稳定时保存截图到 `debug_failures/`

---

## mouse.py — 鼠标自动化模块

模拟鼠标操作，自动适配 Retina 高分屏。

| 函数 | 说明 |
|------|------|
| `_get_scale()` | 检测屏幕缩放比（截图物理像素 / 逻辑坐标），结果缓存 |
| `click(x, y)` | 移动到物理像素坐标并点击，自动转换 |
| `switch_to_next(x, y, wait)` | 点击切换按钮并等待 |

---

## automation/ — Python DSL 视觉自动化引擎

### automation/flow.py — AutomationFlow 基类

流程基类，子类继承并定义 `@step` 方法和 `run()` 编排逻辑。

**内置方法：**

| 方法 | 说明 |
|------|------|
| `click(x, y)` | Retina 自适应点击 |
| `wait(seconds)` | 等待（可分片响应暂停/停止） |
| `screenshot(region)` | 截屏，可选区域裁剪 |
| `crop(image, region)` | 区域裁剪 |
| `find(image, region, threshold)` | 模板匹配，返回 MatchResult |
| `wait_match(image, timeout, interval)` | 轮询等待直到匹配或超时 |
| `match_click(image, target)` | 匹配后自动点击 |
| `find_text(text, region)` | OCR 定位文字，返回 TextResult |
| `ocr_diamonds(region, name_region)` | 钻石识别，返回 dict |
| `goto(name)` | 返回跳转信号 |
| `retry()` | 返回重试信号 |
| `stop()` | 抛出 StopFlow 终止流程 |
| `switch_account(click_pos, wait)` | 切换账户 |
| `main(repeat, hotkeys, debug, dry_run)` | 启动入口 |

**MatchResult:** `matched: bool`, `confidence: float`, `location: (x, y)`
**TextResult:** `found: bool`, `text: str`, `center: (x, y)`

### automation/step.py — @step 装饰器

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `match` | None | 参考图（ImageRef / PIL Image / 路径） |
| `region` | None | 匹配区域 [left, top, right, bottom] |
| `threshold` | 0.85 | 匹配置信度阈值 |
| `max_retries` | 30 | 最大重试次数 |
| `interval` | 1.0 | 重试间隔（秒） |
| `wait_after` | 0.0 | 步骤完成后等待 |
| `on_fail` | None | 失败时调用的方法名 |
| `optional` | False | True 则匹配失败跳过 |

**流程控制信号：** `RETRY = "retry"`、`StopFlow` 异常

### automation/images.py — ImageDir 参考图管理器

声明式图片管理，文件名自动映射为类属性，IDE 自动补全。

```python
class MyImages(ImageDir):
    path = "images/my_flow"
# MyImages.icon → ImageRef("images/my_flow/icon.png")
```

| 方法 | 说明 |
|------|------|
| `list_all()` | 列出所有已映射的 ImageRef |
| `validate()` | 检查所有引用图片是否存在，返回缺失列表 |

### automation/runner.py — FlowRunner

- pynput 热键监听（F5 开始、F6 暂停、F7 停止、ESC 退出）
- 多账户 repeat 循环，每轮后调用 `switch_to_next()`
- 支持 debug、dry_run、start_step 选项

---

## flows/ — 用户流程脚本

Python DSL 流程定义，每个流程是一个继承 AutomationFlow 的类。

| 文件 | 说明 |
|------|------|
| `flows/shop.py` | 商城购买：42 账户循环，购买 3 个槽位 |
| `flows/delegate.py` | 委托任务：73 账户，领取奖励 + 传送 |
| `flows/supply.py` | 补给购买：73 账户，回城 → 购买 → 传送 |
| `flows/diamond_stats.py` | 钻石统计：73 账户，打开任务 → 识别 → 保存 JSON |

运行方式：`python flows/shop.py` 或通过 `python run.py` 菜单选择。

---

## screen_tool.py — 坐标辅助工具

截图查看、坐标获取、参考图裁剪。

| 操作 | 按键 | 效果 |
|------|------|------|
| 悬停 | — | 显示像素坐标 |
| 拖拽框选 | 鼠标 | 显示区域坐标和宽高 |
| 保存参考图 | R | 裁剪选区保存到 `images/` |
| 复制区域坐标 | C | 复制 `[l,t,r,b]` 到剪贴板 |
| 复制点击坐标 | T | 复制 `[x,y]` 到剪贴板 |
| 输入坐标定位 | 回车 | 底部输入框粘贴坐标回车定位 |

---

## run.py — 统一启动脚本

交互式菜单：`python run.py` → 选择钻石识别 / 视觉自动化 / 坐标工具。

---

## calibrate_tool.py — 校准工具

基于 Tkinter 的 GUI 交互式校准工具。

**`RegionSelector` 类：**
- 加载截图，支持滚轮缩放和拖拽平移
- 三步引导：框选钻石区域 → 框选名称区域 → 点击切换按钮
- 自动将坐标写入 `config.yaml`

**操作方式：**
- 鼠标拖拽框选矩形
- 滚轮缩放（0.2× ~ 3.0×）
- Ctrl+拖拽或中键拖拽平移
- 空格确认，ESC 退出

可独立运行：`python calibrate_tool.py <截图路径> <配置路径>`
