"""T03 · 静帧生产。

唯一图片入口（规划案 §5.5）：
    mcode-tools connector call connector__matrix__generate_image  -> node_id
    mcode-tools get-asset-url <node_id>                          -> 临时地址，立即落盘

约束：
- 只生成**静态图**。本脚本不调用任何视频生成接口，产物里也不允许出现视频文件。
- 9:16 / 2K；Pillow 校验可打开、宽高 ≥ 1080×1920、纵横比与 9:16 相差 ≤ 3%。
- 单图请求超时 120s；失败重试 3 次，退避 2/5/10s；质量错位同图重生 2 次。
- 仍失败 → 用 Pillow 画出完整的水墨静图（不留灰块、不留占位）。
- 已有合格文件按 hash 复用，重复构建不消耗远端请求。
"""
from __future__ import annotations

import argparse
import hashlib
import math
import json
import pathlib
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))

IMG_DIR = ROOT / "film" / "assets" / "images"
OVERLAY_DIR = ROOT / "film" / "assets" / "overlays"
MANIFEST = ROOT / "work" / "asset-manifest.json"

TARGET_W, TARGET_H = TOKENS["video"]["width"], TOKENS["video"]["height"]
ASPECT = TARGET_W / TARGET_H
REQUEST_TIMEOUT_S = 120
MAX_ATTEMPTS = 3
BACKOFF = [2, 5, 10]
MAX_REGENERATE = 2

CONNECTOR_TOOL = "connector__matrix__generate_image"


def log(msg: str) -> None:
    print(f"[assets] {msg}", flush=True)


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], timeout: int = REQUEST_TIMEOUT_S) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


def call_generate_image(prompt: str, output_file: str) -> tuple[str | None, str]:
    """调一次出图接口，返回 (node_id, 错误信息)。"""
    payload = {
        "requests": [
            {
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "resolution": "2K",
                "output_file": output_file,
            }
        ]
    }
    code, out, err = run(
        ["mcode-tools", "connector", "call", CONNECTOR_TOOL, "--args", json.dumps(payload, ensure_ascii=False)]
    )
    if code != 0:
        return None, (err or out).strip()[:400]
    try:
        data = json.loads(out[out.index("{") :]) if "{" in out else json.loads(out)
    except Exception as exc:  # noqa: BLE001
        return None, f"解析返回失败: {exc}; raw={out.strip()[:300]}"
    items = data.get("success_items") or []
    if not items:
        return None, f"无成功项: {json.dumps(data, ensure_ascii=False)[:300]}"
    return str(items[0].get("node_id") or ""), ""


def download_asset(node_id: str, dest: pathlib.Path) -> tuple[bool, str]:
    code, out, err = run(["mcode-tools", "get-asset-url", node_id], timeout=60)
    if code != 0:
        return False, (err or out).strip()[:300]
    url = ""
    try:
        data = json.loads(out[out.index("{") :]) if "{" in out else json.loads(out)
        url = data.get("download_url") or data.get("temp_url") or data.get("url") or ""
    except Exception:  # noqa: BLE001
        for token in out.split():
            if token.startswith("https://"):
                url = token.strip('",')
                break
    if not url:
        return False, "取不到临时地址"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=90) as resp, dest.open("wb") as fh:
            fh.write(resp.read())
    except Exception as exc:  # noqa: BLE001
        return False, f"下载失败: {exc}"
    return dest.exists() and dest.stat().st_size > 0, ""


def inspect_image(path: pathlib.Path) -> tuple[bool, str, dict]:
    try:
        with Image.open(path) as im:
            im.load()
            w, h = im.size
    except Exception as exc:  # noqa: BLE001
        return False, f"无法打开: {exc}", {}
    ratio = w / h
    dev = abs(ratio - ASPECT) / ASPECT
    meta = {"width": w, "height": h, "aspect_deviation": round(dev, 4)}
    if w < TARGET_W or h < TARGET_H:
        return False, f"尺寸不足 {w}x{h}", meta
    if dev > 0.03:
        return False, f"纵横比偏离 9:16 超过 3%: {dev:.2%}", meta
    return True, "", meta


def procedural_still(path: pathlib.Path, scene_id: str, title: str) -> None:
    """降级：Pillow 画一幅完整的水墨静图（绢纸底 + 远山 + 墨影 + 朱印），不留灰块。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = TARGET_W, TARGET_H
    base = Image.new("RGB", (w, h), "#E8DFC8")
    draw = ImageDraw.Draw(base, "RGBA")
    # 绢纸纵向纤维
    for i in range(0, w, 7):
        draw.line([(i, 0), (i, h)], fill=(120, 104, 74, 10), width=1)
    # 远山三层
    layers = [((74, 92, 78), 0.30, 0.55), ((46, 62, 52), 0.42, 0.72), ((26, 38, 32), 0.55, 0.88)]
    for color, base_y, amp in layers:
        pts = [(0, h)]
        for x in range(0, w + 1, 24):
            y = int(h * base_y - math_sin(x / w * 6.2 + amp * 9) * h * 0.05)
            pts.append((x, y))
        pts.append((w, h))
        draw.polygon(pts, fill=color + (255,))
    # 水面
    draw.rectangle([0, int(h * 0.86), w, h], fill=(22, 34, 30, 255))
    # 人影（剪影，不露脸）
    cx, cy = w // 2, int(h * 0.72)
    draw.ellipse([cx - 34, cy - 150, cx + 34, cy - 82], fill=(18, 26, 24, 255))
    draw.polygon(
        [(cx - 52, cy - 76), (cx + 52, cy - 76), (cx + 86, cy + 210), (cx - 86, cy + 210)],
        fill=(18, 26, 24, 255),
    )
    # 朱砂印
    draw.rectangle([w - 150, h - 170, w - 86, h - 106], outline=(216, 74, 59, 220), width=6)
    draw.rectangle([w - 138, h - 158, w - 98, h - 118], outline=(216, 74, 59, 180), width=3)
    base = base.filter(ImageFilter.GaussianBlur(0.4))
    base.save(path, "JPEG", quality=92)


def math_sin(x: float) -> float:
    import math

    return math.sin(x)


def produce_one(image_spec: dict, style_prefix: str) -> dict:
    dest = ROOT / image_spec["output_path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    prompt = f"{style_prefix} Subject: {image_spec['subject']}"
    record = {
        "id": image_spec["id"],
        "scene_id": image_spec["scene_id"],
        "prompt": prompt,
        "output_path": str(dest.relative_to(ROOT)),
        "provider": "matrix-image",
        "generation_video": False,
        "source_asset_id": None,
        "rights_status": "pending-review",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "attempts": [],
        "fallback": False,
    }
    if dest.exists():
        ok, why, meta = inspect_image(dest)
        if ok:
            record.update(meta)
            record["sha256"] = sha256_file(dest)
            record["provider"] = "matrix-image"
            record["reused_from_cache"] = True
            log(f"{image_spec['id']} 命中本地缓存，直接复用")
            return record
        log(f"{image_spec['id']} 本地文件不合格（{why}），重新生成")

    node_id = None
    last_error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        tmp = dest.with_suffix(".part.jpg")
        node_id, err = call_generate_image(prompt, image_spec["id"])
        record["attempts"].append({"attempt": attempt, "node_id": node_id, "error": err})
        if err or not node_id:
            last_error = err or "未返回 node_id"
            log(f"{image_spec['id']} 第 {attempt} 次生成失败: {last_error}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])
            continue
        ok, err = download_asset(node_id, tmp)
        if not ok:
            last_error = f"下载失败: {err}"
            log(f"{image_spec['id']} 第 {attempt} 次下载失败: {last_error}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])
            continue
        good, why, meta = inspect_image(tmp)
        record["attempts"][-1].update(meta)
        if good:
            tmp.replace(dest)
            record.update(meta)
            record["sha256"] = sha256_file(dest)
            record["node_id"] = node_id
            log(f"{image_spec['id']} 生成成功 {meta['width']}x{meta['height']}")
            return record
        last_error = why
        tmp.unlink(missing_ok=True)
        log(f"{image_spec['id']} 第 {attempt} 次质量不合格: {why}")
        if attempt < MAX_ATTEMPTS:
            time.sleep(BACKOFF[min(attempt - 1, len(BACKOFF) - 1)])

    # 质量重生（同一提示词再试 2 次）
    for regen in range(1, MAX_REGENERATE + 1):
        node_id, err = call_generate_image(prompt, f"{image_spec['id']}_r{regen}")
        if err or not node_id:
            last_error = err or "未返回 node_id"
            continue
        tmp = dest.with_suffix(".part.jpg")
        ok, err = download_asset(node_id, tmp)
        if not ok:
            last_error = err
            continue
        good, why, meta = inspect_image(tmp)
        if good:
            tmp.replace(dest)
            record.update(meta)
            record["sha256"] = sha256_file(dest)
            record["node_id"] = node_id
            log(f"{image_spec['id']} 重生第 {regen} 次成功")
            return record
        last_error = why
        tmp.unlink(missing_ok=True)

    # 降级：程序静图
    procedural_still(dest, image_spec["scene_id"], image_spec.get("title", ""))
    with Image.open(dest) as im:
        meta = {"width": im.size[0], "height": im.size[1]}
    record.update(meta)
    record["sha256"] = sha256_file(dest)
    record["provider"] = "procedural"
    record["fallback"] = True
    record["fallback_reason"] = last_error
    record["rights_status"] = "procedurally synthesized in project"
    log(f"{image_spec['id']} 降级为程序静图（{last_error}）")
    return record


def optimize_in_place(path: pathlib.Path, target_w: int, target_h: int) -> dict:
    """按规划案 §5.5 裁切算法压到目标分辨率：scale=max(w/W,h/H) → 中心 crop → 无黑边。"""
    with Image.open(path) as im:
        im = im.convert("RGB")
        scale = max(target_w / im.width, target_h / im.height)
        new_w = max(target_w, int(round(im.width * scale)))
        new_h = max(target_h, int(round(im.height * scale)))
        resized = im.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - target_w) // 2
        top = int((new_h - target_h) * 0.46)
        cropped = resized.crop((left, top, left + target_w, top + target_h))
        cropped.save(path, "JPEG", quality=88, optimize=True, progressive=True)
    return {"width": target_w, "height": target_h}


def build_overlays() -> list[dict]:
    """T03 · 程序静帧水墨蒙版（RGBA PNG，静止、无视频）。

    规划案 §5.1：film/assets/overlays/ 放 Pillow 自绘的透明水墨蒙版、纸纹、波纹。
    """
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    made = []

    # 1) 绢纸颗粒
    grain = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    dr = ImageDraw.Draw(grain)
    rng = __import__("random").Random(20261025)
    for _ in range(5200):
        x = rng.randrange(1080)
        y = rng.randrange(1920)
        a = rng.randrange(6, 26)
        dr.point((x, y), fill=(245, 232, 204, a))
    grain = grain.filter(ImageFilter.GaussianBlur(0.3))
    gp = OVERLAY_DIR / "silk-grain.png"
    grain.save(gp)
    made.append({"id": "silk-grain", "path": str(gp.relative_to(ROOT)), "kind": "paper-grain",
                 "sha256": sha256_file(gp), "source_type": "procedural"})

    # 2) 墨晕（不规则水墨块）
    ink = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ink)
    rng = __import__("random").Random(7788)
    for cx, cy, rad in ((300, 520, 300), (760, 980, 360), (520, 1420, 280)):
        pts = []
        for k in range(40):
            ang = 2 * math.pi * k / 40
            rr = rad * (0.72 + 0.28 * rng.random())
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        dr.polygon(pts, fill=(16, 24, 19, 120))
    ink = ink.filter(ImageFilter.GaussianBlur(46))
    ip = OVERLAY_DIR / "ink-wash.png"
    ink.save(ip)
    made.append({"id": "ink-wash", "path": str(ip.relative_to(ROOT)), "kind": "ink-wash",
                 "sha256": sha256_file(ip), "source_type": "procedural"})

    # 3) 水纹（同心弧线，用于追蛟段）
    wave = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    dr = ImageDraw.Draw(wave)
    for i in range(26):
        r = 120 + i * 46
        a = max(8, 92 - i * 3)
        dr.arc([540 - r, 900 - r * 0.55, 540 + r, 900 + r * 0.55], start=196, end=344,
               fill=(223, 206, 172, a), width=3)
    wave = wave.filter(ImageFilter.GaussianBlur(1.1))
    wp = OVERLAY_DIR / "water-ripple.png"
    wave.save(wp)
    made.append({"id": "water-ripple", "path": str(wp.relative_to(ROOT)), "kind": "water-ripple",
                 "sha256": sha256_file(wp), "source_type": "procedural"})

    # 4) 朱砂笔锋斜切
    slash = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    dr = ImageDraw.Draw(slash)
    dr.polygon([(0, 900), (1080, 700), (1080, 736), (0, 946)], fill=(216, 74, 59, 235))
    slash = slash.filter(ImageFilter.GaussianBlur(2.2))
    sp = OVERLAY_DIR / "cinnabar-slash.png"
    slash.save(sp)
    made.append({"id": "cinnabar-slash", "path": str(sp.relative_to(ROOT)), "kind": "slash",
                 "sha256": sha256_file(sp), "source_type": "procedural"})

    return made


def main() -> int:
    parser = argparse.ArgumentParser(description="T03 静帧生产")
    parser.add_argument("--only", nargs="*", help="只生产指定图 id")
    parser.add_argument("--force", action="store_true", help="忽略缓存，全部重生")
    args = parser.parse_args()

    if args.force:
        for spec in STORY["images"]:
            p = ROOT / spec["output_path"]
            p.unlink(missing_ok=True)

    style_prefix = STORY["stylePrefix"]
    specs = STORY["images"]
    if args.only:
        specs = [s for s in specs if s["id"] in set(args.only)]

    records = []
    for spec in specs:
        records.append(produce_one(spec, style_prefix))

    # 统一裁切压缩到目标分辨率，避免把几十 MB 原图塞进仓库
    for rec in records:
        dest = ROOT / rec["output_path"]
        if not dest.exists():
            continue
        before = dest.stat().st_size
        meta = optimize_in_place(dest, TARGET_W, TARGET_H)
        rec["width"], rec["height"] = meta["width"], meta["height"]
        rec["sha256"] = sha256_file(dest)
        rec["bytes"] = dest.stat().st_size
        rec["bytes_before_optimize"] = before
        log(f"{rec['id']} 裁切压缩 {before//1024}KB → {dest.stat().st_size//1024}KB")

    overlays = build_overlays()
    log(f"程序蒙版 {len(overlays)} 个")

    manifest = {
        "task": "LOOP-001",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "mcode-tools connector__matrix__generate_image (9:16 / 2K)",
        "policy": "still images only — no video generation model is called anywhere in this project",
        "images": records,
        "overlays": overlays,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for r in records if not r.get("fallback"))
    log(f"完成：{len(records)} 张，其中远端生成 {ok} 张，程序降级 {len(records) - ok} 张")
    log(f"manifest: {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
