"""生成"定场图"（场景基准图），统一真人实拍质感，供分镜当场景参考。"""
import os
import shutil
import sys

sys.path.insert(0, r"E:\神秘复苏_自动化生成工具_Desktop版\神秘复苏_自动化生成工具\t2v_wan21")
sys.path.insert(0, r"E:\神秘复苏_自动化生成工具_Desktop版\神秘复苏_自动化生成工具")

from comfyui_api import ComfyUIClient, build_character_workflow

OUT_ROOT = r"E:\神秘复苏_视觉资产\02_场景背景图\photo"
OUTPUT_DIR = r"E:\Comfy-Desktop\ComfyUI-Shared\output"

STYLE = (
    "photorealistic cinematic film still, live-action photography, 35mm lens, "
    "natural film grain, realistic texture and materials, no people, "
    "well exposed, clearly visible, sharp focus, crisp fine detail"
)

PLATES = {
    "LOC_CLASSROOM_NIGHT": "an empty Chinese senior-high classroom at night, rows of wooden desks, fluorescent tubes on, blackboard with chalk writing, windows dark outside",
    "LOC_CLASSROOM_OFF": "the same Chinese classroom with all lights off, only moonlight through the windows, deep shadows",
    "LOC_BEDROOM": "a small Chinese teenage bedroom at night, bed with navy quilt, warm desk lamp on, phone charger cable, dark window",
    "LOC_CORRIDOR_SCHOOL": "an empty Chinese school corridor at night, flickering fluorescent tubes, classroom doors on both sides, polished floor",
    "LOC_CORRIDOR_HOSPITAL": "an empty Chinese hospital corridor at night, cold white lights, blue directional signs, handrails, polished linoleum",
    "LOC_ER_ROOM": "a Chinese hospital emergency room at night, empty gurney, medical cabinets, cold fluorescent light, tiled floor",
    "LOC_MORGUE": "a Chinese hospital morgue at night, stainless steel drawers, one drawer half open, cold blue light, tiled walls",
    "LOC_APARTMENT_BLOCK": "a Chinese residential apartment block at night, many windows, most lights off, one lit window, wet asphalt",
    "LOC_RESTROOM": "a Chinese school restroom at night, tiled walls, a row of stalls, one stall door ajar, dim fluorescent light, wet floor",    "LOC_STAIRCASE": "a dark Chinese apartment stairwell, concrete steps, single bulb, peeling paint, iron railing",
    "LOC_SCHOOL_EXTERIOR": "a Chinese senior-high school building exterior at night, dark windows, one row of lights on, empty playground, low angle looking up",
    "LOC_NETIZEN_HOME": "a small Chinese apartment interior at night, narrow entryway facing a closed front door, shoe rack, dim ceiling light",    "LOC_PHONE_FORUM": "extreme close-up of a smartphone screen in the dark showing a Chinese internet forum thread, dark mode, rows of reply text, slight screen reflection",
    "LOC_WHITE_BONE_TREE": "an endless dim grey-white void with no walls and no horizon, one huge pale bone-white tree standing alone in the middle distance, its branches like fused bone, rotting rags and strips of dried skin hanging from them, several dried skulls and paper streamers, thin cold fog on the ground",
    "LOC_WHITE_BONE_TREE_TRUNK": "a pale bone-white tree trunk, a rusted iron coffin nail as thick as a grown man's arm driven deep into the wood, rust flaking in layers, black liquid seeping out and dripping down the bark, dark wet bark texture",
    "LOC_GHOST_DOMAIN": "a pitch-dark interior with no visible light source, barely visible wet cement walls and a grey concrete floor, thick shadow swallowing the edges, cold damp texture, faint wet reflection on the wall",
}

client = ComfyUIClient("127.0.0.1:8188")
if not client.is_server_running():
    print("[FAIL] ComfyUI 未运行")
    sys.exit(1)

os.makedirs(OUT_ROOT, exist_ok=True)

only = sys.argv[1:]
for i, (key, desc) in enumerate(PLATES.items()):
    if only and key not in only:
        continue
    if not only and os.path.exists(os.path.join(OUT_ROOT, f"{key}.png")):
        print("[SKIP]", key, "已存在")
        continue
    wf = build_character_workflow(
        positive_prompt=f"{STYLE}, {desc}",
        unet_name="z_image_turbo_bf16.safetensors",
        clip_name="qwen_3_4b.safetensors",
        vae_name="Z-image-vae.safetensors",
        width=1344, height=768, seed=20261030 + i, steps=8, cfg=1.0,
        filename_prefix="plate",
    )
    try:
        pid = client.queue_prompt(wf)["prompt_id"]
        hist = client.wait_for_completion(pid, timeout=600)
        got = False
        for node_out in (hist.get("outputs") or {}).values():
            for img in (node_out.get("images") or []):
                src = os.path.join(OUTPUT_DIR, img.get("subfolder", ""), img["filename"])
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(OUT_ROOT, f"{key}.png"))
                    got = True
                    break
            if got:
                break
        print(("[OK] " if got else "[FAIL] ") + key)
    except Exception as e:
        print("[ERR]", key, str(e)[:100])


