# 配置说明

配置文件为 `config.yaml`，所有参数均有注释标注用途。

## 配置结构

```yaml
# 热键定义
hotkeys:
  start: f5        # 开始/继续
  pause: f6        # 暂停
  stop: f7         # 停止
  exit: esc        # 紧急退出

# 截图参数
capture:
  diamond_region: [left, top, right, bottom]  # 钻石数量区域（像素坐标）
  name_region: [left, top, right, bottom]     # 云机名称区域，null 则跳过

# 切换参数
switch:
  next_button: [x, y]       # 切换按钮点击位置（像素坐标）
  wait_after_switch: 2.0    # 切换后等待时间（秒）

# 统计参数
stats:
  total_accounts: 0          # 处理账户总数，0 表示无限制
```

## 配置项详解

### hotkeys

热键名称使用 `pynput` 的按键命名，常用值：
- 字母键：`a` ~ `z`
- 功能键：`f1` ~ `f12`
- 特殊键：`esc`, `enter`, `space`, `tab`

### capture.diamond_region

钻石数量在屏幕上的矩形区域，坐标格式 `[left, top, right, bottom]`，单位为**物理像素**。

裁剪区域应尽量紧凑，只包含数字部分，避免图标等干扰元素影响 OCR 准确率。

### capture.name_region

云机名称区域坐标，格式同上。设为 `null` 则跳过名称识别。

### switch.next_button

切换到下一个账户的按钮位置，格式 `[x, y]`，单位为**物理像素**。

### switch.wait_after_switch

点击切换按钮后的固定等待秒数。程序还会额外等待画面加载完成（检测到新钻石数据），此值为保底等待时间。

### stats.total_accounts

要处理的账户总数。设为 `0` 表示无限制，需手动停止。

## 坐标校准

推荐使用 GUI 校准工具获取准确坐标：

```bash
python main.py --calibrate
python calibrate_tool.py calibrate.png
```

也可以手动在图片查看器中打开 `calibrate.png`，用鼠标获取像素坐标后填入配置。
