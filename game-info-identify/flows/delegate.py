"""委托任务流程 — 迁移自 plans/委托.yaml (222行 → ~95行)."""

import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation import ImageDir
from flows.common_define import LOAD_CHECK, OPERATE_ERROR_TIP_CHECK, OPERATE_ERROR_TIP_CLICK, CommonFlows
from conf.log import add_log
add_log(__name__ + '.log')
logger = logging.getLogger(__name__)

class DelegateImages(ImageDir):
    path = "images/委托"

class CommonImages(ImageDir):
    path = "images"


delegate = DelegateImages()
common = CommonImages()

TASK_ICON_CLICK = (4520, 165, 4568, 204)  # 点击任务图标
TASK_PANEL_CHECK = (1180, 410, 1289, 514)  # 判断任务面板是否打开

TASK_CHANGE_CLICK = (1204, 435, 1475, 502)  # 切换横排任务面板到第二栏
TASK_CHANGE_CLICK2 = (1054, 688, 1278, 741)  # 切换小横排任务面板到第二栏
SELECT_CLICK = (430, 897, 1194, 962)  # 打开下拉框
TASK_35_CLICK = (416, 1949, 1185, 2013)  # 点击35级任务
FIRST_TASK_CLICK = (481, 1122, 820, 1214)  # 选择第一个任务

TASK_EXEC_CHECK = (4147, 2439, 4900, 2630)  # 执行任务按钮匹配
TASK_SUCCESS_CHECK = (3361, 2439, 4900, 2630)  # 领取奖励按钮匹配

TASK_EXEC_CLICK = (4351, 2487, 4724, 2575)  # 点击执行任务
TASK_EXEC_CONFIRM = (2750, 1837, 3130, 1919)  # 确认执行任务

REWARDS_CLICK = (3871, 2494, 4623, 2575)  # 点击领取奖励
REWARDS_SELECT = (2474, 1713, 2578, 1815)  # 选择奖励
REWARDS_TIP_CHECK = (2543, 1794, 3316, 1966)  # 判断奖励弹框
REWARDS_TIP_CLOSE_CLICK = (2787, 1855, 3102, 1905)  # 关闭奖励弹框
REWARDS_CLOSE = (2381, 2367, 2641, 2424)  # 关闭确认奖励

TASK_CLOSE = (4805, 173, 4883, 245)  # 关闭任务面板

TP_LIST_CHECK = (1011, 627, 1300, 768)  # 判断是否打开传送列表
TP_LIST_CLICK = (977, 423, 1019, 476)  # 传送列表点击
FIRST_TP_CLICK = (460, 886, 1052, 967)  # 点击第一个传送坐标
FISRT_TP_CONFIRM_CLICK = (1168, 1081, 1216, 1127)  # 确认点击第一个传送坐标
AUTO_ATTACK_CLICK = (4050, 1430, 4137, 1497)  # 开启自动攻击

class DelegateFlow(CommonFlows):
    """73 账户循环：打开任务 → 判断完成/进行中 → 领取或传送。"""

    def run(self) -> None:
        
        try:
            self.__open_task()
        except ValueError:
            self.__go_AFK()
            return
        logger.info("切换到35任务面板")
        
        while True:
            if self.find(delegate.task_exec_button, region=TASK_EXEC_CHECK).matched:  # 有任务执行按钮，未完成
                try:
                    self.__exec_task()
                except ValueError:
                    self.__go_AFK()
                    return
                
            elif self.find(delegate.task_success_check, region=TASK_SUCCESS_CHECK).matched:  # 有领取奖励按钮，已完成
                self.__get_rewards()
            else:  # 没有任务
                logger.info("任务执行完成")
                break

        self.__close_task()
        logger.info("关闭任务面板")
        self.wait(5)
        self.__go_AFK()
        self.wait(5)

    def __close_tip(self):
        tip_saerch = self.find_text("확인", TIP_CHECK)
        self.wait(5)
        if tip_saerch.found:
            logger.info("发现有提示弹框，关闭")
            self.click(*self.text_region(tip_saerch.center, 227, 55, 227, 55))  # 关闭提示弹框
            self.wait(5)

    def __open_task(self):  # 打开任务

        self.click(*TASK_ICON_CLICK)  # 点击任务列表
        logger.info("点击任务图标")
        self.wait(5)

        for i in range(3):
            if self.wait_match(delegate.task_panel_check, region=TASK_PANEL_CHECK, timeout=8).matched:
                logger.info("成功打开任务面板")
                break
            self.click(*TASK_ICON_CLICK)  # 点击任务列表
            logger.info("点击任务图标，次数：%s" % i)
        else:
            logger.error("%s：打开任务面板失败" % self.device_name)
            raise ValueError
        
        self.click(*TASK_CHANGE_CLICK)  # 切换横排面板2
        self.wait(5)
        self.click(*TASK_CHANGE_CLICK2)  # 切换横排小面板2
        self.wait(5)
        self.click(*SELECT_CLICK)  # 打开下拉框
        self.wait(5)
        self.click(*TASK_35_CLICK)  # 选择35任务
        self.wait(5)
        self.click(*FIRST_TASK_CLICK)  # 选中第一个任务
        self.wait(5)
        logger.info("选择到委托任务")
    
    def __exec_task(self):  # 执行任务
        self.wait(5)
        self.click(*TASK_EXEC_CLICK)  # 点击执行任务
        self.wait(5)
        self.click(*TASK_EXEC_CONFIRM)  # 确认执行
        self.wait(5)

        if self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30).matched:
            self.wait(5)
            logger.info("传送完成")
        
        self.__open_task()

        for _ in range(10):
            if self.wait_match(delegate.task_success_check, region=TASK_SUCCESS_CHECK, timeout=30).matched:
                break
            self.click(*FIRST_TASK_CLICK)
            self.wait(5)
            self.click(*TASK_EXEC_CLICK)  # 点击执行任务
            self.wait(5)
            self.click(*TASK_EXEC_CONFIRM)  # 确认执行
            self.wait(5)
            if self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30).matched:
                logger.info("传送完成")
                self.wait(10)
                self.random_tp()
            self.__open_task()
    
    def __get_rewards(self):  # 领取奖励
        self.wait(5)
        self.click(*REWARDS_CLICK)  # 点击领取奖励
        self.wait(5)
        self.click(*REWARDS_SELECT)  # 选择奖励

        self.wait(5)
        if self.find(delegate.rewards_tip_check, region=REWARDS_TIP_CHECK).matched:
            self.click(*REWARDS_TIP_CLOSE_CLICK)
            self.wait(5)

        logger.info("检查并关闭报错弹框")
        self.click_until_gone(common.operate_error_tip, region=OPERATE_ERROR_TIP_CHECK,
                             click_pos=OPERATE_ERROR_TIP_CLICK, max_clicks=10, interval=2)
        self.wait(5)
        self.click(*REWARDS_CLOSE)
        logger.info("关闭奖励弹框")
        self.wait(5)
        self.click(*FIRST_TASK_CLICK)  # 再次选中第一个任务
        logger.info("再次选中第一个任务")
        self.wait(5)

    def __close_task(self):  # 关闭任务面板
        self.wait(5)
        self.click(*TASK_CLOSE)

    def __go_AFK(self):

        self.close_tip()

        if not self.find(common.tp_list_check, region=TP_LIST_CHECK).matched:
            logger.info("打开传送列表")
            self.click(*TP_LIST_CLICK)
            self.wait(5)

        logger.info("选择第一个传送点")
        self.click(*FIRST_TP_CLICK)
        self.wait(5)
        logger.info("确认传送")
        self.click(*FISRT_TP_CONFIRM_CLICK)
        self.wait(5)
        if self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30).matched:
            self.wait(5)
            logger.info("传送完成")
        else:
            logger.error("%s 传送到挂机点加载失败，请查看并手动操作", self.device_name)


if __name__ == "__main__":
    DelegateFlow().main(repeat=64)
