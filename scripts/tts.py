"""T04 · 中文旁白合成与声轨时间线。

豆包 TTS（规划案 §5.4，已在本机跑通）：
    POST https://openspeech.bytedance.com/api/v1/tts
    Header: Authorization: Bearer;<token>   ← 分号，不是空格
    Body  : app:{appid,token,cluster} + request:{reqid,text} + audio:{voice_type,encoding}

产出：
    work/voice/<id>.wav        48k 单声道 PCM
    work/voice_master.wav      按真实样本拼好的整条旁白
    work/voice_timeline.json   每个句/短语的 start_sample / end_sample（唯一时间权威）

粒度：
    --granularity line    8 句（V1–V8），用于 WhisperX 强制对齐的主路径
    --granularity phrase  23 组短语，字幕边界与音频边界完全重合（兜底路径）
"""
from __future__ import annotations

import argparse
import array
import json
import os
import pathlib
import subprocess
import sys
import uuid
import urllib.request
import wave
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((ROOT / "film" / "audio-contract.json").read_text(encoding="utf-8"))

VOICE_DIR = ROOT / "work" / "voice"
MASTER = ROOT / "work" / "voice_master.wav"
TIMELINE = ROOT / "work" / "voice_timeline.json"

SR = CONTRACT["timeline"]["sampleRate"]
HEAD_MS = CONTRACT["timeline"]["headPaddingMs"]
LINE_GAP_MS = CONTRACT["timeline"]["lineGapMs"]
PHRASE_GAP_MS = CONTRACT["timeline"]["phraseGapMs"]
TRIM_DBFS = CONTRACT["timeline"]["silenceTrimThresholdDbfs"]
MIN_TAIL_MS = CONTRACT["timeline"]["minTailSilenceMs"]
VOICE_MUST_END_BY = CONTRACT["timeline"]["voiceMustEndBySec"]
MAX_TEMPO = CONTRACT["timeline"]["maxTempoFactor"]
TTS = CONTRACT["tts"]


def log(msg: str) -> None:
    print(f"[tts] {msg}", flush=True)


def env_or_die(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise SystemExit(f"缺少环境变量 {name}")
    return value


def synthesize(text: str, out_path: pathlib.Path) -> bool:
    """调一次豆包 TTS，落地 mp3。失败返回 False（不打印任何凭据）。"""
    app_id = env_or_die(TTS["env"]["app_id"])
    token = env_or_die(TTS["env"]["access_token"])
    cluster = env_or_die(TTS["env"]["cluster"])
    voice_type = env_or_die(TTS["env"]["voice_type"])

    reqid = str(uuid.uuid4())
    payload = {
        "app": {"appid": app_id, "token": token, "cluster": cluster},
        "user": {"uid": "zhouchu-film"},
        "audio": {"voice_type": voice_type, "encoding": "mp3", "speed_ratio": TTS["speedRatio"]},
        "request": {"reqid": reqid, "text": text, "text_type": "plain", "operation": "query"},
    }
    req = urllib.request.Request(
        TTS["endpoint"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Api-Request-Id": reqid,
            "Authorization": f"Bearer;{token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        log(f"TTS 请求异常: {exc}")
        return False
    if body.get("code") != TTS["successCode"]:
        log(f"TTS 返回 code={body.get('code')} message={body.get('message')}")
        return False
    import base64

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(body["data"]))
    return out_path.exists() and out_path.stat().st_size > 0


def to_pcm_wav(src: pathlib.Path, dst: pathlib.Path) -> bool:
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src), "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(dst),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        log(f"转 PCM 失败: {proc.stderr.strip()[:300]}")
        return False
    return dst.exists()


def read_wav(path: pathlib.Path) -> array.array:
    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1 and wf.getsampwidth() == 2
        data = array.array("h")
        data.frombytes(wf.readframes(wf.getnframes()))
        if sys.byteorder == "big":
            data.byteswap()
        return data


def write_wav(path: pathlib.Path, samples: array.array) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        if sys.byteorder == "big":
            clone = array.array("h", samples)
            clone.byteswap()
            wf.writeframes(clone.tobytes())
        else:
            wf.writeframes(samples.tobytes())


def trim_silence(samples: array.array) -> tuple[array.array, int, int]:
    """裁掉首尾静音；返回 (裁后样本, 首样本偏移, 尾样本偏移)。

    阈值 -48dBFS → 幅度 16bit 约 1283。保留至少 MIN_TAIL_MS 的自然句末余响。
    """
    thresh = 1283
    n = len(samples)
    start = 0
    while start < n and abs(samples[start]) < thresh:
        start += 1
    end = n
    keep_tail = int(SR * MIN_TAIL_MS / 1000)
    floor = n - keep_tail
    while end > floor and abs(samples[end - 1]) < thresh:
        end -= 1
    if start >= end:
        return array.array("h", samples), 0, n
    return array.array("h", samples[start:end]), start, end


def macos_say(text: str, out_path: pathlib.Path) -> bool:
    """兜底发音：macOS say -v Tingting（声型与正式播音有差异，须写入 known-limit）。"""
    cmd = ["say", "-v", "Tingting", "-o", str(out_path.with_suffix(".aiff")), text]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        log(f"say 失败: {proc.stderr.strip()[:200]}")
        return False
    conv = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
         str(out_path.with_suffix(".aiff")), "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le",
         str(out_path.with_suffix(".wav"))],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    return conv.returncode == 0


def build_units(granularity: str) -> list[dict]:
    """产出待合成的单元列表：每项含 id、text、所属台词行。"""
    script = STORY["narration"]["scriptA"]
    units: list[dict] = []
    if granularity == "line":
        for line in script:
            units.append({"id": line["id"], "text": line["text"], "line_id": line["id"],
                          "phrase": line["text"], "chunks": [line["text"]]})
        return units
    chunks = STORY["narration"]["phraseChunks"]
    for line, phrases in zip(script, chunks):
        for idx, phrase in enumerate(phrases, 1):
            units.append({
                "id": f"{line['id']}P{idx}",
                "text": phrase,
                "line_id": line["id"],
                "phrase": phrase,
                "chunks": [phrase],
            })
    return units


def main() -> int:
    parser = argparse.ArgumentParser(description="T04 旁白合成")
    parser.add_argument("--granularity", choices=["line", "phrase"], default="line")
    parser.add_argument("--script", choices=["A", "B"], default="A")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--tag", default=None, help="产物标签，默认与 granularity 相同")
    args = parser.parse_args()

    tag = args.tag or args.granularity
    voice_dir = ROOT / "work" / f"voice_{tag}"
    master_path = ROOT / "work" / f"voice_master_{tag}.wav"
    timeline_path = ROOT / "work" / f"voice_timeline_{tag}.json"

    script_lines = STORY["narration"][f"script{args.script}"]
    units = build_units(args.granularity)
    if args.script == "B":
        # 短稿 B 的短语切分沿用 A 的结构（按行长度比例对齐），保持短语边界可判定
        units = build_units(args.granularity)
        for unit, line in zip(units, script_lines):
            if unit["id"] == line["id"]:
                unit["text"] = line["text"] if args.granularity == "line" else unit["text"]

    voice_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[dict] = []
    for unit in units:
        wav = voice_dir / f"{unit['id']}.wav"
        if wav.exists() and not args.force:
            rendered.append({**unit, "wav": wav, "cached": True})
            continue
        mp3 = voice_dir / f"{unit['id']}.mp3"
        ok = False
        for attempt in range(1, TTS["maxAttempts"] + 1):
            if synthesize(unit["text"], mp3):
                ok = True
                break
            log(f"{unit['id']} 第 {attempt} 次合成失败")
        if not ok:
            log(f"{unit['id']} 远端 TTS 失败，降级 macOS say -v Tingting")
            if not macos_say(unit["text"], wav):
                log(f"{unit['id']} 兜底也失败")
                return 1
            rendered.append({**unit, "wav": wav, "cached": False, "provider": "macos-say"})
            continue
        if not to_pcm_wav(mp3, wav):
            return 1
        rendered.append({**unit, "wav": wav, "cached": False, "provider": "doubao"})

    # 裁静音并按真实样本拼装
    master = array.array("h", [0] * int(SR * HEAD_MS / 1000))
    cursor = len(master)
    gap = PHRASE_GAP_MS if args.granularity == "phrase" else LINE_GAP_MS
    entries = []
    for unit in rendered:
        raw = read_wav(unit["wav"])
        trimmed, head_skip, tail_end = trim_silence(raw)
        start_sample = cursor
        master.extend(trimmed)
        end_sample = cursor + len(trimmed)
        entries.append({
            "id": unit["id"],
            "line_id": unit["line_id"],
            "phrase": unit["phrase"],
            "text": unit["text"],
            "path": str(unit["wav"].relative_to(ROOT)),
            "sample_rate": SR,
            "samples": len(trimmed),
            "start_sample": start_sample,
            "end_sample": end_sample,
            "source_head_trim": head_skip,
            "source_tail_trim": len(raw) - tail_end,
            "provider": unit.get("provider", "doubao"),
        })
        cursor = end_sample + int(SR * gap / 1000)
        master.extend([0] * int(SR * gap / 1000))

    total_samples = cursor - int(SR * gap / 1000)
    voice_end_sec = total_samples / SR
    tempo = 1.0
    if voice_end_sec > VOICE_MUST_END_BY:
        factor = voice_end_sec / CONTRACT["timeline"]["targetVoiceEndSec"]
        if factor <= MAX_TEMPO:
            tempo = factor
            log(f"人声 {voice_end_sec:.3f}s 超限，按 atempo {factor:.4f} 变速")
            raw_master = voice_dir / "_raw_master.wav"
            write_wav(raw_master, master[:total_samples])
            sped = voice_dir / "_sped_master.wav"
            proc = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw_master),
                 "-filter:a", f"atempo={factor:.6f}", "-c:a", "pcm_s16le", str(sped)],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
            )
            if proc.returncode == 0:
                master = read_wav(sped)
                total_samples = len(master)
                voice_end_sec = total_samples / SR
                for e in entries:
                    e["start_sample"] = int(e["start_sample"] / factor)
                    e["end_sample"] = int(e["end_sample"] / factor)
            else:
                log("atempo 失败，保留原始速度")
                tempo = 1.0
        else:
            log(f"人声 {voice_end_sec:.3f}s 超限且变速因子 {factor:.3f} > {MAX_TEMPO}，需改用短稿 B")

    write_wav(master_path, master[:total_samples])
    timeline = {
        "task": "LOOP-001",
        "granularity": args.granularity,
        "script": args.script,
        "sample_rate": SR,
        "head_padding_ms": HEAD_MS,
        "gap_ms": gap,
        "tempo_factor": round(tempo, 6),
        "total_samples": total_samples,
        "voice_end_sec": round(voice_end_sec, 4),
        "voice_must_end_by_sec": VOICE_MUST_END_BY,
        "within_limit": voice_end_sec <= VOICE_MUST_END_BY,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "units": entries,
    }
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"合成完成：{len(entries)} 单元，人声结束 {voice_end_sec:.3f}s "
        f"（上限 {VOICE_MUST_END_BY}s，{'达标' if timeline['within_limit'] else '超限'}）")
    log(f"master: {master_path.relative_to(ROOT)}  timeline: {timeline_path.relative_to(ROOT)}")
    return 0 if timeline["within_limit"] else 3


if __name__ == "__main__":
    sys.exit(main())
