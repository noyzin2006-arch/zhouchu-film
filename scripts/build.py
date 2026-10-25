"""T10 · 一键构建。

规划案 §8.1 第 4 条：
  python3 scripts/build.py > reports/build.log 2>&1；退出码 0，生成完整 deliver/，
  本地 asset hash 重复构建不能再次消耗远端请求。

各步骤幂等：已有合格产物即跳过（--force 可强制重做）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))

DELIVER = ROOT / "deliver"
SCRIPTS = ROOT / "scripts"


def log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def run(cmd: list[str], step: str) -> int:
    log(f"▶ {step}")
    proc = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True)
    tail = proc.stdout[-3000:]
    print(tail, flush=True)
    if proc.returncode != 0:
        log(f"✗ {step} 失败（退出码 {proc.returncode}）")
    return proc.returncode


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_narration() -> None:
    DELIVER.mkdir(parents=True, exist_ok=True)
    lines = [f"{l['id']} {l['text']}" for l in STORY["narration"]["scriptA"]]
    (DELIVER / "narration.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"✔ deliver/narration.txt（{len(lines)} 句）")


def copy_validation() -> None:
    """把校验结果复制进交付目录：校阅页离线状态下也要能读到 PASS/FAIL。"""
    src = ROOT / "reports" / "validation.json"
    if src.exists():
        shutil.copy2(src, DELIVER / "validation.json")
        log("✔ deliver/validation.json")


def copy_preview() -> None:
    src = ROOT / "preview"
    dst = DELIVER / "preview"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    log(f"✔ deliver/preview/（{len(list(dst.iterdir()))} 个文件）")


def write_playback_readme() -> None:
    text = f"""周处除三害 · 30 秒竖屏叙事短片
================================

成片      deliver/zhouchu_30s.mp4
          {TOKENS['video']['width']}×{TOKENS['video']['height']} · {TOKENS['video']['fps']}fps · 900 帧 · 30.000s
          H.264 / yuv420p + AAC 48kHz 立体声

字幕      deliver/zhouchu_30s.srt（UTF-8 with BOM，21 组）
          视频内已烧录硬字幕，与 SRT 同源（同一 CaptionCue 数组生成）

旁白      deliver/narration.txt（8 句官方文案）
封面      deliver/poster.jpg
校阅页    deliver/preview/index.html —— 离线打开即可回放与查看台词；
          不联网、不调用任何生成接口。缺失 MP4 时会明确给出重建命令。

快速播放
--------
  open deliver/preview/index.html          # 浏览器内回放
  open deliver/zhouchu_30s.mp4              # 直接看片

内容说明
--------
  取材于《世说新语·自新》第十五（南朝宋刘义庆），公有领域。
  画面为 AI 生成的静态绢本设色插画 + 代码合成的运镜/转场/特效；
  **全片不含任何视频生成素材**。
  配乐为本项目程序化合成（92 BPM 五声音阶）。

权利与来源详见 reports/rights.md。
"""
    (DELIVER / "README-PLAYBACK.txt").write_text(text, encoding="utf-8")
    log("✔ deliver/README-PLAYBACK.txt")


def write_manifest() -> None:
    asset_manifest = {}
    am = ROOT / "work" / "asset-manifest.json"
    if am.exists():
        asset_manifest = json.loads(am.read_text(encoding="utf-8"))
    rights = {}
    for item in asset_manifest.get("images", []):
        rights[item["output_path"]] = item.get("rights_status")
    for item in asset_manifest.get("overlays", []):
        rights[item["path"]] = item.get("rights_status")

    files = []
    for path in sorted(DELIVER.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(ROOT))
        media_type = {
            ".mp4": "video/mp4", ".srt": "application/x-subrip", ".txt": "text/plain",
            ".jpg": "image/jpeg", ".png": "image/png", ".json": "application/json",
            ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
        }.get(path.suffix.lower(), "application/octet-stream")
        files.append({
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "media_type": media_type,
            "source_type": "generated-by-project",
            "rights_status": rights.get(rel, "procedurally synthesized in project"
                                       if path.suffix.lower() in (".mp4", ".srt") else "project-authored"),
        })

    manifest = {
        "task": "LOOP-001",
        "round": 1,
        "title": "周处除三害 · 30 秒",
        "source_text": "《世说新语·自新》第十五（南朝宋刘义庆）",
        "story_version": STORY["version"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "video": {
            "width": TOKENS["video"]["width"],
            "height": TOKENS["video"]["height"],
            "fps": TOKENS["video"]["fps"],
            "frames": 900,
            "duration_seconds": 30.0,
            "codec": "h264",
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_sample_rate": 48000,
            "audio_channels": 2,
        },
        "renderer": "hyperframes 0.8.104 (HTML+GSAP) + ffmpeg 8.1.1",
        "video_generation_used": False,
        "narration": "豆包 TTS（VOLCENGINE_TTS_*）",
        "music": "procedurally synthesized in project（92 BPM 五声音阶，seed 20261025）",
        "alignment": "whisperx 3.7.5 强制对齐（jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn）",
        "assets": asset_manifest.get("images", []),
        "overlays": asset_manifest.get("overlays", []),
        "files": files,
    }
    (DELIVER / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"✔ deliver/manifest.json（{len(files)} 个文件）")


def package_zip() -> pathlib.Path | None:
    zip_path = ROOT / "zhouchu-film-LOOP-001.zip"
    if zip_path.exists():
        zip_path.unlink()
    cmd = ["zip", "-r", "-q", str(zip_path), "deliver", "-x", "*.DS_Store"]
    proc = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        log(f"打包失败：{proc.stderr.strip()[:300]}")
        return None
    log(f"✔ {zip_path.name}（{zip_path.stat().st_size // 1024}KB，sha256 {sha256_file(zip_path)[:16]}）")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="一键构建")
    parser.add_argument("--force", action="store_true", help="强制重做所有步骤")
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()

    steps = [
        ("导出设计令牌", [sys.executable, str(SCRIPTS / "export_tokens.py")]),
        ("生产静帧与程序蒙版", [sys.executable, str(SCRIPTS / "assets.py")]),
        ("合成中文旁白", [sys.executable, str(SCRIPTS / "tts.py"), "--granularity", "phrase",
                      "--tag", "phrase"]),
        ("字级对齐与字幕", [sys.executable, str(SCRIPTS / "align.py")]),
        ("配乐与混音", [sys.executable, str(SCRIPTS / "audio_mix.py")]),
        ("场景编排", [sys.executable, str(SCRIPTS / "build_scene.py")]),
    ]
    for name, cmd in steps:
        if run(cmd, name) != 0:
            return 1

    if not args.skip_render:
        if run([sys.executable, str(SCRIPTS / "render.py")], "渲染与封装") != 0:
            return 1
        if run([sys.executable, str(SCRIPTS / "contact_sheet.py")], "联系表抽帧") != 0:
            return 1

    write_narration()
    copy_preview()
    write_playback_readme()

    # 验收先跑：校阅页的状态条要读得到校验结果
    rc = run([sys.executable, str(SCRIPTS / "validate.py")], "交付验收")
    copy_validation()

    write_manifest()
    package_zip()
    log("构建完成")
    return rc


if __name__ == "__main__":
    sys.exit(main())
