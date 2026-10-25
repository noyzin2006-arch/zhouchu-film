"""T08 · 联系表抽帧。

规划案 §8.1 第 8 条：抽帧至少 t=0.3/1.4/3.4/5.0/6.8/8.8/11.0/13.9/16.5/18.9/22.1/25.5/28.2/29.8s，
并对每组字幕的 start/end 前后各抽 1 帧证明不提前消失。

产物：reports/contact-sheet.png、reports/frames/*.png
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

PLAN_TIMES = [0.3, 1.4, 3.4, 5.0, 6.8, 8.8, 11.0, 13.9, 16.5, 18.9, 22.1, 25.5, 28.2, 29.8]
FRAMES_DIR = ROOT / "reports" / "frames"
SHEET = ROOT / "reports" / "contact-sheet.png"


def log(msg: str) -> None:
    print(f"[sheet] {msg}", flush=True)


def grab(video: pathlib.Path, t: float, out: pathlib.Path) -> bool:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(out)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    return proc.returncode == 0 and out.exists()


def main() -> int:
    parser = argparse.ArgumentParser(description="联系表抽帧")
    parser.add_argument("--video", default=str(ROOT / "deliver" / "zhouchu_30s.mp4"))
    parser.add_argument("--output", default=str(SHEET))
    args = parser.parse_args()
    video = pathlib.Path(args.video)
    if not video.exists():
        log(f"找不到 {video}")
        return 1

    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for old in FRAMES_DIR.glob("*.png"):
        old.unlink()

    times = list(PLAN_TIMES)
    # 每组字幕的首尾前后各抽一帧
    captions_path = ROOT / "work" / "align" / "captions.json"
    if captions_path.exists():
        caps = json.loads(captions_path.read_text(encoding="utf-8"))["captions"]
        sr = json.loads(captions_path.read_text(encoding="utf-8"))["sample_rate"]
        for cap in caps:
            start = cap["start_sample"] / sr
            end = cap["end_sample"] / sr
            times.extend([max(0.0, start - 0.08), min(29.9, end + 0.08)])
    times = sorted({round(t, 2) for t in times if 0 <= t <= 30})

    grabbed = []
    for t in times:
        out = FRAMES_DIR / f"t{t:06.2f}.png"
        if grab(video, t, out):
            grabbed.append((t, out))
    log(f"抽帧 {len(grabbed)} 张")

    if not grabbed:
        return 1
    # 拼接成联系表（每行 7 列）
    inputs = []
    for t, path in grabbed:
        inputs += ["-i", str(path)]
    cols = 7
    rows = (len(grabbed) + cols - 1) // cols
    scale = 240
    vf = (
        f"scale={scale}:-1,tile={cols}x{rows}:padding=6:margin=6:color=0x101813"
    )
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
         "-filter_complex", vf, "-frames:v", "1", args.output],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    if proc.returncode != 0:
        log(f"拼接失败：{proc.stderr.strip()[:300]}")
        return 1
    log(f"联系表 → {pathlib.Path(args.output).relative_to(ROOT)}（{len(grabbed)} 帧）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
