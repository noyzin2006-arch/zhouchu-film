"""T09 · 校阅页结构与状态自检。

规划案 §3.2 C5–C8：四态文案、图标、ARIA、禁用态、键盘可达；
§3.3：五个断点、reduced-motion、200% 字体、44px 触区。
"""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PREVIEW = ROOT / "preview"
HTML = (PREVIEW / "index.html").read_text(encoding="utf-8") if (PREVIEW / "index.html").exists() else ""
SOURCE = HTML  # 文案可能落在 html，也可能落在 app.js
CSS = (PREVIEW / "styles.css").read_text(encoding="utf-8") if (PREVIEW / "styles.css").exists() else ""
JS = (PREVIEW / "app.js").read_text(encoding="utf-8") if (PREVIEW / "app.js").exists() else ""
SOURCE = HTML + JS


class TestPreviewStates(unittest.TestCase):
    def test_four_states_present(self):
        for text in ("成片尚未生成", "正在读取本地影片", "成片读取失败", "已就绪"):
            self.assertTrue(text in SOURCE, f"校阅页缺少状态文案：{text}")

    def test_empty_state_gives_build_entry(self):
        self.assertTrue("scripts/build.py" in SOURCE, "空状态必须给出构建入口")

    def test_loading_state_offers_cancel(self):
        self.assertIn("cancel-load", HTML)
        self.assertIn("10000", JS, "加载超过 10s 应出现取消")

    def test_error_state_is_alert(self):
        self.assertIn('role="alert"', HTML)
        self.assertTrue("aria-describedby" in SOURCE, "错误应与触发控件通过 aria-describedby 关联")


class TestPreviewAccessibility(unittest.TestCase):
    def test_no_emoji(self):
        emoji = re.compile(
            "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
        )
        for name, text in (("index.html", HTML), ("styles.css", CSS), ("app.js", JS)):
            hit = emoji.findall(text)
            self.assertEqual(hit, [], f"{name} 出现 emoji：{hit}")

    def test_icons_are_inline_svg(self):
        self.assertIn("<svg", HTML)
        self.assertNotIn("😀", HTML)

    def test_icon_buttons_have_aria_label(self):
        labels = re.findall(r"<button[^>]*>", HTML)
        for tag in labels:
            if "btn__label" not in tag:
                continue
            self.assertIn("aria-label", tag, f"图标按钮缺少 aria-label：{tag}")

    def test_keyboard_support(self):
        self.assertIn("keydown", JS)
        self.assertIn("Escape", JS)
        self.assertIn("ArrowRight", JS)
        self.assertIn("ArrowLeft", JS)

    def test_focus_visible_style(self):
        self.assertIn(":focus-visible", CSS)
        self.assertRegex(CSS, r"outline:\s*var\(--focus-width\)")

    def test_touch_target_minimum(self):
        self.assertRegex(CSS, r"--tap-min:\s*44px")

    def test_disabled_state_semantics(self):
        self.assertIn('aria-disabled', JS)
        self.assertIn("aria-busy", JS)
        self.assertIn("role=\"status\"", HTML)


class TestPreviewResponsive(unittest.TestCase):
    def test_five_breakpoints(self):
        # 断点以「下一个断点减一」的上界写法出现在 CSS 中
        for bp in ("1439", "1023", "767", "480"):
            self.assertTrue(bp in CSS, f"缺少 {bp} 断点")

    def test_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", CSS)
        block = CSS.split("@media (prefers-reduced-motion: reduce)")[-1][:2000]
        self.assertTrue("transition-property: opacity" in block, "减弱动效下应只保留 opacity 过渡")

    def test_hover_only_under_media_query(self):
        self.assertIn("@media (hover: hover)", CSS)

    def test_no_horizontal_scroll_risk(self):
        self.assertIn("max-width: min(360px, 100vw - 32px)", CSS)

    def test_single_column_narrow(self):
        self.assertRegex(CSS, r"@media \(max-width: 767px\)[\s\S]{0,400}grid-template-columns:\s*minmax\(0, 1fr\)")


class TestPreviewOffline(unittest.TestCase):
    def test_no_external_resource(self):
        for name, text in (("index.html", HTML), ("styles.css", CSS), ("app.js", JS)):
            for url in re.findall(r"https?://[^\s\"')]+", text):
                self.fail(f"{name} 引用了外部资源 {url}（校阅页必须离线可用）")

    def test_no_generation_api_call(self):
        for token in ("mcode-tools", "connector__matrix", "generate_image"):
            self.assertNotIn(token, JS + HTML, "校阅页不得调用任何生成接口")


class TestPreviewAssets(unittest.TestCase):
    def test_deliver_preview_copy_exists(self):
        target = ROOT / "deliver" / "preview" / "index.html"
        self.assertTrue(target.exists(), "缺少 deliver/preview/index.html")

    def test_narration_loaded_from_delivery(self):
        narration = ROOT / "deliver" / "narration.txt"
        self.assertTrue(narration.exists())
        lines = [l for l in narration.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(lines), 8)


if __name__ == "__main__":
    unittest.main()
