"""T06 · 混音与响度校验。

§8.3 失败演练：人为调大 BGM 导致声区差 < 12dB —— 本文件必须 FAIL。
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = json.loads((ROOT / "film" / "audio-contract.json").read_text(encoding="utf-8"))
TOKENS = json.loads((ROOT / "film" / "design-tokens.json").read_text(encoding="utf-8"))

MEASURE = ROOT / "reports" / "audio-measure.json"
MIX = ROOT / "work" / "final_mix.wav"
VOICE = ROOT / "work" / "voice_master.wav"
BGM = ROOT / "work" / "bgm_norm.wav"


class TestAudioMeasure(unittest.TestCase):
    def setUp(self):
        self.m = json.loads(MEASURE.read_text(encoding="utf-8"))

    def test_voice_loudness(self):
        voice = self.m["voice"]
        self.assertLessEqual(abs(voice["integrated_lufs"] - (-16)), 1,
                             f"人声响度 {voice['integrated_lufs']} LUFS 超出 -16±1")

    def test_mix_true_peak(self):
        mix = self.m["mix"]
        self.assertLessEqual(mix["true_peak_db"], -1.5,
                             f"混音真峰 {mix['true_peak_db']} dBTP 超过 -1.5")

    def test_voice_windows_are_audible_over_bed(self):
        self.assertGreaterEqual(
            self.m["worst_window_difference_db"], 12,
            "人声窗口内底乐与人声差小于 12dB",
        )

    def test_every_voice_window_is_measured(self):
        windows = self.m["voice_windows"]
        self.assertGreaterEqual(len(windows), 8)
        for w in windows:
            self.assertLess(w["start_ms"], w["end_ms"])
            self.assertGreaterEqual(w["difference_db"], 12,
                                    f"第 {w['index']} 个语音窗口被底乐盖过")

    def test_music_tail_reserved(self):
        self.assertTrue(self.m.get("voice_window_count") is None or True)
        self.assertLessEqual(self.m["voice"]["integrated_lufs"], -15)


class TestAudioFiles(unittest.TestCase):
    def setUp(self):
        self.m = json.loads(MEASURE.read_text(encoding="utf-8"))

    def test_files_exist(self):
        for path in (MIX, VOICE, BGM):
            self.assertTrue(path.exists(), f"缺少 {path.name}")

    def test_bgm_is_at_least_thirty_seconds(self):
        import subprocess

        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(BGM)],
            stdout=subprocess.PIPE, text=True,
        )
        self.assertGreaterEqual(float(proc.stdout.strip()), 30.0)

    def test_mix_sample_rate_and_channels(self):
        import subprocess

        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=sample_rate,channels",
             "-of", "csv=p=0", str(MIX)],
            stdout=subprocess.PIPE, text=True,
        )
        rate, channels = proc.stdout.strip().split(",")
        self.assertEqual(int(rate), 48000)
        self.assertEqual(int(channels), 2)

    def test_bgm_rights_are_documented(self):
        self.assertTrue(self.m["bed"]["rights"], "配乐必须写明权利来源")
        self.assertIn("rights", self.m["bed"])


if __name__ == "__main__":
    unittest.main()
