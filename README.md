# video — 小说影视化流水线

把一部小说做成竖屏/横屏短剧的自动化流水线，按**四个阶段**拆分。当前实现基于本地 ComfyUI + MiniMax H3（图生视频）+ Windows TTS。

## 四个阶段

```
① 文本 → 剧本      stage1_script/
② 剧本 → prompt + 图片素材   stage2_prompts/
③ prompt + 图 → 视频        stage3_video/
④ 质检 + 合成               stage4_finish/
```

| 阶段 | 目录 | 做什么 |
|---|---|---|
| ① | `film/stage1_script/` | 切章节、把分集脚本转成分镜骨架、参考片语音转写 |
| ② | `film/stage2_prompts/` | 角色名归一化、参考图挑选、定场图生成、分镜表校验 |
| ③ | `film/stage3_video/` | 配音 → 参考图组装 → 提交 ComfyUI 出片 → 逐章队列 |
| ④ | `film/stage4_finish/` | 抽帧质检（黑屏/过暗）、逐镜片段拼接成片 |

## 快速开始

```bash
# 预检：不渲染，只检查分镜表的数据是否齐（定场图、参考图、时长、prompt 锚）
python -m film check all

# 资产总览：哪些角色有基准图/多视角图
python -m film assets

# 渲染某一章（预检不过会拒绝开工）
python -m film render 3 all
```

## 目录

```
film/
├─ common/paths.py      所有路径与参数的唯一真相源（要改路径先改这里）
├─ stage1_script/
│   ├─ split_chapters.py     从整本小说切章节
│   ├─ script2story.py       分集脚本 → 分镜骨架（台词逐字保留）
│   └─ asr_clip.py           参考片语音转写（faster-whisper）
├─ stage2_prompts/
│   ├─ assets.py             角色名归一化 / 参考图挑选 / 定场图映射
│   ├─ storyboard.py         分镜表校验（5 类规则）
│   ├─ gen_refs_photoreal.py 角色真人基准图
│   ├─ gen_multiangle.py     角色多视角展开（Qwen-Image-Edit 2511）
│   └─ gen_scene_plates.py   场景定场图
├─ stage3_video/
│   ├─ render.py             配音 → 出片
│   └─ run_chapters.ps1      逐章渲染队列（断点续跑）
├─ stage4_finish/
│   ├─ qc.py                 抽帧判黑屏/过暗
│   └─ assemble.py           片段 → 成片
└─ cli.py                    命令行入口
```

## 依赖

- Python 3.10+
- ffmpeg（在 PATH 里）
- ComfyUI（本地，默认 `127.0.0.1:8188`），需要 MiniMax H3 视频模型 + 一个 T2I 模型（Z-Image 或 Qwen-Image）
- edge-tts（`zh-CN-YunxiNeural`）做配音，需联网；受限网络下 403，SAPI 兜底留在 `t2v_wan21/generate_novel_chapter_video.py`

## 设计笔记

三条经验写在 `流水线梳理与重构.md` 里：

1. **渲染前预检比渲染后返工便宜一百倍**：参考图缺失、定场图没匹配、旁白字数与时长不匹配，这些都能在提交前查出来。
2. **角色一致性靠三件事**：一张正典外形描述（所有镜头共用）、多视角参考图、显式的“人群/禁即兴”条款。任缺一项，换镜就换人。
3. **时长只有一个口径**：`duration_sec = 旁白字数 / 4.8`（1.3 倍语速），由字数推出来而不是手写；渲染时以实测音频为准并夹在 8–12 秒。`python -m film durations all` 只报告，加 `--write` 才改分镜表。

## 许可

仅供个人学习与创作使用。模型与素材的版权归各自权利人。
