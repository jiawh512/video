"""机械质检：抽帧看亮度，标记疑似黑屏的镜头。

用法：python -m film.stage4_finish.qc 101
返回：不合格镜号列表（黑屏比例 > 60%）
"""
import json
import os
import re
import subprocess
import sys

from ..common import paths

DARK_FAIL = 0.60


def frame_brightness(path, ts):
    """取一帧的灰度均值（0-255），用 ffmpeg signalstats 近似。"""
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-ss", str(ts), "-i", path, "-frames:v", "1",
             "-vf", "signalstats,metadata=print", "-f", "null", "-"],
            capture_output=True, text=True, timeout=60,
        ).stderr
        m = re.search(r"YAVG=([\d.]+)", out)
        return float(m.group(1)) if m else None
    except Exception:
        return None


def check_shot(path, probe_times=(0.5, None)):
    if not os.path.exists(path):
        return {"ok": False, "problems": ["缺文件"]}
    times = [probe_times[0]]
    try:
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30).stdout.strip())
        times = [max(0.2, dur * f) for f in (0.1, 0.5, 0.9)]
    except Exception:
        pass
    vals = [frame_brightness(path, t) for t in times]
    vals = [v for v in vals if v is not None]
    problems = []
    if vals:
        darkest = min(vals) / 255.0
        if darkest < (1 - DARK_FAIL):
            pass  # 亮度正常
        if darkest <= 0.10:
            problems.append(f"疑似黑屏（最暗灰阶 {darkest*100:.0f}%）")
    return {"ok": not problems, "problems": problems, "brightness": vals}


def main(argv):
    chapter = int(argv[0]) if argv else 101
    tmp = os.path.join(paths.CHAPTER_OUT[chapter], "temp")
    bad = []
    for f in sorted(os.listdir(tmp)):
        if not re.match(r"shot_\d{3}\.mp4$", f):
            continue
        r = check_shot(os.path.join(tmp, f))
        if not r["ok"]:
            bad.append((f, r["problems"]))
    print(f"受检 {chapter}: 不合格 {len(bad)} 个")
    for n, p in bad:
        print(" ", n, p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))