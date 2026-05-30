import logging
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parent.parent))

from automation import AutomationFlow, ImageDir

SWITCH_CLICK = (5075, 1138)
LOAD_CHECK = (3322, 2354, 3409, 2437)
NAME_REGION = (14, 14, 82, 56)
OPERATE_ERROR_TIP_CHECK = (2146, 1792, 2927, 1972)
OPERATE_ERROR_TIP_CLICK = (2209, 1816, 2838, 1944)

TIP_CHECK = (173, 792, 1343, 1536)  # 左上角提示寻找


logger = logging.getLogger(__name__)

class CommonImages(ImageDir):
    path = "images"

common = CommonImages()

class CommonFlows(AutomationFlow):

    def switch_to_next(self) -> None:
        logger.info("切换账户")
        self.click(*SWITCH_CLICK)
        self.wait(3, jitter=0)
        if self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30):
            logger.info("账户加载完成")
        else:
            logger.warning("账户加载超时")

    def close_tip(self):
        tip_saerch = self.find_text("확인", TIP_CHECK)
        self.wait(2)
        if tip_saerch.found:
            logger.info("发现有提示弹框，关闭")
            self.click(*self.text_region(tip_saerch.center, 227, 55, 227, 55))  # 关闭提示弹框
            self.wait(2)
