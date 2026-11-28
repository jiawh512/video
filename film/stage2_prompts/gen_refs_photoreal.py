"""给主要角色批量生成「真人风格」参考图，统一画风，避免分镜之间风格漂移。"""
import os
import shutil
import sys

sys.path.insert(0, r"E:\神秘复苏_自动化生成工具_Desktop版\神秘复苏_自动化生成工具\t2v_wan21")
sys.path.insert(0, r"E:\神秘复苏_自动化生成工具_Desktop版\神秘复苏_自动化生成工具")

from comfyui_api import ComfyUIClient, build_character_workflow

BASE = r"E:\神秘复苏_视觉资产\01_角色概念图"
STYLE = (
    "photorealistic cinematic film still, real human skin texture, natural pores, "
    "live-action photography, 85mm lens, soft key light, plain dark grey background, "
    "well lit, clearly exposed, sharp focus, crisp fine detail"
)

PEOPLE = {
    "杨间": "an 18-year-old Chinese young man, short messy black hair, lean angular face, defined jawline, deeper-set eyes, mature facial structure of a late teenager, calm neutral expression, white shirt, looks like an upper-secondary student not a child",
    "张伟": "an 18-year-old Chinese high school boy, slim and tall, short neat hair, mischievous half-smile, blue and white school uniform",
    "周正": "a Chinese man in his forties, thin gaunt face and heavy build with a round belly, short greying hair, long grey trench coat, tired deep-set eyes",
    "长衫老人": "a very old gaunt Chinese man, waxy brownish skin covered with dark age spots, sunken cheeks, one milky dead-grey eye, black long robe, standing in shadow",
    "方镜": "an 18-year-old Chinese high school boy, narrow face, cold hard eyes, short black hair, school uniform",
    "王珊珊": "an 18-year-old Chinese high school girl, long black hair in a ponytail, pale skin, anxious expression, blue and white school uniform",
    "段鹏": "an 18-year-old Chinese high school boy, buzz cut, heavy build, nervous eyes, blue and white school uniform",
    "郑飞": "an 18-year-old Chinese high school boy, glasses, thin face, frightened expression, blue and white school uniform",
    "赵建国": "a Chinese man in his forties, short grey-flecked hair, weathered face, dark jacket, tired official look",
    "刘小雨": "a Chinese woman in her twenties, short black hair, clean pale face, plain work shirt, calm professional expression",    "苏蕾": "an 18-year-old Chinese high school girl, shoulder-length black hair, round face, faint nervous expression, blue and white school uniform",
    "王老师": "a Chinese female teacher in her thirties, glasses, tied-back hair, plain blouse, stern expression",
    "苗小善": "an 18-year-old Chinese high school girl, long straight black hair, gentle expression, blue and white school uniform",
    "雷电法王": "a Chinese male doctor in his thirties, white coat, short black hair, tired eyes, hospital badge",
    "鬼婴": "a newborn-sized infant ghost, waxy grey-white skin, sunken black eye sockets with no pupils, dark purple lips, sparse thin black hair, emaciated curled body, stiff limbs, wrapped in a tattered dark cloth, no blood, no gore, cold white side light, horror atmosphere",
    "赵强": "an 18-year-old Chinese young man, round face, buzz cut, small single-lidded eyes, flat nose bridge, thick lips, wheat skin, blue and white school uniform, honest simple expression",
}

client = ComfyUIClient("127.0.0.1:8188")
if not client.is_server_running():
    print("[FAIL] ComfyUI 未运行")
    sys.exit(1)

only = sys.argv[1:] if len(sys.argv) > 1 else None
for name, desc in PEOPLE.items():
    if only and name not in only:
        continue
    prompt = f"{STYLE}, {desc}, upper body, facing camera"
    wf = build_character_workflow(
        positive_prompt=prompt,
        unet_name="z_image_turbo_bf16.safetensors",
        clip_name="qwen_3_4b.safetensors",
        vae_name="Z-image-vae.safetensors",
        width=1024, height=1024, seed=20261030, steps=8, cfg=1.0,
        filename_prefix="ref_v2",
    )
    try:
        pid = client.queue_prompt(wf)["prompt_id"]
        hist = client.wait_for_completion(pid, timeout=600)
        got = False
        for node_out in (hist.get("outputs") or {}).values():
            for img in (node_out.get("images") or []):
                src = os.path.join(r"E:\Comfy-Desktop\ComfyUI-Shared\output", img.get("subfolder", ""), img["filename"])
                if os.path.exists(src):
                    dst_dir = os.path.join(BASE, name)
                    os.makedirs(dst_dir, exist_ok=True)
                    shutil.copy2(src, os.path.join(dst_dir, f"{name}_参考图_v2.png"))
                    print("[OK]", name)
                    got = True
                    break
            if got:
                break
        if not got:
            print("[FAIL]", name)
    except Exception as e:
        print("[ERR]", name, str(e)[:120])




