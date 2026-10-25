<!-- sflipmloop-handoff
kind: brief
task: LOOP-001
round: 1
nonce: 5b2ec1bd2aed922d
-->

# 简报 LOOP-001：30 秒《周处除三害》叙事短片（禁用一切视频生成模型）

## 任务

用户原话：「做一个30秒的周处除三害的视频，要求还原《世说新语》的这个故事，并且呢，这个有配音，有背景音乐，然后快节奏的这么一个故事叙事，然后画面丰富。然后画面如果有一些特效就更好了。」

追加硬约束：「**在不使用大模型直接生成视频，就是文生视频这种形式下**」。

我的理解：交付一支 30 秒中文叙事短片，还原《世说新语·自新》周处故事。**画面不得由任何视频生成模型产出**（文生视频、图生视频一律禁止），必须由静态图 + 代码合成（运镜、转场、叠加层、动态图形、水墨粒子等特效）做出来。必须有中文旁白配音、背景音乐、快节奏推进、画面丰富。

## 验收（逐条可判定）

1. 成片时长 `30.0s ± 0.3s`（`ffprobe -show_entries format=duration`），H.264 + AAC，短边 1080，画幅由规划案定死。
2. 音轨含中文旁白 + 底层 BGM；旁白段平均响度 `-16 LUFS ±1`，真峰值 `≤ -1.5 dBTP`，BGM 不盖过人声（旁白段人声/底噪比 ≥ 12 dB）。
3. **无 AI 视频素材**：仓库内不存在来自文生视频/图生视频模型的 `.mp4/.mov` 素材；所有画面可追溯到「静态图 + 合成代码」，构建脚本内无任何视频生成 API 调用。
4. 旁白覆盖原文六个节点且无杜撰：三害设定 → 乡人激将 → 杀虎斩蛟（三日三夜） → 乡人相庆 → 寻陆云「人患志之不立」 → 改励「终为忠臣孝子」。
5. 硬字幕逐句对齐旁白（SRT 时间码与旁白音频偏差 ≤ 0.2s），字幕对比度 ≥ 4.5:1，不遮挡主体。

## 原文（唯一事实来源，出处：南朝宋刘义庆《世说新语·自新》第十五，中华书局本）

> 周处年少时，凶强侠气，为乡里所患；又义兴水中有蛟，山中有邅迹虎，并皆暴犯百姓。义兴人谓为三横，而处尤剧。或说处杀虎斩蛟，实冀三横唯馀其一。处即刺杀虎，又入水击蛟，蛟或浮或没，行数十里，处与之俱。经三日三夜，乡里皆谓已死，更相庆。竟杀蛟而出。闻里人相庆，始知为人情所患，有自改意。乃自吴寻二陆，平原不在，正见清河，具以情告，并云：「欲自修改，而年已蹉跎，终无所成。」清河曰：「古人贵朝闻夕死，况君前途尚可。且人患志之不立，亦何忧令名不彰邪！」处遂改励，终为忠臣孝子。

附注（刘孝标注引《孔氏志怪》）：「义兴有邪足虎，溪渚长桥有苍蛟，并大啖人。」——**「邅迹虎」为跛脚虎**，后世多作「白额虎」；立意时以「邅迹虎」为准并在片中以字幕点出，两种称法不可混用。周处字子隐，义兴（今江苏宜兴）人。

**事实红线**：周处最后「力战而没」「终为忠臣孝子」是原文结论，可在片中作为收束；**不得添加原著没有的情节**（如虚构的师父、虚构的女子、虚构的官职升迁）。陆机陆云为「二陆」，陆机任平原内史故称「平原」，陆云任清河内史故称「清河」。

## 本机环境事实（已逐条实测，规划案可直接依赖）

**硬件/系统**：macOS 25.4.0 arm64（Apple M5 Max，18 核，64GB RAM），磁盘余量 159GB，无 TTY。

**渲染与合成**
- `ffmpeg` / `ffprobe` **8.1.1**（`/opt/homebrew/bin`）：`libx264`、`aac`、`libmp3lame` 可用；`zoompan` `drawtext` `subtitles` `xfade` `fade` `overlay` `gblur` `vignette` `noise` `colorchannelmixer` `afade` `amix` `loudnorm` 等滤镜均在。**无 ImageMagick**，但 Python `PIL 11.3.0` 可用。
- **HyperFrames v0.8.104 可用**（`npx --yes hyperframes@0.8.104`）：HTML + GSAP → MP4 的合成引擎，正好覆盖「静态图 + 运镜 + 转场特效 + 字幕」这条路。关键子命令：`init` `render` `lint` `check` `validate` `inspect` `snapshot` `keyframes` `beats`（从 BGM 检节拍，用于快节奏卡点）`transcribe`（字级时间戳）`normalize-audio`（LUFS 对齐）`grade-compare` `compare` `benchmark` `doctor` `timeline` `media-treatment`。
- `hyperframes doctor` 实测：Node ✓ / FFmpeg ✓ / Chrome ✓（系统 Chrome + puppeteer `chrome-headless-shell` mac_arm-149）/ whisper-cpp ✓ / Docker 未运行（**不影响本机渲染**）；可选缺失项：本地 Kokoro TTS、本地 MusicGen 模型、`onnxruntime-node`、`@google/genai`（首次用到时自动安装）。
- **既有可复用先例**（同机已有跑通的「中文旁白 + 首帧图 + 重定时 + 混音 + 硬字幕 + contact sheet + 打包」流水线，可直接抄结构，不要从零发明）：`/Users/sheng/Documents/空间科学-硬件部分视频/trojan_myth_skill_work/`（`scripts/prepare_trojan_myth.py`、`scripts/build_trojan_myth_final.py`：concat/retime/`amix`/硬字幕/contact sheet/打包；`segments.json` 字段结构；`旁白文案_250字.txt`），以及 `/Users/sheng/Documents/空间科学-硬件部分视频/tools/`（`build_space_weather_version_asr.py`、`burn_srt_with_pil.py`、`realign_srt_from_whisper_words.py`）。先例规格：**剪辑基准 = 旁白音频 + SRT 是唯一时间权威**；BGM 音量 0.56、尾部 `afade` 2s 淡出。

**静态图（本片画面来源）**
- ✅ 可用：`mcode-tools connector call connector__matrix__generate_image --args '{"requests":[{"prompt":"...","aspect_ratio":"9:16","resolution":"2K","output_file":"xx"}]}'` → 返回 `node_id` → `mcode-tools get-asset-url <node_id>` 下载（短时效 URL，需立即 curl 落盘）。
  **实测 1/1 成功**：9:16 / 2K → **1536×2752 JPEG**；「晋代义兴乡野，水墨写意与工笔结合，佩剑少年立于溪畔」提示词产出的**绢本设色山水**质感准确，风格与《世说新语》主题匹配。`aspect_ratio` 支持 `9:16 / 16:9 / 1:1 / 4:3 / 3:4 / 21:9`，`resolution` 支持 `1K/2K/4K`。
- ❌ 不可用：`~/.claude/skills/ark-image/ark-image.sh`（seedream）**实测 HTTP 401**——`ARK_API_KEY` 与 `DOUBAO_API_KEY` 均为 27 字符占位串，端点鉴权不通过。**不要把它写进方案**。

**中文配音（旁白）**
- ✅ 可用：豆包 TTS `POST https://openspeech.bytedance.com/api/v1/tts`。**实测 code=3000 成功**，请求格式（三处都必需，缺一报 3001）：body 需 `app:{appid,token,cluster}` + `request.reqid` + header `Authorization: Bearer;<token>`（**分号，不是空格**）。环境变量 `VOLCENGINE_TTS_APP_ID` / `VOLCENGINE_TTS_ACCESS_TOKEN` / `VOLCENGINE_TTS_SECRET_KEY` / `VOLCENGINE_TTS_CLUSTER` / `VOLCENGINE_TTS_VOICE_TYPE` 已配置（当前 voice_type 为 `ICL_zh_female_qingtiantaotao_cs_tob`）。
- **语速实测**：41 字 → 8.88s ≈ **4.6 字/秒**。据此，30 秒旁白字数落在 **128–150 字**（含标点约 135–160 字符）为合理区间。
- 备选：IndexTTS2（`MODELSCOPE_API_TOKEN` 已配，先例脚本 `trojan_myth_skill_work/scripts/generate_indextts2.py` + 本地 venv `.venv`，需参考音频克隆音色）；macOS `say -v Tingting`（zh_CN，零依赖兜底）。
- ⚠️ 中文字级 ASR 对齐：本机 whisper 模型只有 `~/.cache/whisper-cpp/ggml-small.en.bin`（**英文**）与 OpenAI whisper-python 的 `~/.cache/whisper/small.pt`（多语言，但 Python `whisper` 包未安装）。**中文字级时间戳需另配方案**（例如先例里 `realign_srt_from_whisper_words.py` 的思路，或用豆包 ASR 能力，或按 TTS 分句时长比例对齐）。这是本轮最大的一处技术未知，规划案请给出确定方案。

**背景音乐**
- ✅ 可用一：`mcode-tools connector__matrix__batch_text_to_music`（最多 5 首/次，返回 `node_id` → `get-asset-url` 下载；纯器乐不传歌词）。
- ✅ 可用二：本机已有成品 BGM `/Users/sheng/Downloads/大国重器.mp3`（先例用过，史诗向）。
- ⚠️ 本机**没有** HyperFrames 的本地 MusicGen 模型（`doctor` 显示未装，装它要拉 torch + transformers，重）。`hyperframes beats` 可从任意 BGM 检节拍供卡点。

**中文字体**（系统内置，实测 `fc-list` 105 条 CJK）
`Songti SC`（宋体，Light/Regular/Black）、`Kaiti SC`（楷体）、`Heiti SC`、`Noto Sans CJK SC`（Thin/Light/Regular/Medium/DemiLight/Bold/Black 共 7 档）、`Hiragino Sans GB`、装饰体 `隶变-简` `行楷-简` `翩翩体-简` `雅痞-简`。**没有思源宋体 / Source Han Serif**——若规划案想要更讲究的宋体，需联网下载 woff2 放入 `fonts/`（网络可用，github 200）。

## 本轮范围

**做**
- 30 秒成片（MP4）+ SRT + 旁白文案 + 打包交付目录。
- 静态图素材（seedream 路线连接器）+ 合成管线（HyperFrames 或 ffmpeg 管线，二选一由规划案定）。
- 中文旁白配音、BGM、硬字幕、音量规范化。
- 画面特效：运镜、叠化/转场、水墨/粒子/光影等**代码合成**特效（不得是视频生成结果）。

**不做**
- 任何视频生成模型调用（文生视频 / 图生视频 / 首尾帧生视频）——**用户的硬约束**。
- 真人配音/真人拍摄素材。
- 长视频（只做 30 秒这一条）、多语言版本、系列化 IP。
- 不配置/不触发/不等待 CI。

## 不用管

- `/Users/sheng/Documents/空间科学-硬件部分视频/` 下除上述 5 个先例脚本外的其它工程（空间天气、实验评估分系统等历史项目，与本片无关）。
- `handoff/spec/` 下两份文件由本机提供，你直接读。
- HyperFrames 的 `publish`/`cloud`/`lambda`/`cloudrun`（部署到云）、`capture`（抓网站）、`add`/`catalog`（装组件块）、`history`。

## 已试过不行的做法

- `ark-image.sh`（seedream 直连）→ 401，占位 key，不要重试。
- 豆包 TTS 只带 header 传 key → 3001；**body 里必须有 `app` 与 `request.reqid`，且 Authorization 用分号**。

## 请你输出

见 `handoff/spec/plan-spec.md` —— 按那 10 节写完整规划案。
见 `handoff/spec/design-quality-bar.md` —— 设计与体验的硬性质量线，你的规划必须落在这条线之上。

特别要求：
- **先上网调研**这一类工作当下做得最好的东西（30 秒中文历史故事/典故叙事短片、短视频竖屏叙事、动态图形与运镜、卡点剪辑、无障碍字幕与响度标准），列出你调研过的**具体来源**（产品名/网站/规范 + 你从它学到了什么），再动笔。查不到就写「未能查证」并列入未知清单，**不许编造来源**。
- **零提问**：执行方不会回来问你，每个决策都要定死，不许出现「建议 / 可以考虑 / 视情况 / 按需」。
- **美学可判定**：给具体 hex、px/rem、字阶比例、cubic-bezier、对比度数值、时长与音量数值，不许写「高级感」「简洁大气」。
- 给出：设计语言（令牌表 + 组件规格）、体验设计（信息架构/关键旅程/四态/响应式/无障碍）、关键实现细节与边界处理、按依赖顺序的任务拆解（每项含前置条件/步骤/位置/产物/自查/测试/完成条件）、未知信息的调查入口与分支、本机测试与视觉自检要求、首次交付产物、遇困处置规则。
- **未知项两类都要写全**：有入口的给真实入口（命令/页面/文件/链接 + 怎么判断 + 分支 + 耗时上限）；查不到入口的，给「待查内容 / 怎么查 / 受影响的决策项及分支取值 / 默认取值」。任何一条未知都不许留白。
- 特别请你把两处定死：① **中文字级字幕对齐**的确定方案（见上面「中文字级 ASR 对齐」）；② **画幅**——用户未指定，默认按短视频竖版 **1080×1920** 规划；若你调研后认为横版更优，必须在规划案里明确写出并给出理由，不能默默改。
- 不要用「自行实现」「完善功能」略过难点；不要编造文件路径、API 或命令；不要编造调研来源。

## 附：本机已验证的探针产物（供你判断可行性，不必读）

`/tmp/zk_probe/probe_zc_01.jpg`（1536×2752，绢本设色山水，9:16 2K 出图实测成功）、`/tmp/zk_probe/tts_probe.mp3`（豆包 TTS 实测成功，41 字 8.88s）。这两个文件在本轮正式实现时会用真实素材重新生成，**不要**把它们当作最终素材方案。
