"""T08 · 渲染、封装与封面。

规划案 §5.6：
  npx --yes hyperframes@0.8.104 render --fps 30 --quality high --workers 2 --output ../work/silent.mp4
  ffmpeg -i work/silent.mp4 -i work/final_mix.wav -map 0:v:0 -map 1:a:0 -c:v copy
         -c:a aac -b:a 256k -ar 48000 -ac 2 -t 30 -movflags +faststart -y deliver/zhouchu_30s.mp4
  每次实际用 ffprobe 判断 silent.mp4 是否 900 帧 / 30s；workers=2 内存不稳固定回退 1。

产物：work/silent.mp4、deliver/zhouchu_30s.mp4、deliver/poster.jpg
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))
FILM_DIR = ROOT / "film"
SILENT = ROOT / "work" / "silent.mp4"
MIX = ROOT / "work" / "final_mix.wav"
OUT = ROOT / "deliver" / "zhouchu_30s.mp4"
POSTER = ROOT / "deliver" / "poster.jpg"

FPS = TOKENS["video"]["fps"]
FRAMES = TOKENS["video"]["frames"]
DURATION = TOKENS["video"]["durationSeconds"]
HF = ["npx", "--yes", "hyperframes@0.8.104"]


def log(msg: str) -> None:
    print(f"[render] {msg}", flush=True)


def probe(path: pathlib.Path) -> dict:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels",
         "-of", "json", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if proc.returncode != 0:
        return {}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}


def video_stream(info: dict) -> dict:
    for s in info.get("streams", []):
        if s.get("codec_name") in ("h264", "hevc", "vp9"):
            return s
    return {}


def audio_stream(info: dict) -> dict:
    for s in info.get("streams", []):
        if s.get("codec_name") in ("aac", "mp3", "opus"):
            return s
    return {}


def render_silent(workers: int) -> bool:
    cmd = HF + [
        "render",
        "--fps", str(FPS),
        "--quality", "high",
        "--workers", str(workers),
        "--output", str(SILENT),
    ]
    log(f"渲染静音画面：workers={workers}")
    proc = subprocess.run(cmd, cwd=str(FILM_DIR), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True)
    tail = proc.stdout[-2500:]
    if proc.returncode != 0:
        log("渲染失败，输出尾部：")
        log(tail)
        return False
    log("渲染完成")
    return True


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)

    if not SILENT.exists() or not render_silent(2):
        log("workers=2 未成功，回退 workers=1")
        if not render_silent(1):
            return 1

    info = probe(SILENT)
    vs = video_stream(info)
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    nb = int(vs.get("nb_frames", 0) or 0)
    log(f"silent.mp4：{vs.get('width')}x{vs.get('height')} {vs.get('codec_name')} "
        f"{vs.get('r_frame_rate')} 帧={nb} 时长={dur:.3f}s")
    if abs(dur - DURATION) > 0.2 or (nb and abs(nb - FRAMES) > 2):
        log(f"⚠ 画面时长/帧数与规划不符（期望 {DURATION}s / {FRAMES} 帧）")

    # ---------- 封装 ----------
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(SILENT), "-i", str(MIX),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
        "-t", str(DURATION),
        "-movflags", "+faststart",
        str(OUT),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        log(f"封装失败: {proc.stderr.strip()[:500]}")
        return 1
    log(f"封装完成 → {OUT.relative_to(ROOT)}")

    # ---------- 封面 ----------
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", "2.2", "-i", str(OUT), "-frames:v", "1", "-q:v", "3", str(POSTER)],
        check=True,
    )
    log(f"封面 → {POSTER.relative_to(ROOT)}")

    # ---------- 复核 ----------
    finfo = probe(OUT)
    fv = video_stream(finfo)
    fa = audio_stream(finfo)
    fdur = float(finfo.get("format", {}).get("duration", 0) or 0)
    log(f"成片：{fv.get('width')}x{fv.get('height')} {fv.get('codec_name')} {fv.get('r_frame_rate')} "
        f"帧={fv.get('nb_frames')} | 音频 {fa.get('codec_name')} {fa.get('sample_rate')}Hz "
        f"{fa.get('channels')}ch | 时长 {fdur:.3f}s | 大小 {int(finfo.get('format', {}).get('size', 0)) // 1024}KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
