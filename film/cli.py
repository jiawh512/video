"""film 命令行入口：检查、渲染、拼接。

用法：
    python -m film check 1 2 3        # 校验分镜表（不渲染）
    python -m film check all
    python -m film refs               # 资产总览
    python -m film durations all      # 时长口径对账（只报告）
    python -m film durations all --write   # 按字数重算并写回分镜表
    python -m film render 3 all       # 渲染整章（断点续跑）
    python -m film render 3 1,8,32    # 只跑指定镜
    python -m film assets             # 列出角色缺图情况
"""
import os
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


def cmd_durations(args):
    """时长口径对账：duration_sec = 旁白字数 / 4.8。

    只跑章节线（<100）。剧集线（100+）的节奏由 stage1_script/script2story.py
    按参考片生成（字数/4.8 + 0.5，下限 3 秒），这里不改写。
    """
    write = "--write" in args
    rest = [a for a in args if a != "--write"]
    if not rest or rest == ["all"]:
        chapters = sorted(n for n in paths.CHAPTER_STORY
                          if n < 100 and os.path.exists(paths.CHAPTER_STORY[n]))
    else:
        chapters = [int(a) for a in rest if a.isdigit()]
    total = bad = 0
    for n in chapters:
        try:
            path, todo, skipped, wrote = storyboard.fix_durations(n, write=write)
        except FileNotFoundError as e:
            print(f"  {e}")
            continue
        total += len(todo)
        bad += len(skipped)
        flag = "（已写回）" if wrote and todo else ""
        print(f"\n第 {n} 章: {len(todo)} 镜需改{flag}；{len(skipped)} 镜超出 8–12s 窗口")
        for idx, old, want, chars in todo[:6]:
            print(f"   S{idx}: {old}s -> {want}s（{chars} 字）")
        if len(todo) > 6:
            print(f"   … 还有 {len(todo) - 6} 镜")
        for idx, want, chars in skipped[:4]:
            print(f"   ⚠️ S{idx}: {chars} 字 → {want}s，旁白需再切分（不改字段）")
    print(f"\n合计 {total} 镜可写回，{bad} 镜超界；{'已写回（原文件存 .bak）' if write else '未写回，加 --write 才改'}")
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
    if cmd == "durations":
        return cmd_durations(rest)
    if cmd == "render":
        from .stage3_video import render
        return render.main(rest)
    print(f"未知命令: {cmd}")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

