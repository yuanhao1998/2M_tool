"""委托任务流程 — 迁移自 plans/委托.yaml (222行 → ~95行)."""

import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation import ImageDir
from flows.common_define import LOAD_CHECK, OPERATE_ERROR_TIP_CHECK, OPERATE_ERROR_TIP_CLICK, CommonFlows


logger = logging.getLogger(__name__)

class DelegateImages(ImageDir):
    path = "images/委托"

class CommonImages(ImageDir):
    path = "images"


delegate = DelegateImages()
common = CommonImages()

TASK_ICON_CLICK = (4525, 141, 4601, 232)  # 点击任务图标
TASK_PANEL_CHECK = (1180, 410, 1289, 514)  # 判断任务面板是否打开

TASK_CHANGE_CLICK = (1113, 412, 1566, 525)  # 切换横排任务面板到第二栏
TASK_CHANGE_CLICK2 = (980, 670, 1352, 759)  # 切换小横排任务面板到第二栏
SELECT_CLICK = (175, 876, 1449, 983)  # 打开下拉框
TASK_35_CLICK = (160, 1927, 1441, 2035)  # 点击35级任务
FIRST_TASK_CLICK= (368, 1091, 933, 1245)  # 选择第一个任务

TASK_EXEC_CHECK = (4147, 2439, 4900, 2630)  # 执行任务按钮匹配
TASK_SUCCESS_CHECK = (3361, 2439, 4900, 2630)  # 领取奖励按钮匹配

TASK_EXEC_CLICK = (4227, 2458, 4848, 2604)  # 点击执行任务
TASK_EXEC_CONFIRM = (2623, 1810, 3257, 1946)  # 确认执行任务

REWARDS_CLICK = (3620, 2467, 4874, 2602)  # 点击领取奖励
REWARDS_SELECT = (2439, 1679, 2613, 1849)  # 选择奖励
REWARDS_CLOSE = (2294, 2348, 2728, 2443)  # 关闭确认奖励

TASK_CLOSE = (4779, 149, 4909, 269)  # 关闭任务面板

TP_LIST_CHECK = (1011, 627, 1300, 768)  # 判断是否打开传送列表
TP_LIST_CLICK = (963, 405, 1033, 494)  # 传送列表点击
FIRST_TP_CLICK = (262, 859, 1250, 994)  # 点击第一个传送坐标
FISRT_TP_CONFIRM_CLICK = (1152, 1065, 1232, 1143)  # 确认点击第一个传送坐标
AUTO_ATTACK_CLICK = (4021, 1408, 4166, 1519)  # 开启自动攻击

class DelegateFlow(CommonFlows):
    """73 账户循环：打开任务 → 判断完成/进行中 → 领取或传送。"""

    def run(self) -> None:
    
        self.__open_task()
        logger.info("切换到35任务面板")

        while True:
            if self.find(delegate.task_exec_button, region=TASK_EXEC_CHECK).matched:  # 有任务执行按钮，未完成
                self.__exec_task()
            elif self.find(delegate.task_success_check, region=TASK_SUCCESS_CHECK).matched:  # 有领取奖励按钮，已完成
                self.__get_rewards()
            else:  # 没有任务
                logger.info("任务执行完成")
                break

        self.__close_task()
        logger.info("关闭任务面板")
        self.wait(2)
        self.__go_AFK()
        self.wait(2)

    def __close_tip(self):
        tip_saerch = self.find_text("확인", TIP_CHECK)
        self.wait(2)
        if tip_saerch.found:
            logger.info("发现有提示弹框，关闭")
            self.click(*self.text_region(tip_saerch.center, 227, 55, 227, 55))  # 关闭提示弹框
            self.wait(2)

    def __open_task(self):  # 打开任务

        self.click(*TASK_ICON_CLICK)  # 点击任务列表
        logger.info("点击任务图标")
        self.wait(3)

        if self.wait_match(delegate.task_panel_check, region=TASK_PANEL_CHECK):
            logger.info("成功打开任务面板")
        else:
            logger.error("%s：打开任务面板失败" % self.device_name)
            return
        
        self.click(*TASK_CHANGE_CLICK)  # 切换横排面板2
        self.wait(2)
        self.click(*TASK_CHANGE_CLICK2)  # 切换横排小面板2
        self.wait(2)
        self.click(*SELECT_CLICK)  # 打开下拉框
        self.wait(2)
        self.click(*TASK_35_CLICK)  # 选择35任务
        self.wait(2)
        self.click(*FIRST_TASK_CLICK)  # 选中第一个任务
        self.wait(2)
    
    def __exec_task(self):  # 执行任务
        self.wait(2)
        self.click(*TASK_EXEC_CLICK)  # 点击执行任务
        self.wait(2)
        self.click(*TASK_EXEC_CONFIRM)  # 确认执行
        self.wait(2)

        if self.wait_match(common.loaded, region=LOAD_CHECK, timeout=30).matched:
            self.wait(2)
            logger.info("传送完成")
        
        self.__open_task()
        self.wait_match(delegate.task_success_check, region=TASK_SUCCESS_CHECK, timeout=200)
    
    def __get_rewards(self):  # 领取奖励
        self.wait(2)
        self.click(*REWARDS_CLICK)  # 点击领取奖励
        self.wait(3)
        self.click(*REWARDS_SELECT)  # 选择奖励

        logger.info("检查并关闭报错弹框")
        self.click_until_gone(common.operate_error_tip, region=OPERATE_ERROR_TIP_CHECK,
                             click_pos=OPERATE_ERROR_TIP_CLICK, max_clicks=10, interval=2)
        self.wait(3)
        self.click(*REWARDS_CLOSE)
        logger.info("关闭奖励弹框")
        self.wait(2)
        self.click(*FIRST_TASK_CLICK)  # 再次选中第一个任务
        logger.info("再次选中第一个任务")
        self.wait(2)

    def __close_task(self):  # 关闭任务面板
        self.wait(2)
        self.click(*TASK_CLOSE)

    def __go_AFK(self):

        self.close_tip()

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
            logger.info("传送完成")
        else:
            logger.error("%s 传送到挂机点加载失败，请查看并手动操作", self.device_name)


if __name__ == "__main__":
    from conf.log import add_log
    add_log(__name__ + '.log')
    DelegateFlow().main(repeat=64)
