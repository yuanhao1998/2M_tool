"""AutomationFlow 基类 + 步骤执行引擎。"""

from __future__ import annotations

import functools
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PIL import Image

from core.capture import fullscreen_screenshot, crop_region as _crop_region
from core.mouse import click as _click
from core.ocr_engine import extract_text, recognize_diamond_stable
from automation.step import StepConfig, StopFlow

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """模板匹配结果。

    Attributes:
        matched: 是否匹配成功。
        confidence: 匹配置信度 (0.0-1.0)。
        location: 匹配位置 (x, y)，左上角像素坐标。
    """
    matched: bool
    confidence: float = 0.0
    location: tuple[int, int] = (0, 0)


@dataclass
class TextResult:
    """OCR 文字定位结果。

    Attributes:
        found: 是否找到文字。
        text: 识别到的完整文字。
        center: 文字包围盒中心坐标 (x, y)。
    """
    found: bool
    text: str = ""
    center: tuple[int, int] = (0, 0)


class State:
    """运行状态，由 FlowRunner 的热键线程写入，step 执行时读取。"""
    def __init__(self) -> None:
        self.running = False
        self.paused = False
        self.stopped = False


class AutomationFlow:
    """流程基类。

    子类定义 @step 方法并实现 run():
        class MyFlow(AutomationFlow):
            img = MyImages()

            @step(match=img.target)
            def action(self):
                self.click(100, 200)

            def run(self):
                self.action()

        MyFlow().main(repeat=10)
    """

    def __init__(self) -> None:
        self._state = State()
        self._debug = False
        self._dry_run = False
        self._current_account = 0
        self._wait_jitter = 0.0
        self._wait_long_prob = 0.0
        self._wait_long_min = 2.0
        self._wait_long_max = 6.0
        self.device_name = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for key, value in list(vars(cls).items()):
            if callable(value) and hasattr(value, "_step_config"):
                cfg: StepConfig = value._step_config
                wrapper = _build_step_wrapper(value, cfg)
                setattr(cls, key, wrapper)

    def _load_wait_config(self) -> None:
        """从 conf/config.yaml 读取 wait 相关配置。"""
        from pathlib import Path
        from ruamel.yaml import YAML

        cfg_path = Path("conf/config.yaml")
        if not cfg_path.exists():
            return

        yaml = YAML(typ="safe")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.load(f) or {}

        wait_cfg = cfg.get("wait", {})
        self._wait_jitter = float(wait_cfg.get("jitter", 0.0))
        self._wait_long_prob = float(wait_cfg.get("long_pause_prob", 0.0))
        self._wait_long_min = float(wait_cfg.get("long_pause_min", 2.0))
        self._wait_long_max = float(wait_cfg.get("long_pause_max", 6.0))

    def _capture_device_name(self) -> None:
        """截取云机名称区域并 OCR 识别，存入 self.device_name。"""
        from flows.common_define import NAME_REGION
        try:
            img = self.screenshot(NAME_REGION)
            self.device_name = extract_text(img)
            logger.info("云机名称: %s", self.device_name)
        except Exception:
            self.device_name = ""

    def _check_state(self) -> None:
        """检查运行状态：暂停则阻塞等待，停止则抛出 StopFlow。"""
        while self._state.paused and not self._state.stopped:
            time.sleep(0.1)
        if self._state.stopped:
            raise StopFlow

    # -- 屏幕操作 --
    def _scale_region(self, region: tuple[int, int, int, int] | None) -> tuple[int, int, int, int] | None:
        """将基准分辨率坐标转换为实际屏幕坐标。"""
        if region is None:
            return None
        try:
            from core.mouse import _get_resolution_scale
            rs_w, rs_h = _get_resolution_scale()
        except Exception:
            return region
        return (round(region[0] * rs_w), round(region[1] * rs_h),
                round(region[2] * rs_w), round(region[3] * rs_h))

    def screenshot(self, region: tuple[int, int, int, int] | None = None) -> Image.Image:
        """截取全屏或指定区域。

        Args:
            region: 裁剪区域 [left, top, right, bottom]（基准分辨率），None 表示全屏。

        Returns:
            PIL Image 对象。
        """
        self._check_state()
        img = fullscreen_screenshot()
        region = self._scale_region(region)
        if region:
            img = _crop_region(img, region)
        return img

    def crop(self, image: Image.Image, region: tuple[int, int, int, int]) -> Image.Image:
        """从已有图片中裁剪区域。

        Args:
            image: PIL Image 对象。
            region: 裁剪区域 [left, top, right, bottom]。

        Returns:
            裁剪后的 PIL Image。
        """
        return _crop_region(image, region)

    # -- 点击操作 --
    def click(self, *args: int) -> None:
        """移动鼠标到目标并点击，自动适配 Retina 缩放。

        两种用法:
            self.click(x, y)                          — 精确点击坐标
            self.click(left, top, right, bottom)      — 矩形区域内随机点击

        Note:
            dry_run 模式下只打印日志，不执行实际点击。
        """
        self._check_state()
        if self._dry_run:
            logger.info("[dry-run] click%s", args)
            return
        _click(*args)

    def drag(self, *args: int, duration: float | None = None) -> None:
        """从起点拖拽到终点（按下 → 移动 → 抬起），模拟滑动操作。

        用法:
            self.drag(x1, y1, x2, y2, duration=0.3)                   — 精确起终点
            self.drag(l1,t1,r1,b1, l2,t2,r2,b2, duration=0.5)         — 起终点均区域随机

        Args:
            duration: 滑动耗时（秒），None 使用配置文件 move_duration。
        """
        self._check_state()
        if self._dry_run:
            logger.info("[dry-run] drag%s duration=%s", args, duration)
            return
        from core.mouse import drag as _drag
        if len(args) == 4:
            _drag(*args) if duration is None else _drag(*args, duration=duration)
        elif len(args) == 8:
            l1, t1, r1, b1, l2, t2, r2, b2 = args
            x1 = random.randint(min(l1, r1), max(l1, r1))
            y1 = random.randint(min(t1, b1), max(t1, b1))
            x2 = random.randint(min(l2, r2), max(l2, r2))
            y2 = random.randint(min(t2, b2), max(t2, b2))
            _drag(x1, y1, x2, y2) if duration is None else _drag(x1, y1, x2, y2, duration=duration)
        else:
            raise TypeError(f"drag 需要 4 个参数(精确)或 8 个参数(区域)，实际传入 {len(args)} 个")

    def wait(self, seconds: float, jitter: float | None = None) -> None:
        """等待指定秒数，模拟人类操作节奏。

        大部分时间在 jitter 区间内均匀抖动，小概率触发长时间"走神"等待。

        Args:
            seconds: 基础等待时长（秒）。
            jitter: 覆盖 conf/config.yaml 的抖动比例，None 使用配置文件值。
                    设为 0 强制精确等待。
        """
        j = self._wait_jitter if jitter is None else jitter

        act_type = "精确"
        if j <= 0:
            actual = seconds
        elif random.random() < self._wait_long_prob:
            actual = seconds * random.uniform(self._wait_long_min, self._wait_long_max)
            act_type = "长等待"
        else:
            actual = seconds * (1 + random.uniform(-j, j))
            act_type = "抖动"

        if actual >= seconds * 3:
            logger.info("wait(%.1fs) → 实际 %.1fs (%s)", seconds, actual, act_type)
        else:
            logger.debug("wait(%.1fs) → 实际 %.1fs (%s)", seconds, actual, act_type)

        end = time.monotonic() + actual
        while time.monotonic() < end:
            self._check_state()
            time.sleep(min(0.1, max(0.01, end - time.monotonic())))

    # -- 模板匹配 --
    def _resolve_image(self, image_ref: Any) -> np.ndarray:
        from automation.images import ImageRef

        if isinstance(image_ref, ImageRef):
            pil = Image.open(image_ref.path)
        elif isinstance(image_ref, str):
            pil = Image.open(image_ref)
        elif isinstance(image_ref, Image.Image):
            pil = image_ref
        elif isinstance(image_ref, np.ndarray):
            return image_ref
        else:
            raise TypeError(f"不支持的图片类型: {type(image_ref)}")
        return cv2.cvtColor(np.array(pil.convert("RGB")), cv2.COLOR_RGB2BGR)

    def _screen_bgr(self, region: tuple[int, int, int, int] | None = None) -> np.ndarray:
        """截图并转为 BGR numpy 数组（OpenCV 格式）。"""
        pil = self.screenshot(region)
        return cv2.cvtColor(np.array(pil.convert("RGB")), cv2.COLOR_RGB2BGR)

    def find(self, image: Any, region: tuple[int, int, int, int] | None = None,
             threshold: float = 0.85, on: np.ndarray | None = None) -> MatchResult:
        """模板匹配：在屏幕中查找参考图的位置。

        使用 cv2.matchTemplate + TM_CCOEFF_NORMED 算法。

        Args:
            image: 参考图，支持 ImageRef / PIL Image / 文件路径 / numpy 数组。
            region: 搜索区域 [left, top, right, bottom]，None 表示全屏搜索。
            threshold: 匹配置信度阈值 (0.0-1.0)，推荐 0.85。
            on: 在此图像上匹配而非重新截图（避免重复截屏）。

        Returns:
            MatchResult，其中 matched 为 True 表示置信度达到阈值。
        """
        self._check_state()
        ref = self._resolve_image(image)
        screen = on if on is not None else self._screen_bgr(region)
        result = cv2.matchTemplate(screen, ref, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return MatchResult(matched=max_val >= threshold, confidence=float(max_val),
                          location=(int(max_loc[0]), int(max_loc[1])))

    def wait_match(self, image: Any, region: tuple[int, int, int, int] | None = None,
                   timeout: float = 30, interval: float = 1.0,
                   threshold: float = 0.85) -> MatchResult:
        """轮询等待直到模板匹配成功或超时。

        Args:
            image: 参考图，支持 ImageRef / PIL Image / 文件路径 / numpy 数组。
            region: 搜索区域 [left, top, right, bottom]。
            timeout: 超时时间（秒）。
            interval: 轮询间隔（秒）。
            threshold: 匹配置信度阈值。

        Returns:
            MatchResult，超时时 matched=False。
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            r = self.find(image, region=region, threshold=threshold)
            if r.matched:
                return r
            self.wait(interval)
        return MatchResult(matched=False)

    def match_click(self, image: Any, target: tuple[int, int] |tuple[int, int, int, int] | None = None,
                    region: tuple[int, int, int, int] | None = None,
                    threshold: float = 0.85) -> bool:
        """匹配到参考图后自动点击。

        Args:
            image: 参考图，支持 ImageRef / PIL Image / 文件路径。
            target: 点击坐标 (x, y)，None 则自动点击匹配位置的中心。
            region: 搜索区域 [left, top, right, bottom]。
            threshold: 匹配置信度阈值。

        Returns:
            True 表示匹配成功并已点击，False 表示未匹配到。
        """
        r = self.find(image, region=region, threshold=threshold)
        if r.matched:
            if target:
                self.click(*target)
            else:
                ref = self._resolve_image(image)
                h, w = ref.shape[:2]
                self.click(r.location[0] + w // 2, r.location[1] + h // 2)
            return True
        return False

    def click_until_match(self, match_image: Any,
                          click_pos: tuple[int, int],
                          region: tuple[int, int, int, int] | None = None,
                          threshold: float = 0.85,
                          max_clicks: int = 50,
                          interval: float = 1.0) -> bool:
        """反复点击直到指定图片匹配成功。

        Args:
            match_image: 等待出现的参考图。
            click_pos: 每次循环点击的坐标 (x, y)。
            region: 匹配搜索区域。
            threshold: 匹配置信度阈值。
            max_clicks: 最大点击次数。
            interval: 点击间隔（秒）。

        Returns:
            True 表示匹配成功，False 表示超过最大点击次数。
        """
        for attempt in range(1, max_clicks + 1):
            self._check_state()
            self.click(*click_pos)
            self.wait(interval)
            r = self.find(match_image, region=region, threshold=threshold)
            if r.matched:
                logger.info("click_until_match: 第 %d 次点击后匹配成功", attempt)
                return True
        logger.warning("click_until_match: %d 次点击后仍未匹配", max_clicks)
        return False

    def click_until_gone(self, match_image: Any,
                         click_pos: tuple[int, int] | tuple[int, int, int, int],
                         region: tuple[int, int, int, int] | None = None,
                         threshold: float = 0.85,
                         max_clicks: int = 50,
                         interval: float = 1.0,
                         stable_wait: float = 5.0) -> bool:
        """反复点击直到指定图片稳定消失。

        图片消失后等待 stable_wait 秒再次确认，防止弹框消失后
        立即再次弹出。

        Args:
            match_image: 需要消除的参考图。
            click_pos: 关闭按钮坐标 (x, y) 或区域 (l,t,r,b)。
            region: 匹配搜索区域。
            threshold: 匹配置信度阈值。
            max_clicks: 最大点击次数。
            interval: 点击间隔（秒）。
            stable_wait: 消失后稳定等待时间（秒），再次检查确认已消失。

        Returns:
            True 表示图片已稳定消失，False 表示超过最大点击次数。
        """
        for _ in range(max_clicks):
            self._check_state()
            r = self.find(match_image, region=region, threshold=threshold)
            if not r.matched:
                # 稳定确认：等待后再检查一次，防止弹框又弹出
                self.wait(stable_wait)
                r2 = self.find(match_image, region=region, threshold=threshold)
                if not r2.matched:
                    return True
                logger.debug("click_until_gone: 图片消失后又出现，继续点击")
            self.click(*click_pos)
            self.wait(interval)
        logger.warning("click_until_gone: %d 次点击后仍未稳定消失", max_clicks)
        return False

    def find_text(self, text: str, region: tuple[int, int, int, int] | None = None) -> TextResult:
        """OCR 文字定位：在屏幕中搜索指定文字并返回其中心坐标。

        Args:
            text: 要搜索的文字（大小写不敏感，支持子串匹配）。
            region: 搜索区域 [left, top, right, bottom]，None 表示全屏。

        Returns:
            TextResult，found=True 时包含文字和中心坐标。
        """
        self._check_state()
        from core.ocr_engine import _get_reader
        reader = _get_reader()
        img = self.screenshot(region)
        results = reader.readtext(np.array(img), detail=1)
        # 区域裁剪后坐标需加上偏移量转回全屏坐标
        offset_x = region[0] if region else 0
        offset_y = region[1] if region else 0
        # 去除空格后比对，兼容韩文/英文 EasyOCR 断词差异
        query = text.replace(" ", "").lower()
        for bbox, detected, _ in results:
            if query in detected.replace(" ", "").lower():
                cx = int((bbox[0][0] + bbox[2][0]) / 2) + offset_x
                cy = int((bbox[0][1] + bbox[2][1]) / 2) + offset_y
                return TextResult(found=True, text=detected, center=(cx, cy))
        return TextResult(found=False)

    def text_region(self, center: tuple[int, int],
                    left: int = 15, top: int = 15,
                    right: int = 15, bottom: int = 15) -> tuple[int, int, int, int]:
        """根据中心坐标生成随机点击区域，四周扩展可分别控制。

        Args:
            center: 中心坐标 (x, y)，通常来自 find_text 返回的 .center。
            left: 向左扩展像素。
            top: 向上扩展像素。
            right: 向右扩展像素。
            bottom: 向下扩展像素。

        Returns:
            (left, top, right, bottom) 四元组，可直接传给 self.click()。
        """
        cx, cy = center
        return (cx - left, cy - top, cx + right, cy + bottom)

    # -- 钻石识别 --
    def ocr_diamonds(self, region: tuple[int, int, int, int],
                     name_region: tuple[int, int, int, int] | None = None) -> dict:
        """执行一次钻石数量识别（含稳定采样）。

        截取指定区域的钻石数据进行 OCR，多次采样比对确保准确性。

        Args:
            region: 钻石数量区域 [left, top, right, bottom]。
            name_region: 云机名称区域 [left, top, right, bottom]，None 表示跳过名称识别。

        Returns:
            dict: {"cloud_device": 设备名, "diamonds": 钻石数量字符串, "unstable": 是否不稳定}
        """
        self._check_state()
        device = ""
        if name_region:
            name_img = self.screenshot(name_region)
            device = extract_text(name_img)

        def _capture() -> Image.Image:
            return self.screenshot(region)

        diamonds, unstable = recognize_diamond_stable(
            _capture, max_attempts=6,
            account_index=self._current_account, device_name=device,
        )
        return {"cloud_device": device, "diamonds": diamonds, "unstable": unstable}

    # -- 流程控制 --
    def goto(self, method_name: str) -> str:
        """返回方法名信号，由 @step 包装器解释为跳转到指定步骤。

        在 @step 方法中 return self.goto("step_name") 即可跳转。

        Args:
            method_name: 目标步骤的方法名。
        """
        return method_name

    def retry(self) -> str:
        """返回重试信号，由 @step 包装器解释为重新执行当前步骤。

        在 @step 方法中 return self.retry() 即可重试。
        """
        return "retry"

    def stop(self) -> None:
        """立即终止流程执行。"""
        raise StopFlow

    def switch_account(self, click_pos: tuple[int, int], wait: float = 2.0) -> None:
        """点击切换账户按钮并等待。

        Args:
            click_pos: 切换按钮坐标 (x, y)。
            wait: 点击后等待时间（秒）。
        """
        self.click(*click_pos)
        self.wait(wait)

    # -- 主入口 --
    def main(self, repeat: int = 1,
             hotkeys: dict | None = None,
             debug: bool = False,
             dry_run: bool = False,
             start_step: str | None = None) -> None:
        """启动流程：注册热键，循环执行 run()。

        Args:
            repeat: 循环轮数（即处理的账户数）。
            hotkeys: 自定义热键 dict，如 {"start": "f5", "pause": "f6", "stop": "f7"}。
            debug: True 时每步打印匹配结果、置信度、坐标等详细信息。
            dry_run: True 时只验证匹配不执行实际点击（安全检查模式）。
            start_step: 从指定步骤方法名开始执行（跳过之前的步骤）。
        """
        self._debug = debug
        self._dry_run = dry_run

        from conf.log import add_log
        add_log()
        self._load_wait_config()
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)

        from automation.runner import FlowRunner
        FlowRunner(self, repeat=repeat, hotkeys=hotkeys, start_step=start_step).run()

    def run(self) -> None:
        """子类重写此方法定义流程步骤。

        Raises:
            NotImplementedError: 子类必须实现此方法。
        """
        raise NotImplementedError("子类必须实现 run() 方法")


def _build_step_wrapper(func: Callable, cfg: StepConfig) -> Callable:
    """构建 @step 方法包装器：调用前模板匹配，失败重试/跳转。"""

    @functools.wraps(func)
    def wrapper(self: AutomationFlow, *args: Any, **kwargs: Any) -> Any:
        self._check_state()

        if cfg.match is None:
            result = func(self, *args, **kwargs)
            if cfg.wait_after:
                self.wait(cfg.wait_after)
            return result

        for attempt in range(cfg.max_retries):
            self._check_state()
            r = self.find(cfg.match, region=cfg.region, threshold=cfg.threshold)
            if r.matched:
                if self._debug:
                    logger.info("[%s] 匹配成功 (置信度%.3f, 第%d/%d次)",
                                cfg.name, r.confidence, attempt + 1, cfg.max_retries)
                try:
                    result = func(self, *args, **kwargs)
                except StopFlow:
                    raise
                if cfg.wait_after:
                    self.wait(cfg.wait_after)
                return result

            if cfg.optional:
                if self._debug:
                    logger.info("[%s] 可选步骤，已跳过", cfg.name)
                return None

            if attempt < cfg.max_retries - 1:
                self.wait(cfg.interval)

        # 重试耗尽 → on_fail
        if cfg.on_fail:
            logger.warning("[%s] 重试%d次失败 → 执行 on_fail: %s",
                           cfg.name, cfg.max_retries, cfg.on_fail)
            fail_method = getattr(self, cfg.on_fail, None)
            if fail_method is not None:
                return fail_method()
        logger.error("[%s] 重试%d次后失败", cfg.name, cfg.max_retries)
        return None

    wrapper._step_config = cfg
    return wrapper
