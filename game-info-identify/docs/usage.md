# 使用指南

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--calibrate` | 校准模式：截一张全屏图保存为 `calibrate.png` |
| `--test` | 测试模式：截屏并识别，验证坐标配置是否准确 |
| `--config <path>` | 指定配置文件路径，默认 `config.yaml` |

## 运行模式

### 校准模式

```bash
# 第一步：截取参考图
python main.py --calibrate

# 第二步：打开 GUI 校准工具框选区域
python calibrate_tool.py calibrate.png
```

GUI 操作：
- **鼠标拖拽** — 框选矩形区域
- **滚轮** — 缩放图片
- **Ctrl+拖拽** — 平移图片
- **空格** — 确认当前区域，进入下一步
- **ESC** — 退出

框选顺序：钻石数量区域 → 云机名称区域（可选） → 切换按钮位置。

### 测试模式

```bash
python main.py --test
```

会生成以下调试图片：
- `test_fullscreen.png` — 完整截图
- `test_marked.png` — 带红框标记的截图（确认裁剪区域正确）
- `test_crop_raw.png` — 原始裁剪图
- `test_crop_processed.png` — 预处理后的裁剪图

### 正式运行

```bash
python main.py
```

## 热键

| 按键 | 功能 |
|------|------|
| `F5` | 开始 / 继续 |
| `F6` | 暂停 |
| `F7` | 停止（统计结束） |
| `ESC` | 紧急退出 |

可在 `config.yaml` 的 `hotkeys` 段自定义按键。

## 工作流程

1. 按 `F5` 开始
2. 程序截取全屏 → 裁剪钻石区域 → OCR 识别
3. 裁剪名称区域 → OCR 识别云机名称
4. 结果收集到内存列表
5. 点击切换按钮 → 等待加载 → 重复步骤 2
6. 处理完预设数量或按 `F7` 停止
7. 停止后结果自动保存为 JSON

## 输出文件

停止后结果自动保存到 `data/` 目录，文件名为 `YYYY-MM-DD_N.json`（同一天多次运行序号递增）。

```json
[
  { "cloud_device": "云机-01", "diamonds": 120 },
  { "cloud_device": "云机-02", "diamonds": 85 }
]
```

## 调试

当 OCR 识别不稳定时，截图会自动保存到 `debug_failures/` 目录：
- `*_acctN_M_VALUE.png` — 第 N 个账户的第 M 次采样（VALUE 为识别结果）
- `*_acctN_M_proc.png` — 对应的预处理图片

可用于排查识别失败原因并调整预处理参数。
