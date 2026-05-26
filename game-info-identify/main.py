"""主入口：流程编排 + 热键控制 + 校准模式。"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from ruamel.yaml import YAML
from pynput import keyboard

from capture import fullscreen_screenshot, crop_region
from ocr_engine import recognize_diamond, recognize_diamond_stable, extract_text, preprocess
from automation import switch_to_next

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def load_config(path: str = "config.yaml") -> dict:
    yaml = YAML(typ="safe")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f)


# --- 全局状态 ---
class State:
    running = False
    paused = False
    stopped = False


state = State()
state_lock = None  # 简单场景下用单线程标志即可


def on_press(key, cfg: dict):
    """全局热键回调。"""
    hotkeys = cfg["hotkeys"]
    try:
        k = key.name if hasattr(key, "name") else key.char
    except AttributeError:
        return

    if k == hotkeys["start"]:
        if not state.running:
            state.running = True
            state.paused = False
            logger.info("▶  开始运行")
        elif state.paused:
            state.paused = False
            logger.info("▶  继续运行")
    elif k == hotkeys["pause"]:
        if state.running:
            state.paused = True
            logger.info("⏸  已暂停，按 %s 继续", hotkeys["start"])
    elif k == hotkeys["stop"]:
        state.stopped = True
        state.running = False
        logger.info("⏹  已停止")
    elif k == hotkeys["exit"]:
        logger.info("🛑 紧急退出")
        sys.exit(0)


def run_main_loop(cfg: dict) -> None:
    """主循环：截图 → 识别 → 收集 → 切换。"""
    diamond_region = tuple(cfg["capture"]["diamond_region"])
    name_region = cfg["capture"]["name_region"]
    if name_region:
        name_region = tuple(name_region)
    switch_btn = cfg["switch"]["next_button"]
    switch_wait = cfg["switch"]["wait_after_switch"]
    total = cfg["stats"]["total_accounts"]

    results: list[dict] = []

    # 启动热键监听
    listener = keyboard.Listener(
        on_press=lambda key: on_press(key, cfg)
    )
    listener.daemon = True
    listener.start()

    logger.info("热键监听已启动：F5=开始 F6=暂停 F7=停止 ESC=退出")
    logger.info("等待按 F5 开始...")

    # 等待用户按 F5 启动
    while not state.running and not state.stopped:
        time.sleep(0.1)
    if state.stopped:
        return

    index = 0
    while True:
        if state.stopped:
            logger.info("统计结束，共处理 %d 个账户", index)
            break
        if state.paused:
            time.sleep(0.2)
            continue

        # 检查是否达到预设数量
        if total > 0 and index >= total:
            logger.info("已完成预设的 %d 个账户统计", total)
            break

        logger.info("--- 处理第 %d 个账户 ---", index + 1)

        # 1. 截图
        full = fullscreen_screenshot()

        # 2. 识别云机名称
        name = ""
        if name_region:
            name_img = crop_region(full, name_region)
            name = extract_text(preprocess(name_img))
            logger.info("识别云机名称: %s", name)

        # 3. 识别钻石数量（多次采样比对，防止模糊/对比度低导致误识别）
        diamonds, unstable = recognize_diamond_stable(
            lambda: crop_region(fullscreen_screenshot(), diamond_region),
            account_index=index + 1,
            device_name=name)
        if not diamonds:
            logger.warning("钻石识别为空，跳过此账户")
        else:
            if unstable:
                logger.info("识别钻石数量: %s（不稳定，已投票决定）", diamonds)
            else:
                logger.info("识别钻石数量: %s", diamonds)

        # 4. 收集结果
        index += 1
        entry: dict = {"cloud_device": name or f"云机-{index}", "diamonds": int(diamonds) if diamonds.isdigit() else 0}
        if unstable:
            entry["unstable"] = True
        results.append(entry)

        # 5. 切换到下一个账户（如果不是最后一个）
        if total == 0 or index < total:
            switch_to_next(switch_btn[0], switch_btn[1], switch_wait)
            # 轮询等待新画面加载完成
            logger.info("等待新账户画面加载...")
            for _ in range(30):  # 最多等 30 秒
                if state.stopped:
                    break
                time.sleep(1)
                full = fullscreen_screenshot()
                diamond_img = crop_region(full, diamond_region)
                check = recognize_diamond(diamond_img)
                if check:
                    logger.info("检测到数据: %s，画面加载完成", check)
                    break
            else:
                logger.warning("等待超时，继续下一账户")

    # 保存结果到 JSON
    if results:
        _save_results(results)
    else:
        logger.info("无识别结果，跳过保存")


def _save_results(results: list[dict]) -> None:
    """将识别结果保存为 JSON 数组到 data/ 目录。

    文件名按 日期_次数 生成，同一天多次运行自动递增序号。
    """
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    n = 1
    while True:
        output_path = data_dir / f"{today}_{n}.json"
        if not output_path.exists():
            break
        n += 1

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("结果已保存到 %s（共 %d 条记录）", output_path, len(results))


def run_diamonds_simple(cfg: dict, check_stop=None) -> list[dict]:
    """直接运行钻石识别循环，无热键，给 planner 调用。

    Args:
        cfg: 配置字典。
        check_stop: 可选回调 () -> bool，返回 True 时停止。

    Returns:
        识别结果列表。
    """
    diamond_region = tuple(cfg["capture"]["diamond_region"])
    name_region = cfg["capture"]["name_region"]
    if name_region:
        name_region = tuple(name_region)
    switch_btn = cfg["switch"]["next_button"]
    switch_wait = cfg["switch"]["wait_after_switch"]
    total = cfg["stats"]["total_accounts"]

    results: list[dict] = []
    index = 0

    while True:
        if check_stop and check_stop():
            break
        if total > 0 and index >= total:
            break

        logger.info("--- 处理第 %d 个账户 ---", index + 1)
        full = fullscreen_screenshot()

        name = ""
        if name_region:
            name_img = crop_region(full, name_region)
            name = extract_text(preprocess(name_img))
            logger.info("识别云机名称: %s", name)

        diamonds, unstable = recognize_diamond_stable(
            lambda: crop_region(fullscreen_screenshot(), diamond_region),
            account_index=index + 1,
            device_name=name)
        if not diamonds:
            logger.warning("钻石识别为空，跳过此账户")
        else:
            if unstable:
                logger.info("识别钻石数量: %s（不稳定）", diamonds)
            else:
                logger.info("识别钻石数量: %s", diamonds)

        index += 1
        entry = {"cloud_device": name or f"云机-{index}", "diamonds": int(diamonds) if diamonds.isdigit() else 0}
        if unstable:
            entry["unstable"] = True
        results.append(entry)

        if total == 0 or index < total:
            switch_to_next(switch_btn[0], switch_btn[1], switch_wait)
            logger.info("等待新账户画面加载...")
            for _ in range(30):
                if check_stop and check_stop():
                    break
                time.sleep(1)
                full = fullscreen_screenshot()
                diamond_img = crop_region(full, diamond_region)
                check = recognize_diamond(diamond_img)
                if check:
                    logger.info("检测到数据: %s，画面加载完成", check)
                    break
            else:
                logger.warning("等待超时，继续下一账户")

    if results:
        _save_results(results)
    return results


def calibrate(cfg: dict) -> None:
    """校准模式：截一张图保存，供用户获取坐标。"""
    logger.info("校准模式：正在截取全屏...")
    full = fullscreen_screenshot()
    full.save("calibrate1.png")
    logger.info("截图已保存为 calibrate.png")
    logger.info("请用图片查看器打开，记录以下坐标：")
    logger.info("  1. 钻石数量区域的 (left, top, right, bottom)")
    logger.info("  2. 云机名称区域的 (left, top, right, bottom)（不需要可跳过）")
    logger.info("  3. 切换按钮的点击位置 (x, y)")
    logger.info("记录后将坐标填入 config.yaml 对应位置")


def test_ocr(cfg: dict) -> None:
    """测试模式：截屏 → 裁剪钻石区域 → OCR 识别，验证坐标是否准确。"""
    logger.info("测试模式：截屏并裁剪钻石区域进行识别...")
    full = fullscreen_screenshot()

    # 保存完整截图方便排查
    full.save("test_fullscreen.png")
    logger.info("完整截图已保存为 test_fullscreen.png")

    region = tuple(cfg["capture"]["diamond_region"])
    diamond_img = crop_region(full, region)

    # 在完整截图上画框标记裁剪区域，方便确认位置
    from PIL import ImageDraw
    marked = full.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle(region, outline="red", width=3)
    marked.save("test_marked.png")
    logger.info("标记截图已保存为 test_marked.png（红框=钻石区域）")

    diamond_img.save("test_crop_raw.png")
    logger.info("原始裁剪图已保存为 test_crop_raw.png")

    from ocr_engine import preprocess
    processed = preprocess(diamond_img)
    processed.save("test_crop_processed.png")
    logger.info("预处理后图片已保存为 test_crop_processed.png")

    result = recognize_diamond(diamond_img)
    logger.info("识别结果: '%s'", result)


def main():
    parser = argparse.ArgumentParser(description="云手机游戏钻石识别统计工具")
    parser.add_argument("--calibrate", action="store_true", help="校准模式：截一张图供坐标校准")
    parser.add_argument("--test", action="store_true", help="测试模式：截屏裁剪钻石区域进行 OCR 识别")
    parser.add_argument("--config", type=str, default="config.yaml", help="配置文件路径")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.calibrate:
        calibrate(cfg)
    elif args.test:
        test_ocr(cfg)
    else:
        run_main_loop(cfg)


if __name__ == "__main__":
    main()
