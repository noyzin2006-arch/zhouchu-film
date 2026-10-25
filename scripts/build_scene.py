"""T07 · 场景编排与合成工程生成。

规划案 §5.6：
  - 镜头边界由**真实字级锚点**导出，不写死预设时长
  - 切镜叠化用 opacity；同轨不重叠 → 每个 clip 独占 track
  - JS 只根据帧时码驱动图层 transform/opacity，不操作媒体播放
  - 粒子位置来自固定 seed 的 mulberry32，可重复
  - 硬字幕由 CaptionCue 数组生成，与 SRT 同源

产物：film/index.html（静态 DOM + 内嵌 #scene-data）、work/scenes.json
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))

CAPTIONS = json.loads((ROOT / "work" / "align" / "captions.json").read_text(encoding="utf-8"))
CUES = json.loads((ROOT / "work" / "align" / "char_cues.json").read_text(encoding="utf-8"))

SCENES_JSON = ROOT / "work" / "scenes.json"
INDEX_HTML = ROOT / "film" / "index.html"

FPS = TOKENS["video"]["fps"]
TOTAL_FRAMES = TOKENS["video"]["frames"]
DURATION = TOKENS["video"]["durationSeconds"]
OVERLAP_FRAMES = 3          # 每侧 0.1s → 叠化总长 0.2s（规划案 180–260ms）
MAX_SHOT_FRAMES = 69       # A04：同一张静图连续出现不得超过 2.3s（2.3s × 30fps）
SEED = 20261025
MOTE_COUNT = 28


def log(msg: str) -> None:
    print(f"[scene] {msg}", flush=True)


def is_han(ch: str) -> bool:
    return "一" <= ch <= "鿿"


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


def phrase_char_index(line_text: str, phrase: str) -> int:
    han = [c for c in line_text if is_han(c)]
    want = [c for c in phrase if is_han(c)]
    for i in range(len(han) - len(want) + 1):
        if han[i : i + len(want)] == want:
            return i
    raise SystemExit(f"锚点短语 {phrase!r} 在 {line_text!r} 中找不到")


def cue_time(line_id: str, char_index: int, cues: list[dict]) -> int:
    for c in cues:
        if c["line_id"] == line_id and c["char_index"] == char_index:
            return c["start_sample"]
    raise SystemExit(f"找不到字级时码 {line_id}#{char_index}")


def sample_to_frame(sample: int, sr: int) -> int:
    return int(round(sample * FPS / sr))


def main() -> int:
    sr = CAPTIONS["sample_rate"]
    cues = CUES["cues"]
    lines = {l["id"]: l["text"] for l in STORY["narration"]["scriptA"]}

    # ---------- 镜位：由真实字级锚点导出 ----------
    scene_specs = []
    for scene in STORY["scenes"]:
        a = scene["anchor"]
        idx = phrase_char_index(lines[a["line_id"]], a["phrase"])
        t_sample = cue_time(a["line_id"], idx, cues) + int(a.get("offset_sec", 0) * sr)
        scene_specs.append({**scene, "_anchor_sample": t_sample})

    # 短语边界（用于把偏长的镜头切成子镜）
    phrase_bounds = []
    for cap in CAPTIONS["captions"]:
        phrase_bounds.append(sample_to_frame(cap["start_sample"], sr))

    frames = []
    for i, spec in enumerate(scene_specs):
        start = sample_to_frame(spec["_anchor_sample"], sr)
        if i + 1 < len(scene_specs):
            end = sample_to_frame(scene_specs[i + 1]["_anchor_sample"], sr)
        else:
            end = TOTAL_FRAMES
        start = max(0, min(start, TOTAL_FRAMES - 1))
        end = max(start + 1, min(end, TOTAL_FRAMES))
        frames.append({"start": start, "end": end})

    # S01 必须从 0 起（片头钩子）
    if frames[0]["start"] > 0:
        delta = frames[0]["start"]
        for f in frames:
            f["start"] -= delta
            f["end"] -= delta
        frames[-1]["end"] = TOTAL_FRAMES
        log(f"片头锚点前移 {delta} 帧，使 S01 从 0 开始")

    # ---------- 插入镜 ----------
    inserts_out = []
    for spec, f in zip(scene_specs, frames):
        for ins in spec.get("inserts", []):
            idx = phrase_char_index(lines[ins["line_id"]], ins["phrase"])
            t_sample = cue_time(ins["line_id"], idx, cues)
            start = sample_to_frame(t_sample + int(ins.get("offset_sec", 0) * sr), sr)
            start = max(f["start"], min(start, f["end"] - 2))
            end = min(start + int(round(ins["duration_sec"] * FPS)), f["end"])
            inserts_out.append({
                "image_id": ins["image_id"],
                "dom_id": f"insert-{ins['image_id']}",
                "start_frame": start,
                "end_frame_exclusive": end,
            })

    # ---------- 字幕 ----------
    caption_out = []
    for i, cap in enumerate(CAPTIONS["captions"], 1):
        start = sample_to_frame(cap["start_sample"], sr)
        end = sample_to_frame(cap["end_sample"], sr)
        min_frames = int(round(TOKENS["caption"]["minVisibleMs"] * FPS / 1000))
        if end - start < min_frames:
            end = min(start + min_frames, TOTAL_FRAMES)
        caption_out.append({
            "id": f"C{i:02d}",
            "dom_id": f"caption-{i:02d}",
            "start_frame": start,
            "end_frame_exclusive": min(end, TOTAL_FRAMES),
            "text": cap["text"],
            "lines": cap["lines"],
            "line_id": cap["line_id"],
        })
    # 同轨不重叠：逐个裁掉与下一个重叠的部分
    for i in range(len(caption_out) - 1):
        if caption_out[i]["end_frame_exclusive"] > caption_out[i + 1]["start_frame"]:
            caption_out[i]["end_frame_exclusive"] = caption_out[i + 1]["start_frame"]
    caption_out = [c for c in caption_out if c["end_frame_exclusive"] > c["start_frame"]]

    # ---------- 墨点粒子（固定 seed） ----------
    rng = mulberry32(SEED)
    motes = []
    for i in range(MOTE_COUNT):
        scene = scene_specs[int(rng() * len(scene_specs))]
        f = frames[int(rng() * len(frames))]
        span = max(f["end"] - f["start"], 4)
        start = f["start"] + int(rng() * span * 0.7)
        end = min(f["end"], start + int(span * (0.3 + rng() * 0.5)))
        if end <= start:
            end = min(start + 6, f["end"])
        motes.append({
            "dom_id": f"mote-{i:02d}",
            "start_frame": start,
            "end_frame_exclusive": end,
            "x0": round(-40 + rng() * 1160, 1),
            "y0": round(200 + rng() * 1500, 1),
            "x1": round(-40 + rng() * 1160, 1),
            "y1": round(200 + rng() * 1500, 1),
            "opacity": round(0.18 + rng() * 0.42, 3),
            "scale": round(0.5 + rng() * 1.4, 2),
        })

    # ---------- 组装场景数据 ----------
    scenes_out = []
    for i, (spec, f) in enumerate(zip(scene_specs, frames)):
        clip_start = max(0, f["start"] - OVERLAP_FRAMES)
        clip_end = min(TOTAL_FRAMES, f["end"] + OVERLAP_FRAMES)
        if i == len(scene_specs) - 1:
            clip_end = TOTAL_FRAMES
        scenes_out.append({
            "id": spec["id"],
            "title": spec["title"],
            "dom_id": f"scene-{spec['id']}",
            "image_ids": spec["image_ids"],
            "start_frame": f["start"],
            "end_frame_exclusive": f["end"],
            "clip_start_frame": clip_start,
            "clip_end_frame_exclusive": clip_end,
            "transition_sec": round(OVERLAP_FRAMES * 2 / FPS, 3),
            "exit_fade_sec": round(OVERLAP_FRAMES * 2 / FPS, 3),
            "motion": spec["motion"],
            "effect_ids": spec["effect_ids"],
            "annotation": spec.get("annotation"),
            "annotation_fade_sec": (spec.get("annotation") or {}).get("fade_in_ms", 360) / 1000,
            "overlay_text": spec.get("overlay_text"),
            "inserts": [i2 for i2 in inserts_out if i2["image_id"] in spec["image_ids"]],
            "track_index": i,
        })

    # ---------- 长镜切子镜（A04：同图连续不超过 2.3s）----------
    shots_out = []
    for si, (spec, f, scene) in enumerate(zip(scene_specs, frames, scenes_out)):
        inner = sorted({b for b in phrase_bounds if f["start"] < b < f["end"]})
        cuts = []
        cursor = f["start"]
        while f["end"] - cursor > MAX_SHOT_FRAMES:
            nxt = None
            for b in inner:
                if cursor < b <= cursor + MAX_SHOT_FRAMES:
                    nxt = b
                    break
            if nxt is None:
                nxt = cursor + MAX_SHOT_FRAMES
            cuts.append(nxt)
            cursor = nxt
        bounds = [f["start"]] + cuts + [f["end"]]
        m = scene["motion"]
        total = max(bounds[-1] - bounds[0], 1)
        for k in range(len(bounds) - 1):
            a, b = bounds[k], bounds[k + 1]
            ratio_a = (a - bounds[0]) / total
            ratio_b = (b - bounds[0]) / total
            shots_out.append({
                "dom_id": f"shot-{spec['id']}-{k + 1}",
                "scene_id": spec["id"],
                "image_id": spec["image_ids"][0],
                "start_frame": a,
                "end_frame_exclusive": b,
                "clip_start_frame": max(0, a - OVERLAP_FRAMES),
                "clip_end_frame_exclusive": min(TOTAL_FRAMES, b + OVERLAP_FRAMES),
                "transition_sec": round(OVERLAP_FRAMES * 2 / FPS, 3),
                "exit_fade_sec": round(OVERLAP_FRAMES * 2 / FPS, 3),
                "motion": {
                    "scale_from": round(m["scale_from"] + (m["scale_to"] - m["scale_from"]) * ratio_a, 4),
                    "scale_to": round(m["scale_from"] + (m["scale_to"] - m["scale_from"]) * ratio_b, 4),
                    "x_from": round(m["x_from"] + (m["x_to"] - m["x_from"]) * ratio_a, 1),
                    "x_to": round(m["x_from"] + (m["x_to"] - m["x_from"]) * ratio_b, 1),
                    "y_from": round(m["y_from"] + (m["y_to"] - m["y_from"]) * ratio_a, 1),
                    "y_to": round(m["y_from"] + (m["y_to"] - m["y_from"]) * ratio_b, 1),
                },
                "effect_ids": spec["effect_ids"] if k == 0 else ["ink-transition"],
                "track_index": 100 + len(shots_out),
            })
        if len(bounds) - 1 > 1:
            log(f"{spec['id']} 长度 {f['end'] - f['start']} 帧 → 切为 {len(bounds) - 1} 个子镜")

    # 插入镜单独成 shot
    for ins in inserts_out:
        shots_out.append({
            "dom_id": ins["dom_id"],
            "scene_id": ins["image_id"],
            "image_id": ins["image_id"],
            "start_frame": ins["start_frame"],
            "end_frame_exclusive": ins["end_frame_exclusive"],
            "clip_start_frame": max(0, ins["start_frame"] - OVERLAP_FRAMES),
            "clip_end_frame_exclusive": min(TOTAL_FRAMES, ins["end_frame_exclusive"] + OVERLAP_FRAMES),
            "transition_sec": round(OVERLAP_FRAMES * 2 / FPS, 3),
            "exit_fade_sec": round(OVERLAP_FRAMES * 2 / FPS, 3),
            "motion": {"scale_from": 1.12, "scale_to": 1.04, "x_from": 0, "x_to": 0, "y_from": 0, "y_to": 0},
            "effect_ids": [],
            "track_index": 200 + len(shots_out),
        })

    data = {
        "duration_seconds": DURATION,
        "fps": FPS,
        "total_frames": TOTAL_FRAMES,
        "scenes": scenes_out,
        "shots": shots_out,
        "captions": caption_out,
        "motes": motes,
    }
    SCENES_JSON.parent.mkdir(parents=True, exist_ok=True)
    SCENES_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 生成 film/index.html ----------
    html = build_html(scenes_out, shots_out, caption_out, motes)
    INDEX_HTML.write_text(html, encoding="utf-8")

    # ---------- 自检：帧连续覆盖 ----------
    covered = []
    for s in shots_out:
        covered.append((s["clip_start_frame"], s["clip_end_frame_exclusive"]))
    covered.sort()
    cursor = 0
    for a, b in covered:
        if a > cursor:
            log(f"⚠ 帧空洞 {cursor}–{a}")
        cursor = max(cursor, b)
    if cursor < TOTAL_FRAMES:
        log(f"⚠ 末尾缺帧 {cursor}–{TOTAL_FRAMES}")

    log(f"场景 {len(scenes_out)} 个 / 子镜 {len(shots_out)} 个，字幕 {len(caption_out)} 组，"
        f"插入镜 {len(inserts_out)} 个，粒子 {len(motes)}")
    worst = max((sh["end_frame_exclusive"] - sh["start_frame"]) for sh in shots_out)
    log(f"最长同图连续 {worst} 帧 = {worst / FPS:.2f}s（A04 上限 2.3s）")
    for s in scenes_out:
        log(f"  {s['id']}: 内容帧 {s['start_frame']:3d}–{s['end_frame_exclusive']:3d}"
            f" | clip {s['clip_start_frame']:3d}–{s['clip_end_frame_exclusive']:3d}"
            f" | {s['title']}")
    log(f"写出 {INDEX_HTML.relative_to(ROOT)} 与 {SCENES_JSON.relative_to(ROOT)}")
    return 0


def build_html(scenes, shots, captions, motes) -> str:
    parts = []
    add = parts.append

    add("""<!doctype html>
<html lang="zh-Hans">
  <head>
    <meta charset="utf-8" />
    <title>周处除三害 · 30 秒</title>
    <link rel="stylesheet" href="tokens.css" />
    <link rel="stylesheet" href="scene.css" />
  </head>
  <body>
    <div data-composition-id="root" data-width="1080" data-height="1920" data-duration="30">
      <div class="stage">
        <div class="layer layer-scene" id="layer-scene">""")

    for sh in shots:
        add(f"""          <div class="scene clip" id="{sh['dom_id']}" data-start="{sh['clip_start_frame'] / FPS:.4f}"\
 data-duration="{(sh['clip_end_frame_exclusive'] - sh['clip_start_frame']) / FPS:.4f}"\
 data-track-index="{sh['track_index']}"\
 style="background-image:url(assets/images/{sh['image_id']}.jpg)"></div>""")

    add("""        </div>

        <div class="layer layer-ink" id="layer-ink">
          <div class="ink-wash a" id="ink-wash-a" data-layout-allow-overflow></div>
          <div class="ink-wash b" id="ink-wash-b" data-layout-allow-overflow></div>
          <div class="mist m1" id="mist-m1" data-layout-allow-overflow></div>
          <div class="mist m2" id="mist-m2" data-layout-allow-overflow></div>
          <div class="rain" id="rain-lines" data-layout-allow-overflow></div>
          <div class="focus-mask" id="focus-mask"></div>
          <div class="cinnabar-slash" id="cinnabar-slash" data-layout-allow-overflow></div>""")
    for m in motes:
        add(f'          <div class="mote" id="{m["dom_id"]}"></div>')
    add("""        </div>

        <div class="layer layer-label" id="layer-label">""")
    add('          <div class="hook-title" id="hook-title">三害，最凶的是人。</div>')
    add('          <div class="hook-rule" id="hook-rule"></div>')
    for s in scenes:
        ann = s.get("annotation")
        if not ann:
            continue
        if ann.get("seal"):
            add(f'          <div class="chapter-seal" id="seal-{s["id"]}">{ann["text"]}</div>')
        elif ann.get("big_kanji"):
            add(f'          <div class="big-kanji" id="big-kanji-{s["id"]}">{ann["text"]}</div>')
        else:
            add(f'          <div class="annotation" id="annotation-{s["id"]}">{ann["text"]}</div>')
    for s in scenes:
        if s.get("overlay_text") and s["id"] != "S01":
            add(f'          <div class="final-line" id="final-line-{s["id"]}">{s["overlay_text"]}</div>')
    add("""        </div>

        <div class="layer layer-caption" id="layer-caption">""")
    for i, c in enumerate(captions):
        add(f"""          <div class="caption clip" id="{c['dom_id']}" data-start="{c['start_frame'] / FPS:.4f}"\
 data-duration="{(c['end_frame_exclusive'] - c['start_frame']) / FPS:.4f}"\
 data-track-index="{80 + i}">{c['text']}</div>""")
    add("""        </div>

        <div class="grain" id="grain"></div>
        <div class="vignette" id="vignette"></div>
      </div>
    </div>

    <script type="application/json" id="scene-data">""")
    add(json.dumps({
        "duration_seconds": DURATION,
        "fps": FPS,
        "total_frames": TOTAL_FRAMES,
        "scenes": scenes,
        "captions": captions,
        "motes": motes,
    }, ensure_ascii=False, indent=2))
    add("""</script>
    <script>
      window.__timelines = window.__timelines || {};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <script src="scene.js"></script>
  </body>
</html>
""")
    return "\n".join(parts)


if __name__ == "__main__":
    sys.exit(main())
