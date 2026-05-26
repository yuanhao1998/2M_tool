"""统一启动脚本 — 交互式选择功能。"""

import subprocess
import sys
from pathlib import Path


def run_diamonds():
    print("\n— 钻石识别统计 —")
    print("  1. 正式运行")
    print("  2. 测试识别")
    print("  3. 校准截图")
    choice = input("请选择 (1/2/3): ").strip()

    argv = [sys.executable, "main.py"]
    if choice == "2":
        argv.append("--test")
    elif choice == "3":
        argv.append("--calibrate")

    config = input("配置文件 (回车默认 config.yaml): ").strip()
    if config:
        argv.extend(["--config", config])

    print()
    subprocess.run(argv)


def run_plan():
    plans_dir = Path("plans")
    if plans_dir.exists():
        files = sorted(plans_dir.glob("*.yaml"))
        if files:
            print("\n— 可用流程 —")
            for i, f in enumerate(files, 1):
                print(f"  {i}. {f.name}")
            print(f"  0. 手动输入路径")
            choice = input("请选择: ").strip()
            if choice == "0":
                plan = input("规划文件路径: ").strip()
            else:
                try:
                    plan = str(files[int(choice) - 1])
                except (ValueError, IndexError):
                    print("无效选择")
                    return
        else:
            plan = input("规划文件路径: ").strip()
    else:
        plan = input("规划文件路径: ").strip()

    if not plan or not Path(plan).exists():
        print(f"文件不存在: {plan}")
        return

    repeat = input("覆盖轮数 (回车使用文件中配置): ").strip()
    argv = [sys.executable, "planner.py", plan]
    if repeat.isdigit():
        argv.extend(["--repeat", repeat])

    print()
    subprocess.run(argv)


def run_screen():
    img = input("截图路径 (回车 screen.png): ").strip() or "screen.png"
    if not Path(img).exists():
        print(f"图片不存在: {img}")
        print("请先截图: python -c \"from PIL import ImageGrab; ImageGrab.grab().save('screen.png')\"")
        return
    subprocess.run([sys.executable, "screen_tool.py", img])


def main():
    print("=" * 40)
    print("  云手机自动化工具集")
    print("=" * 40)
    print("  1. 钻石识别统计")
    print("  2. 视觉自动化流程")
    print("  3. 坐标辅助工具")
    print("  0. 退出")
    print("-" * 40)

    choice = input("请选择: ").strip()

    if choice == "1":
        run_diamonds()
    elif choice == "2":
        run_plan()
    elif choice == "3":
        run_screen()
    elif choice == "0":
        print("退出")
    else:
        print("无效选择")


if __name__ == "__main__":
    main()
