"""Python DSL 视觉自动化引擎。

用法:
    from automation import AutomationFlow, step, ImageDir

    class MyImages(ImageDir):
        path = "images/my_flow"

    class MyFlow(AutomationFlow):
        img = MyImages()

        @step(match=img.target)
        def do_action(self):
            self.click(100, 200)

        def run(self):
            self.do_action()

    MyFlow().main(repeat=10)
"""

from automation.flow import AutomationFlow, MatchResult, TextResult
from automation.images import ImageDir, ImageRef
from automation.step import StopFlow, step

__all__ = [
    "AutomationFlow",
    "ImageDir",
    "ImageRef",
    "MatchResult",
    "TextResult",
    "StopFlow",
    "step",
]
