"""@step 装饰器 + StepConfig + 流程控制信号。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


RETRY = "retry"


class StopFlow(Exception):
    """在 step 方法中 raise 或调用 self.stop() 来立即终止流程。"""


@dataclass
class StepConfig:
    """步骤配置，由 @step 装饰器附加到方法上。"""
    name: str
    match: Any = None
    region: tuple[int, int, int, int] | None = None
    threshold: float = 0.85
    max_retries: int = 30
    interval: float = 1.0
    wait_after: float = 0.0
    on_fail: str | None = None
    optional: bool = False


def step(
    match: Any = None,
    *,
    region: tuple[int, int, int, int] | None = None,
    threshold: float = 0.85,
    max_retries: int = 30,
    interval: float = 1.0,
    wait_after: float = 0.0,
    on_fail: str | None = None,
    optional: bool = False,
    name: str | None = None,
) -> Callable:
    """装饰器：声明步骤的匹配条件、重试策略和失败处理。

    方法体仅在 match 匹配成功（或无 match）时执行。
    匹配失败 → 重试 → on_fail 兜底。
    optional=True 时匹配失败直接跳过。

    Args:
        match: 参考图（ImageRef / PIL Image / 路径）。None = 无条件执行。
        region: 匹配区域 [left, top, right, bottom]。
        threshold: 匹配置信度阈值。
        max_retries: 最大重试次数。
        interval: 重试间隔（秒）。
        wait_after: 步骤完成后等待（秒）。
        on_fail: 匹配失败时调用的方法名。
        optional: True 则匹配失败时跳过此步。
        name: 步骤名（默认函数名）。
    """
    def decorator(func: Callable) -> Callable:
        func._step_config = StepConfig(
            name=name or func.__name__,
            match=match,
            region=region,
            threshold=threshold,
            max_retries=max_retries,
            interval=interval,
            wait_after=wait_after,
            on_fail=on_fail,
            optional=optional,
        )
        return func
    return decorator
