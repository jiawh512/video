"""把《前10章_分集脚本.md》转成分镜表骨架（台词逐字保留）。

设计：
  · narration 就是参考片那句原话，不改写、不合并
  · 每句台词一镜，时长 = 字数/4.8 + 0.5，天然落在 4-7 秒
  · speaker 单独存一份，将来接多音色 TTS 直接用
  · visual_prompt 由各集单独生成，这里先留空
"""
import json
import os
import re
import sys

from ..common import paths
from ..stage2_prompts import assets

SCRIPT_MD = r"E:\神秘复苏_视觉资产\35_参考片转写\前10章_分集脚本.md"

RE_EP = re.compile(r"^##\s*第(\d+)集\s*(.*)$")
RE_SCENE = re.compile(r"^###\s*场景(\d+)｜([^｜]+)｜([^｜]+)(?:｜(.*))?$")
RE_LINE = re.compile(r"^([^：:]{1,12})[：:]\s*(.+)$")
RE_PIC = re.compile(r"^画面[：:]\s*(.+)$")

SPEAKER_NOISE = ("（旁白）", "(旁白)", "（内心）", "(内心)")


def parse(md_path=SCRIPT_MD):
    episodes, ep, scene = [], None, None
    with open(md_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n").strip()
            if not line or line.startswith("# ") or line.startswith("---") or line.startswith(">"):
                continue

            m = RE_EP.match(line)
            if m:
                ep = {"no": int(m.group(1)), "title": m.group(2).strip(), "start": "", "scenes": []}
                episodes.append(ep)
                scene = None
                continue
            if ep is None:
                continue

            if line.startswith("**起始"):
                mm = re.search(r"起始\s*([0-9:]+)", line)
                if mm:
                    ep["start"] = mm.group(1)
                continue

            m = RE_SCENE.match(line)
            if m:
                g3 = (m.group(3) or "").strip()
                g4 = (m.group(4) or "").strip()
                if g4:
                    loc_part, time_part, cast_part = m.group(2).strip(), g3, g4
                else:
                    loc_part, time_part, cast_part = m.group(2).strip(), "", g3
                scene = {
                    "no": int(m.group(1)),
                    "location": loc_part,
                    "time": time_part,
                    "cast": [c.strip() for c in re.split(r"[、,，]", cast_part) if c.strip()],
                    "lines": [],
                    "picture": "",
                }
                ep["scenes"].append(scene)
                continue

            m = RE_PIC.match(line)
            if m and scene:
                scene["picture"] = m.group(1).strip()
                continue

            m = RE_LINE.match(line)
            if m and scene:
                speaker = m.group(1).strip()
                for noise in SPEAKER_NOISE:
                    speaker = speaker.replace(noise, "")
                scene["lines"].append({"speaker": speaker.strip(), "text": m.group(2).strip()})
                continue

    def _t(e):
        s = e.get("start") or "0:00"
        try:
            nums = [int(x) for x in s.split(":")]
        except ValueError:
            return 0
        sec = 0
        for n in nums:
            sec = sec * 60 + n
        return sec

    episodes.sort(key=_t)
    for i, e in enumerate(episodes, 1):
        e["local_no"] = e["no"]
        e["no"] = i
    return episodes


def hanzi(s):
    return len(re.sub(r"[^\u4e00-\u9fa5]", "", s or ""))


def is_inner(scene, line):
    loc = scene["location"]
    sp = line["speaker"]
    if any(k in loc for k in ("照片", "记忆", "回忆", "想象", "讲述", "帖", "内层", "鬼域", "梦境")):
        return True
    if sp in ("旁白", "内心", "杨间内心"):
        return True
    return False


def build(ep):
    shots, idx = [], 0
    for sc in ep["scenes"]:
        loc_text = f"{sc['location']}·{sc['time']}" if sc["time"] not in sc["location"] else sc["location"]
        plate, plate_key = assets.plate_for(loc_text, "")
        for ln in sc["lines"]:
            idx += 1
            chars = hanzi(ln["text"])
            dur = round(max(3.5, min(12.0, chars / paths.CHARS_PER_SEC + 0.5)), 1)
            cast = [c for c in sc["cast"] if c != ln["speaker"]]
            if ln["speaker"] not in ("旁白", "内心") and not assets.is_group(ln["speaker"]):
                cast = [ln["speaker"]] + cast
            shots.append({
                "idx": idx,
                "narration": ln["text"],
                "speaker": ln["speaker"],
                "location": loc_text,
                "location_id": plate_key if plate else None,
                "characters": cast[:3],
                "action": sc["picture"],
                "shot_size": "中景",
                "camera_move": "固定",
                "dialogue": [{"speaker": ln["speaker"], "text": ln["text"]}],
                "duration_sec": dur,
                "layer": "inner" if is_inner(sc, ln) else "outer",
                "visual_prompt": "",
            })
    return shots


def emit(ep, out_dir):
    shots = build(ep)
    os.makedirs(out_dir, exist_ok=True)
    data = {
        "episode": ep["no"],
        "title": ep["title"],
        "start": ep["start"],
        "source": "参考片 BV1tmYZ6wEes（台词逐字保留）",
        "shots": shots,
    }
    path = os.path.join(out_dir, "分镜表.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] 第{ep['no']}集 {ep['title']} → {path}（{len(shots)} 镜）")
    return path


def main(argv):
    md = SCRIPT_MD
    if argv and argv[0] == "build":
        ep_no = int(argv[1])
        base = r"D:\Backup\Documents\deepseek-harness\default-workspace\third_party\novel-to-script-team\outputs\神秘复苏\剧集"
        for e in parse(md):
            if e["no"] == ep_no:
                emit(e, os.path.join(base, f"第{ep_no:02d}集"))
                return 0
        print(f"[FAIL] 没有第 {ep_no} 集")
        return 1
    eps = parse(md)
    print(f"解析到 {len(eps)} 集，共 {sum(len(e['scenes']) for e in eps)} 场景，"
          f"{sum(sum(len(s['lines']) for s in e['scenes']) for e in eps)} 句台词")
    for e in eps[:5]:
        n = sum(len(s["lines"]) for s in e["scenes"])
        print(f"  第{e['no']}集 {e['title']}  起始 {e['start']}  场景 {len(e['scenes'])}  台词 {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))