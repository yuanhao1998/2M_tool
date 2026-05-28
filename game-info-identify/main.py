"""主入口：校准模式 + 测试模式。钻石统计主循环已迁移到 flows/diamond_stats.py。"""

import argparse
import logging
import sys

from ruamel.yaml import YAML

from core.capture import fullscreen_screenshot, crop_region
from conf.log import add_log
from core.ocr_engine import recognize_diamond, preprocess

add_log()
logger = logging.getLogger(__name__)


def load_config(path: str = "conf/config.yaml") -> dict:
    yaml = YAML(typ="safe")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f)


def calibrate(cfg: dict) -> None:
    """校准模式：截一张图保存，供用户获取坐标。"""
    logger.info("校准模式：正在截取全屏...")
    full = fullscreen_screenshot()
    full.save("calibrate.png")
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
    full.save("test_fullscreen.png")
    logger.info("完整截图已保存为 test_fullscreen.png")

    region = tuple(cfg["capture"]["diamond_region"])
    diamond_img = crop_region(full, region)

    from PIL import ImageDraw
    marked = full.copy()
    draw = ImageDraw.Draw(marked)
    draw.rectangle(region, outline="red", width=3)
    marked.save("test_marked.png")
    logger.info("标记截图已保存为 test_marked.png（红框=钻石区域）")

    diamond_img.save("test_crop_raw.png")
    logger.info("原始裁剪图已保存为 test_crop_raw.png")

    processed = preprocess(diamond_img)
    processed.save("test_crop_processed.png")
    logger.info("预处理后图片已保存为 test_crop_processed.png")

    result = recognize_diamond(diamond_img)
    logger.info("识别结果: '%s'", result)


def main():
    parser = argparse.ArgumentParser(description="云手机游戏钻石识别校准/测试工具")
    parser.add_argument("--calibrate", action="store_true", help="校准模式：截一张图供坐标校准")
    parser.add_argument("--test", action="store_true", help="测试模式：截屏裁剪钻石区域进行 OCR 识别")
    parser.add_argument("--config", type=str, default="conf/config.yaml", help="配置文件路径")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.calibrate:
        calibrate(cfg)
    elif args.test:
        test_ocr(cfg)
    else:
        logger.info("请选择模式：--calibrate（校准）或 --test（测试）")
        logger.info("钻石统计主循环请运行: python flows/diamond_stats.py")


if __name__ == "__main__":
    main()
