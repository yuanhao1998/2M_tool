"""FlowRunner: 热键监听 + 多轮循环 + 主入口。"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from pynput import keyboard

from automation.step import StopFlow

if TYPE_CHECKING:
    from automation.flow import AutomationFlow

logger = logging.getLogger(__name__)

DEFAULT_HOTKEYS = {"start": "f5", "pause": "f6", "stop": "f7", "exit": "esc"}


class FlowRunner:
    """管理热键和循环，驱动流程执行。"""

    def __init__(self, flow: AutomationFlow, repeat: int = 1,
                 hotkeys: dict | None = None,
                 start_step: str | None = None) -> None:
        self._flow = flow
        self._repeat = repeat
        self._hotkeys = {**DEFAULT_HOTKEYS, **(hotkeys or {})}
        self._start_step = start_step
        self._listener: keyboard.Listener | None = None
        self._state = flow._state
        self._results: list[dict] = []

    def run(self) -> None:
        """启动热键监听，等待 F5 后执行循环。"""
        flow = self._flow

        hk = self._hotkeys

        def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
            try:
                k = _key_name(key)
            except AttributeError:
                return
            if k == hk["start"]:
                self._state.running = True
                self._state.paused = False
                logger.info("▶ 开始")
            elif k == hk["pause"]:
                self._state.paused = not self._state.paused
                logger.info("⏸ 暂停" if self._state.paused else "▶ 继续")
            elif k == hk["stop"]:
                self._state.stopped = True
                self._state.paused = False
                logger.info("⏹ 停止")
            elif k == hk["exit"]:
                self._state.stopped = True
                self._state.paused = False
                logger.info("退出")
                self._listener.stop() if self._listener else None

        self._listener = keyboard.Listener(on_press=on_press)
        self._listener.daemon = True
        self._listener.start()

        logger.info("等待按 %s 开始...", hk["start"].upper())
        while not self._state.running and not self._state.stopped:
            time.sleep(0.1)

        if self._state.stopped:
            return

        try:
            for i in range(self._repeat):
                if self._state.stopped:
                    logger.info("已停止，当前账户: %d/%d", i, self._repeat)
                    break
                flow._current_account = i + 1
                flow._capture_device_name()
                logger.info("--- 账户 %d/%d [%s] ---", flow._current_account, self._repeat, flow.device_name)

                flow.run()

                # 每轮结束后切换账户
                if i < self._repeat - 1 and not self._state.stopped:
                    switch = getattr(flow, "switch_to_next", None)
                    if switch:
                        logger.info("切换账户...")
                        switch()

        except StopFlow:
            logger.info("流程已停止")
        except Exception:
            logger.exception("流程执行异常")

        logger.info("流程结束，共处理 %d 个账户", flow._current_account)

        if self._listener.is_alive():
            self._listener.stop()


def _key_name(key: keyboard.Key | keyboard.KeyCode | None) -> str:
    """将 pynput key 转为小写字符串。"""
    if key is None:
        return ""
    if hasattr(key, "char") and key.char:
        return key.char.lower()
    return str(key).replace("Key.", "").lower()
