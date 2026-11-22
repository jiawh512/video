"""逐镜片段 → 成片（ffmpeg concat）。"""
import os
import subprocess

from ..common import paths


def assemble(chapter, videos, shots):
    if not videos:
        print("[FAIL] 没有可拼接的镜头")
        return None
    tag = "_".join(str(int(s["idx"])) for s in shots)
    out_dir = paths.CHAPTER_OUT[chapter]
    final = os.path.join(out_dir, f"分层试跑_{tag}.mp4")
    listfile = os.path.join(out_dir, "temp", "concat.txt")
    os.makedirs(os.path.dirname(listfile), exist_ok=True)
    with open(listfile, "w", encoding="utf-8") as f:
        for v in videos:
            f.write("file '" + v.replace("\\", "/") + "'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", listfile, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", final],
        check=True,
    )
    print(f"\n[DONE] {final}")
    return final