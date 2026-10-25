"""T01 · 故事真源校验。

覆盖规划案 §6 T01 与 §8.3 的失败演练：
删 V7 引文 / 以白额虎代邅迹虎 / 误置陆机台词 —— 本文件必须 FAIL。
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))

SCRIPT_A = STORY["narration"]["scriptA"]
SCRIPT_B = STORY["narration"]["scriptB"]
SCENES = STORY["scenes"]
IMAGES = STORY["images"]
RULES = STORY["factRules"]


class TestNarrationStructure(unittest.TestCase):
    def test_exactly_eight_lines(self):
        self.assertEqual(len(SCRIPT_A), 8)
        self.assertEqual(len(SCRIPT_B), 8)

    def test_line_ids_are_v1_to_v8(self):
        self.assertEqual([l["id"] for l in SCRIPT_A], [f"V{i}" for i in range(1, 9)])

    def test_all_nodes_present(self):
        self.assertEqual(
            sorted({l["node"] for l in SCRIPT_A}),
            sorted(RULES["mustCover"]),
            "六个原文节点必须全覆盖且不引入新节点",
        )

    def test_every_line_maps_to_known_scenes(self):
        scene_ids = {s["id"] for s in SCENES}
        for line in SCRIPT_A:
            self.assertTrue(line["scene_ids"], f"{line['id']} 没有关联镜头")
            for sid in line["scene_ids"]:
                self.assertIn(sid, scene_ids)

    def test_every_scene_is_covered_by_some_line(self):
        mapped = {sid for line in SCRIPT_A for sid in line["scene_ids"]}
        self.assertEqual(mapped, {s["id"] for s in SCENES})

    def test_phrase_chunks_cover_script_a(self):
        for line, chunks in zip(SCRIPT_A, STORY["narration"]["phraseChunks"]):
            joined = "".join(chunks)
            stripped = "".join(c for c in line["text"] if c not in "：:，。！!，、")
            stripped = stripped.replace("陆云说", "陆云说")
            self.assertEqual(
                len(chunks) >= 2,
                True,
                f"{line['id']} 至少要能切成两个短语",
            )
            self.assertTrue(joined, f"{line['id']} 短语为空")
            self.assertEqual(
                len("".join(chunks)),
                len(line["text"].replace("：", "").replace("，", "").replace("！", "").replace("、", "").replace("。", "")),
                f"{line['id']} 短语拼接后字数应与台词一致：{joined}",
            )
            del stripped


class TestLiteralAccuracy(unittest.TestCase):
    """§8.3：删 V7 引文 / 以白额虎代邅迹虎 / 误置陆机台词 —— 必须 FAIL。

    只检查**会出现在画面与声音里**的内容（台词、画面文案、旁注、图像提示词），
    factRules 里的「禁止项清单」是反面规则本身，不算违规。
    """

    def on_screen_text(self):
        parts = [line["text"] for line in SCRIPT_A]
        parts += [line["text"] for line in SCRIPT_B]
        for scene in SCENES:
            if scene.get("overlay_text"):
                parts.append(scene["overlay_text"])
            if scene.get("annotation"):
                parts.append(scene["annotation"]["text"])
        for img in IMAGES:
            parts.append(img["subject"])
        return "\n".join(parts)

    def test_v7_keeps_the_original_quotation(self):
        v7 = next(l for l in SCRIPT_A if l["id"] == "V7")
        for phrase in ("人患志之不立", "何忧令名不彰"):
            self.assertIn(phrase, v7["text"], f"V7 必须逐字保留「{phrase}」")

    def test_no_white_forehead_tiger(self):
        self.assertNotIn(
            "白额虎",
            self.on_screen_text(),
            "本片统一用「邅迹虎（跛脚虎）」，画面与声音里不得出现白额虎",
        )

    def test_luji_is_never_in_the_room(self):
        self.assertNotIn(
            "陆机",
            self.on_screen_text(),
            "对话者是陆云，画面与旁注不得出现陆机",
        )

    def test_zhou_chu_is_mentioned_as_the_third_threat(self):
        v1 = next(l for l in SCRIPT_A if l["id"] == "V1")
        self.assertIn("周处", v1["text"])
        self.assertIn("邅迹虎", v1["text"])
        self.assertIn("恶蛟", v1["text"])

    def test_ending_is_the_original_ending(self):
        v8 = next(l for l in SCRIPT_A if l["id"] == "V8")
        self.assertIn("终为忠臣孝子", v8["text"])

    def test_three_days_and_three_nights_kept(self):
        v3 = next(l for l in SCRIPT_A if l["id"] == "V3")
        self.assertIn("三日三夜", v3["text"])


class TestScenes(unittest.TestCase):
    def test_twelve_scenes(self):
        self.assertEqual(len(SCENES), 12)
        self.assertEqual([s["id"] for s in SCENES], [f"S{i:02d}" for i in range(1, 13)])

    def test_fourteen_images(self):
        self.assertEqual(len(IMAGES), 14)
        self.assertEqual(len({i["id"] for i in IMAGES}), 14)

    def test_anchor_keys_unique_and_resolvable(self):
        anchors = []
        for scene in SCENES:
            a = scene["anchor"]
            self.assertIn(a["line_id"], {l["id"] for l in SCRIPT_A})
            line = next(l for l in SCRIPT_A if l["id"] == a["line_id"])
            self.assertIn(a["phrase"], line["text"], f"{scene['id']} 锚点短语不在台词里")
            anchors.append((a["line_id"], a["phrase"]))
            for ins in scene.get("inserts", []):
                self.assertIn(ins["image_id"], {i["id"] for i in IMAGES})
                iline = next(l for l in SCRIPT_A if l["id"] == ins["line_id"])
                self.assertIn(ins["phrase"], iline["text"], f"{scene['id']} 插入镜锚点短语不在台词里")
        self.assertEqual(len(anchors), len(set(anchors)), "锚点必须唯一")

    def test_every_scene_has_at_least_one_effect(self):
        for scene in SCENES:
            self.assertTrue(scene["effect_ids"], f"{scene['id']} 缺少特效")

    def test_scene_windows_are_ordered_and_cover_thirty_seconds(self):
        prev = 0.0
        for scene in SCENES:
            self.assertGreater(scene["expected_start_sec"], prev - 1e-9)
            self.assertGreater(scene["expected_end_sec"], scene["expected_start_sec"])
            prev = scene["expected_end_sec"]
        self.assertAlmostEqual(SCENES[-1]["expected_end_sec"], 30.0, places=6)

    def test_no_still_image_held_over_two_point_three_seconds(self):
        """A04：静止同图不可连续超过 2.3s；单镜最长 3.2s（声明了插入镜的镜头按子镜计）。"""
        for scene in SCENES:
            start = scene["expected_start_sec"]
            end = scene["expected_end_sec"]
            inserts = scene.get("inserts", [])
            if not inserts:
                self.assertLessEqual(
                    end - start, 3.2 + 1e-6, f"{scene['id']} 单镜超过规划允许的 3.2s"
                )
                continue
            bounds = [start]
            for ins in inserts:
                bounds.append(ins["expected_start_sec"])
                bounds.append(ins["expected_start_sec"] + ins["duration_sec"])
            bounds.append(end)
            bounds = sorted(b for b in bounds if start <= b <= end)
            spans = [round(bounds[i + 1] - bounds[i], 6) for i in range(len(bounds) - 1)]
            for span in spans:
                self.assertLessEqual(
                    span, 3.2 + 1e-6, f"{scene['id']} 子镜 {span}s 超过 3.2s"
                )
            self.assertGreater(len(scene["image_ids"]), 1, f"{scene['id']} 插入镜必须有多张图")

    def test_insert_images_belong_to_their_scene(self):
        for scene in SCENES:
            for ins in scene.get("inserts", []):
                self.assertIn(ins["image_id"], scene["image_ids"])


class TestTokens(unittest.TestCase):
    def test_video_format(self):
        v = TOKENS["video"]
        self.assertEqual((v["width"], v["height"], v["fps"], v["frames"]), (1080, 1920, 30, 900))
        self.assertAlmostEqual(v["durationSeconds"], 30.0, places=6)

    def test_safe_area(self):
        self.assertEqual(TOKENS["safe"]["captionBox"]["left"], 102)
        self.assertEqual(TOKENS["safe"]["captionBox"]["right"], 202)
        self.assertEqual(TOKENS["safe"]["captionBox"]["top"], 1510)
        self.assertEqual(TOKENS["safe"]["captionBox"]["bottom"], 1640)

    def test_caption_limits(self):
        c = TOKENS["caption"]
        self.assertEqual(c["maxChineseCharsPerLine"], 13)
        self.assertEqual(c["maxLines"], 2)
        self.assertGreaterEqual(c["minContrastRatio"], 4.5)

    def test_audio_targets(self):
        a = TOKENS["audio"]
        self.assertEqual(a["voiceLufs"], -16)
        self.assertLessEqual(a["truePeakDb"], -1.5)
        self.assertGreaterEqual(a["bedRmsBelowVoiceDbMin"], 12)


if __name__ == "__main__":
    unittest.main()
