"""鼠标点击模拟：Retina 自适应 + 贝塞尔曲线人类轨迹。"""

import logging
import math
import random
import time
from pathlib import Path

import pyautogui
from PIL import ImageGrab
from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.0  # 我们自己控制节奏


def _keep_cursor_visible() -> None:
    """macOS 上自动化操作后光标可能消失，强制显示光标。"""
    try:
        import Quartz
        Quartz.CGDisplayShowCursor(Quartz.CGMainDisplayID())
    except ImportError:
        x, y = pyautogui.position()
        pyautogui.moveTo(x + 1, y, duration=0.005)
        pyautogui.moveTo(x, y, duration=0.005)

_scale_cache: float | None = None
_res_cache: tuple[float, float] | None = None  # (宽缩放比, 高缩放比)
_config: dict = {}
_last_logical: tuple[int, int] | None = None


def _get_scale() -> float:
    global _scale_cache
    if _scale_cache is None:
        screenshot_w = ImageGrab.grab().width
        logical_w = pyautogui.size().width
        _scale_cache = screenshot_w / logical_w
        logger.info("屏幕缩放比: %.1fx (截图%dpx / 逻辑%dlp)", _scale_cache, screenshot_w, logical_w)
    return _scale_cache


def _get_resolution_scale() -> tuple[float, float]:
    """获取跨分辨率缩放比，使一套坐标适配不同分辨率机器。"""
    global _res_cache
    if _res_cache is None:
        cfg = _load_config()
        screen_cfg = _load_full_config().get("screen", {})
        base_w = float(screen_cfg.get("base_width", 5120))
        base_h = float(screen_cfg.get("base_height", 0))
        actual_w = ImageGrab.grab().width
        actual_h = ImageGrab.grab().height
        scale_w = actual_w / base_w
        scale_h = actual_h / base_h if base_h > 0 else scale_w
        _res_cache = (scale_w, scale_h)
        logger.info("分辨率缩放: %.2fx / %.2fx (实际%dx%d → 基准%dx%d)",
                     scale_w, scale_h, actual_w, actual_h, int(base_w), int(base_h))
    return _res_cache


def _load_full_config() -> dict:
    """加载完整 config.yaml 配置。"""
    cfg_path = Path("conf/config.yaml")
    if cfg_path.exists():
        yaml = YAML(typ="safe")
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.load(f) or {}
    return {}


def _load_config() -> dict:
    global _config
    if _config:
        return _config
    cfg_path = Path("conf/config.yaml")
    if cfg_path.exists():
        yaml = YAML(typ="safe")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.load(f) or {}
        _config = cfg.get("mouse", {})
    return _config


def _to_logical(x: int, y: int) -> tuple[int, int]:
    """物理像素坐标 → 逻辑坐标，自动适配 Retina + 跨分辨率缩放。"""
    scale = _get_scale()
    rs_w, rs_h = _get_resolution_scale()
    return round(x * rs_w / scale), round(y * rs_h / scale)


def click(*args: int) -> None:
    """移动到目标并点击，自动适配 Retina。

    两种用法:
        click(x, y)               — 精确点击坐标
        click(left, top, right, bottom) — 在矩形区域内随机点击
    """
    if len(args) == 2:
        x, y = args
    elif len(args) == 4:
        left, top, right, bottom = args
        x = random.randint(min(left, right), max(left, right))
        y = random.randint(min(top, bottom), max(top, bottom))
    else:
        raise TypeError(f"click 需要 2 个参数(精确)或 4 个参数(区域)，实际传入 {len(args)} 个")
    move_to(x, y)
    pyautogui.click()
    _keep_cursor_visible()


def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> None:
    """从起点拖拽到终点。

    Args:
        x1, y1: 起点物理像素坐标。
        x2, y2: 终点物理像素坐标。
        duration: 拖拽耗时（秒）。
    """
    lx1, ly1 = _to_logical(x1, y1)
    lx2, ly2 = _to_logical(x2, y2)
    pyautogui.moveTo(lx1, ly1, duration=0.3)
    # _keep_cursor_visible()
    time.sleep(0.5)
    pyautogui.drag(lx2 - lx1, ly2 - ly1, duration=duration, button='left')
    # _keep_cursor_visible()
    global _last_logical
    _last_logical = (lx2, ly2)



def move_to(x: int, y: int, force_duration: float | None = None) -> None:
    """两阶段人类轨迹：快速冲向目标附近 → 可能过冲 → 微调修正。

    Args:
        x: 物理像素横坐标。
        y: 物理像素纵坐标。
        force_duration: 强制覆盖移动耗时（None 使用配置文件）。
    """
    global _last_logical
    cfg = _load_config()
    lx, ly = _to_logical(x, y)

    if _last_logical:
        sx, sy = _last_logical
    else:
        sx, sy = pyautogui.position()

    duration = force_duration if force_duration is not None else float(cfg.get("move_duration", 0.0))
    if duration <= 0:
        pyautogui.moveTo(lx, ly)
        _last_logical = (lx, ly)
        return

    # 移动耗时随机抖动
    dur_jitter = float(cfg.get("move_duration_jitter", 0.3))
    duration = duration * (1 + random.uniform(-dur_jitter, dur_jitter))

    # 最终落点：±3px 随机偏移（人类无法像素级精确）
    final_x = lx + random.randint(-3, 3)
    final_y = ly + random.randint(-3, 3)

    # --- 阶段1：快速冲向"过冲点" ---
    jitter = float(cfg.get("move_jitter", 200))
    overshoot_prob = float(cfg.get("overshoot_prob", 0.6))
    overshoot_range = float(cfg.get("overshoot_range", 40))

    if random.random() < overshoot_prob:
        # 过冲：目标点稍微超过最终位置
        dx = final_x - sx
        dy = final_y - sy
        dist = math.hypot(dx, dy) or 1
        overshoot_x = final_x + (dx / dist) * random.uniform(5, overshoot_range)
        overshoot_y = final_y + (dy / dist) * random.uniform(5, overshoot_range)
    else:
        # 不过冲：停在目标附近
        overshoot_x = final_x + random.uniform(-10, 10)
        overshoot_y = final_y + random.uniform(-10, 10)

    # 贝塞尔控制点
    cp1_x = sx + (overshoot_x - sx) * 0.3 + random.uniform(-jitter, jitter)
    cp1_y = sy + (overshoot_y - sy) * 0.2 + random.uniform(-jitter, jitter)
    cp2_x = sx + (overshoot_x - sx) * 0.7 + random.uniform(-jitter, jitter)
    cp2_y = sy + (overshoot_y - sy) * 0.8 + random.uniform(-jitter, jitter)

    # 快速阶段：移动 80% 路径到过冲点
    fast_steps = max(6, int(duration * 0.7 / 0.005))
    for i in range(fast_steps + 1):
        t = _ease_in_out(i / fast_steps)
        u = 1 - t
        cx = u**3 * sx + 3 * u**2 * t * cp1_x + 3 * u * t**2 * cp2_x + t**3 * overshoot_x
        cy = u**3 * sy + 3 * u**2 * t * cp1_y + 3 * u * t**2 * cp2_y + t**3 * overshoot_y
        pyautogui.moveTo(int(cx), int(cy))

    # --- 阶段2：微调修正，从过冲点滑回最终位置 ---
    correct_steps = max(3, int(duration * 0.3 / 0.008))
    for i in range(correct_steps + 1):
        t = i / correct_steps
        # 修正阶段更慢
        cx = overshoot_x + (final_x - overshoot_x) * _ease_in_out(t)
        cy = overshoot_y + (final_y - overshoot_y) * _ease_in_out(t)
        pyautogui.moveTo(int(cx), int(cy))

    _last_logical = (final_x, final_y)
    # 同步更新终点附近位置，避免连续点击完全重复
    _last_logical = (lx + random.randint(-2, 2), ly + random.randint(-2, 2))


def _ease_in_out(t: float) -> float:
    """缓入缓出函数：开始慢、中间快、结束慢。"""
    return t * t * (3 - 2 * t)


def switch_to_next(x: int, y: int, wait: float = 2.0) -> None:
    """点击切换按钮，然后等待画面加载。"""
    click(x, y)
    logger.info("等待 %.1f 秒让画面加载...", wait)
    time.sleep(wait)
