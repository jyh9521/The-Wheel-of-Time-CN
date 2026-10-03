# The Wheel of Time GOG 简体中文汉化：第一阶段分析报告

日期：2026-10-02（Asia/Tokyo）。分析对象：本地现有安装；不是根据 Unreal Tournament 的版本能力推定。

## 结论摘要

- **游戏已具备 Unicode 字符串和标准 UE1 localization 机制。中文空白的直接阻碍是现有字体覆盖，而不是先改 EXE。**
- 已实际测试 `[menuSinglePlayer] MenuList[2]`：`New Game → 新游戏`。UTF-16 LE BOM 副本启动、退出正常，中文菜单文字为空白。
- `Language=zht` 加独立 `WoT.zht` 的混合文本对照也实际生效：`New Game / 新游戏 / OK` 中 ASCII 可见，中文缺失。
- 原有 277 个文件均已备份、SHA-256 校验，结束时 **277/277 未改变**。修改只留在工作副本。
- **`.int` 不是全部文本。** 地图里有可本地化实例属性，脚本里也有直接写死的可见字符串。
- **`.mov` 并非只有音视频。** 14 个视频含意大利语、西班牙语 legacy QuickTime 文本轨道，共 28 轨。已提取原始文本和时间信息；`Mission_10.mov` 没有此字幕轨道。
- 下一步应验证三个汉字的位图字体页，暂不批量翻译、不修改程序代码。

## 1. 游戏所有可翻译文本所在位置：当前确认清单

### 扫描范围与结果

整个原安装已列入 [原始文件清单](C:/GOG Games/The Wheel of Time/docs/phase1/original_manifest.json)，包括 Help、Movies 和根目录，不只扫描指定的五个目录。

| 资源 | 实际数量 | 结论 |
|---|---:|---|
| System 的 `.int` | 29 | 2,345 个键值条目，含重复键、结构化注册信息与空值；不是 2,345 条待翻译正文 |
| System 的 `.u` | 20 | 类、字节码、默认属性、源文本及嵌入图像/字体/声音 |
| Maps 的地图 | 45 `.wot` | 本安装地图扩展名为 `.wot`，不是 `.unr` |
| Textures | 36 `.utx` | 图像；其中 `UWindowFonts.utx` 含 Font 对象 |
| Sounds | 27 `.uax` | 声音；字幕按照内部 Sound 对象定位，不是按单独 WAV 文件名 |
| Music | 10 `.mp3` | 音乐，未当作对白翻译源 |
| Movies | 17 `.mov` | 视频、音频、部分内嵌文本轨道 |

共读出 128 个 Unreal 包的名称/导入/导出表，包版本 61、63、68，解析错误 0。读出 1,198 个 Sound 对象、26 个 Font 对象；原始包保持只读。

### 文本分类定位

| 玩家看到的内容 | 已确认位置及调用者 |
|---|---|
| 主菜单 | `C:/GOG Games/The Wheel of Time/System/WoT.int` → `[menuMain] MenuList[1..7]`；`WOT.menuMain`、`menuWOT.DrawList` 绘制 |
| 单人菜单/New Game | 同文件 → `[menuSinglePlayer] MenuList[2]`；并非主菜单第一层 |
| Controls/Options | `[menuOptions]`、`[menuKeyboard]`、`[menuPlayer]` |
| Hardware | `[menuConfiguration]`；渲染器选项另外在 `D3DDrv.int`、`OpenGlDrv.int` 等 |
| Inventory/法器资料 | `C:/GOG Games/The Wheel of Time/System/Angreal.int` 的 Title、Description、Quote、PickupMessage；实际默认文本也保留在 `Angreal.u` |
| 兵种资料 | `C:/GOG Games/The Wheel of Time/System/WoTPawns.int` 的各 Inventory 节 |
| 陷阱资料 | `C:/GOG Games/The Wheel of Time/System/WoTTraps.int` 的各 Inventory 节 |
| HUD、拾取/失败/战斗提示 | `WoT.int` 中 WOTPlayer、BattleHUD、AngrealInventory、Seal、计分板等；部分默认属性和字面量在 WOT.u |
| 帮助、任务目标、任务过渡标题 | `WoT.int` 中 WOTHelpInfo、MissionObjectives*、WOTTextWindowInfo、WOTTransitionMapInfo* |
| 地图标题、剧情提示、教程提示、锁门提示 | `C:/GOG Games/The Wheel of Time/Maps/*.wot` 的实例属性；详见下文 |
| NPC/教程语音字幕 | `C:/GOG Games/The Wheel of Time/System/WoTsubtitles.int`，音频多在 `C:/GOG Games/The Wheel of Time/Sounds/DialogA.uax` 和角色 `.uax` |
| 网络浏览器界面 | `C:/GOG Games/The Wheel of Time/System/WoTBrowser.int`、`UBrowser.int`，以及 UWindow/UBrowser 的默认属性和部分字面量 |
| 启动器原生窗口、报错、Advanced Options | Core.int、Engine.int、Window.int、Startup.int、WinDrv.int 等；原生 Windows 窗口不同于游戏 Canvas |
| 注册/安装说明、帮助文档 | 根目录 EULA.txt、System/Reg*.txt、Help/ReadMe*.htm 等；低优先级、独立于游戏内文本 |
| 纹理/视频上的图形文字 | `.utx`、`.u` 内 Texture 和 MOV 视频画面；尚未逐纹理 OCR，不应把资源结构清单当成图形文字完整审计 |

地图只读属性分析成功读取 84,380 个对象的属性流，得到 579 个非空字符串属性，包含 URL、音频名等技术字符串。玩家正文候选包括 **203 个 Messages、48 个 Title、8 个 Content、7 个 Message**，另有 PickupMessage、LockedMessage、UnLockMessage 等。

例：`Mission_05c.wot / MessageTrigger0.Messages[0]` 保存内门操作提示；`Tutorial.wot` 保存独立教程提示。因此“只翻 WoT.int 和 WoTsubtitles.int 就覆盖全部剧情提示”并不成立。

[地图字符串与原始偏移](C:/GOG Games/The Wheel of Time/docs/phase1/map_text_properties.json) · [所有包对象](C:/GOG Games/The Wheel of Time/docs/phase1/packages.json) · [localized 声明](C:/GOG Games/The Wheel of Time/docs/phase1/localized_declarations.json)

## 2. 每类文件负责什么文本，以及标准 localization 是否适用

本地源文本确认 `Engine.Menu` 的 MenuList、HelpMessage、MenuTitle 等带 `localized`；`MessageTrigger.Messages[16]`、门提示和资料页字段也有此声明。`Core.Object` 包含 Localize 和 GetLanguage。

加载路线：选定语言文件覆盖对应 localized 属性；没有相应翻译则按标准引擎机制回退国际英语/包内默认值。标准机制的定义可参考 [OldUnreal localization 文档](https://www.oldunreal.com/wiki/index.php?title=Localization)。本次额外实测了新的 `zht` 扩展，不仅依据文档。

**推荐发布形态**：创建 `WoT.zht`、`Angreal.zht`、`WoTPawns.zht`、`WoTTraps.zht`、`WoTsubtitles.zht`；配置 `Language=zht`。这是本次验证可用的自选语言代号，不代表游戏内置了简体中文语言包。最终还需验证所有包及地图实例的回退覆盖。

地图本地化宜生成对应 `Mission_05c.zht`、`Tutorial.zht` 等资源，保持地图二进制不动。实例节名/数组项应由本版本编辑器 DumpInt 或经过验证的导出工具生成，不直接凭猜测写映射。本地 UCC help 没有 DumpInt commandlet；不要把后期 Unreal 227/UT469 的命令照搬。已验证本地 `ucc batchexport` 可只读导出类，得到 1,168 个 `.uc` 文件；Core/Engine 部分类导出报错，包中的 ScriptText 仍可只读抽取。

`.int` 还包含 `[Public] Object=...` / `Preferences=...` 等结构化元数据；类名、路径、参数不能整行翻译。Python 工具已将这些条目标记并拒绝整值回写，后续应专门处理 Description/Caption 子字段。

**确实存在硬编码文字**：`WOT.BattleScoreBoard.DrawHeader` 直接绘制 `Game Type:`、`Map Title:`、`Author:`、`Ideal Player Load:`。这些不是简单补一个 `.zht` 键就会被该调用读取。当前列出了 129 处静态候选，包含注释/标点/调试路径，仍需逐项筛选。优先完成已有 localization 覆盖，硬编码遗漏另列清单；未改脚本或字节码。

[硬编码 UI 候选](C:/GOG Games/The Wheel of Time/docs/phase1/hardcoded_ui_candidates.json) · [原生 UCC 导出记录](C:/GOG Games/The Wheel of Time/docs/phase1/UCC_export.txt)

## 3. 字幕系统结构

### 实际调用链

`WOTPlayer.ClientHearSound` → 检查 bSubtitles → `PackageName = S.Outer.Name` →

```unrealscript
Localize(string(PackageName), string(S.Name), string(SubtitlesPackageName), true)
```

`SubTitlesPackageName` 默认 `WOTSubtitles`。非空结果传入 SubtitleMessage → BaseHUD.AddSubtitleMessage → Canvas.DrawText。显示持续时间按文本长度计算，存在最短显示时间，并非带绝对时间码的字幕文件。

例如 `[DialogA] Tes_01=...` 对应 `DialogA.Tes_01`，而非 `DialogA.uax` 文件整体。一条 Sound 对象可以多次触发。此路径排除以 WOT.、Angreal. 开头的声音，且单个 SubtitleMessage 槽可被后续声音覆盖；不能据此承诺所有同时说话/所有发声路径均可完整呈现。

原始 User.ini 本来已有 `bSubtitles=True`，本次无需改安装内字幕开关。

### 本地字幕覆盖

| 指标 | 结果 |
|---|---:|
| 字幕键 | 897 |
| 空值 | 817 |
| 非空值 | 80 |
| 与现有 Sound 名称精确匹配的键 | 567 |
| 没有精确音频匹配的键 | 330 |
| 已关联地图 Actor/EventList/SoundList 的键 | 220 |
| DialogA 音频中缺字幕键的对象 | 11 |

空值中混有喘息、受击等声音及缺正文的对白，817 不是“遗漏的对白句数”。502 个 DialogA 键也不是完整现有对白索引。音频名与现有键表间同时存在未使用/旧名称及缺项。

11 个 DialogA 缺键对象：Grn_01..05、Int_16、Nar_01、Nar_02、Int_15、Int_17、Int_18e。需要先确认其剧情用途和本地实际触发，再补键。

完整逐键结果保存在 [字幕—音频—事件关联表](C:/GOG Games/The Wheel of Time/docs/phase1/subtitle_audio_map.json)：每条保留原文本/空状态、音频包、Sound 导出索引/偏移、地图 Actor、Tag、SoundDispatcher 的事件与 Delay，或明确记录无直接关联。当前静态事件关联覆盖 220 个键；这不是每个键的完整运行时播放时序。角色默认 SoundTable、继承、脚本动态触发仍需补追踪。

[地图音频事件索引](C:/GOG Games/The Wheel of Time/docs/phase1/map_audio_links.json) · [缺字幕键音频](C:/GOG Games/The Wheel of Time/docs/phase1/dialog_sounds_missing_keys.json)

### 补写与已有文本恢复

- 字幕结构是常规节/键/文本，原空项可以直接补正文，保留音频标识即可，中文字体解决后可沿用。
- 地图中恢复了教程对白/提示。部分 Messages 前有 `//`；**这不是文件注释，而是代码判断后跳过显示的字符串前缀**。保留这些作为对白来源，不自动启用其显示。
- 现有英文 `.int` 并未恢复全部剧情对白；声音导出名称只证明对应对象，不提供台词正文。
- 已核查 [字幕补丁作者的发布说明](https://www.oldunreal.com/phpBB3/viewtopic.php?p=100242)：作者说明其补全游戏内语音字幕，不覆盖 QuickTime 视频。当前未取得该附件正文，所以没有宣称完成其覆盖/兼容性比对。
- 已下载 [OldUnreal 的本游戏原始英文字幕表](https://github.com/OldUnreal/OldUnreal-Localization/blob/master/Wheel%20of%20Time/SystemLocalized/int/wotsubtitles.int)，仍为 897 键、80 非空，不是作者补全补丁。另有德语/西语/意语 WIP 文件，分别 321/332/630 非空；它们仅作异语文本来源与键名参考，不自动回填英文或翻译。
- 没有进行语音识别、整部转录或机器翻译。

## 4. 字体系统结构

**游戏内文字使用 UE1 UFont/FFontPage 位图图集，不是实时 Windows GDI 字体渲染。** 原生窗口使用 Windows 控件/字体，是另外一条路径。Editor.dll 确认包含 UFontFactory 和 UTrueTypeFontFactory；GDI/TrueType 可用于导入过程，不意味着 Canvas 自动使用系统中文字体。

| 包 | Font 数量 | 覆盖结构 |
|---|---:|---|
| `C:/GOG Games/The Wheel of Time/System/WOT.u` | 13 | 各 1 页 × 256 字符槽 |
| `C:/GOG Games/The Wheel of Time/System/Engine.u` | 4 | 各 1 页 × 256 字符槽 |
| `C:/GOG Games/The Wheel of Time/Textures/UWindowFonts.utx` | 9 | 4 页 × 64 或 8 页 × 32，共 256 槽 |

WOT.u 中确认：F_WOTReg08、F_WOTReg14、F_WOTReg30、F_WOTIta14、F_WOTReg14_S、F_WOTReg30_S，以及 F_Key/F_KeySelected/F_Charge 的普通和小尺寸版本、F_Element。

菜单的 `SetMenuListFont` 使用 F_WOTReg30 或 F_WOTReg14；HUD/字幕/帮助常用 F_WOTReg14；Inventory 标记和数字还使用专用符号字体。避免把数字/元素符号字体全部换成中文正文样式。

UFont 序列化已核对至对象末尾：基础属性结束 → Pages 数组 → 每页 Texture 对象引用和 Characters 数组 → 每字符四个 int32（StartU、StartV、USize、VSize）→ CharactersPerPage（int32）。最后的字段是 **CharactersPerPage，不是 Kerning**。

实例：`WOT.F_WOTReg14` 位于 WOT.u 偏移 130236、长 4106；引用 `F_WOTReg14.Texture9`，图集 256×128、带 Palette、Masked，256 槽中 190 个有非零矩形。对应字体源导入指令使用 PCX。

原生渲染证据：Engine.dll `UCanvas::WrappedPrint` 函数 RVA `0x693E0`，读取 `word` 字符；RVA `0x69555` 保留 16 位字符值，随后用 Font.CharactersPerPage 做除法，商选字体页、余数选字符，缺页/越界就留下零宽高。**不是强行截断为 8 位。**

因此预期的少侵入方案是：保留现有 ASCII 页，追加中文 Unicode 对应页/图集，不改 EXE/DLL。对 WOT 字体 CPP=256 时，“新/游/戏”需页 101/110/98，槽 176/56/15；应使用 Unicode 码点，不能把 GBK 的两个字节当两格字形。GB2312/GBK 可用于决定字库收录范围，文本发布仍优先 UTF-16。

现阶段尚未导入中文字体、尚未证明三个汉字实际成像；只是资源结构和渲染分支证实该路线有依据。下一轮先尝试原版编辑器 TrueType importer 的 Unicode 范围参数；若旧 importer 能力不足，再做保留对象身份/其他导出的字体资源写入器。由于 WOTCanvas 写死 Font'WOT.F_WOTReg14' 等引用，仅增加一个无引用的 Chinese.utx 不会自动生效。

[字体完整结构](C:/GOG Games/The Wheel of Time/docs/phase1/font_structure.json) · [Engine 渲染反汇编](C:/GOG Games/The Wheel of Time/docs/phase1/Engine_text_disassembly.txt) · [编辑器字体导入工厂](C:/GOG Games/The Wheel of Time/docs/phase1/Editor_font_exports.json)

## 5. 当前编码方式

- 本地日志版本 `333`，Game Version `333.310`，原日志编译日期 2000-01-12；原生日志明确标注 `Character set: Unicode`。
- 28 个现有 `.int` 纯 ASCII、无 BOM；WoTsubtitles.int 含高位字节，按 Windows-1252 可读出西文弯引号。检测标为 `cp1252-assumed`，不把“检测可解码”当成文件有编码声明。
- **内部字符串：16 位 TCHAR/FString，实际渲染逐 UTF-16/UCS-2 单元索引。** 本阶段未验证补充平面、代理对或现代复杂文本布局。
- Core.dll `appLoadFileToString` RVA `0x49700` 明确识别 FF FE / FE FF BOM，加载 UTF-16 LE/BE。没有 BOM 的分支逐字节零扩展至 16 位；该函数所见分支不是 GBK/CP932 多字节解码，也不是 UTF-8 解码。
- 所以避免保存 UTF-8 中文无 BOM、UTF-8 BOM 或 GBK 后直接期待正确显示。发布候选使用 **UTF-16 LE BOM**。
- 当前主机 Windows build 26300，ACP 932。本次没有改变非 Unicode 系统区域设置，UTF-16 不依赖把主机切成中文代码页。
- `.u`/地图中的 FString 属序列化字符串，不能直接当 `.int` 文本编码原地替换。

[编码检测清单](C:/GOG Games/The Wheel of Time/work/phase1/export/encodings.json) · [本版 Core 文件加载分支](C:/GOG Games/The Wheel of Time/docs/phase1/Core_load_string_full.txt)

## 6. 中文显示测试结果与视频字幕调查

### 最小测试

修改对象仅为工作副本的 `[menuSinglePlayer] MenuList[2]`，从 New Game 改为新游戏；整份 .int 因编码需要转为 UTF-16 LE BOM，**逻辑正文仅改 1 项**。

最终三次测试均使用完整隔离游戏副本、原版渲染配置，通过 `.\WoT.exe Entry -nosound` 启动，Escape → Enter 进入单人菜单，截图后 WM_CLOSE 正常退出。`-nosound` 仅用于菜单试验，本次不验证语音播放。

| 测试 | 画面观察 | 进程结果 |
|---|---|---|
| BASELINE | New Game 正常显示 | 正常退出 0 |
| MODIFIED | 新游戏对应菜单项无可见字形，其他英文正常；未见乱码替代字形或中文崩溃 | 正常退出 0 |
| ROLLBACK | 同字节恢复英文文件后，New Game 再次显示 | 正常退出 0 |
| LOCALE_CONTROL | 新建 WoT.zht + Language=zht 生效，New Game / 新游戏 / OK 只呈现 ASCII 与分隔符 | 正常退出 0 |

“画面只见 ASCII”描述的是**现有字体的表现**，不是整个游戏不支持 Unicode。原版字体缺页与零尺寸处理分支吻合。

[英文截图](C:/GOG Games/The Wheel of Time/docs/phase1/BASELINE.png) · [中文空白截图](C:/GOG Games/The Wheel of Time/docs/phase1/MODIFIED.png) · [回滚截图](C:/GOG Games/The Wheel of Time/docs/phase1/ROLLBACK.png) · [独立 locale 对照](C:/GOG Games/The Wheel of Time/docs/phase1/LOCALE_CONTROL.png)

试验中早期窗口化采集因旧渲染器/窗口选择/DPI 处理产生无效截图，并有一次采集后强制终止；这些没有当作中文测试结论。最终截图使用正确的原版全屏路径与 DPI-aware 坐标。只测试当前主机，Windows 10、其他主机及字体补丁长期稳定性尚未测试。

### MOV 调查

17 个视频均为 QuickTime，当前探测的视频为 Sorenson SVQ1，640×480；声音主要为 ADPCM IMA QuickTime。**Intro 与大部分 Mission 视频自带 legacy `text` 字幕轨**，不是仅凭文件名推测。

- 共 28 个文本轨，提取 1,538 个原始样本包；包括空白/换页样本，并非 1,538 句独立对白。
- 样本文本明确为意大利语与西班牙语，部分元数据错误标成 eng；不把它们冒充英文原台词。保留 MacRoman 和 CP1252 两种解码以及原始字节、样本偏移、起始/持续时间，便于后续校对。
- `GtLogo.mov`、`Logo.mov`、`Mission_10.mov` 无字幕流。**Mission_10 是当前明确需单独补调查的无轨剧情视频。**
- 所有 MOV 剧情内容均独立于 WoTsubtitles 查表链。语音片段名字 Int_* 的存在不能证明整段视频对白走游戏内字幕。
- 逐视频各取一个纯视频画面检查：抽样画面未见对白硬字幕；品牌 Logo/地图地名则有画面内图形文字。抽样不等于整段视频所有帧都无硬字幕。
- WinDrv.dll 内的 PlayMovie 路径含 QuickTime.qts / theQuickTimeDispatcher。现阶段没有确认它自动发现外置 SRT；有内嵌 text 轨也不等于该播放器可正确显示中文。这条路径的字体和编码要单独验证。
- 无需立即烧录字幕或重编码视频；优先研究已有文本轨的启用、文本格式和无损 remux，保证音视频数据不变。本轮未改 MOV。
- 初试 ffmpeg 转 SRT 出现旧字幕非 UTF-8 解码错误和样式异常，即使部分命令退出 0 也有缺句风险。最终以直接读样本的原始 JSON/TXT 为依据，初试 SRT 不作完整字幕交付。

[视频流清单](C:/GOG Games/The Wheel of Time/docs/phase1/movies.json) · [已有视频文本索引](C:/GOG Games/The Wheel of Time/docs/phase1/movie_text_summary.json) · [抽样画面](C:/GOG Games/The Wheel of Time/docs/phase1/movie_frames_contact.png)

## 7. 是否需要修改 EXE / DLL

**当前证据不支持先修改 EXE/DLL。** Unicode 输入、16 位 Canvas 字符、分页字体均已存在。最小中文缺字问题优先用字体资源解决。

但这不等于“只加 `.int` 就能完整汉化”：Font 主要嵌在 WOT.u，需要资源级改动；硬编码 UI 字面量需要另做处理；中文无空格换行、字幕覆盖、视频轨显示仍未验证。只有资源方案验证失败且定位到明确引擎缺陷后，再评估具体分支。当前未改任何原始 EXE、DLL、脚本逻辑、地图、玩法或视频。

## 8. 最推荐的汉化技术路线

1. **下一个验收点：仅三个汉字的 Font 测试。** 使用授权字体，保留原拉丁/数字/符号页，为“新游戏”追加分页字形；保持 Canvas 原 Font 引用与其他包对象不变。先证明成像、字符宽度、菜单测量、正常退出和回滚。
2. 字体试验成功后再扩展正文字符集：从已审定译文收集 Unicode 字符，不必首轮塞入全部 CJK；普通/小字号、正文/标题/UWindow 分别验证。
3. 文本采用 `.zht` + UTF-16 LE BOM；建立 glossary、数组索引/上下文、占位符和格式指令保护。暂不整库翻译。
4. 地图正文用 map localization sidecar，验证实例节名与默认值覆盖，不改地图。教程 `//` 跳过显示文本保留语义。
5. 取得补全字幕的实际文件后按本地 Sound 清单对比：新增/失效 key、空值、发声覆盖、事件顺序、显示时长；本地反向索引优先于自动听写。
6. MOV 单独建立时间轴文本：先利用原内嵌异语字幕辅助对齐，再找英文文本来源；Mission_10 单列。先验证 text 轨，不重编码音视频。
7. 多环境测试最后收口：Windows 10/11、ACP 1252/932/936、不同 DPI/分辨率、菜单/资料页/任务提示/字幕/视频。当前不把这一步标记完成。

## 9. 已有工具、后续工具与文件记录

### 已编写并验证

| 工具 | 当前功能 |
|---|---|
| `C:/GOG Games/The Wheel of Time/tools/int_tool.py` | 29 个 .int 导出 CSV/JSON；节/键/重复键 occurrence/行号/空值/编码/占位符；重复文本分组；CSV/JSON 导入已填写译文；限定写入 work；UTF-16 BOM；源文本一致性和占位符顺序检查 |
| `C:/GOG Games/The Wheel of Time/tools/ue1_scan.py` | UE1 包版本、名称/导入/导出、字体和 Sound 清单、ScriptText 片段抽取；只读 |
| `C:/GOG Games/The Wheel of Time/tools/map_audit.py` | 地图属性流、SoundEvent/SoundInfoT、Actor/Tag/Event/Delay 与音频关联；只读 |
| `C:/GOG Games/The Wheel of Time/tools/mov_text_export.py` | 原始 QuickTime text 样本/字节/时间/偏移提取；不重编码 |
| `C:/GOG Games/The Wheel of Time/tools/runtime_probe.py` | 隔离副本启动、单人菜单截图、关闭、日志/退出码记录 |
| `C:/GOG Games/The Wheel of Time/tools/ROLLBACK.sh` | 仅恢复 work 下的 WoT.int，字节比较原备份；已在另一份副本上执行 |
| `C:/GOG Games/The Wheel of Time/tools/test_phase1.py` | 7 项测试通过：29 文件原编码往返、单项修改、字体覆盖、地图错误清单、占位符、CSV 导入、回滚一致性 |
| `C:/GOG Games/The Wheel of Time/tools/verify_phase1.py` | 重跑文件检查/回滚/单元测试、277 原文件哈希复核与证据汇总 |

工具目前是第一阶段原型：不自动翻译，不自动安装补丁，不保证任意 Unreal 版本/复杂转义语法全部兼容；导入模式仅输出含译文的文件，未译文件沿用原资源。重复字符串仅分组，未跨上下文强制合并译文。Public 结构化条目整值回写被拒绝。

### 可复用工作流

```powershell
Set-Location 'C:\GOG Games\The Wheel of Time'
python tools\int_tool.py export backup\phase1-original\System work\phase1\export
# 在 CSV 或 JSON 的 translation 列填写已审定译文。
python tools\int_tool.py import backup\phase1-original\System work\phase1\minimal_translation.json work\phase1\modified --encoding utf-16le-bom
python tools\test_phase1.py
```

导出英文 → 带上下文 CSV/JSON → 人工翻译 → 源文/占位符/格式检查 → 工作目录回写 → 字体及画面测试 → 文件差异/哈希/回滚 → 发布补丁。

后续需要开发：中文 Font 页/图集构建与资源级打包器；map localization 导出与实例覆盖验证；完整字幕事件/默认 SoundTable 覆盖检查；QuickTime 文本轨编解码及不改音视频的补丁器；最终差分包 manifest、语言启用/卸载工具。当前不提前实现这些修改器。

### 本次修改记录与四件套

| 原文件/对象 | 修改文件 | 原因/方法 | 可逆性 |
|---|---|---|---|
| `C:/GOG Games/The Wheel of Time/System/WoT.int` | `C:/GOG Games/The Wheel of Time/work/phase1/modified/WoT.int` | 仅 MenuList[2] 替换；UTF-16 LE BOM 写入 | 原备份 + SHA-256；回滚实测 |
| 隔离 runtime/System/WoT.int | 同目录工作副本 | BASELINE/MODIFIED/ROLLBACK 文件轮换，最终保留中文测试副本 | 完整备份，原安装零覆盖 |
| 隔离 runtime/System/WoT.ini | 临时语言/窗口化试验，最终还原原内容 | 最终正式三轮使用原渲染配置；对照用 Language=zht | 原备份已回写工作副本 |
| 无原始 zht 文件 | `C:/GOG Games/The Wheel of Time/work/phase1/control/WoT.zht` 及 runtime 副本 | 新 locale + 混合 ASCII/中文对照 | 仅新增工作文件；安装未改 |

- MODIFIED_FILE：[中文测试文件](C:/GOG Games/The Wheel of Time/work/phase1/modified/WoT.int)
- DIFF_FILE：[逻辑文本差异](C:/GOG Games/The Wheel of Time/docs/phase1/WoT.int.diff)（另有整个文件编码变化）
- VERIFICATION：[命令/输入/原样输出/退出码/哈希/恢复状态](C:/GOG Games/The Wheel of Time/docs/phase1/VERIFICATION.txt)
- ROLLBACK：[回滚脚本](C:/GOG Games/The Wheel of Time/tools/ROLLBACK.sh)

原 WoT.int SHA-256：`6529b7552f52614aa8717ae1493edb1912abca6687f59df26bd75d0714e034f8`。
中文副本 SHA-256：`7fe9a65dd87549c0f2762bb73942b0d22c6e80c08907984340cad84ed941bca3`。

原安装保持英文且全部原文件哈希一致；回滚测试副本恢复英文并有画面验证；中文 MODIFIED_FILE 保持修改。**本阶段完成结构分析与失败机制定位，尚未完成中文字体成像或全游戏汉化。**

## 后续三字字体验证
已补入新/游/戏并实际显示“新游戏”，不改EXE/DLL。详见 `C:\GOG Games\The Wheel of Time\docs\phase2\REPORT_zh-CN.md`，以及同目录 VERIFICATION.txt / FONT_DIFF.json。
