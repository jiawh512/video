"""分镜表读取与校验。

校验项（每一项都对应一次真实踩坑）：
  1. narration 逐字拼接 == 原文
  2. location_id 存在且定场图文件在
  3. 角色能解析到参考图
  4. 旁白字数与声明时长是否匹配
  5. prompt 有真人质感锚 / 年龄锚 / 单人镜隔离词
"""
import json
import os
import re
import shutil

from . import assets
from ..common import paths

REQUIRED_FIELDS = ["idx", "narration", "location", "characters", "layer", "visual_prompt"]


def load(chapter: int):
    p = paths.CHAPTER_STORY.get(chapter)
    if not p or not os.path.exists(p):
        raise FileNotFoundError(f"第 {chapter} 章分镜表不存在: {p}")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data, p


def hanzi(s: str) -> int:
    return len(re.sub(r"[^\u4e00-\u9fa5]", "", s or ""))


# ---------- 时长口径（唯一一条） ----------
# 一句话念多久，由字数决定：1.3 倍语速下 CHARS_PER_SEC = 4.8 字/秒。
# 分镜表里的 duration_sec 是这条规则的产物，不是手写的常量；
# 渲染时以实测音频为准，并夹在 SHOT_MIN_SEC–SHOT_MAX_SEC 之间。
DUR_TOL_SEC = 1.0
DUR_TOL_RATIO = 0.20


def expected_duration(chars: int) -> float:
    if not chars:
        return 0.0
    return round(chars / paths.CHARS_PER_SEC, 1)


def duration_ok(declared: float, expected: float) -> bool:
    if not expected:
        return True
    return abs(declared - expected) <= max(DUR_TOL_SEC, expected * DUR_TOL_RATIO)


def fix_durations(chapter: int, write: bool = False):
    """按旁白字数重算 duration_sec。默认只报告，write=True 才写回分镜表。

    落在 SHOT_MIN_SEC–SHOT_MAX_SEC 之外的**不改**：那是旁白需要再切分，
    不是改时长字段能修的；硬写只会让数据说谎。
    """
    data, path = load(chapter)
    todo, skipped = [], []
    for s in data.get("shots", []):
        chars = hanzi(s.get("narration", ""))
        if not chars:
            continue
        want = expected_duration(chars)
        idx = s.get("idx")
        if want < paths.SHOT_MIN_SEC or want > paths.SHOT_MAX_SEC:
            skipped.append((idx, want, chars))
            continue
        old = s.get("duration_sec")
        try:
            old_f = float(old)
        except (TypeError, ValueError):
            old_f = -1.0
        if old_f < 0 or abs(old_f - want) > 0.05:
            todo.append((idx, old, want, chars))
            s["duration_sec"] = want
    if write and todo:
        shutil.copy2(path, path + ".bak")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return path, todo, skipped, write


def check(chapter: int, verbose=False):
    data, story_path = load(chapter)
    shots = data.get("shots", [])
    errors, warnings = [], []

    total_frames = 0
    layers = {"outer": 0, "inner": 0}
    missing_ref = {}
    missing_plate = []
    inner_no_plate = []
    dur_mismatch = []

    for s in shots:
        idx = s.get("idx")
        for f in REQUIRED_FIELDS:
            if f not in s:
                errors.append(f"S{idx}: 缺字段 {f}")

        layer = s.get("layer")
        if layer in layers:
            layers[layer] += 1

        lid = s.get("location_id")
        plate, plate_key = assets.plate_for(s.get("location", ""), lid or "")
        if not plate:
            if layer == "outer":
                missing_plate.append(f"S{idx}({lid or s.get('location', '')})")
            else:
                inner_no_plate.append(f"S{idx}")

        for name in (s.get("characters") or []):
            if not assets.needs_ref(name):
                continue
            ref, reason = assets.pick_ref(name, s.get("shot_size", ""), s.get("camera_move", ""))
            if not ref:
                missing_ref.setdefault(name, []).append(idx)

        chars = hanzi(s.get("narration", ""))
        declared = float(s.get("duration_sec") or 0)
        expect = expected_duration(chars)
        if chars and declared and not duration_ok(declared, expect):
            dur_mismatch.append((idx, declared, expect))

        vp = s.get("visual_prompt") or ""
        if ("no anime" not in vp) and ("photorealistic live-action film still" not in vp):
            warnings.append(f"S{idx}: prompt 缺真人质感锚")
        if chars and "no children" not in vp and any(k in (s.get("characters") or []) for k in ("学生", "同学")):
            warnings.append(f"S{idx}: 学生镜缺年龄锚")
        if len(s.get("characters") or []) == 1 and "alone in the frame" not in vp and not assets.is_group(s["characters"][0]):
            warnings.append(f"S{idx}: 单人镜缺 alone in the frame")

        total_frames += declared if declared else 0

    if missing_plate:
        errors.append(f"定场图缺失 {len(missing_plate)} 镜: " + ", ".join(missing_plate[:8]) + ("…" if len(missing_plate) > 8 else ""))
    for name, idxs in missing_ref.items():
        errors.append(f"角色「{name}」缺参考图，影响 {len(idxs)} 镜: {idxs[:6]}{'…' if len(idxs) > 6 else ''}")
    if inner_no_plate:
        warnings.append(f"内层镜没有定场图（可接受）{len(inner_no_plate)} 镜")
    if dur_mismatch:
        warnings.append(
            f"时长与旁白字数不一致 {len(dur_mismatch)} 镜（前 5: 镜号, 声明秒, 应为秒）: "
            + str(dur_mismatch[:5])
            + "；能靠字数修的直接跑 `python -m film durations all --write`，超 8–12s 的要切分旁白"
        )

    stats = {
        "shots": len(shots),
        "frames": round(total_frames, 1),
        "outer": layers["outer"],
        "inner": layers["inner"],
        "inner_pct": round(100.0 * layers["inner"] / max(1, len(shots)), 1),
        "avg_dur": round(sum(float(s.get("duration_sec") or 0) for s in shots) / max(1, len(shots)), 2),
        "story": story_path,
    }
    return {"chapter": chapter, "stats": stats, "errors": errors, "warnings": warnings}


def report(res, show_warnings=True):
    st = res["stats"]
    print(f"\n=== 第 {res['chapter']} 章 ===")
    print(f"  镜数 {st['shots']}  时长 {st['frames']}s  平均 {st['avg_dur']}s/镜  内层 {st['inner_pct']}%")
    if res["errors"]:
        print(f"  ❌ 错误 {len(res['errors'])} 条")
        for e in res["errors"]:
            print("     ·", e)
    else:
        print("  ✅ 无阻断性错误")
    if show_warnings and res["warnings"]:
        print(f"  ⚠️ 告警 {len(res['warnings'])} 条")
        for w in res["warnings"][:6]:
            print("     ·", w)
        if len(res["warnings"]) > 6:
            print(f"     … 还有 {len(res['warnings']) - 6} 条")
    return not res["errors"]