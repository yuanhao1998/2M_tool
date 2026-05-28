# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

云手机游戏钻石识别统计工具 + 视觉自动化引擎。钻石识别：对多个云手机实例截图，EasyOCR 识别钻石数量并记录 JSON。视觉自动化：Python DSL 定义流程，截屏与参考图比对，匹配后执行点击等操作。纯 Python，无测试框架，无 CI/CD。

**功能特性：** 自动截图、EasyOCR 深度学习识别、稳定采样比对、自动切换账户、停止后保存 JSON 到 data/、全局热键控制、GUI 交互式校准、Retina 高分屏适配、视觉自动化流程执行。

## 环境要求

- macOS
- Python 3.14+
- 无额外系统依赖（EasyOCR 模型首次运行自动下载）
- 依赖安装：`pip install -r requirements.txt`

## 项目结构

```
├── run.py                  # 统一交互式入口
├── main.py                 # 校准/测试工具入口
├── conf/                   # 配置中心
│   ├── config.yaml         #   运行时配置 + 日志级别
│   └── log.py              #   统一日志（终端 + 文件输出）
├── core/                   # 核心引擎
│   ├── capture.py          #   全屏截图 + 区域裁剪
│   ├── ocr_engine.py       #   EasyOCR 数字/文字识别、稳定采样
│   └── mouse.py            #   鼠标点击（Retina 自适应）
├── automation/             # Python DSL 视觉自动化引擎
│   ├── flow.py             #   AutomationFlow 基类 + 执行引擎
│   ├── step.py             #   @step 装饰器 + 流程控制信号
│   ├── images.py           #   ImageDir 参考图管理器
│   └── runner.py           #   FlowRunner 热键 + 多轮循环
├── flows/                  # 用户自动化流程脚本
├── tools/                  # 辅助工具
│   ├── screen_tool.py      #   坐标查看 + 参考图裁剪（支持 F5 实时截屏）
│   └── calibrate_tool.py   #   GUI 三步校准工具
├── images/                 # 参考图片
├── data/                   # 识别结果 JSON
├── logs/                   # 运行日志
└── docs/                   # 项目文档
| `automation/step.py` | @step 装饰器 + StepConfig + 流程控制信号 |
| `automation/images.py` | ImageDir 参考图管理器（目录→属性映射） |
| `automation/runner.py` | FlowRunner：热键监听 + 多轮循环 |
| `flows/` | 用户自动化流程脚本（Python DSL） |
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

## 关键依赖

- `pillow` — 截图、图像处理
- `easyocr` — 深度学习 OCR（首次运行自动下载模型）
- `pyautogui` — 鼠标点击自动化
- `pynput` — 全局热键监听
- `opencv-python-headless` — 模板匹配（EasyOCR 自带依赖）
- `ruamel.yaml` — YAML 配置读写

## 视觉自动化 (Python DSL)

基于 `cv2.matchTemplate` 的模板匹配引擎，用 Python 类 + 装饰器定义流程。

### 流程定义 (`flows/*.py`)

```python
from automation import AutomationFlow, ImageDir, step

class MyImages(ImageDir):
    path = "images/my_flow"

img = MyImages()

class MyFlow(AutomationFlow):
    def switch_to_next(self):
        """定义如何切换账户"""
        self.click(5075, 1138)
        self.wait(3)
        self.wait_match(img.loaded, timeout=30)

    @step(match=img.target_icon, threshold=0.85)
    def do_action(self):
        """匹配到 target_icon 后执行"""
        self.click(100, 200)
        self.wait(1)

    def run(self):
        self.do_action()
        # 原生 Python：循环、条件、变量、函数调用

if __name__ == "__main__":
    MyFlow().main(repeat=73)
```

### @step 装饰器参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `match` | None | 参考图（ImageRef / PIL Image / 路径） |
| `region` | None | 匹配区域 [left, top, right, bottom] |
| `threshold` | 0.85 | 匹配置信度阈值 |
| `max_retries` | 30 | 最大重试次数 |
| `interval` | 1.0 | 重试间隔（秒） |
| `wait_after` | 0.0 | 步骤完成后等待（秒） |
| `on_fail` | None | 失败时调用的方法名 |
| `optional` | False | True 则匹配失败跳过此步 |

### AutomationFlow 内置方法

| 方法 | 说明 |
|------|------|
| `click(x, y)` | 点击坐标（自动 Retina 适配） |
| `wait(seconds)` | 等待（可响应暂停/停止） |
| `screenshot(region)` | 截屏，可选区域裁剪 |
| `find(image, region, threshold)` | 模板匹配，返回 MatchResult |
| `wait_match(image, timeout, interval)` | 轮询等待匹配成功 |
| `match_click(image, target)` | 匹配后自动点击 |
| `find_text(text, region)` | OCR 文字定位 |
| `ocr_diamonds(region, name_region)` | 钻石识别，返回 dict |
| `goto(name)` / `retry()` / `stop()` | 流程控制 |

### ImageDir 参考图管理器

```python
class StoreImages(ImageDir):
    path = "images/store"

# 自动映射文件名 → 属性，IDE 补全
# StoreImages.store_icon  → ImageRef("images/store/store_icon.png")
# StoreImages.buy_button  → ImageRef("images/store/buy_button.png")

# 工具方法：
# StoreImages.list_all()   → 列出所有图片
# StoreImages.validate()   → 检查缺失文件
```

### 调试选项

| 选项 | 功能 |
|------|------|
| `main(debug=True)` | 每步打印匹配结果、坐标 |
| `main(dry_run=True)` | 只验证不点击 |
| `main(start_step="name")` | 从指定步骤开始 |
| `pdb.set_trace()` | Python 原生断点调试 |

## 关键行为

- **OCR 识别**：基于 EasyOCR 深度学习模型，数字识别使用白名单 `allowlist='0123456789'`，宽图自动触发空间聚类过滤噪点
- **稳定采样**：`recognize_diamond_stable()` 连续截图两次比对，不一致则追加采样直到连续两次一致，最多 6 次后多数投票
- **Retina 适配**：`mouse._get_scale()` 通过截图物理像素 / 逻辑坐标自动计算缩放比并缓存
- **识别失败调试**：采样始终不一致时自动保存截图到 `debug_failures/` 目录
- **结果保存**：停止后结果保存为 `data/YYYY-MM-DD_N.json`，同一天多次运行序号自动递增
- **参考图片准备**：`python screen_tool.py screen.png` 打开截图，拖拽框选后按 R 保存到 `images/`
