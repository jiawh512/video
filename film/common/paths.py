"""统一路径与常量。所有脚本只从这里取路径，别再各自硬编码。"""
import os

# ---------- 根目录 ----------
WORKSPACE = r"D:\Backup\Documents\deepseek-harness\default-workspace"
PROJECT = r"E:\神秘复苏_自动化生成工具_Desktop版\神秘复苏_自动化生成工具"
T2V = os.path.join(PROJECT, "t2v_wan21")

NOVEL = r"E:\神秘复苏_文本资产\神秘复苏(1-500章).txt"
CHAPTER_DIR = r"E:\神秘复苏_文本资产"                  # chapterN.txt
STORY_ROOT = r"D:\Backup\Documents\deepseek-harness\default-workspace\third_party\novel-to-script-team\outputs\神秘复苏"

ASSET_ROOT = r"E:\神秘复苏_视觉资产"
CHAR_DIR = os.path.join(ASSET_ROOT, "01_角色概念图")
PLATE_DIR = os.path.join(ASSET_ROOT, r"02_场景背景图\photo")

COMFY_INPUT = r"E:\Comfy-Desktop\ComfyUI-Shared\input"
COMFY_OUTPUT = r"E:\Comfy-Desktop\ComfyUI-Shared\output"
COMFY_HOST = "127.0.0.1:8188"

# ---------- 生成参数 ----------
WIDTH, HEIGHT, FPS = 1344, 768, 24
NARRATION_SPEED = 1.3          # SAPI 语速倍率
CHARS_PER_SEC = 4.8            # 1.3 倍下的大致语速，用于校验时长
SHOT_MIN_SEC, SHOT_MAX_SEC = 8.0, 12.0

# ---------- 分镜表位置 ----------
CHAPTER_STORY = {
    1: os.path.join(STORY_ROOT, r"第一章_v2\分镜表.json"),
    2: os.path.join(STORY_ROOT, r"第二章\分镜表.json"),
    3: os.path.join(STORY_ROOT, r"第三章\分镜表.json"),
    4: os.path.join(STORY_ROOT, r"第四章\分镜表.json"),
    5: os.path.join(STORY_ROOT, r"第5章\分镜表.json"),
    6: os.path.join(STORY_ROOT, r"第6章\分镜表.json"),
    7: os.path.join(STORY_ROOT, r"第7章\分镜表.json"),
    8: os.path.join(STORY_ROOT, r"第8章\分镜表.json"),
    9: os.path.join(STORY_ROOT, r"第9章\分镜表.json"),
    10: os.path.join(STORY_ROOT, r"第10章\分镜表.json"),
}

CHAPTER_OUT = {
    1: os.path.join(ASSET_ROOT, "32_第一章_重制"),
    2: os.path.join(ASSET_ROOT, "33_第二章_重制"),
    3: os.path.join(ASSET_ROOT, "34_第三章_重制2"),
    4: os.path.join(ASSET_ROOT, "31_第四章重制"),
    5: os.path.join(ASSET_ROOT, "36_第五章"),
    6: os.path.join(ASSET_ROOT, "37_第六章"),
    7: os.path.join(ASSET_ROOT, "38_第七章"),
    8: os.path.join(ASSET_ROOT, "39_第八章"),
    9: os.path.join(ASSET_ROOT, "40_第九章"),
    10: os.path.join(ASSET_ROOT, "41_第十章"),
}

CHAPTER_TXT = {n: os.path.join(CHAPTER_DIR, f"chapter{n}.txt") for n in range(1, 501)}


def chapter_final(n: int) -> str:
    return os.path.join(CHAPTER_OUT[n], f"神秘复苏_第{n}章_成片.mp4")


def shot_temp(n: int, idx: int, suffix: str) -> str:
    return os.path.join(CHAPTER_OUT[n], "temp", f"shot_{idx:03d}{suffix}")



# ---------- 剧集（照参考片脚本改编，独立于「章」） ----------
EP_ROOT = r"D:\Backup\Documents\deepseek-harness\default-workspace\third_party\novel-to-script-team\outputs\神秘复苏\剧集"

for _n in range(1, 19):
    CHAPTER_STORY[100 + _n] = os.path.join(EP_ROOT, f"第{_n:02d}集", "分镜表.json")
    CHAPTER_OUT[100 + _n] = os.path.join(ASSET_ROOT, f"50_第{_n:02d}集")


def is_episode(key: int) -> bool:
    return key >= 100

