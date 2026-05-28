"""补给购买流程 — 迁移自 plans/补给.yaml (150行 → ~65行)."""

import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation import AutomationFlow, ImageDir
from flows.common_define import SWITCH_CLICK, LOAD_CHECK, OPERATE_ERROR_TIP_CHECK, OPERATE_ERROR_TIP_CLICK

logger = logging.getLogger(__name__)


class SuppliesImages(ImageDir):
    path = "images/supplies"


class CommonImages(ImageDir):
    path = "images"


supplies = SuppliesImages()
common = CommonImages()

TIP_CHECK = (531, 1113, 972, 1226)  # 左上角提示寻找

RETURN_CLICK = (1091, 2448, 1191, 2552)  # 回程卷轴点击
SMALL_MAP_CHECK = (141, 783, 195, 835)  # 判断小地图，如果有小地图，代表需要打开NPC列表
STORE_ICON_REGION = (197, 766, 264, 829)  # 左边匹配商店
NPC_LIST_CLICK = (967, 679, 1037, 755)  # 点击打开npc列表

# 下拉npc列表
NPC_LIST_START = (295, 483, 822, 800)
NPC_LIST_END = (327, 1569, 909, 1920)

STORE_CLICK = (190, 748, 826, 855)  # 点击走向商人
STORE_OPEN_CHECK = (483, 2448, 1356, 2619)  # 判断商店是否打开
RANDOM_CLICK = (3031, 1586, 3646, 1974)  # 随机点击一下地板

STORE_ADD_CLICK = (3730, 2465, 4216, 2604)  # 添加购物车
STORE_BUY_CLICK = (4388, 2454, 4850, 2602)  # 购买商品
STORE_BUY_CONFIRM = (2656, 1818, 3253, 1940)  # 确认购买
STORE_CLOSE_CLICK = (4794, 162, 4920, 275)  # 关闭商店点击

TP_LIST_CHECK = (1011, 627, 1300, 768)  # 判断是否打开传送列表
TP_LIST_CLICK = (963, 405, 1033, 494)  # 传送列表点击
FIRST_TP_CLICK = (262, 859, 1250, 994)  # 点击第一个传送坐标
FISRT_TP_CONFIRM_CLICK = (1152, 1065, 1232, 1143)  # 确认点击第一个传送坐标
AUTO_ATTACK_CLICK = (4021, 1408, 4166, 1519)  # 开启自动攻击


class SupplyFlow(AutomationFlow):
    """73 账户循环：回城 → 补给购买 → 传送回刷怪点 → 自动攻击。"""

    def switch_to_next(self) -> None:
        logger.info("切换账户")
        self.click(*SWITCH_CLICK)
        self.wait(3, jitter=0)
        if self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30):
            logger.info("账户加载完成")
        else:
            logger.warning("账户加载超时")

    def run(self) -> None:
        logger.info("=== 账户 %d [%s] 开始 ===", self._current_account, self.device_name)
        
        tip_saerch = self.find_text("확인", TIP_CHECK)
        self.wait(2)
        if tip_saerch.found:
            logger.info("发现有提示弹框，关闭")
            self.click(*self.text_region(tip_saerch.center, 227, 55, 227, 55))  # 关闭提示弹框
            self.wait(2)

        logger.info("点击回城")
        self.click(*RETURN_CLICK)
        self.wait(3)
        if self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30).matched:
            logger.info("回城加载完成")
        else:
            logger.warning("回城加载超时")
        self.wait(3)


        if self.find(common.small_map_check, SMALL_MAP_CHECK).matched:  # 能看到小地图，代表没有打开npc列表
            self.click(*NPC_LIST_CLICK)
            logger.info("打开 NPC 列表")
            self.wait(2)

        # logger.info("下拉 NPC 列表")
        # self.drag(*NPC_LIST_START, *NPC_LIST_END, duration=0.6)
        # self.wait(4)

        if not self.find(supplies.store_icon, region=STORE_ICON_REGION).matched:
            # logger.info("未找到商店图标，再次下拉")
            # self.drag(*NPC_LIST_START, *NPC_LIST_END)
            # self.wait(2)
            # if not self.find(supplies.store_icon, region=STORE_ICON_REGION).matched:
            #     logger.warning("仍未找到商店图标，跳过此账户")
            return
        else:
            logger.info("找到商店图标，走向商人")
            self.click(*STORE_CLICK)

        if not self.__open_store():
            logger.error("%s 无法打开商店，去挂机", self.device_name)
            self.__go_AFK()
            return

        logger.info("开始购买补给")
        self.__buy_store()

        logger.info("检查并关闭报错弹框")
        self.click_until_gone(common.operate_error_tip, region=OPERATE_ERROR_TIP_CHECK,
                             click_pos=OPERATE_ERROR_TIP_CLICK, max_clicks=10, interval=2)

        logger.info("关闭商店")
        self.click(*STORE_CLOSE_CLICK)
        self.wait(2)
        logger.info("传送回挂机点")
        self.__go_AFK()

        logger.info("=== 账户 %d [%s] 完成 ===", self._current_account, self.device_name)

    def __open_store(self) -> bool:
        for i in range(5):
            if not self.wait_match(supplies.store_open_check, region=STORE_OPEN_CHECK,
                                   timeout=20).matched:
                logger.debug("商店未打开 (第%d次)，随机走位后重试", i + 1)
                self.click(*RANDOM_CLICK)
                self.wait(1)
                self.click(*STORE_CLICK)
            else:
                logger.info("商店已打开")
                self.wait(1)
                return True
        logger.warning("5 次尝试后仍未打开商店")
        return False

    def __buy_store(self):
        logger.info("添加购物车")
        self.click(*STORE_ADD_CLICK)
        self.wait(1)
        logger.info("点击购买")
        self.click(*STORE_BUY_CLICK)
        self.wait(1)
        logger.info("确认购买")
        self.click(*STORE_BUY_CONFIRM)
        self.wait(3)

    def __go_AFK(self):
        if not self.find(common.tp_list_check, region=TP_LIST_CHECK).matched:
            logger.info("打开传送列表")
            self.click(*TP_LIST_CLICK)
            self.wait(1)

        logger.info("选择第一个传送点")
        self.click(*FIRST_TP_CLICK)
        self.wait(1)
        logger.info("确认传送")
        self.click(*FISRT_TP_CONFIRM_CLICK)
        self.wait(3)
        if self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30).matched:
            self.wait(1)
            logger.info("传送完成，开启自动攻击")
            self.click(*AUTO_ATTACK_CLICK)
            self.wait(1)
        else:
            logger.error("%s 传送到挂机点加载失败，请查看并手动操作", self.device_name)
        
        


if __name__ == "__main__":
    from conf.log import add_log
    add_log()
    SupplyFlow().main(repeat=64)
