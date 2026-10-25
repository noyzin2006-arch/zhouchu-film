kind: plan
task: LOOP-001
round: 1
nonce: 5b2ec1bd2aed922d
brief_sha: 8248c9b7f101fa8bef459e5b793d4baa2eb7b9ac

# LOOP-001 ·《周处除三害》30 秒竖屏叙事片 · 一次性交付规划

规划日期 2026-10-25。规划角色：首席设计与首席规划顾问；实施由本机 Agent 独立完成。本轮只读取允许的三个仓库文件，未查看仓库其余部分。受控输入：brief blob 8248c9b7f101fa8bef459e5b793d4baa2eb7b9ac；plan-spec blob 01a51bbde14c05b27df30364240d9fc9169540af；design-quality-bar blob d11c1410d71c9ac2c8819b43ba82588ba2d7a738。以下新增路径是**将要创建的交付目标**，不暗示仓库当前已有这些文件。

## 1. 需求、范围与非目标

### 1.1 核心目标
原话：「做一个30秒的周处除三害的视频，要求还原《世说新语》的这个故事，并且呢，这个有配音，有背景音乐，然后快节奏的这么一个故事叙事，然后画面丰富。然后画面如果有一些特效就更好了。」硬约束：「在不使用大模型直接生成视频，就是文生视频这种形式下」。

**明确决策**：30.000s、1080×1920 px、9:16 竖屏、30fps、900 帧；H.264/yuv420p 和 AAC/48kHz 双声道。影像只能来自**生成的原创静态图 + HTML/CSS/GSAP/FFmpeg/Pillow 代码合成**；禁止文生视频、图生视频、首尾帧生视频、视频扩展/插帧模型。可用静态图生成、TTS 和纯器乐生成。风格固定为西晋江南意象的绢本设色、水墨影戏，绝非照片幻灯片。主生产方案：**HyperFrames 0.8.104 渲染静音视觉（包括硬字幕）；FFmpeg 8.1.1 独立完成混音与封装**。全片由声轨时间确定剪辑轴，不让画面预设时长挤压语音。

原文唯一剧情真源是 brief 给出的《世说新语·自新》第十五：乡里三害（邅迹虎、蛟、周处）→乡人劝杀实盼三横剩一→周处刺虎追蛟，经三日三夜→乡人误以为死，互相庆贺→周处知耻决意改过→至吴寻二陆，只见陆云，闻「人患志之不立，亦何忧令名不彰」→改励而为忠臣孝子。不得增加师徒/女子/官职/虚构死亡情节。邅迹虎旁注为“跛脚虎”，禁以“白额虎”当同一版片中文字；对话者是**陆云**（清河），不是陆机（平原）。

### 1.2 范围内及外
内：原典校核与8句台词；原创静帧≥14张及12个镜头；2.5D 视差、平移推拉、墨浪/雨雾/粒子/印章程序特效；中文 TTS、纯器乐 BGM、两分轨及音量测量；字级时间对齐、SRT、硬字幕；MP4、台本、封面、联系表、素材 provenance、打包；本机自动及人工验收；一个**离线校阅页**专用于查看成片和验收四态，无线上部署。
外：任何 AI 视频片段、真人拍摄/配音、横屏和多语言、连续剧情系列、交互影视网页 App、云渲染、CI、PR、部署、搬运影视素材、未经证实的商用音乐授权。过往空间科学项目不纳入工程。

### 1.3 硬验收（编号是后文唯一参照）
- A01：ffprobe 的 duration 29.700–30.300s，实际目标=30.000s；width=1080,height=1920，30/1 CFR、nb_frames=900，视频 h264、音频 aac/48k、没有其他视频流。
- A02：独立的**人声 stem**有效旁白平均 -16 LUFS±1，最终混合音频真峰≤-1.5 dBTP；每个有声窗口人声 RMS 比 BGM 大≥12 dB，目标18 dB；耳听无削波，语音不被鼓点盖过。
- A03：六个原文情节节点全覆盖；关键「三日三夜」「人患志之不立」「终为忠臣孝子」逐字正确；不编造剧情与服装事实，不混陆机/陆云。
- A04：≥12 个明显不同场景、≥14张可追溯静图、每场至少一种真实动态合成特效；静止同图不可连续超过2.3s；视觉镜头与语义因果一致。
- A05：字幕与 TTS 从唯一 word/char timing 真源派生，字幕短语出入声偏差≤0.20s；字级数据每汉字有可查时间；每行≤13汉字/最多两行；正文对比≥4.5:1、不遮主角。
- A06：项目素材 manifest 表明每张图是 still image、每个音源是 voice/music；没有任一视频生成接口/素材文件；脚本只用图、字幕、SVG、程序粒子制作视觉，原始构建视频仅出现在 work/render 与最终 deliver 目录。
- A07：本机真渲染与完整回放成功；375px、1440px 离线预览实测、默认/空/加载/错误/成功态、键盘与 reduced-motion 自检，质量线 A–G 有量化记录。
- A08：所有最终文件 hash 可查，无令牌/过期 asset URL 入库；执行报告包括原始测试 stdout、ffprobe、响度与字幕抽样，不冒充手机真机/未做的测试。

### 1.4 依赖与环境边界
简报声明已实测：macOS 25.4.0 arm64 M5 Max/64GB；FFmpeg/FFprobe 8.1.1 有 libx264,aac,zoompan,overlay,subtitles,loudnorm；Pillow 11.3；系统有 Songti SC、Kaiti SC、Noto Sans CJK SC；HyperFrames 0.8.104 doctor Node/FFmpeg/Chrome/whisper-cpp 通过但 Docker 未开（本地渲染不需要 Docker）；mcode-tools 图片 9:16/2K 返回1536×2752 JPEG 成功；豆包 TTS 41字/8.88s 成功，auth 必须 Bearer; + token，body app/request.reqid 齐全。以上是**简报给出的本机事实**，远程服务可用性在执行日仍要重新实测。不得重试已知 401 的 ark-image.sh；不得依赖 ImageMagick 或英文 small.en 模型做中文对齐。浏览器校阅目标 Chrome/Safari；视频目标主流竖屏播放器。

## 2. 已联网调研的高水准参照与学习结论

### 2.1 五个可核作品/产品（不虚构榜单）
| 已查证参照 | 实际可核特点与要学的点 | 本片采用 | 明确不抄 |
|---|---|---|---|
| TED-Ed《The Chinese myth of the white snake and the meddling monk》https://ed.ted.com/lessons/the-chinese-myth-of-the-white-snake-and-the-meddling-monk-shunan-teng | 中国古代故事可由配音+清晰动画场景串联，视觉承载因果 | 8个声段串12镜，先因果后炫技 | 不移植白蛇传人物/绘画/配乐，不将神话当史料 |
| TED-Ed《The incredible history of China's terracotta warriors》https://ed.ted.com/lessons/the-incredible-history-of-china-s-terracotta-warriors-megan-campisi-and-pen-pen-chen | 中国历史动画作品官方明确署名 educator、script、artist、animator、narrator、sound designer 的协作分工 | 给镜头/文本/音效/字幕各设唯一责任数据，素材逐项归档 | 不抄其长篇 5分钟叙述节奏和插画 |
| Netflix《Blue Eye Samurai》官方 https://www.netflix.com/tudum/articles/blue-eye-samurai-release-date | 官方称其为 2D/3D 混合、强调手工二维视觉感；仅作**材质与层次**参照 | 静态图分层错动、绢本纹理统一、人物轮廓让位给叙事 | 不复制日本江户服装/和服/武士刀、不宣称晋服已有确证复原 |
| Art of the Title 官方 https://www.artofthetitle.com/about/ | 专业影视标题序列设计出版物，提供标题层次和视觉节奏的研究范式 | 0–1s 的反差钩子与末1.8s落款用两级汉字层次 | 不复制任意知名片头/Logo，不拖长开场 |
| Remotion Recorder/Captions 官方 https://www.remotion.dev/docs/recorder 和 https://www.remotion.dev/elements/captions/ | 官方示范字词级时间、可编辑JSON、分组字幕和强调机制 | char timing JSON → SRT/硬字幕同源；孤行避免；名句缓显而非跳字 | 不接第二套 React 渲染器，不以英语ASR推测古文 |

五项为**技法和行业高质量参照**，不是经过证实的2026全球短视频排名。权威的“30 秒中文典故最佳榜单”**未能查证**，列 U10。

### 2.2 标准、设计系统、当下技术来源（实际查到的页面）
1. TikTok 官方 Creative Codes https://ads.tiktok.com/business/en-US/creative-codes ：明确9:16原生画幅、留 UI 安全区、Hook–Body–Close；定片头1s、保底安全边距，竖屏胜过横屏。
2. BBC 社交内容格式指南的网页副本 https://bbcstreaming.pages.dev/delivery/online-content ：列 1080×1920、MP4 和烧录字幕等交付示例；页面属于转存副本，**不当作 BBC 官方实时最新政策证明**。
3. HyperFrames 官方渲染 https://hyperframes.app/docs/3-guides/4-rendering 、GSAP https://hyperframes.app/docs/3-guides/3-gsap-animation 、timing schema https://hyperframes.app/docs/2-concepts/2-data-attributes 和提示 https://hyperframes.app/docs/3-guides/2-prompting ：证实 paused GSAP timeline、window.__timelines、clip 的 data-start / data-duration / data-track-index，render/preview/lint、seek 驱动，无 Math.random/JS 控制视频播放。
4. WhisperX 官方 https://github.com/m-bain/whisperX 及 CLI 源码 https://github.com/m-bain/whisperX/blob/main/whisperx/__main__.py ：确认 return_char_alignments 参数、Mandarin 专属对齐模型与 macOS CPU int8 路线；模型 https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn ，**尚未在本机验证**。
5. FFmpeg 过滤器与 ffprobe 官方 https://ffmpeg.org/ffmpeg-filters.html 和 https://ffmpeg.org/ffprobe.html ：loudnorm 支持 measured_* 双通和真峰控制，容器/码流由 ffprobe 分开验证。
6. EBU R128 2023 https://tech.ebu.ch/publications/r128 ：广播节目常见 -23 LUFS；本片 -16 LUFS 源自 brief 的短视频人声指标，**不要误称 EBU规定 -16**。
7. W3C WCAG2.2 https://www.w3.org/TR/wcag/ ：字幕媒体提供、正文≥4.5:1、大字/控件≥3:1，非色彩单通道。
8. Apple HIG Motion https://developer.apple.com/design/human-interface-guidelines/motion 和 Accessibility https://developer.apple.com/design/human-interface-guidelines/accessibility ：动效有明确作用、控制晕动、提供减弱动效。
9. Adobe 2.5D 静图教程 https://edex.adobe.com/teaching-resources/adding-dimension-to-2d-art-in-after-effects ：静态层可通过 Z 向与视差表达空间；本片选择克制静图纵深合成。

### 2.3 审美与制作判定
这是基于上述作品的**项目设计判断**，不是捏造行业统计：1s 明确冲突、2–3s 完成一意群、角色行为与同一句声音严格对应、叙事反讽处短暂停鼓、最后以“改过”而非“打怪升级”立意；同一水墨-绢本材质贯穿≥12幅场景，运镜不炫到挡字幕。淘汰做法：一图放30s、无来源影视混剪、全片高频闪白、字幕飘在雪白源图上、任意每字疯狂弹跳、AI 视频冒充静图后期。**最小完成标准：静音观影可读出“作恶—除害—知耻—自新”，闭眼听音可复述全部六节点。**

## 3. 设计语言：唯一令牌与组件规格

### 3.1 design-tokens.json 的不可改定值（本文件定义，执行建文件）
| 类别/token | 值与判定用途 |
|---|---|
| color.bg.base / surface / raised / caption | #101813 / #1D2921 / #2B352B / #101813（字幕罩不透明度 .92） |
| color.text.primary / secondary / muted / inverse | #F5E8CC / #DFCEAC / #C7AF80 / #101813 |
| color.border.strong / subtle | #94856D / #C7AF80；深底的控件边线 ≥3:1 |
| color.accent.gold / cinnabar | #D4A452 / #D84A3B；后者只用于印章、小面积强调，不承载长段正文 |
| color.semantic.ok / warning / error / info | #9BBAA8 / #D4A452 / #F29D91 / #AFA796；必须同步呈现文字及图标 |
| color.focus | #F5E8CC，outline 2px，offset 3px；与hover金色线/选中朱红边不混 |
| type.cn.title/body/annotation | Songti SC Black / Noto Sans CJK SC Bold / Kaiti SC Regular |
| type.cn.stack | "Noto Sans CJK SC","Hiragino Sans GB","Heiti SC",sans-serif |
| type.title.stack | "Songti SC","STSong","Noto Serif CJK SC",serif |
| type.latin.stack | Georgia,"Noto Sans",Arial,sans-serif |
| type.scale | 24/30/38/48/60/75px 六档，约1.25比例；片头独立94px |
| type.leading | 标题1.2；正文1.6；字幕1.54；紧凑控件1.3；字幕字距1px，数字 tabular-nums，正文中文行长≤40字 |
| grid.unit/spacing | 4px基准；间距4/8/12/16/24/32/48/64/96；标签16、字幕内距24、板块24、章节48 |
| radius.tag/button/card/panel/pill | 4/8/12/16/999px |
| border.normal/active | 1px #94856D / 2px #D4A452 |
| shadow.0/1/2 | none / 0 2px 6px #00000033 / 0 8px 24px #0000003D |
| shadow.3/4 | 0 16px 36px #00000052 / 0 24px 48px #00000066；只用于预览浮层，不用于主体影像 |
| z.scene/ink/labels/captions/toast/modal | 0/10/20/30/50/60 |
| motion.micro/switch/scene | 120/220/420ms |
| ease.enter/exit/camera | cubic-bezier(0.22,1,0.36,1) / cubic-bezier(0.4,0,1,1) / cubic-bezier(0.45,0,0.55,1) |
| motion.camera/transition/ink | 1.06–1.13×尺度、平移≤28px；叠化180–260ms；墨痕展开360ms；禁止亮白频闪，≤2次/秒 |
| video.format | 1080×1920，30fps，yuv420p，900帧，sRGB；原图优先 1536×2752 |
| voice/bed/TP | -16 LUFS±1 / 人声窗口配乐RMS比人声低18dB（最低12dB）/ 混音≤-1.5dBTP |
| safe.visible | x=96..878 的文字主区；字幕容器 left=102,right=202, top=1510..1640；上边180px/底部280px禁止关键文本 |

画面字幕 #F5E8CC 对 #101813 约14.9:1；副字 #DFCEAC 对 #1D2921 显著高于4.5:1；#94856D 边线对 #101813 约5:1，禁用仍≥2。计算与截图由验收程序在真实文本上再测，避免底图透光破坏对比。所有 hex 只允许出现在 JSON token 源文件；HTML/CSS/合成代码使用自动生成的令牌引用。以 4px 栅格、固定标题/字幕字阶和≤13字/行使片中文字不会随机断行。

**艺术总规：**西晋江南历史意象而非声称考古精确重建；手绘绢纸/老纸颗粒、深松绿/赭石/淡金与克制朱砂。周处保持「青年、瘦削、深青交领窄袖、褐腰带、束发、背直剑」轮廓，侧背影优先；虎有跛行特征；蛟为水中蛇形巨影无西方龙翼。禁止日式铠甲、现代钢结构、唐明标志性帽/衣、血腥、图中文字/水印、真实影视演员面孔。

### 3.2 可见组件规范（C1–C8）
视频画面为线性媒体，**不是互动网页**；C1–C4 对 hover/focus/键盘/ARIA 本身为 N/A，仍需覆盖数据空/加载/错误/成功构建状态。为落实质量线的交互条款，随包附一个独立、无网络的 preview 页面（C5–C8）。

| 组件 | 构成/几何/状态与反馈 | 空/加载/错误/成功四态 |
|---|---|---|
| C1 场景图层 | img cover 9:16，主体 x=120..850,y=370..1380；无圆角阴影；相机 1.06–1.13×、低速平移/前景雾 12px；不以整图固定30s | 空:抛「场景Sxx缺少静帧」；加载:构建日志「准备Sxx」；错误:列路径及失败原因；成功:保存图尺寸/hash |
| C2 章回文字 | Songti Black 75/94px，左x116/y260，宽≤820，#F5E8CC，金线120px×2；0–1.25s和28.2–30s出现 | 空:缺可选装饰隐藏；加载:留原底图；错误:字裁切则阻止渲染；成功:关键帧截图字体完整 |
| C3 知识旁注/印章 | Kaiti 30px，x=96..440,y=1140..1310；朱砂方章radius4；「邅迹虎｜跛脚虎」「清河｜陆云」各至少1.2s，360ms淡显 | 空/错误:漏任一必备注释 FAIL；加载:沿用有内容画面；成功:未盖主体 |
| C4 硬字幕 | Noto Sans Bold 48px，x=102..878,y=1510..1640，最多2行/行≤13汉字，底罩 bg.caption 92%，padding 18×24,radius12；80ms opacity 显现，单次至少0.65s | 空:无语音时完全消失；加载:最终片严禁“字幕生成中”；错误:时间/换行/对比不合格中止；成功:文字与SRT同源 |
| C5 校阅播放器 | max-width360px、aspect-ratio9/16、border1px、radius12；主按钮44×44；Enter/Space播放暂停，聚焦播放器时方向键seek±5s | 空「成片尚未生成。请运行 python3 scripts/build.py。」；加载「正在读取本地影片…」有进度及10s后「取消加载」；错误「成片读取失败。检查交付目录中的MP4后重试。」；成功「30秒成片已就绪」 |
| C6 播放/重播/下载按钮 | 高44px，宽≥100px，padding 12×16，16px正文、8px圆角、surface背景/border.strong；icon为自绘24px线性SVG 2px线宽、round cap。pointer:hover换raised底、active scale(.97)、focus 2px外轮廓、disabled带aria-disabled文字 | 空「请先生成成片」；加载 aria-busy及100ms反馈；错误邻接role=alert「无法下载：MP4不存在」；成功role=status「下载已开始」 |
| C7 台词/文献折叠区 | 最宽960px，Noto Sans16px/行高1.65；源文与旁白分两个清晰标题；展开仅opacity 220ms，不旋转整屏 | 空「台词尚未生成，请先运行构建脚本」；加载「正在读取台词…」；错误「缺少 narration.txt，检查交付文件」；成功「已载入8句旁白」 |
| C8 状态条 | min-height48px、14px、1px细边、图标+文字，最大宽960px；正常/警告/失败各自semantic色但不能只靠色传达 | 空「尚未运行本机验证」；加载「正在校验媒体指标…」；错误「发现未通过项，查看 validation.json」；成功「已通过媒体与字幕校验」 |

C5–C8 的统一互动完整状态矩阵：默认见表；hover仅@media(hover:hover)使用 raised 底；pressed transform scale(.97)；focus-visible 2px/offset3；disabled opacity .65、aria-disabled=true、忽略激活；loading aria-busy=true、进度文案；error 就地 role=alert 且说明恢复；empty 给构建入口；success 用 role=status。点击后≤100ms 显示状态，重复播放不得叠音；图标按钮有 aria-label，图片有 alt，装饰 alt=""；禁止 emoji。没有破坏性操作，故无虚假二次确认弹窗。

### 3.3 层级、阴影、断点
校阅主容器 max-width1120px、居中；≥1440 留白64px，1024–1439 留白48px，768–1023 留白32px，481–767 留白24px，≤480 留白16px。
- ≥1024 双栏：左380px预览/右1fr台词+测试；768–1023 双栏：左320px/右余量；
- 481–767 单栏：播放器居中，按钮组在视频下方；
- ≤480 单栏：视频宽min(360px,100vw-32px)，控件按需**固定换两行**，不横滚、触区≥44px；
- 字体200%时卡片改一列、行高1.6，标题行长≤40汉字，表格如较宽改纵向条目，不出现水平页面滚动。
图像定宽高防CLS；纯视频不适用页面 hover；静态校阅页 C5–C8 的CSS在 prefers-reduced-motion:reduce 下去掉平移/视差、所有反馈改≤120ms opacity。**已编码MP4无法读取观众 reduced-motion 设置**，报告不得声称视频会自动适配系统设定。

## 4. 完整体验设计与30秒镜头语言

### 4.1 最终旁白脚本 A（严禁即兴增删）
V1：义兴三害：山中邅迹虎，水中恶蛟，还有周处。
V2：乡人劝周处除虎斩蛟，暗盼三害只余其一。
V3：他刺虎，追蛟数十里，三日三夜未归。
V4：乡人以为他死了，竟相庆贺。
V5：周处斩蛟归来，才知自己为人所患，决意改过。
V6：他寻二陆，只见陆云，忧年已蹉跎。
V7：陆云说：人患志之不立，何忧令名不彰！
V8：周处遂改励，终为忠臣孝子。

脚本共116个汉字（不计标点）。V6“二陆”仅在画面旁注解释陆机与陆云，不假造陆机在场；V7完整保留名句要害；“忧年已蹉跎”是原文主旨，不称周处已经垂老。

### 4.2 钩子/剧情/收束与镜头表
**主流程**：观众看到0–1秒的「三害，最凶的是人。」→三害画像→乡人借刀杀害→追杀三日→误以为死，群起庆祝→周处自觉受厌→陆云劝志→改励落字。静音仍可从注释和字幕了解原文；只听声音仍能完整讲述。
镜头预期窗口是**审美位置而非硬剪轴**，最终镜头边界由 TTS 真实字级锚点导出。脚本映射为 V1→S01-S04，V2→S05，V3→S06-S08，V4→S09，V5→S10，V6/V7→S11/S11B，V8→S12。视觉尾帧锁 30.000s。
| 镜头及预期窗口 | 场面/源静帧 | 运镜/特效/文字 |
|---|---|---|
| S01 0–1.4s | 绢纸与三种墨影，少年背影隐现 | 260ms墨痕揭题；94px钩子标题；暗鼓一击 |
| S02 1.4–3.4 | 竹林石径中跛足虎 | scale1.08前推、雾横移12px，「邅迹虎｜跛脚虎」≥1.2s |
| S03 3.4–5.0 | 溪渊桥下蛟影 | -20px pan，墨浪弧线，不画西方飞龙 |
| S04 5.0–6.8 | 周处背影，村民躲避 | scale1.11缓拉远、前景剪影差速移动、章印「周处」 |
| S05 6.8–8.8 | 乡人隔席劝周处 | 画内两个焦点遮罩切换，不添加引号对白 |
| S06 8.8–11.0 | 竹林刺虎剪影 | 朱砂笔锋0.16s斜切、无血浆 |
| S07 11.0–13.9 | 激流中的追蛟背影、S07B浪花特写 | scale1.12斜推、雨线与水纹三层视差 |
| S08 13.9–16.5 | 同一水路晨昏对照 | 三记墨印变景，60px「三日三夜」 |
| S09 16.5–18.9 | 乡人互相相庆，周处不在场 | 缓拉远，音乐急止0.25s，不造尸骨葬礼 |
| S10 18.9–22.1 | 周处斩蛟归来，隔河看村人 | 暗部低饱和、0.35s情绪留白，切面不误读“乡人欢迎” |
| S11 22.1–27.8 | 吴地质朴书斋，两人——周处/陆云；S11B竹简与手势 | 两幅交叉、旁注「清河｜陆云」，名句持续可读≥1.8s |
| S12 27.8–30.0 | 周处背剑走向晴后远山 | 深墨化淡、章印「自新」、终句「终为忠臣孝子」、末1.2s音乐淡出 |

音乐剪辑按声段意义而非全部生硬踩点；相邻镜头标准转场 0.18–0.26s，动作冲突镜头 S06/S07 可用0.10s直接切；同一个场景最长3.2s但其内部必须有可见运镜/前景纹理。关键镜头切入节点依赖真实 voice sample 锚点，每个场景出现的时间前后最多偏离预期窗口0.8s；若语音时长不同，优先保留 V7 引文≥1.8s、S09反讽≥1.6s，压缩前部景不超每景0.4s；镜头数据生成器保存真实帧起止供测试。

### 4.3 校阅页关键旅程与四态
交付信息架构只有一层：header「周处除三害｜30秒」→竖屏播放器→播放/重播/下载MP4/下载SRT→8句可折叠台词→源文与素材出处→测试状态。无账户、登录、服务、导航深层级。媒体可下载保留浏览器前进/后退语义，不拦截。
主操作：进入页面看到加载短文案；≤1s 出现 poster；播放按钮100ms内反馈且能 Space 暂停；方向键5s seek；下载按钮立刻给“下载已开始”；点击「展开完整台词」显示8句，Esc能关闭浮层并将焦点归还。副流程：缺影片时不转圈到无穷而出现明确步骤；失败点击「重试读取」；断网不影响离线包已保存资源。
固定四态文案：空「成片还未生成。请先执行 python3 scripts/build.py。」；加载「正在读取本地影片…」（超过10s显示“取消加载”）；错误「无法读取成片，请检查MP4是否仍在交付目录中。」；成功「影片、字幕和台词已载入」。所有错误关联 aria-describedby/role=alert，成功 role=status；按钮没有只靠 hover 才显露的动作；Tab顺序视觉一致，Enter/Space激活，Esc关闭浮层，focus outline不被裁掉。加载超过10s可取消，重复请求要防并发/幂等。
音频交互只由 HTML5 视频播放器用户触发，不会在打开页面时自动出声。subtitle 始终硬字幕，SRT可下载；不得虚构无法关闭的“CC开关”有效。视频画面组件本身不存在拖拽、筛选、排序，预览页亦不实现无用的伪控件。


## 5. 技术实现、数据结构与边界处理

### 5.1 模块结构（全是将新建的目标位置）
- film/design-tokens.json 是唯一视觉 token 真源；scripts/export_tokens.py 导出 film/tokens.css 并为 PIL 图层生成同源色板；非 token 文件不得直写 hex。
- film/story.json 包含 V1–V8、S01–S12 与 S07B/S11B 图像定义、提示词、关键语句音画锚点；film/audio-contract.json 含 TTS、声场与混音目标。
- film/index.html、film/scene.css、film/scene.js 是 HyperFrames 无声影像项目，JS 仅根据帧时码驱动图层 transform/opacity、顶轨字幕和程序墨点，不使用任何视频源。
- film/assets/images/S01.jpg…S12.jpg、S07B.jpg、S11B.jpg（14张静帧）；film/assets/overlays/ 是 Pillow 自绘透明水墨蒙版、纸纹、波纹等**静止PNG/SVG**。
- scripts/assets.py、tts.py、align.py、build_timeline.py、build_scene.py、audio_mix.py、render.py、validate.py、contact_sheet.py、export_tokens.py、build.py，责任按文件名一一对应，不相互复制逻辑。
- preview/index.html、preview/styles.css、preview/app.js 为离线 QA 预览，不部署、不调用生成 API；生成后复制至 deliver/preview/。
- tests/test_story.py、test_timing.py、test_provenance.py、test_audio.py、test_preview.py；requirements.txt 固定 Pillow、NumPy 等最少包的解析版本，WhisperX 单独可选 venv 安装，不能因此阻断确定兜底。
- work/ 用于语音片段、中间 MP4、模型缓存、字幕审校；reports/ 用于证据；deliver/ 用于已验收的成片、SRT、台词、poster、preview、manifest。work/及密钥一律 gitignore，视频素材生成的临时本机下载地址不可提交。

### 5.2 类型契约、数据流和纯函数边界
规定 JSON schema 与 Python 类型，以下不是声称已有代码：
- StoryLine = {id:"V1", text:string, node:"three-threats"|"provocation"|"battle"|"celebration"|"realization"|"counsel"|"reform", scene_ids:string[]}；严格8条，文本与4.1逐字匹配，禁止临场改写。
- StaticAsset = {scene_id:string,prompt:string,output_path:string,sha256:string,width:int,height:int,provider:"matrix-image"|"procedural",generation_video:false,source_asset_id:string|null,rights_status:string}；不能存暂时签名的下载链接。
- VoiceClip = {line_id:string,path:string,sample_rate:48000,samples:int,start_sample:int,end_sample:int,text:string,clip_gain_db:number}。
- CharCue = {line_id:string,char_index:int,glyph:string,start_sample:int,end_sample:int,source:"forced"|"verified-manual"|"chunk-boundary",reviewed:boolean}；所有汉字都必须有 entry；标点归并到所在字幕文本，非汉字不假造发声区间。
- CaptionCue = {start_ms:int,end_ms:int,text:string,char_range:[int,int],lines:[string]}；视频硬字幕与独立 SRT **都由一个 CaptionCue 数组生成**。
- SceneCue = {scene_id:string,start_frame:int,end_frame_exclusive:int,image_ids:string[],anchor_key:string,motion:{scale_from:number,scale_to:number,x_from:int,x_to:int,y_from:int,y_to:int},effect_ids:string[]}；镜头使用半开帧区间，合起来覆盖 [0,900)。
- ValidationRecord = {id:string,expected:any,observed:any,status:"PASS"|"FAIL"|"NA",evidence_path:string,comment:string}。
模块主导出：load_story(path)->Story; request_still(scene_id,prompt)->StaticAsset; synthesize_voice(line)->VoiceClip; concat_voice(clips)->VoiceTimeline; align_known_text(voice,story)->list[CharCue]; create_caption_groups(chars)->list[CaptionCue]; allocate_scenes(story,char_cues)->list[SceneCue]; render_silent_video(scene_cues)->Path; mix_audio(voice,bgm,windows)->Path; mux(video,audio)->Path; validate_delivery(root)->list[ValidationRecord]。全部函数有非零失败退出/异常类型；文件原子写入再重命名防半文件。数据流：固定台本→单句TTS WAV→采样级绝对时码→字级对齐/校正→字幕与镜头时轴→静图HTML渲染→独立混音→视频音轨封装→probe/人工核验→manifest/报告；由 sha256 复核缓存与可追踪性。

### 5.3 **中文逐字字幕对齐的确定方案**
本节是关键技术闸门。与仅用 Whisper 猜中文字幕不同，本片**文本已知**、由 TTS 分句自产；先天可精确测出各句音频时长。

**主路径：中文强制对齐 + 人工字级审校。**
1. V1–V8 分句合成真实音频，原样保存文本和脱敏请求摘要。所有音频用 FFmpeg 转 48k mono PCM；用静音阈值 -48dBFS 测尾静音，仅剔除多余静音，保留≥100ms自然句末余响，每句之间插入80ms静音，头部留220ms。计算每句从完整 PCM 的 int sample offset，不能用 mp3 容器时长直接加到一起；因而每句 start/end 精确。
2. 不用英文 small.en 或无法确认的中文 ASR 转写。用 WhisperX 的 Mandarin 强制对齐功能，固定 known text 为 V1–V8，按句段将准确的 start/end 和 text 喂给 align；HF 对齐模型选 jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn；在 CPU 模式运行，要求 return_char_alignments=True。已证实文档 https://github.com/m-bain/whisperX ，字符参数入口 https://github.com/m-bain/whisperX/blob/main/whisperx/__main__.py 。Python API 先 inspect.signature(whisperx.load_align_model/align)，以安装包实际签名为准，不能编造 keyword name；将 version/签名/实际模型 id 记到报告。
3. 强制对齐不取代审校：移除标点后逐字对照参考文稿，检查输出字符数量、顺序、start/end 有效、汉字 coverage=100%、每组 start≤end 且单调。遇到“邅”这样的 OOV（未对齐字符）时，用前后字音时间作临时内插并标 source=verified-manual 的待核值；不得把内插推测标作 ASR 实测。局部不合理超过0.20s，同样进行人工纠偏。
4. 用固定短语切分生成可见 SubtitleCue：每组4–12汉字、单行≤13汉字、最多2行；start取第一字真实时码、end取最后字；相邻组留20–80ms视觉间隙，关键「人患志之不立」「何忧令名不彰」不拆断因果。导出 work/align/char_cues.json、work/align/captions.json、UTF-8 SRT，且由同一数组渲染电影硬字幕。以 48k 样本转 ms 采用 round(samples*1000/48000)，所有时间 clamp到0..30000。
5. 本机人工需看波形并 0.5×速度听**全部短语首尾**，另对「邅迹虎」「三日三夜」「乡人相庆」「陆云」「志之不立」「忠臣孝子」6处作0.25×定位复核；记录 estimated_start、corrected_start、差值、审校状态、对应截图到 reports/word-alignment-review.csv。**绝不靠模型输出就宣称≤0.2s。**

**强制对齐失败的确定兜底：23段短语 TTS，消除句组边界 ASR 不确定性。**若模型安装/下载失败、CPU推理超20分钟、对齐无完整汉字，直接以如下23组逐组 TTS，确切每组 WAV 样本首尾就是字幕的首尾：V1「义兴三害」「山中邅迹虎」「水中恶蛟」「还有周处」；V2「乡人劝周处」「除虎斩蛟」「暗盼三害只余其一」；V3「他刺虎」「追蛟数十里」「三日三夜未归」；V4「乡人以为他死了」「竟相庆贺」；V5「周处斩蛟归来」「才知自己为人所患」「决意改过」；V6「他寻二陆」「只见陆云」「忧年已蹉跎」；V7「陆云说」「人患志之不立」「何忧令名不彰」；V8「周处遂改励」「终为忠臣孝子」。这些是**23个短语**，文本连接后加标点仍必须对应 V1–V8。短语间60–90ms、同一个 voice_type/参数，必须试听断裂感；绝不为缩短时长吞字。字内细粒度先按每汉字均匀分配作**估计**，再通过波形低速逐字修正并标 reviewed=true，不能把等速内插称为已验证逐字精度；若无法证实每段字幕实际语音边界≤0.20s，则 A05=FAIL，禁止READY。主/兜底都保证字幕**可见边界**与 voice 精确一源，且完成真实人工字级核验。

### 5.4 TTS请求、真实时长与固定短稿
豆包 TTS POST https://openspeech.bytedance.com/api/v1/tts，环境变量 VOLCENGINE_TTS_APP_ID、VOLCENGINE_TTS_ACCESS_TOKEN、VOLCENGINE_TTS_CLUSTER、VOLCENGINE_TTS_VOICE_TYPE；Header Authorization="Bearer;"+ token（**分号非空格**），body 必有 app:{appid,token,cluster}、request:{reqid,...}；其他字段严格沿用本机已跑通的探针，未从简报核到的字段名称不假定成立。reqid 每句 UUID，code=3000 才视为成功，响应解码真实音频后由 ffprobe/PIL 类方法核格式。token/secret 不打印、不写 JSON；不要重新触碰已失败的 ark-image.sh。
首版116汉字，依据简报约4.6汉字/秒作**预算估算**，不是实测最终长度。TTS+头部220ms+句隙80ms的有效人声结束必须≤28.7s，保留≥1.3s音乐尾声。若超出：先用 FFmpeg atempo 按实际总长/28.48 做不升调变速（只允许因子≤1.08）；若仍超出或需要>1.08，则启用以下**固定短稿 B**（不允许Agent现场删改）：
B1「义兴三害：虎、蛟、还有周处。」
B2「乡人劝他除虎斩蛟，盼只剩一害。」
B3「刺虎追蛟，三日三夜未归。」
B4「乡人误以为他死了，纷纷庆贺。」
B5「周处斩蛟归来，才知自己招人厌恶。」
B6「他寻二陆，只见陆云，欲改过又恐太迟。」
B7「陆云劝：人患志之不立，何忧令名不彰！」
B8「周处遂改励，终为忠臣孝子。」
启用B时 S02 字幕旁注保留“邅迹虎（跛脚虎）”，S07 旁注必须另写“与蛟俱行数十里”，以免缩略口播丢失原文特征；B仍超限最多再 atempo 1.08；依旧超出则记 FAIL，绝不裁掉原文结尾。若TTS普通接口三次调用失败，固定降级为 macOS say -v Tingting，重新测 LUFS/句长，仍须保留可听清的中文；声型与正式播音差异写 known-limit。

### 5.5 14张静图的确定生产契约
唯一图片入口（简报已成功探针）：mcode-tools connector call connector__matrix__generate_image --args '{"requests":[{"prompt":"完整提示词","aspect_ratio":"9:16","resolution":"2K","output_file":"S01.jpg"}]}'；获得 node_id 后立即 mcode-tools get-asset-url <node_id> 下载临时地址到本地，验证 Pillow 能打开且宽高≥1080×1920、纵横比与9:16相差≤3%。重试最多3次，指数退避2/5/10秒，单图请求上限120秒；质量错位则同图重新生成最多2次；仍失败则用 Pillow/SVG 自绘**完整水墨静图**替代，不能留灰占位或有损坏图片。
图像共用画风 Prompt 固定前缀（所有图拼接，不能省）：'Vertical 9:16 Chinese Jin-era Jiangnan illustrated moral fable, handmade silk-scroll painting, expressive ink wash and meticulous figure linework, deep pine-green, ochre, muted parchment, restrained cinnabar, archival silk grain, layered foreground/middleground/background, dramatic silhouette. Consistent Zhou Chu: lean young Chinese man, tied black hair, deep green crossed-collar robe with narrow sleeves, brown waist sash and straight sword. No embedded words, no logo, no watermarks, no Japanese armor, no modern architecture, no photorealism, no gore.'
逐图独特场面：
- S01：暗绢纸、青年背影、山虎/水蛟/人影隐现三组墨痕，左上大片负空间；
- S02：险恶山林石径、一只步态不匀的猛虎，赭金斑纹，无白额装饰；
- S03：江南深潭石桥、水面下隐约蛇形蛟影，无龙翼角；
- S04：村街、村民回避、青衣周处背影佩剑；
- S05：乡人隔竹帘劝说，周处半侧身，无手写气泡/虚构人物；
- S06：竹林山口，青年与猛虎错位交锋剪影，无血浆；
- S07：洪水中追逐蛟影的青衣青年，深蓝墨绿飞溅；
- S07B：水浪、衣袖、剑锋与黛青水痕特写，用作S07内插；
- S08：同一水道昼夜变化、雨云/晨曦水墨对照；
- S09：山乡街口，人们互相庆贺，**周处不在这一场**，不做丧礼或宴席；
- S10：水岸归来、湿衣青年隔河看见乡人、孤独留白；
- S11：吴地质朴书斋，画面严格只有周处与**陆云**两人，无陆机第三人；
- S11B：竹简、窗影、两人手势局部与远山，画里不要可读文字；
- S12：青衣背剑青年走向雨后晴明山路、背影与大面积落款负空间。
每幅保存 prompt、服务结果 node_id（只存标识非短链）、尺寸、hash、实际生成日期、source_type=still、权利核对状态。拒绝现代建筑、唐明古装明显细节、人物三臂/漂移、乱码字；失败后用无脸剪影+深墨背景作既定风格降级，不凭空造古籍封面版权。裁切算法：scale=max(1080/w,1920/h)、中心 crop、zoom范围1.06–1.13，最终视口不露黑边。若没有真实 alpha 分层素材，不把整张人物图重复移动产生鬼影，改为单层相机运动+前景程序墨点独立层。

### 5.6 HyperFrames 视觉渲染固定路径与失败分支
在 film/index.html 根声明 data-composition-id="root"、data-width="1080"、data-height="1920"，S01–S12 的 img 以 class="clip"、data-start、data-duration、data-track-index 管理，字幕始终高 track；切镜叠化用 opacity，若同一 track 禁止重叠则通过交错轨道合成，确保没有黑帧。JS 注册 const tl=gsap.timeline({paused:true}); window.__timelines["root"]=tl；所有镜头 fromTo/to/set 使用绝对秒位置；最后 tl.set({}, {}, 30) 延长总轴；浏览器和框架负责 seek，**JS 不操作媒体 play/currentTime**。
一切动态粒子从 frame=floor(t*30) 的纯函数计算，用固定 seed=20261025 的 mulberry32；禁止 Date.now/Math.random/requestAnimationFrame/CSS无限动画/网络fetch导致的不可重复帧。相机只动 transform/opacity，CSS 不动画 layout；字幕用真实 CaptionCue 生成并放顶层，不能再运行 FFmpeg subtitles 二次叠字。
官方命令入口：npx --yes hyperframes@0.8.104 init film --example blank --skip-skills --skip-transcribe（若参数不兼容就据官方 HTML Schema 手写骨架，不能反复撞 CLI）；在 film/ 内执行 npx --yes hyperframes@0.8.104 lint 及 npx --yes hyperframes@0.8.104 render --fps 30 --quality high --workers 2 --output ../work/silent.mp4 。每次实际用 ffprobe 判断 silent.mp4 900帧/30s；本机 Docker 不运行，绝不加 --docker 伪造可用。workers=2 内存不稳固定回退1。
HyperFrames 完全不可用（按7节上限调研）时，唯一降级引擎为 FFmpeg 8.1.1：每个场景先用 zoompan d=对应帧数:s=1080x1920:fps=30 渲染静帧运动，程序墨纹/字幕由 Pillow 导出 RGBA层叠加，再用 concat / xfade 合成；xfade 两侧统一像素格式/时间基/帧率，offset从 SceneCue 精确计算，帧数最后保持900。备用轨仍用同一故事/字幕/颜色/输出检验，不能降低分辨率或删除关键场。
FFmpeg 封装范式：ffmpeg -i work/silent.mp4 -i work/final_mix.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k -ar 48000 -ac 2 -t 30 -movflags +faststart -y deliver/zhouchu_30s.mp4 。生成后必须核画面最后一帧及 duration，不能依靠 -shortest 偷偷截字。音画 start_time 实测；音频有尾部 padding 时 trim 保留 30.000s。

### 5.7 纯器乐 BGM、授权、响度与混音
第一候选：mcode-tools connector__matrix__batch_text_to_music 一次最多3条，纯器乐 prompt 固定为“30 seconds instrumental Chinese moral-redemption historical short; guqin plucks, xiao flute, muted low war drums, subtle stream sound; 92 BPM in 4/4; first 12 seconds tense, 12–20 urgent, 20–26 sparse introspection, last 4 luminous resolve; NO VOICE, NO LYRICS, no EDM, no trailer braams”。每条获取 node_id 并即时下载、ffprobe 解码，按顺序选择第一个“≥30s、没有人声/歌词、音质不削波、覆盖故事4段且**存在可核使用权**”的候选。账号条款未证实可公开发布则**无条件**采用下面代码合成的 BGM；本机已有“大国重器.mp3”只能做试听对照，不凭文件存在推定许可。
纯代码兜底（必实现）：scripts/audio_mix.py 以 NumPy 48k立体声合成固定92 BPM五声音阶配乐。A3/C4/D4/E4/G4 的拨弦由基频与2/3倍频谐波合成、指数衰减0.18s；低鼓为82→46Hz的220ms扫频正弦加瞬态；木击以 seed=20261025 伪随机噪声加6kHz低通短窗；水声为确定 seed 滤波噪声≤-32dBFS；节拍按0–12s能量0.55、12–20s能量0.90、20–26s能量0.32、26–30s能量0.55；最后1.20s cosine淡出。生成 FLAC/WAV 并记录其“procedurally synthesized in project”权利来源，不调用音乐模型也可保底得到不侵权的自制基底。
语音归一化：FFmpeg loudnorm **两通**，目标 I=-16:LRA=7:TP=-1.8，先通过第一遍 print_format=json 获取 measured_I/LRA/TP/thresh/target_offset，再填第二通，之后校验独立 voice stem 有效有声窗口平均 -16±1。配乐先独立归一化至 -25 LUFS，然后根据每个 CharCue 的完整人声时间窗口，以 voice 与 bgm 的真实样本 RMS 比为准，使 bgm 在声区比voice低**18dB**（至少12dB）；段首尾 duck 包络各120ms平滑；中频200–4000Hz BGM 要适当降增益避免掩蔽，不能固定“音量0.56”。混合后 ebur128=peak=true/真实峰值≤-1.5 dBTP；若超限以0.5dB步长降低总混音并重测，最多4次；不能让过量limiter导致旁白低于-17 LUFS。报告 voice、bgm 每句RMS、差值、voice LUFS、whole true peak。所有来源无讲话时段，底乐音量不得突变。

### 5.8 边界/性能/明确禁法
- 丢图/空图、403资产短链、API超时：同一图最多3次连接重试、2次质量重生，再程序静态画面；不准用灰块。
- TTS缺句、口型不准确（此片无口型）、文本超长：不能截断汉字；按5.4固定短稿；任何词错或念错需重生成相应片段，并从该句重新对齐后续字幕。人声末尾≤28.7s，否则A01阻断。
- 字幕超长：在语义边界分组，最多2行/行13汉字；不得省略引句/加省略号敷衍，不得显示在右侧交互栏 x>878 或底部 y>1680。
- 网络/账户权利：素材生成限并发≤2，日志脱敏，敏感变量不入repo。离线再次执行能复用完整本地素材 hash 并渲染，不再请求 API。
- 大体积：禁止生成900张长期保留的未压缩全帧 PNG；必要时用缓存 PNG 序列只在 work/，完成删除。预览首交互≤2.5s、轻操作≤300ms、反馈≤100ms、CLS≤0.1；视频 poster 固定 aspect-ratio防布局跳动。
- 禁令：一切AI视频生成、影视混剪、日式古装、白额虎替写、虚构第三人陆机在场、无来源素材、系统默认HTML裸样式、emoji、动画width/height/top/left、随机粒子不固定seed、无焦点环、把ASR估计当精准认证、硬字幕与SRT分开手工编辑、导出秘密。

## 6. 任务拆解（按依赖排序，七要素一个不少）

| 编号/依赖/规范 | 前置条件 | 具体操作步骤 | 相关位置 | 预期产物 | 自查方法 | 测试方式 | 客观完成条件 |
|---|---|---|---|---|---|---|---|
| T01 无依赖；A1–A5/E | 已读本规划及3份受控文件 | 初始化 tokens、story、audio-contract；写8句A、8句B、12景14图ID、剪辑锚点、通用风格和事实红线 | film/design-tokens.json;film/story.json;film/audio-contract.json | 3份JSON真源 | Python json.load成功；逐字核原文六节点 | tests/test_story.py 断言8句、12镜、14张、锚点唯一、节点不缺 | 无空ID、没有虚构史实/二陆错位 |
| T02 T01；A1–A5/D/E | T01 PASS | 导出 tokens.css；搭film/index.html+scene.css+paused scene.js；一张图10帧试跑；搭preview C5–C8静态骨架，不先依赖影片 | scripts/export_tokens.py;film/index.html/scene.css/scene.js;preview/* | CSS/HTML/JS骨架、测试帧 | HyperFrames lint+渲染草稿，检查 CSS computed fonts 和900帧延长 | test_preview.py 检token引用、z-index、预览状态文案、媒体比例 | 0 lint error、界面无裸色、字体真实加载 |
| T03 T01；A5/E | 图片服务可调或走固定降级 | assets.py按5.5循环14 prompt；即时下载、Pillow核尺寸、人工查手/衣/脸/纹理；错误分支替换代码静帧，记录hash/rights | scripts/assets.py;film/assets/images/*;film/assets/overlays/*;work/asset-manifest.json | 14图+透明墨痕PNG/SVG+manifest | PIL打开全图，无黑边/乱码/人物漂移 | test_provenance.py 检来源/尺寸/hash/无任何生成视频输入 | 14图全部可打开且逐景对应 |
| T04 T01；B4/E | TTS环境变量存在或macOS say替代 | 逐句合成8段；统一48k；剔过长空白、80ms句隙与220ms头部；按真实样本判5.4时长分支；录逐句sha | scripts/tts.py;work/voice/*;work/voice_timeline.json | voice_master.wav 和样本级起止 | ffprobe真实采样、实际听“邅迹”及结尾；总人声结束≤28.7s | test_timing.py 校验sample算术、无丢句、文稿指纹 | 中文8句语义完整、不吞字、限时满足 |
| T05 T04；A1/A2/C | 完整voice_master.wav | 先Mandarin WhisperX known-text字级强制对齐；失败转23短语TTS；人工逐组低速听、修字级锚点；一数据源导出SRT及硬字幕cue | scripts/align.py;scripts/build_timeline.py;work/align/*;deliver/zhouchu_30s.srt;reports/word-alignment-review.csv | CharCue、CaptionCue、UTF8 SRT | 对照字幕拼接的每字与旁白稿逐字相同，时间不倒流 | test_timing.py 检字符覆盖100%、误差审校记录、起止范围、无重叠 | ≥6重点锚点+全部字幕组人工≤0.2s通过 |
| T06 T04,T05；B4/E | 真实人声窗口已知 | 最多生成3个纯音乐候选并查权利，无授权走代码合成；旁白两通loudnorm、音乐降噪duck、出立体声混音 | scripts/audio_mix.py;work/bgm.wav;work/final_mix.wav;reports/audio-measure.json;reports/rights.md | 48k/30s成片声轨+双stem数据 | 用耳机与外放听全片，量化声区RMS差和true peak | test_audio.py 每句≥12dB，-16±1LUFS，TP≤-1.5 | 无音量硬切、清晰人声、有BGM、有来源 |
| T07 T02,T03,T05；A1–A5/D | 合法静帧与CaptionCue均在 | build_scene按真实字级锚点切镜，GSAP transform/opacity、墨浪/粒子、SRT同源的C4顶轨；scene数与帧连续检查 | scripts/build_scene.py;film/index.html/scene.js/scene.css | 有字幕的12镜视觉项目 | HyperFrames preview定格逐景看主体与“清河/跛脚虎”，联系表看总色温 | test_timing.py SceneCue覆盖[0,900)、每镜≥1个特效、无缺帧 | 首尾完整且字幕不遮角色，关键短句稳定可读 |
| T08 T06,T07；A2/D | 通过音画局部验证 | 用HyperFrames high/30fps/workers2渲染silent.mp4（异常1 worker）；FFmpeg mux；生成poster/联系表 | scripts/render.py;scripts/contact_sheet.py;deliver/zhouchu_30s.mp4;deliver/poster.jpg | 成片+封面+联系表 | ffprobe核30s/900帧、播放0–30s | scripts/validate.py媒体约束与人工播放全片 | 1080×1920 H264/AAC、人声字幕无截字 |
| T09 T02,T08；B1–B5/C/D/E | MP4/SRT均可读取 | preview C5–C8接实际文件，完成空/载入/失败/成功；aria/focus/键盘/取消/禁用/下载；五断点及reduce motion；复制到deliver/preview | preview/index.html/styles.css/app.js;deliver/preview/* | 离线校阅页、状态与响应式截图 | Chrome 375/480/768/1024/1440及200%逐态浏览，拔鼠标走Tab/Enter/Esc | test_preview.py检查语义标签、链接、状态文案、无横向滚动 | 首屏≤2.5s、100ms反馈、44px点击区、无焦点丢失 |
| T10 T01–T09；A–G/E | 媒体与校阅页真实可用 | 模拟丢图/缺MP4/字幕漏字/网络超时；执行单测+probe+声音数据；contact sheet逐帧抽样；报告每条PASS/FAIL/NA与证据；打包manifest与zip | scripts/validate.py;reports/latest.md;reports/*.json,*.log;deliver/manifest.json | 完整成片与真实验收报告 | SHA检查包内实际文件/引用、确认无密钥；逐条读报告而非口头PASS | python3 -m unittest discover -s tests -v 与本机浏览器/手机测试 | A01–A08 PASS、A–G各条有结果、无伪造证据时才可交 |

执行依赖序：T01→T02/T03/T04→T05→T06/T07→T08→T09→T10；每项的测试都在本机真实运行，不把规划视为执行证明。UI质量基线每项引用 A1–E 对应章节；纯视频没有交互时必须记录“不适用”及具体理由，不虚构 hover 状态。

## 7. 未知信息：分类、入口、限时与保守分支

### 7.0 清单
U1 HyperFrames本机兼容性【有入口】；U2图片接口与质量【有入口】；U3 TTS速度与发音【有入口】；U4中文WhisperX强制对齐【有入口】；U5纯音乐服务和可解码性【有入口】；U6实际字体与Unicode字形【有入口】；U7最终音量指标【有入口】；U8视觉人物统一性/时代差错【无入口，必须本机看生成结果】；U9发布平台实际挡字安全区【无入口】；U10 2026权威“最好”榜单【无入口，未能查证】；U11录音和900帧可兼容性【有入口】；U12账号级静图/音乐发布授权【无入口】。

### 7.1 有入口，每条五要素
**U1** 问题：HyperFrames 0.8.104 是否如文档支持根 composition/GSAP/clip/导出。查哪里：npx --yes hyperframes@0.8.104 doctor、lint，官方 https://hyperframes.app/docs/2-concepts/1-compositions 及 https://hyperframes.app/docs/3-guides/4-rendering 。怎么判断：10帧试渲成功且doctor Node/Chrome/FFmpeg PASS。分支：PASS主路径；init flag不支持则手写HTML schema；renderer整体异常且10分钟内无法打通则转第5.6的 FFmpeg/Pillow 降级，仍验900帧。耗时上限10分钟。
**U2** 问题：新一轮图像服务是否还能9:16/2K出片。入口：brief 给出的 mcode-tools connector__matrix__generate_image/get-asset-url，PIL.Image.open探针。判断：node_id有效、≥1080×1920、画面不含乱码。分支：合格逐张生产；3次服务失败或2次品质失败程序化绘制静态水墨图+SVG剪影并记录fallback，绝不调用视频模型。耗时：单图6分钟，总40分钟。
**U3** 问题：8句中文TTS是否准音且时长≤28.7s。入口：https://openspeech.bytedance.com/api/v1/tts 和 env，ffprobe、逐句听。判据：code=3000、音频可解码、文本正确、终点≤28.7。分支：按5.4固定atempo/短稿B；“邅”读错且不能修复用口播「跛脚虎」并硬字幕正写「邅迹虎（跛脚虎）」并报告差异；远端不可用3次降级macOS say -v Tingting。上限15分钟。
**U4** 问题：Mac CPU+Mandarin模型能否得字级时码。入口：https://github.com/m-bain/whisperX 、https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn ，venv中inspect.signature(whisperx.align)并以1句WAV试跑。判断：字级输出非空且顺序覆盖并经关键字试听≤0.2s。分支：成功处理全片人工修正；下载/安装/性能/字段缺失退回5.3的23短语法且必须手动审校；无法证实则 A05 FAIL。下载上限10分钟、首句处理20分钟。
**U5** 问题：音乐服务有无无歌词可解码候选。入口 mcode-tools connector__matrix__batch_text_to_music，实际返回node_id、ffprobe解码。判断：音源≥30s、清晰无语音。分支：通过且账号条款有明确授权才用第一合格曲；否则直接第5.7的程序音乐。上限12分钟。
**U6** 问题：字体是否真的以宋体/Noto渲染。入口：fc-list | grep -E 'Songti SC|Noto Sans CJK SC|Kaiti SC'，Chrome DevTools Computed Fonts 与 HyperFrames关键帧。判断：字形无方框、标题与字幕长宽未溢出。分支：成功原字体；若宋体失败改Noto Sans CJK SC Bold并保留字号；若特定字是豆腐方块，做逐字字体fallback并记录。上限5分钟。
**U7** 问题：混音真峰和声压比是否过线。入口：ffmpeg -i work/final_mix.wav -af 'ebur128=peak=true' -f null - 及 scripts/validate.py stem-rms日志。判断：每voice窗口≥12dB、独立人声-16±1、TP≤-1.5。分支：不达标依次将BGM减3dB、重新归一化stem、最后混合整体每轮减0.5dB最多4轮；仍不达标标BLOCKED。上限10分钟。
**U11** 问题：最终30秒轴是否漏帧或截语句。入口：ffprobe voice_master/silent.mp4 的duration、nb_frames，scripts/build_timeline.py样本报告。判断：voice尾≤28.7、video900帧且第899帧可见。分支：时长长按5.4，帧缺回到scene编排，禁止静默截断；失败停止。上限8分钟。

### 7.2 无唯一可查入口，必须回答“查什么、怎么查、决定什么、默认什么”
**U8 人物视觉**：待查是否图像生成把晋人画成现代/日本装扮或把陆云变为陆机/三个人、关键镜头有脸与手畸形；怎么查为本机14图并列、0/5/10/20/26s联系表人工逐幅看，无现成静图可由网上查；决策分支 A符合→保留 B失败→同prompt重试2次 C仍失败→改无脸剪影/环境物静图；默认C，明确写被替换镜头。
**U9 平台安全区**：待查最终要上传的具体App版本及会遮挡多少画面；怎么查：本轮用户未指定平台，无其账户UI或分发链接，运行离线375×812手机比例模拟审核；分支 A有平台官方安全框→依据官方画面另出适配版且不修改本次默认版 B未指定→x=102..878,y=1510..1640、底部280/右边202安全余量；默认B，禁止扩大服务范围至另出平台版本。
**U10 最高水准名次**：待查是否存在可核验的“2026 30秒中文典故叙事短片榜单”；怎么查：本轮已检索TED-Ed、专业影视标题、TikTok，未能证实；执行不为排行榜延误做片；决定 A有权威榜单→只附来源证据 B无→标“未能查证”；默认B；不把技法参考称“全球第一”。
**U12 账号授权**：待查 matrix-image 和音乐服务的**用户账号实际授权范围**，公开发行和商业使用是否覆盖；怎么查：执行登录其已有账户查看 Terms/License/返回的资产授权字段，并把实际网页/时间/截图或条款摘录存 reports/rights.md，**网页规划者无账号入口，不伪造链接**。决策 A图片+音乐都明确允许→正常提交 B图片允许但音乐无权→图像保留音乐程序自制 C图像也无法证权→所有最终有权利声明的图改为 Pillow/SVG 原创程序静态图，不可谎称生成图可商业发布；默认**C＋程序音乐**，并对最终图案重跑 A04 审查。因本案允许图像模型但不承诺版权转让，必须写实际依据，不用“已生成即自动有商用权”敷衍。

### 7.3 未知执行出口
12条均有明确判据、耗时或本机调查方法及保守分支。7.1每项先查到上限再固定降级，不得无限撞工具；7.2每项无输入即用默认。所有U1–U12结果写进 reports/latest.md “未知调查结果”，包括调查证据、分支、默认及影响。不能因“未知”跳过硬性故事内容/图数/30s与版权诚实记录。

## 8. 必须真实执行的验收、回归和视觉自检

### 8.1 机器可复现命令及预期
1. python3 -m unittest discover -s tests -v > reports/unit-test.log 2>&1；退出码0，结果 Ran N tests/OK 的N从文件自动读取，禁止手填测试数。
2. npx --yes hyperframes@0.8.104 doctor > reports/doctor.log 2>&1；Node/FFmpeg/Chrome合格；Docker missing记NA，不作为失败。
3. 在 film 目录执行 npx --yes hyperframes@0.8.104 lint > ../reports/lint.log 2>&1；零error；若已走FFmpeg降级，写 N/A + 真实替代命令，不虚构HyperFrames PASS。
4. python3 scripts/build.py > reports/build.log 2>&1；退出码0，生成完整deliver/，本地asset hash重复构建不能再次消耗远端请求。
5. ffprobe -v error -show_entries format=duration -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels -of json deliver/zhouchu_30s.mp4 > reports/ffprobe.json；逐项检查A01，不仅看mp4存在。
6. ffmpeg -hide_banner -i deliver/zhouchu_30s.mp4 -af 'ebur128=peak=true' -vn -f null - 2> reports/loudness-full.log；voice_master.wav 同样单独量响；分离voice/BGM声区统计 RMS 差，保存 reports/audio-measure.json。全轨LUFS不等于人声stem LUFS，禁止混用。
7. python3 scripts/validate.py --delivery deliver --report reports/validation.json；自动校验实际 900 帧、时长、视频血缘、8句文本、SRT时间有序、每个字幕完整、色板对比度、stem响度和 hash。
8. python3 scripts/contact_sheet.py --video deliver/zhouchu_30s.mp4 --output reports/contact-sheet.png；抽帧至少 t=0.3/1.4/3.4/5.0/6.8/8.8/11.0/13.9/16.5/18.9/22.1/25.5/28.2/29.8s，并对每组字幕的start/end前后各抽1帧证明不提前消失。
上列 Python 命令均对应第5–6节新建的脚本文件，由执行者按本案接口实现后运行，不冒充现在已存在。

### 8.2 实机主流程、字幕与视效
- 用本机Chrome播放已渲染MP4从0到30秒**完整两遍**；第一遍有声闭环，第二遍静音读字幕与图像，确保三害/乡人借刀/三日/庆贺反讽/陆云/改过六节点可被看懂。
- iPhone/Android任一真实手机竖屏播放一遍并听耳机与外放；没有真机必须记“NOT TESTED: 实际手机”，不得把DevTools手机模拟当真机证据。
- 逐镜看虎的步态、蛟的水下形态、村民先暗盼后庆贺、周处回来的心理冲击、吴地**只见陆云**；色彩/衣料/粒子保持同一个风格，无现代建筑、过多手指、印章乱字、水印、黑屏、遮脸、画幅拉伸。
- 每个字幕短语在0.5×播放手听并与时间表比对；“邅迹虎”“三日三夜”“陆云”“人患志之不立”“忠臣孝子”在0.25×逐字复核；每组语音错位≤200ms，有截图/CSV数字；每行≤13字、1–2行，y≤1640、遮罩对比≥4.5。
- 30fps每个镜头至少观察首中尾3帧，一幅图静止连续不超过2.3s，无闪白>2/s，无音量突然失控；字幕在字数大段出现时也不盖脸、剑、蛟影。
- 校阅页实开5个断点375/480/768/1024/1440以及200%字体、默认/空/加载/错误/成功五态逐一截图；Tab/ShiftTab/Enter/Space/Esc完成全流程；焦点环2px、热区44px、不可用按钮aria-disabled、错误role=alert、成功role=status；prefers-reduced-motion:reduce下无大面积平移。
- 对比度抽查在设计词色上用WCAG公式读取primary/bg、secondary/surface、border/bg、disabled/bg，记录实测比值>=4.5、>=4.5、>=3、>=2；图像上采用实心遮罩而非采样背景碰运气。
- quality-bar 的A1–A5、B1–B5、C、D、E、F、G全项目逐条填写 PASS/NA/FAIL；对于线性MP4不存在网页hover/键盘，填NA并解释；对于校阅页不能NA关键交互状态。

### 8.3 必覆盖的失败演练
删V7引文/以白额虎代邅迹虎/误置陆机台词：test_story 必须FAIL；把场景生成视频文件假扮图或 manifest标generation_video=true：test_provenance 必须FAIL；删一字/字幕错时0.3s/强行压成三行：test_timing 必须FAIL；人为调大BGM导致声区差<12dB：test_audio 必须FAIL；移走S02原图：构建应提示缺哪张且走既定静态替代；移走deliver MP4：预览页必须在错误态说明“如何恢复”；断网后已成功缓存的资产仍能完成离线渲染。
**FAIL=不得交付**：A01–A08任何一个不通过、视频生成素材、字幕不对应旁白、事实红线被破坏、音量越线、无完整图像、密钥或未经查证的“商用授权”、无法在本机真实播放。**可以交付**：全部硬门PASS，UI质量条款逐项可查且不存在G不合格场景，实际看完30秒，未知项使用默认均有登记。

## 9. 首次交付实际文件清单、报告与证据

### 9.1 仓库/交付结构
必须新增 handoff/plans/LOOP-001.md（本文）。
工程：film/design-tokens.json、story.json、audio-contract.json、index.html、scene.css、scene.js、tokens.css、assets/images/下14张图、assets/overlays/下程序水墨静态蒙版；scripts/ 所有第5.1列出的.py；tests/5个测试文件；requirements.txt；.gitignore。
对外交付：deliver/zhouchu_30s.mp4、zhouchu_30s.srt、narration.txt、poster.jpg、manifest.json、README-PLAYBACK.txt、preview/index.html/styles.css/app.js；另打包 zhouchu-film-LOOP-001.zip 并记录 SHA256。
证据：reports/latest.md、ffprobe.json、audio-measure.json、validation.json、word-alignment-review.csv、contact-sheet.png、unit-test.log、build.log、doctor.log、lint.log、rights.md，及375/1440浏览器截图。若单MP4超过GitHub 100MB限制，调CRF到18–21重编码直到能保存且画面通过；仍>100MB则将实际文件保留本地deliver并报告未能上传的真实路径与hash，**绝不声称已推送该MP4**。

### 9.2 执行报告 reports/latest.md 必须有的小节
(1) brief_sha/代码commit/依赖实际版本；(2) T01–T10逐项实际执行状态与产物；(3) 原文六节点到V1–V8/S01–S12对应表、脚本A/B最终启用；(4) 所有静帧prompt/hash/source/版权状态；(5) 字级时间原始输出/修订表/人工审核方法及最坏偏差；(6) 声区stem/配乐比例/TP数值；(7) 命令日志、自动化真实测试 N passed / M failed（从真实log读）；(8) 联系表和每断点/状态/键盘截图索引；(9) design-quality-bar A–G逐条PASS/NA/FAIL及观察证据；(10) U1–U12每个未知的调查/默认分支；(11) 限制、失败、NOT TESTED/实际设备缺口；(12) 最终投产/交付判定。
测试结果唯一真源是 unittest log、ffprobe JSON、ebur128 log 和真实媒体文件，不得复制规划里的目标值冒充observed。所有已知限制必须写“未做事项、原因、影响”，例如没有真实手机就显式NOT TESTED。

### 9.3 manifest与权利/安全
deliver/manifest.json 枚举所有最终文件path、bytes、sha256、media_type、source_type、source_asset_id、rights_status及story_version；整体包含 task/round/brief_sha、video_frames=900、audio_targets、renderer_version、生成时间。zip SHA存 reports/latest.md；不要暴露短期签名URL、VOLCENGINE_*、MODELSCOPE token、私密本地目录和临时追踪URL；只提交有权利凭据的静图音乐或按U12程序化降级。交付以“文件在仓库/本机真实存在并可播放”为准，不能把计划提交当成成片交付。

## 10. 执行 Agent 遇困规则、偏离记录及终局

此为唯一规划回合，后续**禁止回头找网页版ChatGPT、不得提问、不得等待额外复审**。按T01→T10执行，优先维护六个原文节点、禁止生成视频、30秒1080p、配音+音乐+字幕这四类硬约束。计划未覆盖的新情况自己在本机查证，并用第3节token、第8节质量判据选择保守能运行分支；在 reports/latest.md 的“新增未知”填事实/分支/观测/影响，不可静默自由发挥。计划与真实API/机器冲突，以可重复跑通为准，记录偏离第几节、API/报错、为何调整、实际替代步骤与复验结果，不能虚构输出。403/401不能无止境重试；遇图像/TTS/音乐/WhisperX/HyperFrames故障分别按7.1的固定fallback执行。权利未证不得声明可商用；字幕≤0.2s/音乐响度不能实证则 BLOCKED，不写READY。
本轮只交付一次完整30秒作品及可复核证据，不接CI、不部署、不合并PR。**只有A01–A08完全通过、质量线逐项合格且真实成片文件存在**，才在 reports/latest.md 最后一行写 READY_FOR_DELIVERY；失败则写 BLOCKED 及具体尚未达标的指标和位置。未知项或真机缺口必须诚实呈现，即使最终技术可用也不伪造真实设备测试记录。

---
### 规划阶段证据边界
以上研究来源已经公开网络核查；“有绝对权威的2026最佳中文典故短片榜单”“这台Mac的WhisperX普通话模型能可靠工作”“本账号生成图/音乐具有商用权”“最终14张图必定美观”均**未能在规划阶段实证**，分别写入U10/U4/U12/U8，提供有限时、可观察的调研与兜底。本文不代表任何业务代码、成片、测试或真机已由规划者运行。
