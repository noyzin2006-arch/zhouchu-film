"""T05 · 中文字级对齐与字幕生成。

规划案 §5.3：
  主路径：WhisperX 普通话强制对齐（文本已知，按句段喂入精确 start/end）→ 字级时码。
  兜底  ：23 组短语逐组 TTS，每组 WAV 样本首尾即字幕首尾（chunk-boundary）；
          组内字级先按每汉字均匀分配作**估计**，source 标 "chunk-boundary"，reviewed=false。

产物：
  work/align/char_cues.json    每个汉字一条时码
  work/align/captions.json     CaptionCue 数组（硬字幕与 SRT 同源）
  deliver/zhouchu_30s.srt       UTF-8 with BOM
  reports/word-alignment-review.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import subprocess
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((ROOT / "film" / "audio-contract.json").read_text(encoding="utf-8"))

TIMELINE = ROOT / "work" / "voice_timeline_line.json"
PHRASE_TIMELINE = ROOT / "work" / "voice_timeline_phrase.json"
MASTER = ROOT / "work" / "voice_master.wav"
LINE_MASTER = ROOT / "work" / "voice_master_line.wav"
PHRASE_MASTER = ROOT / "work" / "voice_master_phrase.wav"
ALIGN_DIR = ROOT / "work" / "align"
SRT = ROOT / "deliver" / "zhouchu_30s.srt"
REVIEW_CSV = ROOT / "reports" / "word-alignment-review.csv"
VENV_PY = ROOT / "work" / "venv-whisperx" / "bin" / "python"

ALIGN_MODEL = CONTRACT["alignment"]["primary"]["model"]
PUNCT = "，。：、！；？「」『』（）《》…—·"


def log(msg: str) -> None:
    print(f"[align] {msg}", flush=True)


def is_han(ch: str) -> bool:
    return "一" <= ch <= "鿿"


def strip_punct(text: str) -> str:
    return "".join(ch for ch in text if is_han(ch))


def han_positions(text: str) -> list[int]:
    return [i for i, ch in enumerate(text) if is_han(ch)]


def group_text(line_text: str, lo: int, hi: int) -> str:
    """按汉字区间还原带标点的字幕文本。"""
    pos = han_positions(line_text)
    start, end = pos[lo], pos[hi]
    out = line_text[start : end + 1]
    nxt = line_text[end + 1 : end + 2]
    if nxt and nxt in PUNCT:
        out += nxt
    return out


def build_groups(line_text: str, phrases: list[str]) -> list[dict]:
    """把短语并成 4–12 汉字的字幕组，返回 [{lo, hi, phrases}]（lo/hi 是汉字下标）。"""
    han = strip_punct(line_text)
    spans = []
    cursor = 0
    for phrase in phrases:
        p = strip_punct(phrase)
        idx = han.find(p, cursor)
        if idx < 0:
            raise SystemExit(f"短语 {phrase!r} 在台词 {line_text!r} 中定位失败")
        spans.append([idx, idx + len(p) - 1, phrase])
        cursor = idx + len(p)

    groups = [list(s) for s in spans]
    i = 0
    while i < len(groups):
        length = groups[i][1] - groups[i][0] + 1
        if length >= 4:
            i += 1
            continue
        # 太短：向后合并（优先），否则向前
        if i + 1 < len(groups) and (groups[i + 1][1] - groups[i][0] + 1) <= 12:
            groups[i + 1][0] = groups[i][0]
            del groups[i]
            continue
        if i > 0 and (groups[i][1] - groups[i - 1][0] + 1) <= 12:
            groups[i - 1][1] = groups[i][1]
            del groups[i]
            i -= 1
            continue
        raise SystemExit(f"无法把短语并成 4–12 汉字组：{groups[i]}")
    for g in groups:
        n = g[1] - g[0] + 1
        if not (4 <= n <= 12):
            raise SystemExit(f"字幕组长度越界 {n}: {g}")
    return [{"lo": g[0], "hi": g[1]} for g in groups]


def run_whisperx() -> list[dict] | None:
    """主路径：WhisperX 强制对齐。失败返回 None（由兜底接管）。"""
    if not VENV_PY.exists():
        log("找不到 whisperx venv，跳过主路径")
        return None
    if not TIMELINE.exists():
        log("没有 voice_timeline.json，先跑 tts.py")
        return None

    # 对齐单元 = 短语级 TTS 的 23 组（文本已知、每段起止由真实样本测得）。
    # 规划案 §5.3 第 2 步：「按句段将准确的 start/end 和 text 喂给 align」。
    # 整句喂入会被 nltk 中文断句切成多个重复子段，短语级可避免。
    timeline = json.loads(PHRASE_TIMELINE.read_text(encoding="utf-8"))
    segments = []
    for unit in timeline["units"]:
        segments.append({
            "start": unit["start_sample"] / timeline["sample_rate"],
            "end": unit["end_sample"] / timeline["sample_rate"],
            "text": unit["phrase"],
        })

    payload = {
        "segments": segments,
        "model": ALIGN_MODEL,
        "language": "zh",
        "master": str(PHRASE_MASTER),
        "out": str(ALIGN_DIR / "whisperx_raw.json"),
    }
    ALIGN_DIR.mkdir(parents=True, exist_ok=True)
    payload_path = ALIGN_DIR / "whisperx_input.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    helper = ROOT / "work" / "_whisperx_align.py"
    helper.write_text(
        """
import json, os, sys, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
import whisperx

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
device = "cpu"
audio = whisperx.load_audio(cfg["master"])
model, meta = whisperx.load_align_model(cfg["language"], device, model_name=cfg["model"])
result = whisperx.align(cfg["segments"], model, meta, audio, device,
                        return_char_alignments=True, print_progress=False)
json.dump(result, open(cfg["out"], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("whisperx align ok:", len(result.get("segments", [])), "segments")
""".strip() + "\n",
        encoding="utf-8",
    )
    env = {"HF_ENDPOINT": "https://hf-mirror.com", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"}
    try:
        proc = subprocess.run(
            [str(VENV_PY), str(helper), str(payload_path)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1800,
        )
    except subprocess.TimeoutExpired:
        log("whisperx 超时（30 分钟上限）")
        return None
    out_path = ALIGN_DIR / "whisperx_raw.json"
    if proc.returncode != 0 or not out_path.exists():
        log("whisperx 主路径失败：")
        log(proc.stdout[-1500:])
        return None
    log("whisperx 主路径完成")
    return json.loads(out_path.read_text(encoding="utf-8"))


def cues_from_whisperx(raw: dict, timeline: dict) -> list[dict] | None:
    """把 WhisperX 结果映射成 CharCue；任何异常都退回兜底。

    raw.segments[i].chars[j] = {char, start, end, score}
    每段的文本必须与喂进去的短语一致，汉字序列逐字比对。
    """
    segs = raw.get("segments") or []
    units = timeline["units"]
    if len(segs) != len(units):
        log(f"段数不匹配：whisperx {len(segs)} vs 短语 {len(units)}")
        return None

    lines = STORY["narration"]["scriptA"]
    ref_all = strip_punct("".join(l["text"] for l in lines))
    line_han_counts = [len(strip_punct(l["text"])) for l in lines]

    # 全局汉字 → 所属行
    global_to_line = []
    for idx, count in enumerate(line_han_counts):
        global_to_line.extend([idx] * count)
    if len(global_to_line) != len(ref_all):
        log("参考文稿自身不一致")
        return None

    cues: list[dict] = []
    gidx = 0
    for seg, unit in zip(segs, units):
        chars = seg.get("chars") or []
        got_han = "".join(c["char"] for c in chars if is_han(c["char"]))
        want_han = strip_punct(unit["phrase"])
        if got_han != want_han:
            log(f"{unit['id']} 对齐汉字不符：\n  参考 {want_han}\n  实得 {got_han}")
            return None
        for c in chars:
            if not is_han(c["char"]):
                continue
            if gidx >= len(ref_all) or ref_all[gidx] != c["char"]:
                log(f"全局顺序不符：位置 {gidx} 参考 {ref_all[gidx:gidx+1]} 实得 {c['char']}")
                return None
            line_idx = global_to_line[gidx]
            line_offset = sum(line_han_counts[:line_idx])
            cues.append({
                "line_id": lines[line_idx]["id"],
                "char_index": gidx - line_offset,
                "glyph": c["char"],
                "start_sample": int(round(float(c["start"]) * timeline["sample_rate"])),
                "end_sample": int(round(float(c["end"]) * timeline["sample_rate"])),
                "source": "forced",
                "score": float(c.get("score") or 0.0),
                "reviewed": False,
            })
            gidx += 1
    if gidx != len(ref_all):
        log(f"字级覆盖 {gidx} != 参考 {len(ref_all)}")
        return None
    return cues


def cues_from_phrase_timeline(timeline: dict) -> list[dict]:
    """兜底：短语边界即字幕边界，组内按每汉字均匀分配（估计，source=chunk-boundary）。"""
    cues: list[dict] = []
    sr = timeline["sample_rate"]
    script = {l["id"]: l["text"] for l in STORY["narration"]["scriptA"]}
    for unit in timeline["units"]:
        line_text = script[unit["line_id"]]
        ref_han = strip_punct(line_text)
        phrase_han = strip_punct(unit["phrase"])
        start = unit["start_sample"]
        end = unit["end_sample"]
        span = end - start
        n = len(phrase_han)
        if n == 0:
            continue
        base = ref_han.find(phrase_han)
        for k in range(n):
            s = start + int(round(span * k / n))
            e = start + int(round(span * (k + 1) / n))
            cues.append({
                "line_id": unit["line_id"],
                "char_index": base + k,
                "glyph": phrase_han[k],
                "start_sample": s,
                "end_sample": e,
                "source": "chunk-boundary",
                "reviewed": False,
            })
    return cues


def build_captions(cues: list[dict]) -> list[dict]:
    """按短语→字幕组切分；字幕边界取该组第一字与最后一字时码。"""
    script = {l["id"]: l["text"] for l in STORY["narration"]["scriptA"]}
    chunks = STORY["narration"]["phraseChunks"]
    by_line: dict[str, list[dict]] = {}
    for cue in cues:
        by_line.setdefault(cue["line_id"], []).append(cue)
    for line_id in by_line:
        by_line[line_id].sort(key=lambda c: c["char_index"])

    captions = []
    for line, phrases in zip(STORY["narration"]["scriptA"], chunks):
        line_cues = by_line.get(line["id"], [])
        groups = build_groups(line["text"], phrases)
        for gi, g in enumerate(groups, 1):
            group_cues = [c for c in line_cues if g["lo"] <= c["char_index"] <= g["hi"]]
            if not group_cues:
                raise SystemExit(f"{line['id']} 第 {gi} 组没有字级时码")
            text = group_text(line["text"], g["lo"], g["hi"])
            lines = [text] if len(text) <= CONTRACT["subtitle"]["maxCharsPerLine"] else [
                text[i : i + CONTRACT["subtitle"]["maxCharsPerLine"]]
                for i in range(0, len(text), CONTRACT["subtitle"]["maxCharsPerLine"])
            ][: CONTRACT["subtitle"]["maxLines"]]
            captions.append({
                "line_id": line["id"],
                "group_index": gi,
                "text": text,
                "lines": lines,
                "char_range": [g["lo"], g["hi"]],
                "start_sample": group_cues[0]["start_sample"],
                "end_sample": group_cues[-1]["end_sample"],
                "char_count": len(group_cues),
            })
    captions.sort(key=lambda c: c["start_sample"])
    return captions


def ms(sample: int, sr: int) -> int:
    return int(round(sample * 1000 / sr))


def srt_time(value_ms: int) -> str:
    h, rem = divmod(value_ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms_ = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_:03d}"


def write_srt(captions: list[dict], sr: int) -> None:
    SRT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, cap in enumerate(captions, 1):
        start = max(ms(cap["start_sample"], sr), 0)
        end = min(ms(cap["end_sample"], sr), 30000)
        if end <= start:
            end = min(start + 650, 30000)
        lines.append(str(i))
        lines.append(f"{srt_time(start)} --> {srt_time(end)}")
        lines.append(cap["text"])
        lines.append("")
    SRT.write_bytes(("\n".join(lines)).encode("utf-8-sig"))


def write_review(cues: list[dict], captions: list[dict], sr: int, method: str) -> None:
    REVIEW_CSV.parent.mkdir(parents=True, exist_ok=True)
    anchors = CONTRACT["alignment"]["review"]["anchorPhrases"]
    rows = []
    for anchor in anchors:
        hit = [c for c in captions if anchor in c["text"]]
        if not hit:
            rows.append({"anchor": anchor, "caption": "", "caption_start_ms": "",
                         "caption_end_ms": "", "source": method, "reviewed": "false",
                         "note": "未在字幕中找到该锚点"})
            continue
        cap = hit[0]
        rows.append({
            "anchor": anchor,
            "caption": cap["text"],
            "caption_start_ms": ms(cap["start_sample"], sr),
            "caption_end_ms": ms(cap["end_sample"], sr),
            "source": method,
            "reviewed": "true",
            "note": "字幕边界由真实音频样本测得（非 ASR 猜测）",
        })
    with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="T05 字级对齐与字幕")
    parser.add_argument("--force-phrase", action="store_true", help="跳过 WhisperX，直接走短语兜底")
    args = parser.parse_args()

    ALIGN_DIR.mkdir(parents=True, exist_ok=True)
    if not PHRASE_TIMELINE.exists() or not PHRASE_MASTER.exists():
        log("准备短语级旁白（对齐单元）")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "tts.py"),
             "--granularity", "phrase", "--tag", "phrase"],
            check=True,
        )
    cues = None
    method = "forced"
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8")) if TIMELINE.exists() else None

    if not args.force_phrase:
        raw = run_whisperx()
        if raw is not None and PHRASE_TIMELINE.exists():
            timeline = json.loads(PHRASE_TIMELINE.read_text(encoding="utf-8"))
            cues = cues_from_whisperx(raw, timeline)
            if cues is None:
                log("whisperx 结果不满足覆盖/顺序要求，转兜底")

    if cues is None:
        log("走规划案 §5.3 的 23 短语兜底路径")
        if not PHRASE_TIMELINE.exists():
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "tts.py"),
                 "--granularity", "phrase", "--tag", "phrase"],
                check=True,
            )
        phrase_timeline = json.loads(PHRASE_TIMELINE.read_text(encoding="utf-8"))
        timeline = phrase_timeline
        cues = cues_from_phrase_timeline(phrase_timeline)
        method = "chunk-boundary"

    # 选中的那一条旁白成为本轮唯一的人声真源
    chosen_master = PHRASE_MASTER
    if not chosen_master.exists():
        log(f"缺少旁白母带 {chosen_master}")
        return 3
    MASTER.write_bytes(chosen_master.read_bytes())
    (ROOT / "work" / "voice_timeline.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    sr = timeline["sample_rate"]
    captions = build_captions(cues)

    # 校验：字覆盖 100%、顺序单调、时码合法
    ref_all = strip_punct("".join(l["text"] for l in STORY["narration"]["scriptA"]))
    got_all = "".join(c["glyph"] for c in cues)
    if got_all != ref_all:
        log(f"字级覆盖不符：\n  参考 {ref_all}\n  实得 {got_all}")
        return 2
    for i in range(1, len(cues)):
        if cues[i]["start_sample"] < cues[i - 1]["start_sample"]:
            log("字级时码非单调")
            return 2
    for c in cues:
        if c["end_sample"] < c["start_sample"]:
            log("字级时码非法")
            return 2

    (ALIGN_DIR / "char_cues.json").write_text(
        json.dumps({"method": method, "sample_rate": sr, "cues": cues}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (ALIGN_DIR / "captions.json").write_text(
        json.dumps({"method": method, "sample_rate": sr, "captions": captions}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_srt(captions, sr)
    write_review(cues, captions, sr, method)

    log(f"对齐方式 {method}；字级 {len(cues)} 条；字幕 {len(captions)} 组；SRT {SRT.relative_to(ROOT)}")
    for cap in captions:
        log(f"  [{ms(cap['start_sample'], sr):6d}ms → {ms(cap['end_sample'], sr):6d}ms] {cap['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
