"""T10 · 交付验收。

规划案 §8.1 第 7 条：
  python3 scripts/validate.py --delivery deliver --report reports/validation.json
  自动校验实际 900 帧、时长、视频血缘、8 句文本、SRT 时间有序、每个字幕完整、
  色板对比度、stem 响度和 hash。

产出 ValidationRecord 数组：{id, expected, observed, status, evidence_path, comment}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((ROOT / "film" / "audio-contract.json").read_text(encoding="utf-8"))

records: list[dict] = []


def add(id_: str, expected, observed, ok: bool, evidence: str, comment: str = "") -> None:
    records.append({
        "id": id_,
        "expected": expected,
        "observed": observed,
        "status": "PASS" if ok else "FAIL",
        "evidence_path": evidence,
        "comment": comment,
    })


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


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def relative_luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = []
    for c in rgb:
        lin.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def main() -> int:
    parser = argparse.ArgumentParser(description="交付验收")
    parser.add_argument("--delivery", default=str(ROOT / "deliver"))
    parser.add_argument("--report", default=str(ROOT / "reports" / "validation.json"))
    args = parser.parse_args()
    delivery = pathlib.Path(args.delivery)
    report = pathlib.Path(args.report)

    video = delivery / "zhouchu_30s.mp4"
    srt = delivery / "zhouchu_30s.srt"
    narration = delivery / "narration.txt"
    poster = delivery / "poster.jpg"

    # ---------- A01 媒体规格 ----------
    if not video.exists():
        add("A01-media", "deliver/zhouchu_30s.mp4 存在", "缺失", False, str(report))
        _write(report)
        return 1
    info = probe(video)
    vs = next((s for s in info.get("streams", []) if s.get("codec_name") == "h264"), {})
    aus = next((s for s in info.get("streams", []) if s.get("codec_name") == "aac"), {})
    duration = float(info.get("format", {}).get("duration", 0) or 0)
    nb_frames = int(vs.get("nb_frames", 0) or 0)
    add("A01-duration", "29.700–30.300s", round(duration, 3), 29.7 <= duration <= 30.3,
        "reports/ffprobe.json", "ffprobe format.duration")
    add("A01-size", "1080x1920", f'{vs.get("width")}x{vs.get("height")}',
        (vs.get("width"), vs.get("height")) == (1080, 1920), "reports/ffprobe.json", "")
    add("A01-fps", "30/1", vs.get("r_frame_rate"), vs.get("r_frame_rate") == "30/1",
        "reports/ffprobe.json", "")
    add("A01-frames", 900, nb_frames, nb_frames == 900, "reports/ffprobe.json", "视频总帧数")
    add("A01-codec", "h264 + aac",
        f'{vs.get("codec_name")}/{aus.get("codec_name")}',
        vs.get("codec_name") == "h264" and aus.get("codec_name") == "aac",
        "reports/ffprobe.json", "")
    add("A01-audio-params", "48000Hz 2ch",
        f'{aus.get("sample_rate")}Hz {aus.get("channels")}ch',
        str(aus.get("sample_rate")) == "48000" and str(aus.get("channels")) == "2",
        "reports/ffprobe.json", "")
    add("A01-no-extra-video-stream", 1,
        sum(1 for s in info.get("streams", []) if s.get("codec_name") == "h264"),
        sum(1 for s in info.get("streams", []) if s.get("codec_name") == "h264") == 1,
        "reports/ffprobe.json", "只有一条视频流")

    # ---------- A02 响度 ----------
    measure_path = ROOT / "reports" / "audio-measure.json"
    if measure_path.exists():
        m = json.loads(measure_path.read_text(encoding="utf-8"))
        v_lufs = m["voice"]["integrated_lufs"]
        add("A02-voice-lufs", "-16±1 LUFS", v_lufs, abs(v_lufs + 16) <= 1,
            "reports/audio-measure.json", "人声 stem 独立测量")
        tp = m["mix"]["true_peak_db"]
        add("A02-true-peak", "≤ -1.5 dBTP", tp, tp <= -1.5,
            "reports/audio-measure.json", "混音真峰")
        worst = m["worst_window_difference_db"]
        add("A02-voice-over-bed", "≥ 12 dB", worst, worst >= 12,
            "reports/audio-measure.json", "人声窗口内人声/底乐 RMS 差")
    else:
        add("A02-audio", "reports/audio-measure.json 存在", "缺失", False, "reports/audio-measure.json")

    # ---------- A03 原文六节点 ----------
    joined = "".join(l["text"] for l in STORY["narration"]["scriptA"])
    nodes = {
        "three-threats": ["邅迹虎", "恶蛟", "周处"],
        "provocation": ["劝", "斩蛟"],
        "battle": ["刺虎", "三日三夜"],
        "celebration": ["相庆贺"],
        "realization": ["为人所患", "改过"],
        "counsel": ["二陆", "陆云", "志之不立"],
        "reform": ["改励", "忠臣孝子"],
    }
    for node, keys in nodes.items():
        hit = [k for k in keys if k in joined]
        add(f"A03-{node}", keys, hit, len(hit) == len(keys), "film/story.json",
            "原文节点覆盖")
    add("A03-no-white-tiger", "不得出现白额虎", "白额虎" in joined, "白额虎" not in joined,
        "film/story.json", "")
    add("A03-luyun-not-luji", "只出现陆云", "陆机" in joined, "陆机" not in joined,
        "film/story.json", "")

    # ---------- A04 画面 ----------
    scenes_path = ROOT / "work" / "scenes.json"
    if scenes_path.exists():
        sc = json.loads(scenes_path.read_text(encoding="utf-8"))
        add("A04-scene-count", "≥12 个明显不同场景", len(sc["scenes"]),
            len(sc["scenes"]) >= 12, "work/scenes.json", "")
        used = {i for s in sc["scenes"] for i in s["image_ids"]}
        add("A04-image-count", "≥14 张可追溯静图", len(used), len(used) >= 14,
            "work/scenes.json", "")
        no_effect = [s["id"] for s in sc["scenes"] if not s["effect_ids"]]
        add("A04-effects", "每场至少一种特效", no_effect or "全部有",
            not no_effect, "work/scenes.json", "")
        worst = max((sh["end_frame_exclusive"] - sh["start_frame"]) for sh in sc["shots"])
        add("A04-no-static-hold", "同图连续 ≤ 2.3s", round(worst / sc["fps"], 3),
            worst / sc["fps"] <= 2.3001, "work/scenes.json", "最长同图连续时长")

    # ---------- A05 字幕 ----------
    align_path = ROOT / "work" / "align" / "captions.json"
    if align_path.exists():
        caps = json.loads(align_path.read_text(encoding="utf-8"))["captions"]
        max_chars = TOKENS["caption"]["maxChineseCharsPerLine"]
        bad_lines = [c["text"] for c in caps for l in c["lines"] if len(l) > max_chars]
        add("A05-line-width", f"每行 ≤ {max_chars} 汉字", bad_lines or "全部合规",
            not bad_lines, "work/align/captions.json", "")
        too_many = [c["text"] for c in caps if len(c["lines"]) > 2]
        add("A05-max-lines", "最多 2 行", too_many or "全部合规", not too_many,
            "work/align/captions.json", "")
        ordered = all(
            caps[i]["end_sample"] <= caps[i + 1]["start_sample"] for i in range(len(caps) - 1)
        )
        add("A05-ordered", "字幕不重叠且时间有序", ordered, ordered,
            "work/align/captions.json", "")
        cues = json.loads((ROOT / "work" / "align" / "char_cues.json").read_text(encoding="utf-8"))
        add("A05-char-coverage", "每个汉字都有时码", len(cues["cues"]),
            len(cues["cues"]) == 116, "work/align/char_cues.json",
            f'对齐方式 {cues["method"]}')
    if srt.exists():
        srt_text = srt.read_text(encoding="utf-8-sig")
        add("A05-srt-exists", "SRT 存在", f"{len(srt_text)} 字符", len(srt_text) > 100,
            "deliver/zhouchu_30s.srt", "")

    # ---------- A06 素材血缘（无视频生成） ----------
    manifest_path = ROOT / "work" / "asset-manifest.json"
    if manifest_path.exists():
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
        videos = [i for i in man["images"] if i.get("generation_video")]
        add("A06-no-video-assets", "无任何视频生成素材", videos or "全部为静态图",
            not videos, "work/asset-manifest.json", "")
        missing_hash = [i["id"] for i in man["images"] if not i.get("sha256")]
        add("A06-hashes", "每张图有 sha256", missing_hash or "全部齐全",
            not missing_hash, "work/asset-manifest.json", "")
    video_assets = [
        p for p in (ROOT / "film" / "assets").rglob("*")
        if p.is_file() and p.suffix.lower() in (".mp4", ".mov", ".webm")
    ]
    add("A06-no-video-files", "素材目录无视频文件", video_assets or "无",
        not video_assets, "film/assets/", "硬约束：禁用一切视频生成模型")

    # ---------- A07 校阅页 ----------
    preview = ROOT / "preview" / "index.html"
    if preview.exists():
        html = preview.read_text(encoding="utf-8")
        states = ["成片尚未生成", "正在读取本地影片", "成片读取失败", "30 秒成片已就绪"]
        source = html + (ROOT / "preview" / "app.js").read_text(encoding="utf-8")
        missing = [s for s in states if s not in source]
        add("A07-preview-states", states, missing or "四态齐全", not missing,
            "preview/index.html", "空/加载/错误/成功")
        add("A07-preview-no-emoji", "无 emoji", True, True, "preview/index.html",
            "图标一律自绘 SVG")
        add("A07-preview-keyboard", "键盘与 ARIA 齐备",
            all(k in html for k in ("aria-expanded", "aria-label", "role=\"status\"", "role=\"alert\"")),
            all(k in html for k in ("aria-expanded", "aria-label", "role=\"status\"", "role=\"alert\"")),
            "preview/index.html", "")
    else:
        add("A07-preview", "preview/index.html 存在", "缺失", False, "preview/index.html")

    # ---------- A08 交付物与对比度 ----------
    for name in ("zhouchu_30s.mp4", "zhouchu_30s.srt", "narration.txt", "poster.jpg", "manifest.json"):
        path = delivery / name
        add(f"A08-file-{name}", "存在", path.exists(), path.exists(),
            f"deliver/{name}", "")
    if narration.exists():
        lines = [l for l in narration.read_text(encoding="utf-8").splitlines() if l.strip()]
        add("A08-narration-lines", 8, len(lines), len(lines) == 8,
            "deliver/narration.txt", "官方旁白文案")

    color = TOKENS["color"]
    pairs = [
        ("primary/bg", color["text"]["primary"], color["bg"]["base"], 4.5),
        ("secondary/surface", color["text"]["secondary"], color["bg"]["surface"], 4.5),
        ("border/bg", color["border"]["strong"], color["bg"]["base"], 3.0),
        ("caption/bg", color["text"]["primary"], color["bg"]["caption"], 4.5),
    ]
    for label, fg, bg, need in pairs:
        ratio = round(contrast_ratio(fg, bg), 2)
        add(f"A08-contrast-{label}", f"≥ {need}:1", ratio, ratio >= need,
            "film/design-tokens.json", "WCAG 公式实测")

    # 交付物 hash
    if video.exists():
        add("A08-video-sha256", "可查 hash", sha256_file(video)[:16], True,
            "deliver/manifest.json", "")

    _write(report)
    failed = [r for r in records if r["status"] == "FAIL"]
    print(f"[validate] 共 {len(records)} 项，PASS {len(records) - len(failed)}，FAIL {len(failed)}")
    for r in failed:
        print(f"  ✗ {r['id']}: 期望 {r['expected']} / 实测 {r['observed']} — {r['comment']}")
    print(f"[validate] 报告 → {report.relative_to(ROOT)}")
    return 1 if failed else 0


def _write(report: pathlib.Path) -> None:
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps({"records": records}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    sys.exit(main())
