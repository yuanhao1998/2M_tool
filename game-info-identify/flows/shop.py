"""商城购买流程 — 迁移自 plans/商城购买.yaml (227行 → ~75行)."""

import sys
from pathlib import Path
import logging
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation import AutomationFlow, ImageDir, step
from flows.common_define import SWITCH_CLICK, LOAD_CHECK

logger = logging.getLogger(__name__)


class StoreImages(ImageDir):
    path = "images/store"


class CommonImages(ImageDir):
    path = "images"


store = StoreImages()
common = CommonImages()

STORE_ICON = (3752, 123, 3865, 260)  # 从主界面进入商店的图标点击位置
AD_REGION = (4729, 2515, 4971, 2720)  # 右下角广告匹配 X
CLOSE_AD_CLICK = (4792, 2558, 4913, 2669)  # 点击关闭广告
LIST_REGION = (2442, 428, 2691, 508)  # 匹配是否出现商品页签
LIST_CLICK = (2341, 423, 2845, 510)  # 点击商品页签
LIST_LOCATION_DICT = {  # 每个购买列表所在的位置
    1: (4260, 716, 4724, 842),
    2: (4253, 967, 4694, 1082),
    4: (4260, 1447, 4696, 1579)
}
BUY_CLICK = (4308, 2587, 4846, 2680)  # 点击购买按钮
BUY_CONFIRM = (2573, 2291, 3281, 2435)  # 购买确认
CLOSE_BUY = (1781, 2287, 2445, 2435)  # 关闭购买弹框
BUY_CHECK_REGION = (2654, 2143, 2790, 2211)  # 判断0金币截图
BUY_FINISH_CHECK = (3439, 2207, 3567, 2274)  # 判断购买是否完成（点击购买确认按钮是否能出现弹框）
CLOSE_STORE = (4774, 151, 4922, 292)  # 关闭商店


class ShopFlow(AutomationFlow):
    """ 账户循环：进入商店 → 关闭广告 → 购买槽位 1/2/4 → 退出。"""

    def switch_to_next(self) -> None:
        logger.info("切换账户 → 点击切换 %s", SWITCH_CLICK)
        self.click(*SWITCH_CLICK)
        self.wait(3, jitter=0)
        r = self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30)
        if r.matched:
            logger.info("账户加载完成")
        else:
            logger.warning("账户加载超时")

    def run(self) -> None:
        logger.info("=== 账户 %d 开始 ===", self._current_account)

        self.click(*STORE_ICON)
        logger.info("进入商店 %s", STORE_ICON)
        self.wait(5)

        self._close_ad()
        if not self.click_until_gone(store.store_guanggao, click_pos=AD_REGION, region=AD_REGION, max_clicks=20, interval=2):
            return  # 无法关闭广告则跳过

        self.match_click(store.store_list, target=LIST_CLICK, region=LIST_REGION)
        logger.info("已打开商品页签")
        self.wait(2)

        for k, location in LIST_LOCATION_DICT.items():
            logger.info("--- 购买槽位 %d/%d ---", k, len(LIST_LOCATION_DICT))
            self.click(*location)
            self.wait(1)
            self._do_buy()

            if self._check_already_bought():
                logger.info("槽位 %d 已购买过，关闭弹框", k)
                self.click(*CLOSE_BUY)
                self.wait(1)
            else:
                logger.info("槽位 %d 开始购买", k)
                self.click(*BUY_CONFIRM)

                # 一直点击购买按钮，直到出现购买弹框，代表已经购买完成
                if self.click_until_match(store.buy_finish_check, region=BUY_FINISH_CHECK, click_pos=BUY_CLICK, max_clicks=30, interval=2):
                    self.wait(1)
                    self.click(*CLOSE_BUY)
                    logger.info("槽位 %d 购买完成", k)
                    self.wait(1)
                else:
                    logger.error("槽位 %d 购买超时，跳过", k)
                    return

        self.click(*CLOSE_STORE)
        logger.info("关闭商店 %s", CLOSE_STORE)
        self.wait(3)
        logger.info("=== 账户 %d 完成 ===", self._current_account)

    @step(match=store.store_guanggao, region=AD_REGION, optional=True)
    def _close_ad(self) -> None:
        logger.info("检测到广告，关闭 %s", CLOSE_AD_CLICK)
        self.click(*CLOSE_AD_CLICK)
        self.wait(2)

    def _do_buy(self) -> None:
        logger.debug("点击购买 %s", BUY_CLICK)
        self.click(*BUY_CLICK)
        self.wait(1)

    def _check_already_bought(self) -> bool:
        r = self.find(store.store_buy_check, region=BUY_CHECK_REGION)
        self.wait(1)
        return r.matched


if __name__ == "__main__":
    from conf.log import add_log
    add_log()
    ShopFlow().main(repeat=72)
