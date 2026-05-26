# 模块说明

## main.py — 主入口

流程编排与全局控制。

**主要功能：**
- 解析命令行参数（`--calibrate`, `--test`, `--config`）
- 加载 `config.yaml` 配置
- 启停全局热键监听（`pynput`）
- 主循环：截图→识别→收集→切换
- 停止后将结果保存为 `data/YYYY-MM-DD_N.json`
- 校准模式：截一张全屏图
- 测试模式：截屏并输出调试图片

**关键函数：**
- `run_main_loop(cfg)` — 主循环，等待 F5 后开始自动处理
- `_save_results(payload)` — 将结果保存为 JSON，自动递增序号
- `_prompt_sync(filepath, url)` — 询问用户后从文件读取最新内容发送
- `_sync_to_server(payload, url)` — POST 结果到远程接口
- `calibrate(cfg)` — 校准模式
- `test_ocr(cfg)` — 测试模式，输出 4 张调试图片

---

## capture.py — 截图模块

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

## automation.py — 自动化模块

模拟鼠标操作，自动适配 Retina 高分屏。

| 函数 | 说明 |
|------|------|
| `_get_scale()` | 检测屏幕缩放比（截图物理像素 / 逻辑坐标），结果缓存 |
| `click(x, y)` | 移动到物理像素坐标并点击，自动转换 |
| `switch_to_next(x, y, wait)` | 点击切换按钮并等待 |

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
