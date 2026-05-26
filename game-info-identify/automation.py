"""自动化模块：鼠标点击模拟，自动适配 Retina 缩放。"""

import logging
import time

import pyautogui
from PIL import ImageGrab

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


_scale_cache: float | None = None


def _get_scale() -> float:
    """获取 Retina 缩放比：截图物理像素 / 屏幕逻辑坐标，结果缓存。"""
    global _scale_cache
    if _scale_cache is None:
        screenshot_w = ImageGrab.grab().width
        logical_w = pyautogui.size().width
        _scale_cache = screenshot_w / logical_w
        logger.info("检测到屏幕缩放比: %.1fx (截图%dpx / 逻辑%dlp)", _scale_cache, screenshot_w, logical_w)
    return _scale_cache


def click(x: int, y: int) -> None:
    """移动鼠标到目标坐标并点击，自动适配 Retina。

    Args:
        x: 物理像素横坐标（来自截图）。
        y: 物理像素纵坐标（来自截图）。
    """
    scale = _get_scale()
    lx = round(x / scale)
    ly = round(y / scale)
    pyautogui.click(lx, ly)


def switch_to_next(x: int, y: int, wait: float = 2.0) -> None:
    """点击切换按钮，然后等待画面加载。

    Args:
        x: 按钮物理像素横坐标。
        y: 按钮物理像素纵坐标。
        wait: 切换后等待时间（秒）。
    """
    click(x, y)
    logger.info("等待 %.1f 秒让画面加载...", wait)
    time.sleep(wait)
