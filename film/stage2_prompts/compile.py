"""提示词编译器：把结构化分镜编译成可校验的提示词包。

为什么要有它（2026-11-22 审计）：
  第 1 章 60 镜的 visual_prompt 是「LLM 自由写的英文散文」，
  · 长度 510–844 字符，长短差 65%
  · 角色外形出现 61 种写法（杨间 → "a lean teenage boy" / "a boy" / "the boy"）
  · shot_size / camera_move 字段存着，但基本没进 prompt
  结果就是换镜换人、景别失准。

设计（参考 storyboard-master 的「决策先行」）：
  提示词不是写出来的，是**编译**出来的：
    风格锚（常量）
  + 镜头语言（shot_size / camera_move → 固定英文词表）
  + 场景（location + location_id）
  + 角色（canon.json 里的正典外形，**逐字**复制，不允许改写）
  + 动作（action 的中文原文，或分镜里给的 action_en）
  + 台词口型（<d> 标签）
  + 人群纪律（常量）
  + 负向条款（常量）
  同一份分镜 → 永远生成同一段 prompt，可复现、可 diff。

不自作聪明的地方：
  · 不翻译 action（翻译是 LLM 的活；没有 action_en 就如实报告缺口）
  · 不补写角色（canon 里没有的名字 → 报错，不猜）
"""
from __future__ import annotations

import json
import os
import re
import sys

from ..common import paths
from . import assets

HERE = os.path.dirname(os.path.abspath(__file__))
CANON_PATH = os.path.join(HERE, "canon.json")

# ---------- 固定词表 ----------
STYLE_ANCHOR = (
    "Chinese characters with East Asian faces, photorealistic live-action film still, "
    "real human skin texture, natural skin pores, cinematic color grade, "
    "35mm film look, shallow depth of field, natural motion blur"
)
NEGATIVE = (
    "no anime, no illustration, no 3d render, no cartoon, no CGI look, "
    "no plastic skin, no extra fingers, no watermark, no text overlay, "
    "no children, no stylized hair, no extra hands, no extra fingers, no deformed hands"
)
CROWD_RULE = (
    "Crowd discipline: at most FOUR background people, each with a different posture and "
    "none looking at the camera; background people stay in place across the shot."
)
SOLO_RULE = "alone in the frame, no other people in view"
HAND_RULE = ("anatomy lock: the person has exactly two hands and two arms, five fingers per hand; " + "any object is held by two hands at most; no third hand, no extra limbs")

SHOT_SIZE_EN = {
    "大特写": "extreme close-up",
    "特写": "close-up",
    "近景": "medium close-up",
    "中景": "medium shot",
    "全景": "full shot",
    "远景": "wide shot",
    "大远景": "extreme wide shot",
}
CAMERA_MOVE_EN = {
    "固定": "static locked-off camera",
    "推": "slow push-in",
    "拉": "slow pull-back",
    "摇": "slow pan",
    "移": "lateral tracking move",
    "跟": "follow tracking shot",
    "手持": "handheld slight sway",
}
LAYER_STYLE = {
    "outer": "",  # 现实层：不加额外修饰
    "inner": "inside a story-telling reconstruction, slightly heightened atmosphere",
}


def load_canon(path: str = CANON_PATH) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"缺少正典外形表: {path}")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {k: (v.get("canon") if isinstance(v, dict) else v) for k, v in raw.items()}


TEXT_NOISE = ('片头', '字幕', '黑底白字', '白字', '大字', '字样', '文字', '标题', '浮在画面', '屏幕上的字')


def _clean_action(text: str) -> str:
    """去掉会在画面上生成文字的描述（模型会把"片头白字"真的画成乱码）。"""
    if not text:
        return ''
    parts = re.split(r'[，,。；;]', text)
    kept = [p for p in parts if not any(k in p for k in TEXT_NOISE)]
    return '，'.join(kept).strip()


def _dialogue_tag(shot: dict) -> str:
    lines = shot.get("dialogue") or []
    if not lines:
        return ""
    parts = []
    for d in lines[:3]:
        spk = (d.get("speaker") or "").strip()
        text = (d.get("text") or "").strip()
        if not text:
            continue
        parts.append(f"<d>{spk}: {text}</d>" if spk and spk not in ("旁白", "内心") else f"<d>{text}</d>")
    return " ".join(parts)


def compile_prompt(shot: dict, canon: dict, model: str = "minimax_h3") -> dict:
    """编译单个镜头。返回提示词包；缺料进 `gaps`，不静默糊过去。"""
    gaps: list[str] = []

    # 1) 镜头语言
    size_cn = (shot.get("shot_size") or "").strip()
    move_cn = (shot.get("camera_move") or "").strip()
    size_en = SHOT_SIZE_EN.get(size_cn)
    move_en = CAMERA_MOVE_EN.get(move_cn)
    if not size_en:
        gaps.append(f"景别「{size_cn}」不在词表里")
    if not move_en:
        gaps.append(f"运镜「{move_cn}」不在词表里")

    # 2) 场景
    loc = (shot.get("location") or "").strip()
    plate, plate_key = assets.plate_for(loc, shot.get("location_id") or "")
    if not loc:
        gaps.append("location 为空")
    if not plate:
        gaps.append(f"定场图未匹配（{plate_key}）")

    # 3) 角色正典（逐字）
    cast = [c for c in (shot.get("characters") or []) if assets.needs_ref(c)]
    char_clauses = []
    for name in cast[:3]:
        key = assets.normalize(name)
        text = canon.get(key) or canon.get(name)
        if not text:
            gaps.append(f"角色「{name}」没有正典外形（canon.json）")
            continue
        char_clauses.append(f"<{key}> is {text}")

    # 4) 动作
    action_en = (shot.get("action_en") or "").strip()
    action_cn = _clean_action(shot.get("action") or "")
    if action_en:
        action = action_en
    elif action_cn:
        # H3 是中文母语模型，中文动作可以直接用；有英文版则优先英文
        action = action_cn
    else:
        action = ""
        gaps.append("action 为空")

    # 5) 组装
    segs = [STYLE_ANCHOR]
    if size_en or move_en:
        segs.append(", ".join(x for x in (size_en, move_en) if x))
    if loc:
        segs.append(f"scene: {loc}")
    if LAYER_STYLE.get(shot.get("layer") or "outer"):
        segs.append(LAYER_STYLE[shot["layer"]])
    segs.extend(char_clauses)
    if action:
        segs.append(f"action: {action}")
    tag = _dialogue_tag(shot)
    if tag:
        segs.append(f"dialogue {tag}")
    if cast:
        segs.append(HAND_RULE)
        needs_crowd = _has_crowd(shot) or _action_has_others(shot.get('action') or '')
        segs.append(CROWD_RULE if needs_crowd else SOLO_RULE)
    segs.append(NEGATIVE)
    prompt = ". ".join(s.rstrip(".") for s in segs if s) + "."

    refs = [{"role": "plate", "path": plate}] if plate else []
    for name in cast[:2]:
        ref, reason = assets.pick_ref(name, size_cn, move_cn)
        if ref:
            refs.append({"role": f"character:{assets.normalize(name)}", "path": ref, "reason": reason})

    return {
        "model": model,
        "prompt": prompt,
        "negative": "",  # H3 把负向写进正文，这里留空以示区别
        "params": {
            "景别": size_cn, "景别_en": size_en,
            "运镜": move_cn, "运镜_en": move_en,
            "duration": shot.get("duration_sec"),
            "width": paths.WIDTH, "height": paths.HEIGHT, "fps": paths.FPS,
        },
        "references": refs,
        "consistency": {"plate": plate_key if plate else None, "characters": list(cast)},
        "provenance": {
            "canon_keys": [assets.normalize(c) for c in cast],
            "action_source": "action_en" if action_en else ("action(中文)" if action_cn else "缺"),
        },
        "gaps": gaps,
        "length": len(prompt),
    }


OTHERS = ('医生', '护士', '警察', '医护人员', '急救', '抬', '围观', '同学', '学生', '人群', '两人', '几个人', '众人')


def _action_has_others(action: str) -> bool:
    return any(k in action for k in OTHERS)


def _has_crowd(shot: dict) -> bool:
    return any(assets.is_group(c) for c in (shot.get("characters") or []))


def validate(pack: dict, shot: dict) -> list[str]:
    """编译产物的硬校验：不是「包含某个词就过」，而是逐项对账。"""
    issues = list(pack.get("gaps") or [])
    prompt = pack["prompt"]
    params = pack["params"]

    if params.get("景别_en") and params["景别_en"] not in prompt:
        issues.append(f"景别词「{params['景别_en']}」没进 prompt")
    if params.get("运镜_en") and params["运镜_en"] not in prompt:
        issues.append(f"运镜词「{params['运镜_en']}」没进 prompt")
    for name in pack["consistency"]["characters"]:
        key = assets.normalize(name)
        if f"<{key}>" not in prompt:
            issues.append(f"角色「{key}」的正典段没进 prompt")
    if len(prompt) < 400:
        issues.append(f"prompt 过短（{len(prompt)} 字符，低于 400）")
    if len(prompt) > 2000:
        issues.append(f"prompt 过长（{len(prompt)} 字符，超过 2000）")
    if "no anime" not in prompt:
        issues.append("缺负向条款")
    return issues


def compile_chapter(chapter: int, model: str = "minimax_h3") -> dict:
    from . import storyboard

    data, path = storyboard.load(chapter)
    canon = load_canon()
    packs = []
    for shot in data.get("shots", []):
        pack = compile_prompt(shot, canon, model)
        pack["idx"] = shot.get("idx")
        pack["issues"] = validate(pack, shot)
        packs.append(pack)
    return {"chapter": chapter, "source": path, "packs": packs}


def main(argv):
    chapter = int(argv[0]) if argv else 1
    out = compile_chapter(chapter)
    packs = out["packs"]
    bad = [p for p in packs if p["issues"]]
    print(f"=== 第 {chapter} 章编译：{len(packs)} 镜，{len(bad)} 镜有问题 ===")
    ls = [p["length"] for p in packs]
    print(f"prompt 长度: 最短 {min(ls)} / 最长 {max(ls)} / 平均 {sum(ls)//len(ls)}")
    shown = 0
    for p in packs[:3]:
        print(f"\n--- S{p['idx']}（{p['length']} 字符）")
        print(p["prompt"][:500])
    for p in bad[:5]:
        print(f"\n!! S{p['idx']}: " + "；".join(p["issues"][:4]))
    if "-o" in argv:
        dst = os.path.join(paths.CHAPTER_OUT[chapter], "prompt_packs.json")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\n已写 {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
