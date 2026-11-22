"""n2f 命令行入口：检查、渲染、拼接。

用法：
    python -m film check 1 2 3        # 校验分镜表（不渲染）
    python -m film check all
    python -m film refs               # 资产总览
    python -m film render 3 all       # 渲染整章（断点续跑）
    python -m film render 3 1,8,32    # 只跑指定镜
    python -m film assets             # 列出角色缺图情况
"""
import sys

from .common import paths
from .stage2_prompts import assets, storyboard


def cmd_check(args):
    chapters = list(paths.CHAPTER_STORY.keys()) if args == ["all"] else [int(a) for a in args]
    bad = 0
    for n in chapters:
        try:
            res = storyboard.check(n)
        except FileNotFoundError as e:
            print(f"\n=== 第 {n} 章 ===\n  ❌ {e}")
            bad += 1
            continue
        if not storyboard.report(res):
            bad += 1
    print(f"\n汇总：{len(chapters)} 章，{len(chapters) - bad} 章可渲染，{bad} 章有阻断问题")
    return 1 if bad else 0


def cmd_assets(args):
    rows = assets.list_characters()
    print(f"{'角色':<10}{'基准图':<8}{'视角图'}")
    for r in rows:
        print(f"{r['name']:<10}{'有' if r['base'] else '无':<8}{r['views']}")
    no_base = [r["name"] for r in rows if not r["base"]]
    print("\n缺基准图:", ", ".join(no_base) if no_base else "无")
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "check":
        return cmd_check(rest or ["all"])
    if cmd == "assets" or cmd == "refs":
        return cmd_assets(rest)
    if cmd == "render":
        from .stage3_video import render
        return render.main(rest)
    print(f"未知命令: {cmd}")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

