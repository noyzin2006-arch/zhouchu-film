"""T06 · 配乐生成与混音。

规划案 §5.7：
  - 第一候选：mcode-tools connector__matrix__batch_text_to_music（纯器乐，无歌词）
  - 兜底（必实现）：NumPy 48k 立体声程序合成，92 BPM 五声音阶，四段能量弧线
  - 人声：loudnorm 两通，I=-16 / LRA=7 / TP=-1.8
  - 配乐：独立归一化至 -25 LUFS，再按每个字级人声窗口把底乐压到比人声低 18dB（至少 12dB）
  - 混音：真峰 ≤ -1.5 dBTP，超限则每次降 0.5dB，最多 4 轮

产物：work/bgm.wav / work/voice_norm.wav / work/final_mix.wav
      reports/audio-measure.json / reports/rights.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((ROOT / "film" / "audio-contract.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))

WORK = ROOT / "work"
BGM_WAV = WORK / "bgm.wav"
VOICE_NORM = WORK / "voice_norm.wav"
MIX_WAV = WORK / "final_mix.wav"
MEASURE = ROOT / "reports" / "audio-measure.json"
RIGHTS = ROOT / "reports" / "rights.md"
ALIGN_CUES = WORK / "align" / "char_cues.json"

SR = CONTRACT["timeline"]["sampleRate"]
DURATION = TOKENS["video"]["durationSeconds"]
SEED = CONTRACT["music"]["proceduralFallback"]["seed"]
BPM = CONTRACT["music"]["proceduralFallback"]["bpm"]
SCALE = CONTRACT["music"]["proceduralFallback"]["scale"]
FREQ = {"A3": 220.00, "C4": 261.63, "D4": 293.66, "E4": 329.63, "G4": 392.00}
ENERGY = CONTRACT["music"]["proceduralFallback"]["energyBySegment"]
FADE_OUT = CONTRACT["music"]["proceduralFallback"]["fadeOutSec"]

MIX = CONTRACT["mix"]
DB_18 = 10 ** (MIX["bedRmsBelowVoiceDb"] / 20.0)
DB_12 = 10 ** (MIX["bedRmsBelowVoiceDbMin"] / 20.0)


def log(msg: str) -> None:
    print(f"[mix] {msg}", flush=True)


def mulberry32(seed: int):
    state = seed & 0xFFFFFFFF

    def nxt() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = (t ^ (t >> 15)) * (1 | t)
        t = (t + ((t ^ (t >> 7)) * (61 | t))) & 0xFFFFFFFF
        t ^= t >> 14
        return (t & 0x7FFFFFFF) / 0x7FFFFFFF

    return nxt


def energy_at(t: float) -> float:
    for start, end, e in ENERGY:
        if start <= t < end:
            return e
    return ENERGY[-1][2]


def synth_pluck(freq: float, dur: float, gain: float, decay: float) -> np.ndarray:
    t = np.arange(int(SR * dur), dtype=np.float64) / SR
    env = np.exp(-t / decay)
    body = (
        np.sin(2 * np.pi * freq * t)
        + 0.42 * np.sin(2 * np.pi * freq * 2.01 * t)
        + 0.18 * np.sin(2 * np.pi * freq * 3.02 * t)
    )
    # 轻微起音噪声，像指甲触弦
    attack = np.clip(t / 0.004, 0, 1)
    noise = (np.random.default_rng(int(freq * 100)).normal(0, 1, t.size)) * np.exp(-t / 0.01) * 0.08
    return (body * env * attack + noise) * gain


def synth_drum(dur: float, gain: float) -> np.ndarray:
    t = np.arange(int(SR * dur), dtype=np.float64) / SR
    f0, f1 = 82.0, 46.0
    k = (f1 / f0) ** (1.0 / max(dur, 1e-6))
    phase = 2 * np.pi * f0 * (k ** t - 1) / np.log(k)
    body = np.sin(phase) * np.exp(-t / 0.09)
    click = np.random.default_rng(7).normal(0, 1, t.size) * np.exp(-t / 0.006) * 0.5
    return (body + click) * gain


def synth_wood(gain: float) -> np.ndarray:
    dur = 0.07
    t = np.arange(int(SR * dur), dtype=np.float64) / SR
    noise = np.random.default_rng(11).normal(0, 1, t.size)
    # 单极点低通 ≈ 6kHz
    alpha = 1.0 - np.exp(-2 * np.pi * 6000.0 / SR)
    filtered = np.empty_like(noise)
    acc = 0.0
    for i, x in enumerate(noise):
        acc += alpha * (x - acc)
        filtered[i] = acc
    return filtered * np.exp(-t / 0.018) * gain


def synth_xiao(freq: float, dur: float, gain: float) -> np.ndarray:
    t = np.arange(int(SR * dur), dtype=np.float64) / SR
    env = np.minimum(t / 0.18, 1.0) * np.minimum((dur - t) / 0.32, 1.0)
    tone = (
        np.sin(2 * np.pi * freq * t)
        + 0.24 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.1 * np.sin(2 * np.pi * freq * 3 * t)
    )
    breath = np.random.default_rng(3).normal(0, 1, t.size) * 0.02
    return (tone + breath) * np.clip(env, 0, 1) * gain


def synthesize_bgm() -> np.ndarray:
    """规划案 §5.7 的程序合成兜底（必实现）。"""
    rng = mulberry32(SEED)
    total = int(SR * DURATION)
    buf = np.zeros(total, dtype=np.float64)
    beat = 60.0 / BPM
    bar = beat * 4
    n_beats = int(DURATION / beat) + 1

    scale_idx = list(range(len(SCALE)))
    for b in range(n_beats):
        t0 = b * beat
        if t0 >= DURATION:
            break
        e = energy_at(t0)
        bar_beat = b % 4

        # 低鼓：每小节 1、3 拍
        if bar_beat in (0, 2):
            d = synth_drum(0.22, 0.34 * e)
            start = int(t0 * SR)
            end = min(start + d.size, total)
            buf[start:end] += d[: end - start]

        # 木击：急段加花
        if 12.0 <= t0 < 20.0 and bar_beat in (1, 3) and rng() > 0.35:
            d = synth_wood(0.1 * e)
            start = int(t0 * SR)
            end = min(start + d.size, total)
            buf[start:end] += d[: end - start]

        # 拨弦：每拍按能量决定出现概率
        if rng() < 0.42 + 0.5 * e:
            step = scale_idx[int(rng() * len(scale_idx))]
            octave = 1.0 if rng() > 0.72 else 0.5
            freq = FREQ[SCALE[step]] * octave
            d = synth_pluck(freq, 1.1, 0.16 * e, 0.18)
            start = int(t0 * SR)
            end = min(start + d.size, total)
            buf[start:end] += d[: end - start]

        # 低音根音：每小节一次
        if bar_beat == 0:
            d = synth_pluck(FREQ["A3"] * 0.5, 1.6, 0.13 * e, 0.42)
            start = int(t0 * SR)
            end = min(start + d.size, total)
            buf[start:end] += d[: end - start]

    # 箫：稀疏段（20–26s）与收束（26–30s）的持续声
    for t0, dur, note in ((20.0, 5.4, "E4"), (25.6, 3.8, "G4")):
        d = synth_xiao(FREQ[note], dur, 0.085)
        start = int(t0 * SR)
        end = min(start + d.size, total)
        buf[start:end] += d[: end - start]

    # 水声：≤ -32dBFS
    water = np.random.default_rng(29).normal(0, 1, total)
    alpha = 1.0 - np.exp(-2 * np.pi * 900.0 / SR)
    acc = 0.0
    filt = np.empty_like(water)
    for i, x in enumerate(water):
        acc += alpha * (x - acc)
        filt[i] = acc
    filt = filt / max(np.max(np.abs(filt)), 1e-9) * (10 ** (-32 / 20))
    buf += filt

    # 尾部 1.2s cosine 淡出
    fade_n = int(SR * FADE_OUT)
    if fade_n < total:
        ramp = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_n)))
        buf[-fade_n:] *= ramp

    peak = np.max(np.abs(buf))
    if peak > 0:
        buf = buf / peak * 0.7
    return buf


def write_stereo_wav(path: pathlib.Path, mono: np.ndarray, gain_db: float = 0.0) -> None:
    """左右声道做极小延时差，制造宽度；不改变单声道内容。"""
    g = 10 ** (gain_db / 20.0)
    left = mono * g
    right = np.roll(mono, 37) * g
    stereo = np.stack([left, right], axis=1)
    pcm = np.clip(stereo, -1.0, 1.0)
    data = (pcm * 32767.0).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
         "-c:a", "pcm_s16le", str(path)],
        input=data.tobytes(), check=True,
    )


def read_wav_mono(path: pathlib.Path) -> tuple[np.ndarray, int]:
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
         "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        stdout=subprocess.PIPE, check=True,
    )
    data = np.frombuffer(out.stdout, dtype="<f4").astype(np.float64)
    return data, SR


def loudnorm_two_pass(src: pathlib.Path, dst: pathlib.Path, i: float, lra: float, tp: float) -> dict:
    first = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
         f"loudnorm=I={i}:LRA={lra}:TP={tp}:print_format=json",
         "-f", "null", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    measured = {}
    for blob in (first.stderr, first.stdout):
        start = blob.rfind("{")
        end = blob.rfind("}")
        if start >= 0 and end > start:
            try:
                measured = json.loads(blob[start : end + 1])
                break
            except json.JSONDecodeError:
                continue
    if not measured:
        raise SystemExit("loudnorm 第一遍拿不到 measured_*")
    filt = (
        f"loudnorm=I={i}:LRA={lra}:TP={tp}:"
        f"measured_I={measured['input_i']}:measured_LRA={measured['input_lra']}:"
        f"measured_TP={measured['input_tp']}:measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:linear=true:print_format=summary"
    )
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
         "-af", filt, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
        check=True,
    )
    return measured


def integrated_lufs(path: pathlib.Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
         "-f", "null", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    text = proc.stderr
    tail = text[-2600:]
    i_val = t_val = None
    for line in tail.splitlines():
        line = line.strip()
        if line.startswith("I:"):
            try:
                i_val = float(line.split()[1])
            except (IndexError, ValueError):
                pass
        if line.startswith("Peak:"):
            try:
                t_val = float(line.split()[1])
            except (IndexError, ValueError):
                pass
    if i_val is None:
        return float("nan")
    return i_val


def true_peak_db(path: pathlib.Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
         "-f", "null", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    tail = proc.stderr[-2600:]
    for line in tail.splitlines():
        line = line.strip()
        if line.startswith("Peak:"):
            try:
                return float(line.split()[1])
            except (IndexError, ValueError):
                continue
    return float("nan")


def voice_windows() -> list[tuple[int, int]]:
    """人声有声窗口（字级时码的外包络，按 40ms 步长合并）。"""
    if not ALIGN_CUES.exists():
        return []
    data = json.loads(ALIGN_CUES.read_text(encoding="utf-8"))
    cues = data["cues"]
    if not cues:
        return []
    windows = []
    cur_start, cur_end = cues[0]["start_sample"], cues[0]["end_sample"]
    for c in cues[1:]:
        if c["start_sample"] - cur_end <= int(SR * 0.04):
            cur_end = max(cur_end, c["end_sample"])
        else:
            windows.append((cur_start, cur_end))
            cur_start, cur_end = c["start_sample"], c["end_sample"]
    windows.append((cur_start, cur_end))
    return windows


def rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(x ** 2)))


def build_envelope(windows: list[tuple[int, int]], voice: np.ndarray, bed: np.ndarray,
                   length: int, target_ratio: float) -> tuple[np.ndarray, list[float]]:
    """真正的 ducking：人声窗口内底乐降到「比人声低 target_ratio dB」，间隙放开。

    每个窗口按实测 RMS 求所需增益；边缘 120ms 平滑（attack/release）。
    返回 (逐样本增益包络, 各窗口所需增益列表)。
    """
    gains = np.ones(length, dtype=np.float64)
    per_window = []
    for start, end in windows:
        s0 = max(0, min(length, start))
        e0 = max(0, min(length, end))
        if e0 <= s0:
            per_window.append(1.0)
            continue
        v = rms(voice[s0:e0])
        b = rms(bed[s0:e0])
        if v <= 1e-9 or b <= 1e-12:
            per_window.append(1.0)
            continue
        need = (v / b) / target_ratio
        need = float(min(max(need, 0.0), 1.0))
        per_window.append(need)
        gains[s0:e0] = need
    # 间隙处保持 1.0（音乐托底），窗口边界做平滑
    attack = int(SR * MIX["duckAttackMs"] / 1000)
    release = int(SR * MIX["duckReleaseMs"] / 1000)
    if attack > 1:
        kernel = np.ones(attack) / attack
        gains = np.convolve(gains, kernel, mode="same")
    if release > 1:
        kernel = np.ones(release) / release
        gains = np.convolve(gains, kernel, mode="same")
    return np.clip(gains, 0.0, 1.0), per_window


def main() -> int:
    parser = argparse.ArgumentParser(description="T06 配乐与混音")
    parser.add_argument("--skip-generator", action="store_true")
    args = parser.parse_args()

    WORK.mkdir(parents=True, exist_ok=True)
    VOICE_NORM.parent.mkdir(parents=True, exist_ok=True)

    # ---------- 1. 配乐 ----------
    generator_candidates = []
    if not args.skip_generator:
        log("尝试音乐生成服务（纯器乐，最多 3 条）")
        gen = CONTRACT["music"]["generator"]
        try:
            proc = subprocess.run(
                ["mcode-tools", "connector", "call", "connector__matrix__batch_text_to_music",
                 "--args", json.dumps({"requests": [{"prompt": gen["prompt"]} for _ in range(3)]},
                                      ensure_ascii=False)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600,
            )
            out = proc.stdout
            start = out.find("{")
            if start >= 0:
                data = json.loads(out[start:])
                for item in data.get("success_items", []) or []:
                    generator_candidates.append({
                        "node_id": item.get("node_id"),
                        "file_name": item.get("file_name"),
                        "rights_status": "account-terms-unverified",
                    })
        except Exception as exc:  # noqa: BLE001
            log(f"音乐生成服务调用异常：{exc}")
        log(f"音乐生成候选 {len(generator_candidates)} 条（仅作备选记录）")

    log("使用程序合成配乐（92 BPM 五声音阶，权利清晰、可重复）")
    bgm = synthesize_bgm()
    write_stereo_wav(BGM_WAV, bgm)

    # ---------- 2. 人声归一化 ----------
    voice_src = WORK / "voice_master.wav"
    if not voice_src.exists():
        raise SystemExit("缺少 work/voice_master.wav，先跑 tts.py")
    ln = MIX["voiceLoudnorm"]
    measured = loudnorm_two_pass(voice_src, VOICE_NORM, ln["I"], ln["LRA"], ln["TP"])
    voice_lufs = integrated_lufs(VOICE_NORM)
    log(f"人声归一化：measured_I={measured.get('input_i')} → {voice_lufs:.2f} LUFS")

    # ---------- 3. 配乐归一化到 -25 LUFS ----------
    bgm_raw = WORK / "bgm_raw.wav"
    write_stereo_wav(bgm_raw, bgm)
    bgm_norm = WORK / "bgm_norm.wav"
    loudnorm_two_pass(bgm_raw, bgm_norm, MIX["bgmLufs"], 7, -3.0)

    # ---------- 4. 按人声窗口压制底乐 ----------
    bgm_mono, _ = read_wav_mono(bgm_norm)
    voice_mono, _ = read_wav_mono(VOICE_NORM)
    length = max(len(bgm_mono), len(voice_mono))
    bgm_mono = np.pad(bgm_mono, (0, max(0, length - len(bgm_mono))))
    voice_mono = np.pad(voice_mono, (0, max(0, length - len(voice_mono))))

    windows = voice_windows()
    if not windows:
        raise SystemExit("缺少字级时码，无法计算人声窗口")
    target_ratio = 10 ** (MIX["bedRmsBelowVoiceDb"] / 20.0)
    env, _ = build_envelope(windows, voice_mono, bgm_mono, length, target_ratio)
    ducked = bgm_mono * env

    # 复核：逐窗测量人声/底乐 RMS 差；不足 12dB 则整体再压
    def measure_ratios(bed: np.ndarray) -> list[float]:
        out = []
        for start, end in windows:
            v = rms(voice_mono[start:end])
            b = rms(bed[start:end])
            if v > 1e-9 and b > 1e-12:
                out.append(float(20 * np.log10(v / b)))
            elif v > 1e-9:
                out.append(99.0)
        return out

    ratios = measure_ratios(ducked)
    if ratios and min(ratios) < MIX["bedRmsBelowVoiceDbMin"]:
        need_db = MIX["bedRmsBelowVoiceDbMin"] - min(ratios) + 0.5
        scale = 10 ** (-need_db / 20.0)
        ducked = ducked * scale
        log(f"底乐整体再压 {need_db:.2f} dB 以满足声区差 ≥ {MIX['bedRmsBelowVoiceDbMin']} dB")
        ratios = measure_ratios(ducked)

    mix = voice_mono + ducked
    applied_gain_db = 0.0
    rounds = 0
    # 真峰（含采样间峰值）必须实测，不能只看样本峰值
    while True:
        write_stereo_wav(MIX_WAV, mix * (10 ** (applied_gain_db / 20.0)))
        tp = true_peak_db(MIX_WAV)
        if tp <= MIX["truePeakMaxDb"] or rounds >= MIX["mixDownMaxRounds"]:
            break
        applied_gain_db -= MIX["mixDownStepDb"]
        rounds += 1
        log(f"真峰 {tp:.2f} dBTP 超限，降 {MIX['mixDownStepDb']} dB 后重测（第 {rounds} 轮）")

    # ---------- 5. 复核测量 ----------
    final_lufs = integrated_lufs(MIX_WAV)
    final_tp = true_peak_db(MIX_WAV)
    voice_tp = true_peak_db(VOICE_NORM)
    window_rows = []
    mix_mono, _ = read_wav_mono(MIX_WAV)
    for idx, (start, end) in enumerate(windows, 1):
        v = rms(voice_mono[start:end])
        b = rms(ducked[start:end])
        window_rows.append({
            "index": idx,
            "start_ms": int(round(start * 1000 / SR)),
            "end_ms": int(round(end * 1000 / SR)),
            "voice_rms_db": round(float(20 * np.log10(max(v, 1e-12))), 2),
            "bed_rms_db": round(float(20 * np.log10(max(b, 1e-12))), 2),
            "difference_db": round(float(20 * np.log10(max(v, 1e-12) / max(b, 1e-12))), 2),
        })

    measure = {
        "sample_rate": SR,
        "voice": {
            "source": "work/voice_master.wav",
            "integrated_lufs": round(float(voice_lufs), 2),
            "target_lufs": ln["I"],
            "tolerance": 1,
            "true_peak_db": round(float(voice_tp), 2),
            "lufs_pass": bool(abs(float(voice_lufs) - ln["I"]) <= 1),
        },
        "bed": {
            "source": "work/bgm_norm.wav",
            "target_lufs": MIX["bgmLufs"],
            "rights": "procedurally synthesized in project",
            "generator_candidates": generator_candidates,
        },
        "mix": {
            "source": "work/final_mix.wav",
            "integrated_lufs": round(float(final_lufs), 2),
            "true_peak_db": round(float(final_tp), 2),
            "true_peak_limit_db": MIX["truePeakMaxDb"],
            "applied_gain_db": round(float(applied_gain_db), 2),
            "downmix_rounds": rounds,
            "peak_pass": bool(float(final_tp) <= MIX["truePeakMaxDb"] + 0.05),
        },
        "voice_windows": window_rows,
        "worst_window_difference_db": round(float(min(ratios)), 2) if ratios else None,
        "window_difference_pass": bool(ratios) and float(min(ratios)) >= MIX["bedRmsBelowVoiceDbMin"],
    }
    MEASURE.parent.mkdir(parents=True, exist_ok=True)
    MEASURE.write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"人声 {float(voice_lufs):.2f} LUFS / TP {float(voice_tp):.2f} dBTP")
    log(f"混音 {float(final_lufs):.2f} LUFS / TP {float(final_tp):.2f} dBTP（限 -1.5）")
    log(f"最差声区差 {measure['worst_window_difference_db']} dB（下限 12）")
    log(f"测量写入 {MEASURE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
