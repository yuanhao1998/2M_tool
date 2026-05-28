"""委托任务流程 — 迁移自 plans/委托.yaml (222行 → ~95行)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation import AutomationFlow, ImageDir, step


class DelegateImages(ImageDir):
    path = "images/委托"


class SuppliesImages(ImageDir):
    path = "images/supplies"


class CommonImages(ImageDir):
    path = "images"


delegate = DelegateImages()
supplies = SuppliesImages()
common = CommonImages()

MISSION_REGION = (1280, 1065, 1472, 1240)


class DelegateFlow(AutomationFlow):
    """73 账户循环：打开任务 → 判断完成/进行中 → 领取或传送。"""

    def switch_to_next(self) -> None:
        self.click(5075, 1138)
        self.wait(3)
        self.wait_match(common.loaded, region=(4724, 2689, 4807, 2760), timeout=30)

    def run(self) -> None:
        self._open_mission_ui()
        self._process_missions()

    # -- 打开任务界面 --
    def _open_mission_ui(self) -> None:
        self.click(4531, 190)        # 打开任务
        self.wait(2)
        self.click(1150, 710)        # 切换面板
        self.wait(2)
        self.click(1390, 931)        # 打开任务列表
        self.wait(2)
        self.click(296, 1988)        # 选择 35 级任务
        self.wait(2)

    # -- 处理任务循环 --
    def _process_missions(self) -> None:
        for _ in range(200):         # 最多 200 轮
            self._check_state()

            # 检查任务状态
            done = self.find(delegate.委托完成, region=MISSION_REGION)
            active = self.find(delegate.委托进行, region=MISSION_REGION)

            if done.matched:
                self._claim_and_next()
            elif active.matched:
                self.wait(2)
            else:
                self._fallback_teleport()
                return

    # -- 领取奖励并选择下一个任务 --
    def _claim_and_next(self) -> None:
        self.click(924, 1174)        # 选择自己的任务
        self.wait(2)
        self.click(4129, 2534)       # 领取按钮
        self.wait(2)
        self.click(2520, 1774)       # 选择奖励
        self.wait(2)

        # 关闭提示弹窗
        r = self.find(delegate.领取奖励提示, region=(2534, 1788, 3322, 1969))
        if r.matched:
            self.click(2917, 1884)
            self.wait(2)

        self.click(2508, 2404)       # 领取奖励
        self.wait(2)
        self.click(992, 1178)        # 选择下一个任务
        self.wait(2)

        # 再次检查：这个新任务是否也完成了？
        done2 = self.find(delegate.委托完成, region=MISSION_REGION)
        if done2.matched:
            self.click(924, 1174)
            self.wait(2)
            self._claim_and_next()   # 递归领取
            return

        active2 = self.find(delegate.委托进行, region=MISSION_REGION)
        if active2.matched:
            self._teleport_to_mission()

    # -- 传送到任务地点 --
    def _teleport_to_mission(self) -> None:
        self.click(4522, 2541)       # 传送
        self.wait(2)
        self.click(2931, 1872)       # 确认传送
        self.wait(2)
        self.wait_match(common.loaded, region=(4724, 2689, 4807, 2760), timeout=20)
        self._open_mission_ui()
        # 递归回到主循环
        self._process_missions()

    # -- 兜底：打开传送门传送到敌人附近 --
    def _fallback_teleport(self) -> None:
        self.click(4851, 211)        # 退出任务界面
        self.wait(3)
        self.click(997, 444)         # 打开传送列表
        self.wait(2)
        self.match_click(supplies.tp_check, target=(647, 920),
                         region=(1018, 632, 1296, 762))
        self.wait(2)
        self.click(1190, 1115)       # 确认传送
        self.wait(3)
        self.stop()


if __name__ == "__main__":
    DelegateFlow().main(repeat=73)
