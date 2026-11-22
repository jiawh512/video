"""用 Qwen-Image-Edit 2511 + 多角度 LoRA，从一张真人头像扩出多视角设定图。

用法：python gen_multiangle.py 杨间
"""
import os
import shutil
import sys

PROJ = r"E:\神秘复苏_自动化生成工具_Desktop版\神秘复苏_自动化生成工具"
sys.path.insert(0, PROJ)

from comfyui_api import ComfyUIClient

ANGLES = [
    (0, "正面", "front view, facing the camera directly, same person, same face, same hairstyle, same clothing"),
    (90, "右侧", "right side profile view, head turned ninety degrees to the right, same person, same face, same hairstyle"),
    (180, "背面", "back view, seen from behind, same person, same hairstyle, same clothing"),
    (45, "四分之三", "three-quarter view, slightly turned to the right, same person, same face, same hairstyle"),
    (-30, "仰视", "low angle view looking slightly up at the subject, same person, same face"),
]

CHAR_ROOT = r"E:\神秘复苏_视觉资产\01_角色概念图"
INPUT_DIR = r"E:\Comfy-Desktop\ComfyUI-Shared\input"
OUTPUT_DIR = r"E:\Comfy-Desktop\ComfyUI-Shared\output"


def build_angle_prompt(image_name, text, seed, prefix):
    """和 p3 同一条管线，但把缺失的 QwenMultiangleCameraNode 换成文字指令。"""
    return {
        "5": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2511_bf16.safetensors", "weight_dtype": "fp8_e4m3fn"}},
        "6": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "10": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "18": {"class_type": "LoadImage", "inputs": {"image": image_name, "upload": "image"}},
        "37": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["18", 0]}},
        "8": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["6", 0], "prompt": text, "vae": ["10", 0], "image1": ["37", 0]}},
        "9": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["6", 0], "prompt": "", "vae": ["10", 0], "image1": ["37", 0]}},
        "19": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["8", 0], "reference_latents_method": "index_timestep_zero"}},
        "20": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["9", 0], "reference_latents_method": "index_timestep_zero"}},
        "25": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["5", 0], "lora_name": "qwen-image-edit-2511-multiple-angles-loraX2.safetensors", "strength_model": 1.0}},
        "26": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["25", 0], "lora_name": "Qwen_Image_Edit_2511_Lightning_4步加速Lora_fp32.safetensors", "strength_model": 1.0}},
        "27": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["26", 0], "shift": 3.1}},
        "28": {"class_type": "CFGNorm", "inputs": {"model": ["27", 0], "strength": 1.0}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["37", 0], "vae": ["10", 0]}},
        "1": {"class_type": "KSampler", "inputs": {"model": ["28", 0], "positive": ["19", 0], "negative": ["20", 0], "latent_image": ["11", 0], "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "15": {"class_type": "VAEDecode", "inputs": {"samples": ["1", 0], "vae": ["10", 0]}},
        "31": {"class_type": "SaveImage", "inputs": {"images": ["15", 0], "filename_prefix": prefix}},
    }


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "杨间"
    src = os.path.join(CHAR_ROOT, name, f"{name}_参考图_v2.png")
    if not os.path.exists(src):
        print("[FAIL] 没有参考图:", src)
        return 1

    seed_name = f"{name}_seed.png"
    shutil.copy2(src, os.path.join(INPUT_DIR, seed_name))

    out_dir = os.path.join(CHAR_ROOT, name, "视角")
    os.makedirs(out_dir, exist_ok=True)

    client = ComfyUIClient("127.0.0.1:8188")
    if not client.is_server_running():
        print("[FAIL] ComfyUI 未运行")
        return 1

    for idx, (_h, label, text) in enumerate(ANGLES):
        prefix = f"ma_{name}_{idx}_{label}"
        wf = build_angle_prompt(seed_name, text, 20261030 + idx, prefix)
        try:
            pid = client.queue_prompt(wf)["prompt_id"]
            hist = client.wait_for_completion(pid, timeout=900)
        except Exception as e:
            print(f"[FAIL] {label}: {str(e)[:120]}")
            continue
        got = []
        for node_out in (hist.get("outputs") or {}).values():
            for img in (node_out.get("images") or []):
                p = os.path.join(OUTPUT_DIR, img.get("subfolder", ""), img["filename"])
                if os.path.exists(p):
                    dst = os.path.join(out_dir, f"{name}_{label}.png")
                    shutil.copy2(p, dst)
                    got.append(dst)
        print(f"[{'OK' if got else 'FAIL'}] {label}  {len(got)} 张")
    print("[DONE]", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())

