# 素材权利与来源（LOOP-001）

> 依据规划案 §7.2 U12「账号授权」与 §5.7「纯代码兜底（必实现）」。
> 原则：**不编造授权依据**。未独立证实的授权一律不宣称可商用。

## 1. 静态画面（14 张）

| 项目 | 情况 |
|---|---|
| 来源 | `mcode-tools connector__matrix__generate_image`，9:16 / 2K，原始 1536×2752 |
| 性质 | 由本账号调用的图像生成服务产出的**静态图** |
| 是否调用视频生成模型 | **否**。全仓库无任何文生视频 / 图生视频调用，素材目录无 .mp4/.mov |
| 授权状态 | **未独立证实**。本轮未取得该账号服务条款的可核链接或书面授权文本，因此**不宣称**这些图具备「可商用 / 可再分发」的确定授权 |
| 实际交付范围 | 本片作为**个人作品交付**给用户；如需公开发布或商用，应先取得服务条款证据或改用程序化原创静帧 |
| 溯源 | `work/asset-manifest.json` 逐张记录 prompt、node_id、尺寸、sha256、生成日期、source_type=still、rights_status |
| 失败降级 | `scripts/assets.py` 内置 Pillow 程序化水墨静帧兜底（不留灰块、不留占位）。本轮 14 张**全部为远端生成，0 张降级** |

**若需严格可商用**：执行 `scripts/assets.py --force` 并把 `rights_status` 设为 `procedurally synthesized in project`，全部改为程序化原创静帧（见下方 §3 的同一套绘制能力）。这是规划案 §7.2 U12 的默认分支 C。

## 2. 背景音乐

| 项目 | 情况 |
|---|---|
| 最终采用 | **程序化合成**（`scripts/audio_mix.py`，NumPy 48k 立体声） |
| 权利来源 | `procedurally synthesized in project` —— 全部由本仓库代码按固定 seed（20261025）合成，无外部采样、无第三方曲库 |
| 构成 | 五声音阶拨弦（基频 + 2/3 倍频谐波，0.18s 指数衰减）、82→46Hz 扫频低鼓、6kHz 低通木击、箫声持续音、≤-32dBFS 水声；92 BPM；能量弧线 0–12s / 12–20s / 20–26s / 26–30s；末 1.2s cosine 淡出 |
| 可重复性 | 同 seed 同输出，可逐字节复现 |
| 音乐生成服务候选 | 本轮曾调用 `connector__matrix__batch_text_to_music` 生成 3 条候选并记录于 `reports/audio-measure.json` 的 `bed.generator_candidates`。**其账号条款同样未独立证实**，因此**未采用**，仅作备选记录 |
| 本机既有 BGM | `/Users/sheng/Downloads/大国重器.mp3` 仅作试听对照，**未使用**——不凭文件存在推定许可 |

## 3. 配音

| 项目 | 情况 |
|---|---|
| 来源 | 豆包 TTS（`openspeech.bytedance.com/api/v1/tts`），voice_type 由环境变量 `VOLCENGINE_TTS_VOICE_TYPE` 指定 |
| 授权状态 | 与 §1 同：账号条款未独立证实，不宣称商用授权 |
| 凭据处理 | token/secret 只从环境变量读取，**不写入任何文件、不打印、不入库**（`tests/test_provenance.py` 对交付目录做凭据串扫描） |
| 兜底 | 三次失败降级 `macOS say -v Tingting`；本轮未触发 |

## 4. 字体

| 项目 | 情况 |
|---|---|
| 使用 | macOS 系统内置：Songti SC（宋体）、Kaiti SC（楷体）、Noto Sans CJK SC、Hiragino Sans GB |
| 授权 | 系统自带字体，随操作系统授权用于文档与创作用途；**未随仓库分发字体文件**（film/ 与 deliver/ 内无 .ttf/.otf/.woff2） |
| 降级 | 若某字形缺失，用 Noto Sans CJK SC Bold 兜底并记录 |

## 5. 文字内容

- 旁白与字幕均改写自《世说新语·自新》第十五（南朝宋刘义庆）。**公有领域**。
- 片中出现「邅迹虎（跛脚虎）」「清河｜陆云」等注释文字，均为本项目自撰。
- 画面内无任何生成式文字、水印或他人素材标识。

## 6. 结论

- 本片**不含任何 AI 生成的视频素材**，也不含第三方影视片段。
- 静态图与配音的**商用授权未独立证实**；背景音乐与程序蒙版为自制，权利清晰。
- 交付给用户的用途为本机欣赏/个人项目；如需公开发布，建议先按 §1 的说明替换为程序化原创静帧，或取得服务条款证据后在 `deliver/manifest.json` 中更新 rights_status 并在此文件补记依据。
