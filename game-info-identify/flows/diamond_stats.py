"""钻石统计流程 — 迁移自 plans/钻石统计.yaml (36行 → ~35行)."""

import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automation import AutomationFlow, ImageDir


class CommonImages(ImageDir):
    path = "images"


common = CommonImages()


class DiamondStatsFlow(AutomationFlow):
    """73 账户循环：打开任务 → 识别钻石 → 退出并保存。"""

    DIAMOND_REGION = (2291, 127, 2475, 237)
    NAME_REGION = (14, 14, 82, 56)

    def switch_to_next(self) -> None:
        self.click(5075, 1138)
        self.wait(3)
        self.wait_match(common.loaded, region=(4724, 2689, 4807, 2760), timeout=30)

    def run(self) -> None:
        self.click(4531, 190)
        self.wait(2)

        result = self.ocr_diamonds(self.DIAMOND_REGION, self.NAME_REGION)
        self._save_result(result)

        self.click(4851, 211)
        self.wait(3)

    def _save_result(self, result: dict) -> None:
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")

        i = 1
        while (data_dir / f"{today}_{i}.json").exists():
            i += 1

        if not hasattr(self, "_results"):
            self._results: list[dict] = []
        self._results.append(result)

        out = data_dir / f"{today}_{i}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self._results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    DiamondStatsFlow().main(repeat=73)
