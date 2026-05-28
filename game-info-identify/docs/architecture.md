# 架构设计

## 整体架构

```
┌──────────────────────────────────────────────────────┐
│                     run.py                            │
│                  统一交互式入口                         │
├──────────────────────┬───────────────────────────────┤
│     main.py           │    automation/ + flows/       │
│  校准/测试模式          │  Python DSL 视觉自动化引擎     │
├──────┬──────┬─────────┤──────┬──────┬───────┬────────┤
│capture│ocr  │mouse    │screen│capture│ocr    │mouse   │
│截图   │识别  │点击      │工具   │截图   │识别   │点击     │
└──────┴──────┴─────────┴──────┴──────┴───────┴────────┘
```

## 数据流

```
钻石识别:  flows/diamond_stats.py → 截图 → OCR 识别 → data/YYYY-MM-DD_N.json

自动化:    flows/*.py (Python DSL) → 截屏比对/OCR文字 → 匹配则点击 → 多账户循环
```

## 模块职责

| 模块 | 职责 | 关键依赖 |
|------|------|----------|
| `run.py` | 统一交互式入口 | — |
| `main.py` | 校准/测试工具入口 | core.capture, core.ocr |
| `conf/log.py` | 统一日志配置（终端 + 文件） | ruamel.yaml |
| `conf/config.yaml` | 运行时配置 + 日志级别 | — |
| `core/capture.py` | 全屏截图、区域裁剪 | Pillow |
| `core/ocr_engine.py` | EasyOCR 数字/文字识别、稳定采样 | EasyOCR, Pillow |
| `core/mouse.py` | 鼠标点击、Retina 缩放适配 | pyautogui, Pillow |
| `automation/flow.py` | AutomationFlow 基类 + 步骤执行引擎 | core.*, cv2 |
| `automation/step.py` | @step 装饰器 + StepConfig + 流程控制信号 | — |
| `automation/images.py` | ImageDir 参考图管理器（目录→属性映射） | Pillow |
| `automation/runner.py` | FlowRunner：热键监听 + 多轮循环 | pynput |
| `flows/` | 用户流程脚本（Python 类继承 AutomationFlow） | automation |
| `tools/screen_tool.py` | 坐标查看、参考图裁剪，支持 F5 实时截屏 | Tkinter, Pillow, pynput |
| `tools/calibrate_tool.py` | GUI 校准工具，框选区域写入 config.yaml | Tkinter, Pillow |

## 设计要点

### OCR 识别

`ocr_engine.py` 基于 EasyOCR 深度学习模型：

- 数字识别使用 `allowlist='0123456789'` 白名单限制
- 小文字自动 3× 放大提升识别率
- 宽图（宽高比 > 5）自动触发空间聚类，过滤图标等远端噪点
- Reader 懒加载单例，首次运行自动下载模型

### Python DSL 视觉自动化引擎

`automation/` 包提供 Python 类 + 装饰器 DSL，替代旧的 YAML 流程定义：

- **@step 装饰器**：声明步骤的匹配条件（参考图、区域、阈值）、重试策略（max_retries、interval）和失败处理（on_fail、optional）
- **`__init_subclass__` 包装**：类创建时自动将 @step 方法包装为匹配→执行→重试的完整流程
- **流程控制**：方法返回 `"retry"` 重试当前步骤，返回方法名跳转，raise `StopFlow` 终止
- **ImageDir**：目录→属性映射，IDE 自动补全参考图，支持 `validate()` 检查缺失文件
- **模板匹配**：`cv2.matchTemplate` + `TM_CCOEFF_NORMED`，同时支持 OCR 文字定位（`find_text`）

### 稳定采样机制

`recognize_diamond_stable()` 采用连续两次比对+追加采样+多数投票的组合策略，不一致时自动保存调试截图到 `debug_failures/`。

### Retina 屏幕适配

`mouse.py` 通过比较截图物理像素和屏幕逻辑坐标，自动计算缩放比，确保在高分屏上点击位置准确。
