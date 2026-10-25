"""T03 · 素材溯源校验。

§8.3 失败演练：把场景生成视频文件假扮图 / manifest 标 generation_video=true
—— 本文件必须 FAIL。
"""
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORY = json.loads((ROOT / "film" / "story.json").read_text(encoding="utf-8"))
MANIFEST_PATH = ROOT / "work" / "asset-manifest.json"
IMG_DIR = ROOT / "film" / "assets" / "images"
OVERLAY_DIR = ROOT / "film" / "assets" / "overlays"
DELIVER = ROOT / "deliver"

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv", ".gif"}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class TestAssetManifest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_exists(self):
        self.assertTrue(MANIFEST_PATH.exists(), "缺少 work/asset-manifest.json")

    def test_fourteen_stills(self):
        images = self.manifest["images"]
        self.assertEqual(len(images), 14)
        self.assertEqual(len({i["id"] for i in images}), 14)

    def test_every_entry_is_a_still_not_a_video(self):
        for item in self.manifest["images"]:
            self.assertIs(item["generation_video"], False,
                          f"{item['id']} 被标为视频生成，必须为静态图")
            self.assertIn(item["provider"], ("matrix-image", "procedural"))
            self.assertNotEqual(item["provider"], "video")
            self.assertTrue(item["prompt"], f"{item['id']} 缺少 prompt")
            self.assertTrue(item["sha256"], f"{item['id']} 缺少 sha256")
            self.assertTrue(item["rights_status"], f"{item['id']} 缺少权利状态")

    def test_no_temporary_signed_urls_in_manifest(self):
        blob = json.dumps(self.manifest, ensure_ascii=False)
        self.assertNotIn("Expires=", blob, "manifest 里不得留短时效签名 URL")
        self.assertNotIn("x-oss-signature", blob)

    def test_image_files_exist_and_match_hash(self):
        for item in self.manifest["images"]:
            path = ROOT / item["output_path"]
            self.assertTrue(path.exists(), f"{item['id']} 文件缺失")
            self.assertEqual(sha256_file(path), item["sha256"], f"{item['id']} hash 不符")

    def test_overlays_are_procedural_and_present(self):
        overlays = self.manifest.get("overlays", [])
        self.assertGreaterEqual(len(overlays), 3)
        for ov in overlays:
            path = ROOT / ov["path"]
            self.assertTrue(path.exists(), f"{ov['id']} 蒙版缺失")
            self.assertEqual(ov["source_type"], "procedural")


class TestNoVideoMaterial(unittest.TestCase):
    def test_no_video_file_in_project_assets(self):
        for base in (IMG_DIR, OVERLAY_DIR):
            for path in base.rglob("*"):
                if path.is_file():
                    self.assertNotIn(path.suffix.lower(), VIDEO_EXT,
                                     f"素材目录出现视频文件：{path}")

    def test_no_video_generation_api_in_scripts(self):
        """检查的是「调用」，不是字样：manifest 字段 video_generation_used 是声明，不算调用。"""
        import re

        banned = (
            r"text_to_video", r"text-to-video", r"img2video", r"image_to_video",
            r"generate_video", r"video_generation_model", r"h3_video", r"bailian_video",
            r"video[-_]?gen", r"t2v", r"i2v",
        )
        for path in (ROOT / "scripts").glob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for pattern in banned:
                for hit in re.finditer(pattern, text):
                    line = text[max(0, hit.start() - 40): hit.start() + 40]
                    # 出现在 manifest 的声明字段里不算调用
                    if "video_generation_used" in line or "生成视频" in line or "视频生成" in line:
                        continue
                    self.fail(f"{path.name} 出现疑似视频生成调用：{hit.group(0)} … {line.strip()[:70]}")

    def test_story_images_map_to_story_json(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        expected = {img["output_path"] for img in STORY["images"]}
        actual = {item["output_path"] for item in manifest["images"]}
        self.assertEqual(expected, actual, "manifest 与 story.json 的图片清单不一致")


class TestDeliverableHygiene(unittest.TestCase):
    def test_deliver_has_no_secret_material(self):
        """扫描真实密钥值与鉴权串；变量名（如 VOLCENGINE_TTS_*）是说明，不算泄露。"""
        import os

        if not DELIVER.exists():
            self.skipTest("deliver 尚未生成")
        secrets = [
            v for k, v in os.environ.items()
            if k.startswith(("VOLCENGINE_", "ARK_", "DASHSCOPE_", "BAILIAN_", "MODELSCOPE_"))
            and v and len(v) >= 12
        ]
        for path in DELIVER.rglob("*"):
            if not path.is_file() or path.suffix.lower() in VIDEO_EXT:
                continue
            if path.suffix.lower() in (".json", ".txt", ".srt", ".md", ".html", ".js", ".css"):
                text = path.read_text(encoding="utf-8", errors="ignore")
                for secret in secrets:
                    self.assertNotIn(secret, text, f"{path} 含真实密钥值")
                self.assertNotIn("Bearer;", text, f"{path} 含鉴权串")
                self.assertNotIn("Expires=", text, f"{path} 含短时效签名 URL")

    def test_deliver_files_exist_for_finished_step(self):
        for name in ("zhouchu_30s.srt",):
            self.assertTrue((DELIVER / name).exists(), f"缺少 deliver/{name}")


if __name__ == "__main__":
    unittest.main()
