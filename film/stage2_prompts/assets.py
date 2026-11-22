"""资产解析：角色名归一化、参考图挑选（含多视角）、定场图映射。

历史问题：
  · 分镜里写「老人」「雷电法王（白大褂医生）」，资产目录叫「长衫老人」「雷电法王」→ 找不到图且静默跳过
  · 45 张多视角图做出来了，驱动从没用过，永远只喂一张正面
"""
import os
import re

from ..common import paths

NAME_ALIAS = {
    "老人": "长衫老人",
    "黑衫老人": "长衫老人",
    "长衫老人（照片）": "长衫老人",
    "雷电法王（白大褂医生）": "雷电法王",
    "雷电法王(白大褂医生)": "雷电法王",
    "医生": "雷电法王",
    "杨间（未来）": "杨间",
    "杨间(未来)": "杨间",
    "刘小宇": "刘小雨",
    "王珊珊等": "王珊珊",
}

GROUP_PATTERNS = ("学生", "同学", "警察", "病人", "急救", "尸体", "数名", "几名",
                  "前排", "群众", "全班", "众人", "大家", "人群", "所有人", "围观",
                  "人皮", "黑影", "鬼影", "声音", "羊皮纸", "纸", "录像", "录音")

VIEW_HINTS = {
    "背影": "背面", "背": "背面", "背面": "背面",
    "侧": "右侧", "侧面": "右侧",
    "俯": "俯视", "仰": "仰视",
}

PLATE_MAP = [
    (("教室", "黑板", "讲台", "课桌"), "LOC_CLASSROOM_NIGHT"),
    (("熄灯", "全黑"), "LOC_CLASSROOM_OFF"),
    (("卧室", "被窝", "床"), "LOC_BEDROOM"),
    (("医院走廊", "走廊·医院"), "LOC_CORRIDOR_HOSPITAL"),
    (("急诊", "抢救"), "LOC_ER_ROOM"),
    (("停尸", "太平间"), "LOC_MORGUE"),
    (("厕所", "隔间", "洗手间"), "LOC_RESTROOM"),
    (("走廊",), "LOC_CORRIDOR_SCHOOL"),
    (("小区", "居民楼", "单元门"), "LOC_APARTMENT_BLOCK"),
    (("楼梯",), "LOC_STAIRCASE"),
    (("操场", "校舍", "教学楼外"), "LOC_SCHOOL_EXTERIOR"),
    (("玄关", "网友家", "房门口"), "LOC_NETIZEN_HOME"),
    (("手机", "帖", "屏"), "LOC_PHONE_FORUM"),
]


def normalize(name: str) -> str:
    """归一化：去【】标记、去括号备注、去「等」、别名映射。"""
    n = (name or "").strip()
    n = re.sub(r"【[^】]*】", "", n)
    n = re.sub(r"[（(][^）)]*[）)]", "", n).strip()
    n = n.rstrip("等").strip()
    return NAME_ALIAS.get(n, n)


def is_group(name: str) -> bool:
    return any(p in (name or "") for p in GROUP_PATTERNS)


def character_dir(name: str) -> str:
    return os.path.join(paths.CHAR_DIR, normalize(name))


def base_ref(name: str):
    d = character_dir(name)
    if not os.path.isdir(d):
        return None
    n = normalize(name)
    p = os.path.join(d, f"{n}_参考图_v2.png")
    return p if os.path.exists(p) else None


def pick_ref(name: str, shot_size: str = "", camera_move: str = ""):
    """按景别/运镜挑参考图；挑不到退回正面基准图。返回 (path, reason)。"""
    d = character_dir(name)
    n = normalize(name)
    views = os.path.join(d, "视角")
    if os.path.isdir(views):
        tag = None
        for key, view in VIEW_HINTS.items():
            if key in (shot_size or "") or key in (camera_move or ""):
                tag = view
                break
        if tag:
            p = os.path.join(views, f"{n}_{tag}.png")
            if os.path.exists(p):
                return p, f"视角图·{tag}"
    p = base_ref(name)
    if p:
        return p, "基准正面图"
    return None, "缺参考图"


def plate_for(location: str = "", location_id: str = ""):
    """定场图：优先 location_id，其次按地点文字匹配。返回 (path, key)。"""
    if location_id:
        p = os.path.join(paths.PLATE_DIR, location_id + ".png")
        if os.path.exists(p):
            return p, location_id
        return None, location_id + "（文件不存在）"
    loc = location or ""
    for keys, key in PLATE_MAP:
        if any(k in loc for k in keys):
            p = os.path.join(paths.PLATE_DIR, key + ".png")
            if os.path.exists(p):
                return p, key
            return None, key + "（文件不存在）"
    return None, "未匹配"


def list_characters():
    out = []
    if not os.path.isdir(paths.CHAR_DIR):
        return out
    for d in sorted(os.listdir(paths.CHAR_DIR)):
        full = os.path.join(paths.CHAR_DIR, d)
        if not os.path.isdir(full) or d.startswith("_"):
            continue
        base = os.path.join(full, f"{d}_参考图_v2.png")
        views_dir = os.path.join(full, "视角")
        views = len(os.listdir(views_dir)) if os.path.isdir(views_dir) else 0
        out.append({"name": d, "base": os.path.exists(base), "views": views})
    return out