"""视觉自动化执行引擎：按预设 YAML 流程截屏比对，执行点击、等待等操作。

支持动作类型：
  click            — 直接点击
  wait             — 纯延时等待
  wait_match       — 截屏比对，匹配后继续（判断画面加载完成）
  match_click      — 截屏比对，匹配后点击
  click_until_match— 重复点击直到画面匹配，然后点击指定位置
  loop             — 循环执行子步骤
"""

import argparse
import logging
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageGrab
from ruamel.yaml import YAML
from pynput import keyboard

import json
from datetime import datetime
from pathlib import Path

from automation import click
from ocr_engine import extract_text, preprocess, _get_reader, recognize_diamond, recognize_diamond_stable
from capture import fullscreen_screenshot, crop_region

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("planner")


class State:
    running = False
    paused = False
    stopped = False


_state = State()

# 钻石识别结果收集
_diamond_results: list[dict] = []
_diamond_output: Path | None = None

# ---- 图像比对 ----

def _match(image: np.ndarray, reference_path: str, threshold: float) -> tuple[bool, float]:
    """模板匹配：在截图中查找参考图，返回 (是否匹配, 匹配置信度)。"""
    ref = cv2.imread(reference_path)
    if ref is None:
        logger.error("无法加载参考图: %s", reference_path)
        return False, 0.0

    if image.shape[0] < ref.shape[0] or image.shape[1] < ref.shape[1]:
        logger.warning("截图区域小于参考图，无法匹配")
        return False, 0.0

    result = cv2.matchTemplate(image, ref, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val >= threshold, max_val


def _screenshot_region(region: tuple[int, int, int, int]) -> np.ndarray:
    """截取指定区域 (left, top, right, bottom)，返回 BGR numpy array。

    macOS 的 screencapture -R 期望 x,y,width,height，与 bbox 格式不同，
    因此用全屏截取 + PIL 裁剪，避免跨平台兼容性问题。
    """
    left, top, right, bottom = region
    full = ImageGrab.grab()
    crop = full.crop((left, top, right, bottom))
    return cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)


def _match_text(image, expected: str) -> bool:
    """OCR 识别图片中的文字，检查 expected 是否为子串。"""
    text = extract_text(preprocess(image))
    return expected in text


def _find_text_position(image, expected: str) -> tuple[int, int] | None:
    """在图片中用 OCR 定位文字，返回文字中心在图片中的坐标 (x, y)。"""
    reader = _get_reader()
    results = reader.readtext(np.array(preprocess(image)), detail=1)
    for bbox, text, _ in results:
        if expected in text:
            cx = int((bbox[0][0] + bbox[2][0]) / 2)
            cy = int((bbox[0][1] + bbox[2][1]) / 2)
            return cx, cy
    return None


def _do_match(image: np.ndarray, step: dict) -> tuple[bool, float]:
    """根据 step 配置选择图片匹配或文字匹配。"""
    match_text = step.get("match_text")
    if match_text:
        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        ok = _match_text(pil_img, match_text)
        return ok, 1.0 if ok else 0.0
    reference = step["reference"]
    threshold = step.get("threshold", 0.85)
    return _match(image, reference, threshold)


# ---- 热键 ----

def _on_press(key, hotkeys: dict):
    k = None
    try:
        k = key.name if hasattr(key, "name") else key.char
    except AttributeError:
        return

    if k == hotkeys.get("start"):
        if not _state.running:
            _state.running = True
            _state.paused = False
            logger.info("▶  开始执行")
        elif _state.paused:
            _state.paused = False
            logger.info("▶  继续执行")
    elif k == hotkeys.get("pause"):
        if _state.running:
            _state.paused = True
            logger.info("⏸  已暂停")
    elif k == hotkeys.get("stop"):
        _state.stopped = True
        _state.running = False
        logger.info("⏹  已停止")
    elif k == hotkeys.get("exit"):
        logger.info("🛑 退出")
        sys.exit(0)


def _check_state() -> bool:
    """检查是否应继续执行。暂停时阻塞，停止时返回 False。"""
    while _state.paused and not _state.stopped:
        time.sleep(0.2)
    return not _state.stopped


# ---- 动作执行 ----
#
# _execute_step 返回值:
#   None      — 继续下一步
#   "retry"   — 重试当前步骤
#   int       — 跳转到指定步骤 (1-based)
#   "end"     — 结束流程

def _wait_match(step: dict, step_prefix: str) -> bool:
    """轮询截屏比对，支持图片匹配或文字匹配，匹配后返回 True。"""
    region = tuple(step["match_region"])
    match_text = step.get("match_text")
    threshold = step.get("threshold", 0.85)
    max_retries = step.get("max_retries", 30)
    interval = step.get("interval", 1)

    hint = f"文字 \"{match_text}\"" if match_text else f"图片（阈值 {threshold:.2f}）"
    logger.info("%s等待匹配 %s ...", step_prefix, hint)
    for attempt in range(1, max_retries + 1):
        if not _check_state():
            return False

        region_img = _screenshot_region(region)
        ok, conf = _do_match(region_img, step)
        if ok:
            logger.info("%s  ✓ 匹配成功（第 %d 次，置信度 %.3f）", step_prefix, attempt, conf)
            return True
        time.sleep(interval)

    logger.warning("%s  ✗ 超时未匹配（%d 次）", step_prefix, max_retries)
    return False


def _handle_fail(step: dict, step_prefix: str) -> str | int | None:
    """匹配失败时执行 on_fail，返回流程跳转信号。

    on_fail 支持两种格式:
      1. 列表: 每个元素为完整步骤，依次执行
      2. 字典: { action: click/wait/stop, target: [x,y], goto: N, retry: true }
    """
    on_fail = step.get("on_fail")
    if not on_fail:
        return None

    label = f"{step_prefix} [on_fail]"

    # 格式 1: 列表 → 依次执行子步骤
    if isinstance(on_fail, list):
        logger.info("%s执行失败处理（%d 步）", label, len(on_fail))
        for j, sub in enumerate(on_fail):
            if not _check_state():
                return None
            signal = _execute_step(sub, f"{step_prefix}.f{j + 1}")
            if signal:
                return signal
        return None

    # 格式 2: 字典 → 简单动作
    action = on_fail.get("action")
    if action:
        logger.info("%s执行失败处理: %s", label, action)
        if action == "click":
            target = on_fail.get("target")
            if not target:
                logger.warning("%son_fail.action=click 但缺少 target", label)
            else:
                click(target[0], target[1])
                if on_fail.get("wait_after"):
                    time.sleep(on_fail["wait_after"])
        elif action == "wait":
            time.sleep(on_fail.get("duration", 1))
        elif action == "stop":
            logger.info("%s流程终止", label)
            return "end"
        else:
            # 复杂动作（match_click, wait_match 等）→ 当作完整步骤执行
            signal = _execute_step(on_fail, label)
            if signal:
                return signal

    if on_fail.get("retry"):
        return "retry"
    if "goto" in on_fail:
        goto = on_fail["goto"]
        if goto == "end":
            return "end"
        if isinstance(goto, (list, tuple)) and len(goto) == 3:
            logger.info("%s跳转到步骤 %d case%d 子步骤 %d", label, goto[0], goto[1], goto[2])
            return tuple(goto)
        if isinstance(goto, (list, tuple)) and len(goto) == 2:
            logger.info("%s跳转到步骤 %d 子步骤 %d", label, goto[0], goto[1])
            return tuple(goto)
        if isinstance(goto, int) and goto >= 1:
            logger.info("%s跳转到步骤 %d", label, goto)
            return goto
    return None
def _resolve_target(step: dict) -> tuple[int, int] | None:
    """获取点击目标：优先用 target 字段，否则用 match_text 定位文字坐标。"""
    target = step.get("target") or step.get("then_click")
    if target:
        return tuple(target)

    match_text = step.get("match_text")
    if match_text and "match_region" in step:
        region = tuple(step["match_region"])
        left, top = region[0], region[1]
        pil_img = ImageGrab.grab().crop(region)
        pos = _find_text_position(pil_img, match_text)
        if pos:
            return (left + pos[0], top + pos[1])
    return None


def _next_signal(step: dict) -> str | int | tuple | None:
    """从步骤中读取成功后的 goto/retry 信号。

    字段:
      goto: N / "end"        — 跳转到步骤 N 或结束
      goto: [N, M]           — 跳转到步骤 N 的子步骤 M
      goto: [N, C, M]        — 跳转到步骤 N case C 的子步骤 M
      retry: true            — 成功后重试当前步骤
    """
    if step.get("retry"):
        return "retry"
    if "goto" in step:
        goto = step["goto"]
        if goto == "end":
            return "end"
        if isinstance(goto, (list, tuple)) and len(goto) in (2, 3):
            return tuple(goto)
        if isinstance(goto, int) and goto >= 1:
            return goto
    return None


def _execute_step(step: dict, step_prefix: str) -> str | int | None:
    """执行单个步骤，返回流程跳转信号。"""
    action = step.get("action", "click")
    name = step.get("name", "")
    label = f"[{step_prefix}] {name}" if name else f"[{step_prefix}]"

    if action == "click":
        target = step["target"]
        logger.info("%s直接点击 (%d, %d)", label, target[0], target[1])
        click(target[0], target[1])
        if step.get("wait_after"):
            time.sleep(step["wait_after"])

    elif action == "wait":
        duration = step.get("duration", 1)
        logger.info("%s等待 %.1f 秒", label, duration)
        time.sleep(duration)

    elif action == "wait_match":
        if _wait_match(step, label):
            if step.get("wait_after"):
                time.sleep(step["wait_after"])
        else:
            return _handle_fail(step, step_prefix)

    elif action == "match_click":
        if _wait_match(step, label):
            target = _resolve_target(step)
            if target:
                logger.info("%s已点击 (%d, %d)", label, target[0], target[1])
                click(target[0], target[1])
            else:
                logger.info("%s匹配成功，无需点击")
            if step.get("wait_after"):
                time.sleep(step["wait_after"])
        else:
            return _handle_fail(step, step_prefix)

    elif action == "loop":
        times = step.get("times", 1)
        sub_steps = step.get("steps", [])
        sub_total = len(sub_steps)
        start_sub = step.pop("_start_sub", None)  # 外部 goto [N,M] 注入的起始子步骤
        logger.info("%s循环 %d 次（%d 个子步骤）", label, times, sub_total)
        for i in range(times):
            if not _check_state():
                return None
            j = start_sub - 1 if start_sub else 0
            start_sub = None  # 仅第一轮生效
            while j < sub_total:
                if not _check_state():
                    return None
                sub = sub_steps[j]
                signal = _execute_step(sub, f"{step_prefix}.{i + 1}.{j + 1}")
                if signal == "retry":
                    continue
                elif signal == "end":
                    return signal
                elif isinstance(signal, int):
                    if 1 <= signal <= sub_total:
                        logger.info("%s  ↳ 跳转到子步骤 %d", label, signal)
                        j = signal - 1
                        continue
                    else:
                        logger.warning("%s无效的子步骤 goto: %d（范围 1-%d）", label, signal, sub_total)
                j += 1

    elif action == "while_match":
        max_loops = step.get("max_loops", 200)
        interval = step.get("interval", 1)
        start_sub = step.pop("_start_sub", None)     # 外部 goto 注入
        start_case = step.pop("_start_case", None)   # 外部 goto [N,C,M] 注入
        cases = step.get("cases")                    # 多 case 模式
        single = not cases

        if single:
            match_region = tuple(step["match_region"])
            sub_steps = step.get("steps", [])

        logger.info("%s循环检测（最多 %d 次）", label, max_loops)
        for n in range(1, max_loops + 1):
            if not _check_state():
                return None

            if start_case is not None and n == 1:
                # 外部注入：直接进入指定 case，跳过首轮匹配检测
                ci = start_case - 1
                active_steps = cases[ci].get("steps", [])
                logger.info("%s  ↳ 跳入 case%d", label, start_case)
                start_case = None
            elif single:
                region_img = _screenshot_region(match_region)
                ok, _ = _do_match(region_img, step)
                if not ok:
                    logger.info("%s  ✓ 第 %d 次检测已消失，跳出循环", label, n)
                    break
                active_steps = sub_steps
            else:
                # 多 case：依次检测，取第一个匹配的
                active_steps = None
                for ci, case in enumerate(cases, 1):
                    r = tuple(case["match_region"])
                    img = _screenshot_region(r)
                    ok, _ = _do_match(img, case)
                    if ok:
                        logger.info("%s  ✓ case%d 匹配（第 %d 次）", label, ci, n)
                        active_steps = case.get("steps", [])
                        break
                if active_steps is None:
                    logger.info("%s  ✓ 第 %d 次无匹配，跳出循环", label, n)
                    break

            # 执行匹配到的步骤
            sub_total = len(active_steps)
            j = start_sub - 1 if start_sub else 0
            start_sub = None
            while j < sub_total:
                if not _check_state():
                    return None
                sub = active_steps[j]
                signal = _execute_step(sub, f"{step_prefix}.{n}.{j + 1}")
                if signal == "retry":
                    continue
                elif signal == "end":
                    return signal
                elif isinstance(signal, (list, tuple)) and len(signal) == 2 and not single:
                    # goto: [case_N, sub_step] → 切换到指定 case 的子步骤
                    ci = signal[0] - 1
                    if 0 <= ci < len(cases):
                        active_steps = cases[ci].get("steps", [])
                        sub_total = len(active_steps)
                        sj = signal[1] - 1
                        if 0 <= sj < sub_total:
                            logger.info("%s  ↳ 切换到 case%d 子步骤 %d", label, signal[0], signal[1])
                            j = sj
                            continue
                elif isinstance(signal, int):
                    if 1 <= signal <= sub_total:
                        logger.info("%s  ↳ 跳转到子步骤 %d", label, signal)
                        j = signal - 1
                        continue
                    else:
                        logger.warning("%s无效的子步骤 goto: %d（范围 1-%d）", label, signal, sub_total)
                j += 1
            time.sleep(interval)
        else:
            logger.warning("%s  ✗ 循环 %d 次后仍未消失", label, max_loops)
            return _handle_fail(step, step_prefix)

        if step.get("wait_after"):
            time.sleep(step["wait_after"])

    elif action == "click_until_match":
        click_target = step.get("click_target")
        match_region = tuple(step["match_region"])
        max_clicks = step.get("max_clicks", 50)
        interval = step.get("interval", 0.5)
        check_first = step.get("check_first", False)

        if check_first:
            logger.info("%s等待消失（最多 %d 次）", label, max_clicks)
            gone = False
            for n in range(1, max_clicks + 1):
                if not _check_state():
                    return None

                region_img = _screenshot_region(match_region)
                ok, conf = _do_match(region_img, step)
                if not ok:
                    logger.info("%s  ✓ 第 %d 次检测已消失（置信度 %.3f）", label, n, conf)
                    gone = True
                    break

                if click_target:
                    click(click_target[0], click_target[1])
                time.sleep(interval)
            else:
                logger.warning("%s  ✗ 尝试 %d 次后仍未消失", label, max_clicks)
                return _handle_fail(step, step_prefix)

            if gone:
                target = _resolve_target(step)
                if target:
                    logger.info("%s消失后点击 (%d, %d)", label, target[0], target[1])
                    click(target[0], target[1])
        else:
            logger.info("%s轮询直到匹配（最多 %d 次）", label, max_clicks)
            matched = False
            for n in range(1, max_clicks + 1):
                if not _check_state():
                    return None

                if click_target:
                    click(click_target[0], click_target[1])
                time.sleep(interval)

                region_img = _screenshot_region(match_region)
                ok, conf = _do_match(region_img, step)
                if ok:
                    logger.info("%s  ✓ 第 %d 次检测匹配成功（置信度 %.3f）", label, n, conf)
                    matched = True
                    break

            if matched:
                target = _resolve_target(step)
                if target:
                    logger.info("%s匹配后点击 (%d, %d)", label, target[0], target[1])
                    click(target[0], target[1])
            else:
                logger.warning("%s  ✗ 尝试 %d 次后仍未匹配", label, max_clicks)
                return _handle_fail(step, step_prefix)

        if step.get("wait_after"):
            time.sleep(step["wait_after"])

    elif action == "stop":
        logger.info("%s流程终止", label)
        return "end"

    elif action == "diamonds":
        diamond_region = tuple(step["diamond_region"])
        name_region = tuple(step["name_region"]) if step.get("name_region") else None

        full = fullscreen_screenshot()
        name = ""
        if name_region:
            name_img = crop_region(full, name_region)
            name = extract_text(preprocess(name_img))
            logger.info("%s云机名称: %s", label, name)

        diamonds, unstable = recognize_diamond_stable(
            lambda: crop_region(fullscreen_screenshot(), diamond_region),
            account_index=0,
            device_name=name)
        if not diamonds:
            logger.warning("%s钻石识别为空", label)
        else:
            if unstable:
                logger.info("%s钻石数量: %s（不稳定）", label, diamonds)
            else:
                logger.info("%s钻石数量: %s", label, diamonds)

        global _diamond_results, _diamond_output
        index = len(_diamond_results) + 1
        entry = {"cloud_device": name or f"云机-{index}", "diamonds": int(diamonds) if diamonds.isdigit() else 0}
        if unstable:
            entry["unstable"] = True
        _diamond_results.append(entry)

        # 增量保存
        if _diamond_output is None:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            n = 1
            while True:
                _diamond_output = data_dir / f"{today}_{n}.json"
                if not _diamond_output.exists():
                    break
                n += 1

        with open(_diamond_output, "w", encoding="utf-8") as f:
            json.dump(_diamond_results, f, ensure_ascii=False, indent=2)

    else:
        logger.warning("%s未知动作类型: %s", label, action)

    return _next_signal(step)


# ---- 主流程 ----

def _run_steps(steps: list[dict], prefix: str = "") -> bool:
    """执行步骤列表，返回 False 表示被停止。

    Args:
        steps: 步骤列表。
        prefix: 日志前缀（多账户时显示轮次）。

    Returns:
        True 正常结束，False 被用户停止。
    """
    total = len(steps)
    idx = 0
    while idx < total:
        if not _check_state():
            return False
        step = steps[idx]
        step_prefix = f"{prefix}{idx + 1}" if prefix else str(idx + 1)
        signal = _execute_step(step, step_prefix)

        if signal == "retry":
            logger.info("↻ 重试步骤 %d", idx + 1)
            continue
        elif signal == "end":
            return True
        elif isinstance(signal, (list, tuple)) and len(signal) == 3:
            # goto: [外层步骤, case, 子步骤] → 跳转到 while_match 指定 case
            next_idx, ci, sub = signal[0] - 1, signal[1], signal[2]
            if 0 <= next_idx < total:
                logger.info("↳ 跳转到步骤 %d case%d 子步骤 %d", signal[0], ci, sub)
                steps[next_idx]["_start_case"] = ci
                steps[next_idx]["_start_sub"] = sub
                idx = next_idx
                continue
            else:
                logger.warning("无效的嵌套 goto: %s", signal)
        elif isinstance(signal, (list, tuple)) and len(signal) == 2:
            # goto: [外层步骤, 子步骤] → 跳转到 loop/while_match 内部的指定子步骤
            next_idx, sub = signal[0] - 1, signal[1]
            if 0 <= next_idx < total:
                logger.info("↳ 跳转到步骤 %d 子步骤 %d", signal[0], sub)
                steps[next_idx]["_start_sub"] = sub
                idx = next_idx
                continue
            else:
                logger.warning("无效的嵌套 goto: %s", signal)
        elif isinstance(signal, int):
            next_idx = signal - 1
            if 0 <= next_idx < total:
                logger.info("↳ 跳转到步骤 %d", signal)
                idx = next_idx
                continue
            else:
                logger.warning("无效的 goto: %d（步骤范围 1-%d），继续下一步", signal, total)
        idx += 1

    return True


def run_plan(plan: dict, repeat_override: int | None = None) -> None:
    """执行规划流程，支持多账户循环+自动切换。

    plan 中可定义 repeat 段:
      repeat:
        times: 73                  # 账户总数
        switch:                     # 切换账户的动作序列
          - action: click
            target: [x, y]
            wait_after: 2
          - action: wait_match
            match_region: [...]
            reference: "images/loaded.png"
    """
    hotkeys = plan.get("hotkeys", {})
    repeat_cfg = plan.get("repeat", {})
    # 支持 steps 在顶层或 repeat 内部
    steps = plan.get("steps") or repeat_cfg.get("steps")
    if not steps:
        logger.error("规划文件中缺少 'steps' 字段，请检查文件格式")
        logger.error("示例: plans/example.yaml")
        return
    repeat_times = repeat_override or repeat_cfg.get("times", 1)
    switch_steps = repeat_cfg.get("switch", [])

    logger.info("加载流程: %s（每轮 %d 步，共 %d 轮）",
                 plan.get("name", "未命名"), len(steps), repeat_times)

    # 热键监听
    listener = keyboard.Listener(on_press=lambda key: _on_press(key, hotkeys))
    listener.daemon = True
    listener.start()

    logger.info("等待按 %s 开始...", hotkeys.get("start", "F5").upper())
    while not _state.running and not _state.stopped:
        time.sleep(0.1)
    if _state.stopped:
        return

    for round_num in range(1, repeat_times + 1):
        logger.info("=" * 40)
        logger.info("第 %d/%d 轮", round_num, repeat_times)
        logger.info("=" * 40)

        if not _run_steps(steps):
            break

        # 最后一轮不切换
        if round_num < repeat_times and switch_steps:
            logger.info("--- 切换下一个账户 ---")
            if not _run_steps(switch_steps, f"切换."):
                break

    logger.info("流程执行完毕（共完成 %d 轮）", round_num)


def main():
    parser = argparse.ArgumentParser(description="视觉自动化执行引擎")
    parser.add_argument("plan", help="规划文件路径 (YAML)")
    parser.add_argument("--repeat", type=int, default=None,
                        help="覆盖计划中的 repeat.times")
    args = parser.parse_args()

    yaml = YAML(typ="safe")
    with open(args.plan, "r", encoding="utf-8") as f:
        plan = yaml.load(f)

    run_plan(plan, args.repeat)


if __name__ == "__main__":
    main()
