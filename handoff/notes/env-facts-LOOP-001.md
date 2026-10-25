# LOOP-001 本机能力事实笔记（策展阶段实测）

> 用途：把「规划案落地前必须知道、且在本机已实测过」的事实固化下来，避免执行期重复踩坑。
> 性质：事实调查笔记，非实现代码。实现方案以 `handoff/plans/LOOP-001.md` 为准。
> 所有数据均为本机真实命令输出，非估计值。

## 1. 中文字幕对齐方案（简报中标记的最大未知 → 已收敛）

### 结论：主方案 = 分句 TTS 精确时间轴（零 ASR 依赖，零误差）

**机制**：旁白文案按字幕句切成 N 句 → 每句独立调用豆包 TTS 得到一段音频 → `ffprobe` 量出每句精确时长 → 按序拼接（句间插入设计好的静音间隙）→ 每句的起止时间即字幕时间轴。因为时间轴是从**实际音频**量出来的，不存在 ASR 误差。

**实测（2026-10-25，本机）**：

```
句1: 4.368000 s | 周处年少时，凶强侠气，为乡里所患。
句2: 4.296000 s | 义兴水中有蛟，山中有邅迹虎，并皆暴犯百姓。
=== 拼接 + 200ms 间隙 时间轴 ===
  [ 0.000s →  4.368s] (4.368s) 周处年少时，凶强侠气，为乡里所患。
  [ 4.568s →  8.864s] (4.296s) 义兴水中有蛟，山中有邅迹虎，并皆暴犯百姓。
总时长(含末间隙前): 8.864 s
```

**语速标定**：21 字 / 4.368s = **4.81 字/秒**（含标点）。30 秒旁白的合理字数区间 ≈ **130–150 字**。

### 备选方案：whisper.cpp + 中文多语种模型（仅在需要「独立 ASR 复核」时启用）

- `whisper-cli` 已在 `/opt/homebrew/bin/`，支持 `--output-words`（词级时间戳）与 `--dtw`（token 级）。
- ⚠️ 本机现有模型 `~/.cache/whisper-cpp/ggml-small.en.bin` **只支持英文**，不能用于中文。
- 中文多语种 ggml 模型可从 `hf-mirror.com` 下载（`huggingface.co` 直连返回 000，不通；`hf-mirror.com` 返回 200）。候选：`ggml-small.bin`（约 488MB，多语种）/ `ggml-base.bin`（约 148MB，多语种）。
- 已知先例：`/Users/sheng/Documents/空间科学-硬件部分视频/tools/realign_srt_from_whisper_words.py`（whisper 字级时间戳重对齐既有 SRT 的做法）。
- Python 侧无 `torch` / `openai-whisper` / `faster_whisper`；`pypi.org` 可达（200），装 openai-whisper 需拉 torch，代价大，除非确有必要不用。

### ❌ 不可用：豆包 AUC ASR（字级时间戳）

- 接口：`https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit` + `/query`，资源 `volc.bigasr.auc`，请求体 `request:{model_name:"bigmodel", enable_itn:true, enable_punc:true, show_utterances:true}`，返回 `result.utterances[].words[]` 逐字时间戳（毫秒）。
- 凭据复用 `VOLCENGINE_TTS_APP_ID` / `VOLCENGINE_TTS_ACCESS_TOKEN`（`/Users/sheng/Documents/空间科学-硬件部分视频/doubao_asr_timestamp_test/probe_doubao_asr_timestamps.mjs` 如此写，且 2026-06-15 实测通过：样本1 PaddleSpeech 中文 WAV 文本完全一致、句级+字级时间齐全）。
- **本轮实测 2026-10-25 失败**：`submit` 返回 `45000030 [resource_id=volc.bigasr.auc] requested resource not granted` —— 当前 TTS 应用**未被授予** ASR 资源。
  → 实现期**不要**把豆包 AUC ASR 写进方案，除非先解决资源授权。

## 2. 其它链路实测结论

| 能力 | 状态 | 证据 / 备注 |
|---|---|---|
| 静态图生成 | ✅ 可用 | `mcode-tools connector call connector__matrix__generate_image`，9:16/2K → 1536×2752 JPEG，实测 1/1 成功，水墨绢本质感达标 |
| 图生图 | ✅ 参数支持 | 同工具的 `input_urls` 字段（先例 segments.json 用它做风格统一首帧） |
| 中文配音 | ✅ 可用 | 豆包 TTS `api/v1/tts`，`code=3000`，**三处必需**：`app:{appid,token,cluster}` + `request.reqid` + header `Authorization: Bearer;<分号>` |
| 本地上传取公网 URL | ✅ 可用 | `mcode-tools upload-temp-url <file>` → 临时 URL，有效期 3600s |
| 音乐生成 | ✅ 可用 | `mcode-tools connector__matrix__batch_text_to_music`，最多 5 首/次，返回 node_id |
| 现成 BGM | ✅ 可用 | `/Users/sheng/Downloads/大国重器.mp3`（先例用过，史诗向） |
| HyperFrames | ✅ 可用 | v0.8.104；`doctor` 全绿（Node/FFmpeg/Chrome/whisper-cpp）；Docker 未运行但本机渲染不需要 |
| ffmpeg | ✅ 可用 | 8.1.1，libx264 + aac；`zoompan/drawtext/subtitles/xfade/fade/overlay/gblur/vignette/loudnorm/amix/afade` 全在 |
| 中文字体 | ✅ 充足 | Songti SC（Light/Regular/Black）、Kaiti SC、Heiti SC、Noto Sans CJK SC（7 字重）、Hiragino Sans GB、隶变-简/行楷-简/翩翩体-简/雅痞-简；**无思源宋体/Source Han Serif** |
| seedream 直连 | ❌ 401 | `ARK_API_KEY` / `DOUBAO_API_KEY` 均为 27 字符占位串，端点鉴权不通过 |
| 豆包 AUC ASR | ❌ 45000030 | 资源未授权（见上） |
| Docker | ❌ 未运行 | 本机渲染不需要，不影响本轮 |

## 3. 先例工程（可直接抄结构，不要重新发明）

根目录：`/Users/sheng/Documents/空间科学-硬件部分视频/`

| 路径 | 可复用内容 |
|---|---|
| `trojan_myth_skill_work/scripts/build_trojan_myth_final.py` | 完整成片装配：重定时 concat → `amix` 混音 → 硬字幕烧录 → contact sheet 抽帧 → 交付打包（416 行） |
| `trojan_myth_skill_work/scripts/prepare_trojan_myth.py` | 分镜/素材准备与 `segments.json` 字段结构（shot / subtitle_start / subtitle_end / start / end / duration / segment_copy / image_prompt / video_prompt） |
| `trojan_myth_skill_work/旁白文案_250字.txt` | 250 字中文故事旁白的写法样例（语速与断句参考） |
| `tools/build_space_weather_version_asr.py` | 以旁白音频 + SRT 为唯一基准的剪辑装配 |
| `tools/burn_srt_with_pil.py` | 用 PIL 精确绘制居中硬字幕（描边 + 高对比） |
| `tools/realign_srt_from_whisper_words.py` | whisper 字级时间戳重对齐 SRT |
| `剪辑基准_以spk音频和SRT为准.md` | 剪辑纪律：**旁白音频 + SRT 是唯一时间权威** |

先例混音参数（可直接沿用）：BGM 音量 `0.56`、尾部 `afade out 2s`、`amix inputs=2 duration=first dropout_transition=0`。

## 4. 交付包约定（先例沿用）

硬字幕 MP4 + 纯净版 MP4（无硬字幕）+ SRT（UTF-8 with BOM）+ 官方旁白文案 + 首帧/封面图 + 旁白音频 + BGM + 交付说明；默认 `zip -r "<名字>_无密码.zip"`。
