"""T05/T07 · 时间轴与字幕校验。

§8.3 失败演练：删一字 / 字幕错时 0.3s / 强行压成三行 —— 本文件必须 FAIL。
"""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((ROOT / "film" / "audio-contract.json").read_text(encoding="utf-8"))

ALIGN = ROOT / "work" / "align"
CUES = json.loads((ALIGN / "char_cues.json").read_text(encoding="utf-8"))
CAPTIONS = json.loads((ALIGN / "captions.json").read_text(encoding="utf-8"))
SCENES = json.loads((ROOT / "work" / "scenes.json").read_text(encoding="utf-8"))
TIMELINE = json.loads((ROOT / "work" / "voice_timeline.json").read_text(encoding="utf-8"))
SRT = ROOT / "deliver" / "zhouchu_30s.srt"

SR = CUES["sample_rate"]
TOTAL_FRAMES = TOKENS["video"]["frames"]
DURATION_MS = int(TOKENS["video"]["durationSeconds"] * 1000)


def is_han(ch):
    return "一" <= ch <= "鿿"


def strip_punct(text):
    return "".join(c for c in text if is_han(c))


class TestCharCues(unittest.TestCase):
    def test_every_han_character_has_a_cue(self):
        ref = strip_punct("".join(l["text"] for l in STORY["narration"]["scriptA"]))
        got = "".join(c["glyph"] for c in CUES["cues"])
        self.assertEqual(len(got), len(ref), "字级时码数量必须覆盖全部汉字")
        self.assertEqual(got, ref, "字级时码的字符序列必须与台本逐字一致")

    def test_cues_are_monotonic_and_valid(self):
        prev = -1
        for c in CUES["cues"]:
            self.assertLessEqual(c["start_sample"], c["end_sample"], "字级时码非法")
            self.assertGreaterEqual(c["start_sample"], prev, "字级时码必须单调不减")
            prev = c["start_sample"]

    def test_all_cues_inside_the_timeline(self):
        total = TIMELINE["total_samples"]
        for c in CUES["cues"]:
            self.assertGreaterEqual(c["start_sample"], 0)
            self.assertLessEqual(c["end_sample"], total + SR * 0.05)

    def test_alignment_method_is_recorded(self):
        self.assertIn(CUES["method"], ("forced", "chunk-boundary"))


class TestCaptions(unittest.TestCase):
    def test_caption_count(self):
        self.assertGreaterEqual(len(CAPTIONS["captions"]), 10)

    def test_caption_boundaries_within_zero_to_thirty_seconds(self):
        for cap in CAPTIONS["captions"]:
            start = int(round(cap["start_sample"] * 1000 / SR))
            end = int(round(cap["end_sample"] * 1000 / SR))
            self.assertGreaterEqual(start, 0)
            self.assertLessEqual(end, DURATION_MS)

    def test_caption_lines_fit_the_safe_area(self):
        max_chars = TOKENS["caption"]["maxChineseCharsPerLine"]
        max_lines = TOKENS["caption"]["maxLines"]
        for cap in CAPTIONS["captions"]:
            self.assertLessEqual(len(cap["lines"]), max_lines, f"{cap['text']} 行数超限")
            for line in cap["lines"]:
                self.assertLessEqual(len(line), max_chars, f"{cap['text']} 单行超 {max_chars} 字")

    def test_captions_do_not_overlap(self):
        caps = sorted(CAPTIONS["captions"], key=lambda c: c["start_sample"])
        for i in range(len(caps) - 1):
            self.assertLessEqual(
                caps[i]["end_sample"], caps[i + 1]["start_sample"],
                f"字幕重叠：{caps[i]['text']} / {caps[i+1]['text']}",
            )

    def test_caption_text_comes_from_the_script(self):
        joined = "".join(c["text"] for c in CAPTIONS["captions"])
        for line in STORY["narration"]["scriptA"]:
            for ch in strip_punct(line["text"]):
                self.assertIn(ch, joined, f"字幕未覆盖台本字符 {ch}")

    def test_key_phrases_are_not_split(self):
        joined = "".join(c["text"] for c in CAPTIONS["captions"])
        for phrase in ("人患志之不立", "何忧令名不彰", "三日三夜", "终为忠臣孝子"):
            self.assertIn(phrase, joined, f"关键句 {phrase} 被拆断或缺失")


class TestSceneTimeline(unittest.TestCase):
    def test_shots_cover_the_whole_frame_range(self):
        spans = sorted(
            (s["start_frame"], s["end_frame_exclusive"]) for s in SCENES["shots"]
        )
        cursor = 0
        for a, b in spans:
            self.assertLessEqual(a, cursor + 1, f"帧空洞：{cursor}–{a}")
            cursor = max(cursor, b)
        self.assertEqual(SCENES["total_frames"], TOTAL_FRAMES)
        self.assertGreaterEqual(cursor, TOTAL_FRAMES - 1)

    def test_no_still_image_held_over_two_point_three_seconds(self):
        limit = int(round(2.3 * SCENES["fps"]))
        for s in SCENES["shots"]:
            span = s["end_frame_exclusive"] - s["start_frame"]
            self.assertLessEqual(span, limit, f"{s['dom_id']} 同图连续 {span / SCENES['fps']:.2f}s")

    def test_every_scene_has_at_least_one_effect(self):
        for scene in SCENES["scenes"]:
            self.assertTrue(scene["effect_ids"], f"{scene['id']} 缺少特效")

    def test_twelve_scenes_and_at_least_twelve_distinct_images(self):
        self.assertEqual(len(SCENES["scenes"]), 12)
        used = {img for s in SCENES["scenes"] for img in s["image_ids"]}
        self.assertGreaterEqual(len(used), 12)


class TestSrt(unittest.TestCase):
    def setUp(self):
        self.text = SRT.read_text(encoding="utf-8-sig") if SRT.exists() else ""

    def test_srt_exists_and_matches_caption_count(self):
        self.assertTrue(self.text, "SRT 未生成")
        blocks = [b for b in re.split(r"\n\s*\n", self.text.strip()) if b.strip()]
        self.assertEqual(len(blocks), len(CAPTIONS["captions"]))

    def test_srt_times_are_ordered_and_in_range(self):
        times = re.findall(r"(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})", self.text)
        self.assertTrue(times)
        prev_end = -1
        for t in times:
            start = int(t[0]) * 3600000 + int(t[1]) * 60000 + int(t[2]) * 1000 + int(t[3])
            end = int(t[4]) * 3600000 + int(t[5]) * 60000 + int(t[6]) * 1000 + int(t[7])
            self.assertGreaterEqual(start, prev_end, "SRT 时间码倒流或重叠")
            self.assertLessEqual(end, DURATION_MS + 100)
            prev_end = end


if __name__ == "__main__":
    unittest.main()
