"""从整本小说里切出指定章节。用法：python split_chapters.py 2 3 4"""
import re
import sys

SRC = r"E:\神秘复苏_文本资产\神秘复苏(1-500章).txt"
OUT = r"E:\神秘复苏_文本资产"

CN = "零一二三四五六七八九十百千两"


def cn2int(s: str) -> int:
    if s.isdigit():
        return int(s)
    s = s.replace("两", "二")
    digits = {c: i for i, c in enumerate("零一二三四五六七八九")}
    total, unit, cur = 0, 1, 0
    for ch in s:
        if ch in digits:
            cur = digits[ch]
        elif ch in "十百千":
            u = {"十": 10, "百": 100, "千": 1000}[ch]
            if cur == 0:
                cur = 1
            total += cur * u
            cur = 0
    return total + cur


def main():
    with open(SRC, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    pat = re.compile(r"^[ \t　]*第([" + CN + r"\d]+)章[ \t　]*(.*)$", re.M)
    marks = []
    for m in pat.finditer(text):
        try:
            num = cn2int(m.group(1))
        except Exception:
            continue
        marks.append((num, m.start(), m.group(0).strip()))

    # 去重（同一个章节号可能因目录/正文重复出现，取最后一次）
    by_num = {}
    for num, pos, title in marks:
        by_num[num] = (pos, title)
    nums = sorted(by_num)

    want = [int(x) for x in sys.argv[1:]] or [2]
    for n in want:
        if n not in by_num:
            print(f"[MISS] 第 {n} 章没找到")
            continue
        start = by_num[n][0]
        nxt = next((x for x in nums if x > n), None)
        end = by_num[nxt][0] if nxt else len(text)
        body = text[start:end].strip()
        path = f"{OUT}\\chapter{n}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(body + "\n")
        print(f"[OK] 第 {n} 章 → {path}  {len(body)} 字  | {by_num[n][1]}")

    print(f"共识别到 {len(nums)} 章，范围 {nums[0]}–{nums[-1]}")


if __name__ == "__main__":
    main()
