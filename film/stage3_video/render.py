"""按分镜表渲染：配音 → 参考图组装 → MiniMax H3 出片 → 交给 stage4 合成。

相对旧驱动的改动：
  · 参考图走 assets.pick_ref：按景别挑多视角图，不再永远只喂正面
  · 角色名先归一化，找不到会打印告警而不是静默跳过
  · 出片前先跑 storyboard.check，有阻断错误直接拒绝开工
"""
import os
import random
import sys
import time

from ..common import paths
from ..stage2_prompts import assets, storyboard
from ..stage4_finish import assemble

sys.path.insert(0, paths.T2V)
import generate_novel_chapter_video as g  # noqa: E402
from comfyui_api import ComfyUIClient  # noqa: E402


def build_refs(shot, verbose=True):
    refs, notes = [], []
    plate, key = assets.plate_for(shot.get("location", ""), shot.get("location_id") or "")
    if plate:
        refs.append({"path": plate})
        notes.append(f"定场 {os.path.basename(plate)}")
    else:
        notes.append(f"定场 ∅（{key}）")

    for name in (shot.get("characters") or [])[:2]:
        if assets.is_group(name):
            continue
        ref, reason = assets.pick_ref(name, shot.get("shot_size", ""), shot.get("camera_move", ""))
        if ref:
            refs.append({"path": ref})
            notes.append(f"{assets.normalize(name)}·{reason}")
        else:
            notes.append(f"{assets.normalize(name)}·缺图!")
    if verbose:
        print("  [REF] " + " | ".join(notes))
    return refs


def render_shot(client, chapter, shot, steps=0):
    idx = int(shot["idx"])
    audio = paths.shot_temp(chapter, idx, ".mp3")
    raw = paths.shot_temp(chapter, idx, "_raw.mp4")
    seg = paths.shot_temp(chapter, idx, ".mp4")
    os.makedirs(os.path.dirname(audio), exist_ok=True)

    print(f"\n[SHOT {idx}] {shot.get('layer')} / {shot.get('location')} / {shot.get('shot_size')} / {shot.get('camera_move')}")

    if not os.path.exists(audio):
        if not g.generate_narration(shot["narration"], audio):
            print("  [FAIL] 配音失败")
            return None
        g._apply_tempo(audio, paths.NARRATION_SPEED)

    dur = g.get_audio_duration(audio)
    if dur <= 0:
        print("  [FAIL] 音频时长无效")
        return None
    target = max(paths.SHOT_MIN_SEC, min(dur, paths.SHOT_MAX_SEC))
    length = g.round_minimax_h3_length(int(target * paths.FPS))
    print(f"  旁白 {dur:.2f}s → {length} 帧 = {length/24:.2f}s")

    refs = build_refs(shot)

    if not os.path.exists(raw):
        attempts = [
            {"refs": refs, "length": length},
            {"refs": refs[:1], "length": max(85, length - 17)},
            {"refs": [], "length": max(85, length - 34)},
        ]
        ok = False
        for ai, at in enumerate(attempts, 1):
            try:
                g.generate_minimax_h3_ref2va_video(
                    client=client, prompt=shot["visual_prompt"], output_path=raw,
                    reference_images=at["refs"], width=paths.WIDTH, height=paths.HEIGHT,
                    length=at["length"], seed=random.randint(1, 10**8), steps=20,
                    scheduler="simple", sampler_name="res_multistep",
                    enable_lightning_lora=True,
                    lightning_steps=(steps or (6 if shot.get("layer") == "inner" else 4)),
                    fps=paths.FPS, filename_prefix=f"story_{idx:03d}",
                )
                ok = True
                break
            except Exception as e:
                msg = str(e).split("\n")[0][:160]
                print(f"  [RETRY {ai}/3] {msg}")
                if ai < len(attempts):
                    try:
                        client.interrupt()
                    except Exception:
                        pass
                    time.sleep(15)
        if not ok:
            print("  [FAIL] 三次都失败，跳过这一镜")
            return None

    if not g.combine_video_with_audio(raw, audio, seg):
        print("  [FAIL] 合成失败")
        return None
    print(f"  [OK] {seg}")
    return seg


def main(argv):
    if not argv:
        print("用法: python -m film render <章节号> <all|1,8,32>")
        return 2
    chapter = int(argv[0])
    sel = argv[1] if len(argv) > 1 else "all"
    steps = int(argv[2]) if len(argv) > 2 else 0

    res = storyboard.check(chapter)
    if not storyboard.report(res):
        print("\n[拒绝开工] 先修上面的阻断问题（参考图/定场图）")
        return 1

    data, _ = storyboard.load(chapter)
    all_shots = data["shots"]
    if sel == "all":
        shots = all_shots
    elif "," in sel:
        want = {int(x) for x in sel.split(",") if x.strip()}
        shots = [s for s in all_shots if int(s["idx"]) in want]
    else:
        shots = all_shots[: int(sel)]

    client = ComfyUIClient(paths.COMFY_HOST)
    if not client.is_server_running():
        print("[FAIL] ComfyUI 未运行")
        return 1

    videos = []
    for s in shots:
        seg = render_shot(client, chapter, s, steps)
        if seg:
            videos.append(seg)
    assemble.assemble(chapter, videos, shots)
    return 0