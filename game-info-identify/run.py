"""统一启动脚本 — 交互式选择功能。"""

import subprocess
import sys
from pathlib import Path

from conf.log import add_log
add_log()


def run_diamonds():
    print("\n— 钻石识别统计 —")
    print("  1. 正式运行")
    print("  2. 测试识别")
    print("  3. 校准截图")
    choice = input("请选择 (1/2/3): ").strip()

    if choice == "1":
        argv = [sys.executable, "flows/diamond_stats.py"]
    else:
        argv = [sys.executable, "main.py"]
        if choice == "2":
            argv.append("--test")
        elif choice == "3":
            argv.append("--calibrate")

    if choice != "1":
        config = input("配置文件 (回车默认 config.yaml): ").strip()
        if config:
            argv.extend(["--config", config])

    print()
    subprocess.run(argv)


def run_flow():
    flows_dir = Path("flows")
    if flows_dir.exists():
        files = sorted(flows_dir.glob("*.py"))
        if files:
            print("\n— 可用流程 —")
            for i, f in enumerate(files, 1):
                print(f"  {i}. {f.stem}")
            print(f"  0. 手动输入路径")
            choice = input("请选择: ").strip()
            if choice == "0":
                flow = input("流程文件路径: ").strip()
            else:
                try:
                    flow = str(files[int(choice) - 1])
                except (ValueError, IndexError):
                    print("无效选择")
                    return
        else:
            flow = input("流程文件路径: ").strip()
    else:
        flow = input("流程文件路径: ").strip()

    if not flow or not Path(flow).exists():
        print(f"文件不存在: {flow}")
        return

    argv = [sys.executable, flow]

    print()
    subprocess.run(argv)


def run_screen():
    print("\n  1. 实时截图模式（按 F5 截屏）")
    print("  2. 打开已有截图")
    choice = input("请选择 (1/2): ").strip()

    if choice == "2":
        img = input("截图路径: ").strip()
        if not Path(img).exists():
            print(f"图片不存在: {img}")
            return
        subprocess.run([sys.executable, "tools/screen_tool.py", img])
    else:
        subprocess.run([sys.executable, "tools/screen_tool.py"])


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
        run_flow()
    elif choice == "3":
        run_screen()
    elif choice == "0":
        print("退出")
    else:
        print("无效选择")


if __name__ == "__main__":
    main()
