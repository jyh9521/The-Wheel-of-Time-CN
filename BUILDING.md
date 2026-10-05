# 构建与复现

## 环境

工具：Python **3.14**（本地验证 3.14.2），Pillow 12.2.0、fonttools 4.63.0。
Windows 10/11 上执行原版游戏实机 QA；Linux CI 只跑合成测试及译文校验。
不使用 Python `-O`，资源完整性断言必须启用。
无需 Unreal SDK、编译器、QuickTime 重编码工具或预编译补丁 DLL。

## 玩家或开发者自行提供的输入

1. 一份未修改的 GOG 安装；4 个必需资源见 `profiles/gog-v68.json`：
   `System/WOT.u`、`WoT.int`、`WoTsubtitles.int`、`Angreal.int`。
   文本提取可额外读取 System 里的其他 `.int`；完整游戏副本仅实机 QA 使用。
2. 一份允许用于所选用途、覆盖译文字符的 TTF/OTF/TTC 字体；通过 `--font` 指定。
   TTC 子字体索引来自 locale 配置。字体不捆绑。
   本地 PoC 用 Windows 自带字体验证，**不是再分发字体授权**。
   若用其他字体，原资源与字符映射仍可重建，但像素及输出散列会改变；须重新验收。
3. 原版版本、大小、SHA-256 必须匹配 profile；未知版本首先研究并新增 profile，不能绕过检查。

## 全新克隆 → 构建

```powershell
git clone https://github.com/jyh9521/The-Wheel-of-Time-CN.git
cd The-Wheel-of-Time-CN
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python build.py test
.venv/Scripts/python build.py validate --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf"
.venv/Scripts/python build.py --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf"
```

字体与游戏路径均通过构建参数提供；不依赖 `work/phase*`、作者备份或手改资源。
输出必须在原安装之外，默认 `build/<locale>/`，可通过 `--out` 指定。
生产构建前运行 `validate --strict`：当前基础116条均为draft；启用社区来源时还包括12条draft和233条pending，因此严格验收应失败，不能伪装已审校。

## 产物

- `resources/System/`：仅发生变化的资源副本；本地使用，不提交完整游戏资源。
- `FONT_DIFF.json` + atlas PNG：字形映射、矩形/字宽、字体改动与预览。
- `PATCH.json`：版本化 COPY/LITERAL 差分，安装前后 SHA-256 校验。
- `BUILD_REPORT.json`：原/改文件大小与散列、字体文件散列、依赖版本、语言配置/译文散列、字幕补偿。
- `build/qa/`：可选的原生运行日志、截图和记录；生成物不推送。

差分和字库仍可能包含字体衍生数据/游戏结构数据，**本地构建不自动批准再分发**。
发布前选择可再分发字体、审查差分、添加许可与玩家说明。
目前没有预编译二进制工具或正式安装包；所有工具都是 Python 源码。

## 可重复构建与回滚

同一 profile、译文、配置、字体 SHA-256/TTC 索引、Python 与依赖版本，应产生相同资源和差分。
构建记录保存这些输入身份；资源中不嵌入私人路径或运行时间。

```powershell
python build.py --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf" --out build/repeat
python -m tools.validate.integration --game-dir "D:/GOG Games/The Wheel of Time" --build-dir build/zh-CN --out build/rollback-test
```

集成测试在独立四资源副本中执行原始读取、差分安装、逐字节校验、恢复，并保留已构建资源不变。
不启动游戏。安装器会拒绝安装后又编辑过的资源，避免覆盖修改。
回滚只能证明资源恢复，不能代替真实运行、存档/切图/战斗验收。

## 文本工作流

```powershell
python build.py extract --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --out out/extract
# 编辑 strings.csv 的 translation 列；同源重复行可参考 duplicates.json，不能丢失各 ID。
python -m tools.import.catalog out/extract/strings.csv out/translation.json
# 评审后将所选条目并入 locales/<locale>/strings.json，不把完整原文导出文件提交仓库。
python build.py validate --locale zh-CN --font "D:/Fonts/source-font.ttf"
python build.py --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf"
```

## 实机 QA（必须显式运行）

自行复制完整原版为独立 `build/runtime/`；脚本检查其不是源安装或其子目录。

```powershell
python -m tools.validate.runtime --game-dir "D:/GOG Games/The Wheel of Time" --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view menu
```

当前 QA 仅1920x1080；`--resolution` 默认1920x1080。1366x768与2560x1440延后安排在汉化完成后检查。
4K仅保留既有测试证据和已知问题，不再进入主动测试/适配矩阵。
可先离线生成原/改资源对照计划，不会启动游戏：

```powershell
python -m tools.validate.qa_policy --locale zh-CN --out build/qa-plan.json
```

矩阵与推荐值维护在 `profiles/qa-policy.json`，对所有语言共用；计划以1080p优先。
视图：main（主菜单）、menu（单人菜单）、options（Controls）、inventory、subtitle；`--original` 跑未改资源对照。
脚本只发送键盘到前台的自己启动窗口，关闭自己的主窗口；测试时保持窗口前台，不操作其他应用。
日志必须出现相应 `Best-match display mode`；JSON 的窗口截图尺寸仅表示桌面捕获面积。
画面是否有字、裁切、换行、标点和清晰度必须人工观察。

## 迁移后的独立构建

新正式目录为C:/Users/noway/Downloads/The-Wheel-of-Time-CN；路径只是当前实例，不写入工具核心。始终从源码树执行build.py，以--game-dir指定指纹匹配的原版安装、--font指定字体、--out指定输出。此前game-root的backup/work和现成汉化包均不是依赖。构建仅需System/WOT.u、WoT.int、WoTsubtitles.int、Angreal.int；运行时探针另需完整游戏，但迁移测试没有运行探针。install.py用--target引用指定的副本，自动备份与严格散列回滚。

旧根目录工具原位保留，legacy命令并非正式构建前置步骤；MOV/map等辅助研究暂不加入生产路径。新目录起初为无.git模板文件树，现已从原GitHub origin/main接回完整历史；迁移修改已普通推送于3df2156。源码独立构建验证与远程发布是两件事。完整迁移与后续缺项见docs/MIGRATION_AUDIT.md。

## Controls逐行显示检查

`python -m tools.validate.runtime --game-dir "GAME" --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view options --sweep` 在一次启动内仅Down选择并捕获11项帮助；加--original执行原版对照。行数来自语言无关profiles/qa-policy.json的menu_item_counts。未配置视图禁止sweep；普通单帧接口保持不变。所有这些runtime命令会启动隔离游戏副本，离线plan命令不启动。

## 当前1080p与字形布局

后续开发QA只跑1920x1080；QA plan为10个原/改视图探针，不再自动运行1366x768/1440p。这两种分辨率延后给玩家最终验收，历史记录不删除；4K仍为已知问题。

正常build入口自动重建完整字形边界并按profile.font_line_height_policy=preserve-legacy保留原版行高；locale.font提供collection_index、top_padding/bottom_padding（当前0）。旧baseline_anchor仅兼容覆盖检查，不再决定裁剪边界。随后应用profile中经过版本/导出SHA/上下文保护的字幕显示Y字段。FONT_DIFF的bytecode_unchanged仅属于字体阶段，最终BUILD_REPORT.resource_edits/bytecode_unchanged才描述完整输出。无需手工改二进制。详见docs/GLYPH_LAYOUT_FIX.md。

## 全字幕专项进展（2026-10-03）

当前49条草稿；保留原37条，补译教程Tes_02～Tes_13。教程原版80条英文均非空，但中文仅13/80；其余对白817空键须分类恢复，不能等同817句缺文。新译文已静态构建验证，实际后续触发/时序、剧情视频与全对白覆盖待验。详见[字幕覆盖报告](docs/SUBTITLE_COVERAGE.md)。

## 可选字幕来源审计

已下载的社区字幕可用tools.import.subtitle_source在独立目录保守合并；命令和来源见docs/SUBTITLE_COVERAGE.md。此步骤仍为研究准备，不自动加入当前49条生产构建；原版profile输入保持不变，不用覆盖原游戏来构建。

## 可选社区字幕来源：生产构建入口

```powershell
python build.py extract --locale zh-CN --game-dir "GAME" --subtitle-source "DOWNLOADED_SUBTITLES" --out build/source-export
python build.py validate --locale zh-CN --game-dir "GAME" --subtitle-source "DOWNLOADED_SUBTITLES" --font "FONT"
python build.py --locale zh-CN --game-dir "GAME" --subtitle-source "DOWNLOADED_SUBTITLES" --font "FONT" --out build/source-enabled
```

下载文件作为外部输入；支持的SHA-256与47语音资源版本记录在profiles/subtitle-source.json。全新克隆+原版游戏+匹配的社区文件+字体即可重建，无旧工作目录依赖。省略--subtitle-source保留基础49条构建，结果与接入前相同。启用时另读locale.config.subtitle_rows；当前294条中233未译，61已有译文均草稿，strict失败是预期。源层临时目录退出后清理；最终PATCH包含恢复英语和已有中文，不是中文全覆盖Release。

`--subtitle-source`未知/改动输入在写产物前拒绝；保留原版profile和安装器原版hash校验。字幕Len补偿以合并后真实英文长度为基准；已有教程英文被保留，因此原49条的源hash与时长规则不变。

## 教程翻译批次（2026-10-03）

Tes_01～Tes_80已全部有中文草稿；该阶段追加67条，原49条保持。基础译文116条，启用社区来源时361条中128条已有译文、233条待译。文本完成不等于实机验收：这一阶段只做了离线验证，未运行游戏，完整教程及分支留待1080p实机检查。测试方法和80键清单见[TUTORIAL_QA.md](docs/TUTORIAL_QA.md)。本地差分预览包包含标准库安装器，安装/核验/回滚已验证；未发布公共Release。

## 开场缺段修正

Tes_01原非空文本也会缺段：该阶段仅经双source hash批准采用社区完整432字符，译文由subtitle_overrides组合，Len补偿使用432而非350。完整版教程构建需--subtitle-source；其余条目不动。详见[TUTORIAL_INTRO_FIX.md](docs/TUTORIAL_INTRO_FIX.md)；80/80非空key不等于音频全段覆盖。


## 当前字幕来源策略（2026-10-03）
采用社区优先完整并集：所有同key冲突使用社区值，原版独有key保留。详见 [COMMUNITY_SOURCE_POLICY](docs/COMMUNITY_SOURCE_POLICY.md)。旧保守合并描述仅为历史记录。

## 实验性字幕分段模块

单音频多段字幕的资源级实验模块需原版GOG UCC（不再分发），独立构建入口为`python -m tools.build.subtitle_runtime build --game-dir GAME --locale zh-CN --out build/subtitle-timing-audit/fixed`。它不改地图/音频/EXE/DLL，不自动替换玩家类或默认汉化构建；专用测试入口、安装/回滚及实机限制见[SUBTITLE_SEGMENTS](docs/SUBTITLE_SEGMENTS.md)。编译成功不等于游戏中类选择、分段或存档兼容验收通过。


## 全文首轮构建与覆盖审计（2026-10-04）

当前profile额外固定原版WoTPawns.int与WoTTraps.int的大小/SHA-256；构建仍从指定的原版读取，生成资源增至6个。没有固定“4文件”的安装假设，集成验证按实际manifest文件数执行。

```powershell
python -m tools.validate.text_coverage --locale zh-CN --game-dir "GAME" --subtitle-source "DOWNLOADED_SUBTITLES" --out build/coverage.json
```

覆盖审计区分非空草稿、原样保留条目、未纳入文本、与源文完全相同的值；不会把`validate`的0空译文当成全中文或审校完成。当前1002草稿仍全部draft；--strict应失败。165条保留规则按身份与精确源文SHA-256固定，改变来源则重新审查。其余工具/字体/来源依赖与重建命令不变。

## 图片按钮构建（2026-10-04）

默认 `python build.py --locale zh-CN --game-dir GAME --subtitle-source DOWNLOADED_SUBTITLES --font FONT --out build/zh-CN` 已包含八张中文按钮纹理；不依赖手工图片或旧工作区。配置、原对象指纹和工具分别位于locales/<locale>/texture-labels.json、profiles/texture-labels.json、tools/font/build_texture_labels.py。字体必须覆盖全部标签字符。输出仍为六资源PATCH.json，额外输出TEXTURE_LABEL_DIFF.json和texture-labels/*.png。省略locale的texture_labels配置可跳过图片标签阶段。

可单独验证范围：

```powershell
python -m tools.validate.texture_labels --source MODIFIED_WOT --profile profiles/texture-labels.json --manifest TEXTURE_LABEL_DIFF.json --baseline PREVIOUS_WOT
```

BASELINE指此前字库/译文一致、未修改按钮的WOT.u副本；范围测试要求所有其他导出对象、包表和文件大小不变。全新构建无需该副本，只需要经profile校验的原版游戏、社区字幕来源及字体。

## 原生高级选项补翻（2026-10-04）

locale.config.native_ui指向native-ui.json，默认构建接入Preferences子字段导入器；该批新增13个原版hash固定的.int输入，PATCH共19资源，不依赖旧手工文件。省略native_ui配置可关闭该阶段。原生UI使用Windows字体，而非游戏字库；新增译文的字体覆盖会在validate --font中检查。新语言需同步树根标题及所有Caption/Parent；详见[原生高级选项](docs/NATIVE_ADVANCED_OPTIONS.md)。

## 操作设置动态值适配

默认构建自动应用`profiles/gog-v68.json`的`display_expressions`，仅修改构建副本的菜单显示函数；无额外运行时DLL/EXE补丁，无额外字体或语言依赖。输出仍为19资源PATCH.json，新增MENU_VALUE_DIFF.json记录函数哈希、字节数、VM长度及六个槽位。其他语言复用既有OnText/OffText译文。

可重现编译格式验证（仅编译自编夹具，不启动游戏；需要指定的原版UCC及已校验依赖）：

```powershell
python -m tools.validate.display_compiler --game-dir GAME --out build/display-proof
python -m tools.validate.menu_values modified --reference GAME/System/WOT.u --package build/zh-CN/resources/System/WOT.u
```

夹具不安装到游戏或提交其生成包。原版输入只读，通用build无需运行UCC；适配所需指纹和表达式在源码仓库中。

## 深层高级选项、纹理细节与制作人员页

当前默认构建为20资源（新增Window.dll差分）；需要原版System/Window.dll，原始大小/hash已入profile。依赖由`requirements.txt`提供pefile 2024.8.26及keystone-engine 0.9.2；模拟验证额外`python -m pip install -r requirements-dev.txt`（unicorn 2.1.4）。构建命令不变，干净源码+原版游戏+既有字幕来源+字体即可重建，不需预编译适配DLL。

locale的credits.json保存默认数组译文和新增署名；native-properties.json保存原生显示表及布局配置。生成CREDITS_DIFF.json、NATIVE_DISPLAY_DIFF.json、MENU_VALUE_DIFF.json。若不使用原生显示适配，可删除locale.config.native_properties配置并重新构建，其他资源仍可生成。

```powershell
python -m tools.validate.settings_followup modified --game-dir GAME --resources build/zh-CN/resources/System
python -m tools.validate.native_display --dll build/zh-CN/resources/System/Window.dll --report build/zh-CN/NATIVE_DISPLAY_DIFF.json
```

第二条只在CPU模拟器执行自编显示stub，不启动或注入游戏。安装前完整退出游戏，使用新20文件manifest；升级现有19文件补丁先通过旧manifest恢复，再应用新manifest。原始游戏目录只作输入，测试目录另行保存；卸载按新manifest恢复20个原版资源。

## 动态文本补漏与FMV提取（2026-10-04）

基础构建新增键名表和6条进度文字，字库覆盖35条教程提示。提示须另行重建LocaleRuntime并使用现有Game+Class入口；源地图只读且指纹核验。详见[UI_TEXT_FOLLOWUP](docs/UI_TEXT_FOLLOWUP.md)。FMV的ffprobe参数化只读提取见[FMV_SUBTITLES](docs/FMV_SUBTITLES.md)，暂不安装视频字幕或重编码。

## 设置补漏构建与验证

已补上循环竞技场关卡和高级选项下拉列表的显示、查找与反向回写适配，原始配置值保持不变。此前对应待办由本节更新；159项测试、730项CPU模拟、UCC加载通过，1080p实机切换与保存待验。实现、位置及命令见[设置动态值补漏](docs/SETTINGS_VALUES_FIX.md)。未知标识、设备/API与自定义值仍保留原样。
## 完整 FMV 中文字幕构建

游戏内最小显示已经确认。先按上面的命令构建普通汉化资源，再用 `python -m tools.build.build_fmv build --game-dir "GAME" --runtime-dir "GAME" --resource-build "BUILD_OUTPUT" --out build/formal-game --locale zh-CN` 生成独立的完整游戏副本，不依赖旧的 build/runtime。原片/播放器均做版本门禁，普通资源与 14 段剧情的 628 条对白一起导入，音视频不重编码；字体由系统提供。详情、核验及独立回滚见 [FMV 正式测试](docs/FMV_FULL_QA.md)。下面保留之前的 PoC 入口作为研究历史，不作为正式测试入口。

## 独立 FMV 中文字幕实验入口

提供了不安装、不启动游戏的原生 QuickTime 预览构建：

```powershell
python -m tools.build.build_fmv_preview --game-dir "GAME" --locale zh-CN
```

依赖 Windows .NET Framework 4 csc（编译为 x86）、Python 和系统已安装的 QuickTime。
原版输入仅 Movies/Intro.mov，SHA 门禁来自 locales/zh-CN/fmv_probe.json。
QuickTime 路径默认读取 32 位注册表，亦可显式传 --qt-dir。产物为 build/fmv-preview 下
MODIFIED_FILE.mov、DIFF_FILE.json、quicktime_player.exe、PREVIEW.json、PLAY_FMV.ps1 和 ROLLBACK.sh。
没有复制 QuickTime DLL 或字体；系统需提供配置的字体。测试视频只有第 1–7 秒一条中文。
入口/回滚/验收与原生字段说明见 [FMV 研究](docs/FMV_SUBTITLES.md)。

## 游戏内 FMV 隔离测试构建

先建立游戏内最小验证，不先翻译全片：

```powershell
python -m tools.build.build_fmv_game_probe build --source "GAME_OR_LOCALIZED_COPY" --locale zh-CN --out build/fmv-game-qa
```

输入需要完整目录，且 WinDrv.dll 与 Intro.mov 必须匹配所记录的原版 SHA；可以使用此前
build/runtime 来保留已有汉化。原版目录也可直接重建，只是菜单不会因此全部变为中文。
工具物理复制资源到新的输出目录，不启动游戏，不覆盖旧目录。输出游戏入口为
build/fmv-game-qa/LAUNCH_GAME.ps1；运行后在主菜单选择“重播开场”。
范围、回滚、离线证据和游戏内待验收项见 [FMV 游戏验证](docs/FMV_GAME_QA.md)。
