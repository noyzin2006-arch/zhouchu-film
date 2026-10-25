"""T02 · 设计令牌导出。

`film/design-tokens.json` 是唯一视觉真源（规划案 §5.1）。
本脚本导出：
  film/tokens.css        CSS 自定义属性（HTML/CSS 只允许引用变量，不许直写 hex）
  work/palette.json      同一份色板，供 Pillow 图层生成使用（与 CSS 同源）

用法：python3 scripts/export_tokens.py
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS_PATH = ROOT / "film" / "design-tokens.json"
CSS_PATH = ROOT / "film" / "tokens.css"
PALETTE_PATH = ROOT / "work" / "palette.json"

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def flatten(prefix: str, value, out: dict[str, str]) -> None:
    if isinstance(value, dict):
        for key, sub in value.items():
            flatten(f"{prefix}.{key}" if prefix else key, sub, out)
    elif isinstance(value, list):
        out[prefix] = json.dumps(value, ensure_ascii=False)
    elif isinstance(value, bool):
        out[prefix] = "true" if value else "false"
    elif isinstance(value, (int, float)):
        out[prefix] = str(value)
    elif isinstance(value, str):
        out[prefix] = value


def main() -> int:
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    flat: dict[str, str] = {}
    flatten("", tokens, flat)

    lines = [
        "/* 由 scripts/export_tokens.py 从 film/design-tokens.json 自动生成 —— 请勿手改。 */",
        ":root {",
    ]
    for name, value in flat.items():
        var = "--" + name.replace(".", "-")
        if HEX_RE.match(value):
            lines.append(f"  {var}: {value};")
        else:
            lines.append(f"  {var}: {value};")
    lines.append("}")
    CSS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    palette = {
        "colors": {
            k: v for k, v in flat.items()
            if k.startswith("color.") and isinstance(v, str) and HEX_RE.match(v)
        },
        "type": tokens["type"],
        "typeScale": tokens["typeScale"],
        "video": tokens["video"],
        "caption": tokens["caption"],
        "annotation": tokens["annotation"],
        "safe": tokens["safe"],
        "motion": tokens["motion"],
    }
    PALETTE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PALETTE_PATH.write_text(json.dumps(palette, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[tokens] {CSS_PATH.relative_to(ROOT)}  ({len(flat)} 个令牌)")
    print(f"[tokens] {PALETTE_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
