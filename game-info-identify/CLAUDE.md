# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

云手机游戏钻石识别统计工具 + 视觉自动化引擎。钻石识别：对多个云手机实例截图，EasyOCR 识别钻石数量并记录 JSON。视觉自动化：自定义流程，截屏与参考图比对，匹配后执行点击等操作。纯 Python，无测试框架，无 CI/CD。

**功能特性：** 自动截图、EasyOCR 深度学习识别、稳定采样比对、自动切换账户、停止后保存 JSON 到 data/、全局热键控制、GUI 交互式校准、Retina 高分屏适配、视觉自动化流程执行。

## 环境要求

- macOS
- Python 3.14+
- 无额外系统依赖（EasyOCR 模型首次运行自动下载）
- 依赖安装：`pip install -r requirements.txt`

## 模块结构

| 文件 | 职责 |
|------|------|
| `main.py` | 入口，流程编排、全局热键（pynput）、校准/测试/正式三种模式 |
| `capture.py` | 全屏截图 + 区域裁剪（Pillow ImageGrab） |
| `ocr_engine.py` | OCR 识别核心：EasyOCR 数字/文字识别、空间聚类、稳定采样 |
| `planner.py` | 视觉自动化引擎：截屏模板匹配 → 点击，按 YAML 流程执行 |
| `automation.py` | 鼠标点击模拟，自动检测 Retina 缩放比（pyautogui） |
| `screen_tool.py` | 坐标辅助工具：查看坐标、裁剪参考图、生成 YAML 片段 |
| `config.yaml` | 钻石识别运行时配置 |
| `plans/*.yaml` | 视觉自动化流程定义 |
| `images/` | 视觉自动化的参考图片 |

## 文档索引

| 文件 | 适用场景 |
|------|----------|
| `docs/architecture.md` | 理解整体架构、数据流、OCR 多策略设计 |
| `docs/usage.md` | 运行方式、热键说明、调试方法 |
| `docs/configuration.md` | 配置 config.yaml 时查阅各字段含义 |
| `docs/modules.md` | 修改代码前了解各模块的函数/类接口 |

## 快速上手

```bash
python run.py         # 交互式菜单选择功能
```

启动后显示：
```
  1. 钻石识别统计
  2. 视觉自动化流程  
  3. 坐标辅助工具
```
```

## 关键依赖

- `pillow` — 截图、图像处理
- `easyocr` — 深度学习 OCR（首次运行自动下载模型）
- `pyautogui` — 鼠标点击自动化
- `pynput` — 全局热键监听
- `opencv-python-headless` — 模板匹配（EasyOCR 自带依赖）
- `ruamel.yaml` — YAML 配置读写

## 视觉自动化 (planner.py)

基于 `cv2.matchTemplate` 的模板匹配引擎：

- **流程定义**：YAML 文件，按步骤顺序执行
- **每步**：定义截图区域 + 参考图片 + 匹配阈值 + 点击目标 + 重试策略
- **匹配方法**：`TM_CCOEFF_NORMED`（归一化相关系数），阈值建议 0.85+
- **参考图片准备**：`python screen_tool.py screen.png` 打开截图，拖拽框选后按 R 保存到 `images/`，按 Space 生成 YAML 片段
- **支持热键**：F5 开始、F6 暂停、F7 停止、ESC 退出

### 规划文件格式 (`plans/*.yaml`)

```yaml
name: "流程名称"
hotkeys:
  start: f5
  pause: f6
  stop: f7
  exit: esc

# 多账户循环（可选）
repeat:
  times: 73                               # 账户总数
  switch:                                 # 每轮结束后切换账户的动作序列
    - action: click
      target: [x, y]
      wait_after: 2
    - action: wait_match                  # 等待新账户加载
      match_region: [...]
      reference: "images/loaded.png"

steps:
  - name: "步骤描述"
    match_region: [left, top, right, bottom]
    reference: "images/xxx.png"
    threshold: 0.85
    action: click
    target: [x, y]
    max_retries: 30
    interval: 1
    wait_after: 1
    on_fail:
      action: click
      target: [x, y]
      retry: true
      # goto: 5                            # 或跳转到步骤 5
```

CLI 参数：`python planner.py plans/xxx.yaml --repeat 10` 可覆盖 `repeat.times`。

## 关键行为

- **OCR 识别**：基于 EasyOCR 深度学习模型，数字识别使用白名单 `allowlist='0123456789'`，宽图自动触发空间聚类过滤噪点
- **稳定采样**：`recognize_diamond_stable()` 连续截图两次比对，不一致则追加采样直到连续两次一致，最多 6 次后多数投票
- **Retina 适配**：`automation._get_scale()` 通过截图物理像素 / 逻辑坐标自动计算缩放比并缓存
- **识别失败调试**：采样始终不一致时自动保存截图到 `debug_failures/` 目录
- **结果保存**：停止后结果保存为 `data/YYYY-MM-DD_N.json`，同一天多次运行序号自动递增
- **等待画面加载**：切换账户后轮询检测钻石数据是否出现，最多等 30 秒
