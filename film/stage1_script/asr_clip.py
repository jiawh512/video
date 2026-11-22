"""转写 B 站某条视频的前 N 秒音频（无字幕时用）。"""
import os
import subprocess
import sys

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
os.environ.setdefault('HF_HOME', r'C:\Users\Administrator\.dsh\bili-duty\.hf-cache')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')

URL = 'https://www.bilibili.com/video/BV1tmYZ6wEes/'
SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 2400
MODEL = sys.argv[2] if len(sys.argv) > 2 else 'small'

OUT_DIR = r'E:\神秘复苏_视觉资产\35_参考片转写'
os.makedirs(OUT_DIR, exist_ok=True)
AUDIO = os.path.join(OUT_DIR, f"clip_p1_{SECONDS}s.m4a")
TXT = os.path.join(OUT_DIR, f"clip_p1_{SECONDS}s.txt")


def fetch_audio():
    if os.path.exists(AUDIO) and os.path.getsize(AUDIO) > 1024 * 1024:
        print('[跳过] 已有音频', os.path.getsize(AUDIO) // 1024 // 1024, 'MB', flush=True)
        return True
    cmd = [
        sys.executable, '-m', 'yt_dlp',
        '--no-playlist', '-f', 'bestaudio/best',
        '--download-sections', f'*0-{SECONDS}',
        '--force-keyframes-at-cuts',
        '-o', AUDIO,
        '--no-warnings',
        URL,
    ]
    print('[下载] 前', SECONDS, '秒音频...', flush=True)
    r = subprocess.run(cmd)
    return r.returncode == 0 and os.path.exists(AUDIO)


def transcribe():
    from faster_whisper import WhisperModel
    print(f'[加载模型] {MODEL}', flush=True)
    dev = os.environ.get('ASR_DEVICE', 'cpu')
    if dev == 'cuda':
        m = WhisperModel(MODEL, device='cuda', compute_type='float16')
    else:
        m = WhisperModel(MODEL, device='cpu', compute_type='int8', cpu_threads=8, num_workers=1)
    segs, info = m.transcribe(AUDIO, language='zh', vad_filter=True, beam_size=5)
    with open(TXT, 'w', encoding='utf-8') as f:
        for s in segs:
            line = f'[{int(s.start)//60:02d}:{int(s.start)%60:02d}] {s.text.strip()}'
            f.write(line + '\n')
            print(line, flush=True)
    print('[完成]', TXT, flush=True)


if __name__ == '__main__':
    if not fetch_audio():
        print('[FAIL] 音频下载失败', flush=True)
        sys.exit(1)
    transcribe()


