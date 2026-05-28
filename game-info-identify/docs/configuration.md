# 配置说明

## config.yaml — 钻石识别配置

校准/测试模式使用。

```yaml
hotkeys:
  start: f5        # 开始/继续
  pause: f6        # 暂停
  stop: f7         # 停止
  exit: esc        # 紧急退出

capture:
  diamond_region: [left, top, right, bottom]  # 钻石数量区域
  name_region: [left, top, right, bottom]     # 云机名称区域，null 跳过

switch:
  next_button: [x, y]       # 切换按钮点击位置
  wait_after_switch: 2.0    # 切换后等待时间（秒）

stats:
  total_accounts: 0          # 账户总数，0 表示无限制
```

## flows/*.py — Python DSL 流程定义

流程用 Python 编写，继承 `AutomationFlow`。主要装饰器和内置方法见 `CLAUDE.md`。

### 简要示例

```python
from automation import AutomationFlow, ImageDir, step

class MyImages(ImageDir):
    path = "images/my_flow"

img = MyImages()

class MyFlow(AutomationFlow):
    def switch_to_next(self):
        """定义账户切换逻辑"""
        self.click(5075, 1138)
        self.wait(3)

    @step(match=img.target, threshold=0.85, max_retries=10)
    def action(self):
        self.click(100, 200)

    def run(self):
        self.action()
        # 原生 Python 控制流：循环、条件、函数

if __name__ == "__main__":
    MyFlow().main(repeat=73)
```

### @step 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `match` | None | 参考图（ImageRef / PIL Image / 路径） |
| `region` | None | 匹配区域 |
| `threshold` | 0.85 | 置信度阈值 |
| `max_retries` | 30 | 最大重试 |
| `interval` | 1.0 | 重试间隔 |
| `wait_after` | 0.0 | 执行后等待 |
| `on_fail` | None | 失败时调用的方法名 |
| `optional` | False | 匹配失败时跳过 |

### 钻石识别

```python
result = self.ocr_diamonds(
    region=(2291, 127, 2475, 237),
    name_region=(14, 14, 82, 56)
)
# → {"cloud_device": "设备名", "diamonds": "123", "unstable": False}
```

## 坐标校准

推荐使用 screen_tool 获取准确坐标：

```bash
python -c "from PIL import ImageGrab; ImageGrab.grab().save('screen.png')"
python tools/screen_tool.py screen.png
```

| 操作 | 按键 | 效果 |
|------|------|------|
| 拖拽框选 | 鼠标 | 显示区域坐标 |
| 保存参考图 | R | 裁剪选区保存到 `images/` |
| 复制区域坐标 | C | 复制 `[l,t,r,b]` 到剪贴板 |
| 复制点击坐标 | T | 复制 `[x,y]` 到剪贴板 |
