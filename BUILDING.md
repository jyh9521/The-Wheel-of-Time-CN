# 构建与复现

## 环境

工具：Python **3.14**（本地验证 3.14.2），Pillow 12.2.0、fonttools 4.63.0。
Windows 10/11 上执行原版游戏实机 QA；Linux CI 只跑合成测试及译文校验。
不使用 Python `-O`，资源完整性断言必须启用。
无需 Unreal SDK、编译器、QuickTime 重编码工具或预编译补丁 DLL。

## 用户自行提供的输入

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

字体与游戏路径均由使用者提供；不依赖 `work/phase*`、作者备份或手改资源。
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
不启动游戏。安装器会拒绝用户随后编辑过的资源，避免覆盖修改。
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

当前 QA 仅1920x1080；`--resolution` 默认1920x1080。1366x768与2560x1440延后由用户在汉化完成后检查。
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

新正式目录为C:/Users/noway/Downloads/The-Wheel-of-Time-CN；路径只是当前实例，不写入工具核心。始终从源码树执行build.py，以--game-dir指定指纹匹配的原版安装、--font指定字体、--out指定输出。此前game-root的backup/work和现成汉化包均不是依赖。构建仅需System/WOT.u、WoT.int、WoTsubtitles.int、Angreal.int；运行时探针另需完整游戏，但迁移测试没有运行探针。install.py用--target引用用户副本，自动备份与严格散列回滚。

旧根目录工具原位保留，legacy命令并非正式构建前置步骤；MOV/map等辅助研究暂不加入生产路径。新目录起初为无.git模板文件树，现已从原GitHub origin/main接回完整历史；迁移修改已普通推送于3df2156。源码独立构建验证与远程发布是两件事。完整迁移与后续缺项见docs/MIGRATION_AUDIT.md。

## Controls逐行显示检查

`python -m tools.validate.runtime --game-dir "GAME" --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view options --sweep` 在一次启动内仅Down选择并捕获11项帮助；加--original执行原版对照。行数来自语言无关profiles/qa-policy.json的menu_item_counts。未配置视图禁止sweep；普通单帧接口保持不变。所有这些runtime命令会启动隔离游戏副本，离线plan命令不启动。

## 当前1080p与字形布局

后续开发QA只跑1920x1080；QA plan为10个原/改视图探针，不再自动运行1366x768/1440p。这两种分辨率延后给玩家最终验收，历史记录不删除；4K仍为已知问题。

正常build入口自动重建完整字形边界并按profile.font_line_height_policy=preserve-legacy保留原版行高；locale.font提供collection_index、top_padding/bottom_padding（当前0）。旧baseline_anchor仅兼容覆盖检查，不再决定裁剪边界。随后应用profile中经过版本/导出SHA/上下文保护的字幕显示Y字段。FONT_DIFF的bytecode_unchanged仅属于字体阶段，最终BUILD_REPORT.resource_edits/bytecode_unchanged才描述完整输出。无需手工改二进制。详见docs/GLYPH_LAYOUT_FIX.md。

## 全字幕专项进展（2026-10-03）

当前49条草稿；保留原37条，补译教程Tes_02～Tes_13。教程原版80条英文均非空，但中文仅13/80；其余对白817空键须分类恢复，不能等同817句缺文。新译文已静态构建验证，实际后续触发/时序、剧情视频与全对白覆盖待验。详见[字幕覆盖报告](docs/SUBTITLE_COVERAGE.md)。

## 可选字幕来源审计

用户提供的社区字幕可用tools.import.subtitle_source在独立目录保守合并；命令和来源见docs/SUBTITLE_COVERAGE.md。此步骤仍为研究准备，不自动加入当前49条生产构建；原版profile输入保持不变，不用覆盖原游戏来构建。

## 可选社区字幕来源：生产构建入口

```powershell
python build.py extract --locale zh-CN --game-dir "GAME" --subtitle-source "DOWNLOADED_SUBTITLES" --out build/source-export
python build.py validate --locale zh-CN --game-dir "GAME" --subtitle-source "DOWNLOADED_SUBTITLES" --font "FONT"
python build.py --locale zh-CN --game-dir "GAME" --subtitle-source "DOWNLOADED_SUBTITLES" --font "FONT" --out build/source-enabled
```

下载文件作为外部输入；支持的SHA-256与47语音资源版本记录在profiles/subtitle-source.json。全新克隆+原版游戏+匹配的社区文件+字体即可重建，无旧工作目录依赖。省略--subtitle-source保留基础49条构建，结果与接入前相同。启用时另读locale.config.subtitle_rows；当前294条中233未译，61已有译文均草稿，strict失败是预期。源层临时目录退出后清理；最终PATCH包含恢复英语和已有中文，不是中文全覆盖Release。

`--subtitle-source`未知/改动输入在写产物前拒绝；保留原版profile和安装器原版hash校验。字幕Len补偿以合并后真实英文长度为基准；已有教程英文被保留，因此原49条的源hash与时长规则不变。

## 教程翻译批次（2026-10-03）

Tes_01～Tes_80已全部有中文草稿；本轮追加67条，原49条保持。基础译文116条，启用社区来源时361条中128条已有译文、233条待译。文本完成不等于实机验收：本轮未启动游戏，由用户在1080p检查完整教程及分支。测试方法和80键清单见[TUTORIAL_QA.md](docs/TUTORIAL_QA.md)。本地差分预览包包含标准库安装器，安装/核验/回滚已验证；未发布公共Release。

## 开场缺段修正

Tes_01原非空文本也会缺段：本轮仅经双source hash批准采用社区完整432字符，译文由subtitle_overrides组合，Len补偿使用432而非350。完整版教程构建需--subtitle-source；其余条目不动。详见[TUTORIAL_INTRO_FIX.md](docs/TUTORIAL_INTRO_FIX.md)；80/80非空key不等于音频全段覆盖。


## 当前字幕来源策略（2026-10-03）
采用社区优先完整并集：所有同key冲突使用社区值，原版独有key保留。详见 [COMMUNITY_SOURCE_POLICY](docs/COMMUNITY_SOURCE_POLICY.md)。旧保守合并描述仅为历史记录。

## 实验性字幕分段模块

单音频多段字幕的资源级实验模块需原版GOG UCC（不再分发），独立构建入口为`python -m tools.build.subtitle_runtime build --game-dir GAME --locale zh-CN --out build/subtitle-timing-audit/fixed`。它不改地图/音频/EXE/DLL，不自动替换玩家类或默认汉化构建；专用测试入口、安装/回滚及实机限制见[SUBTITLE_SEGMENTS](docs/SUBTITLE_SEGMENTS.md)。编译成功不等于游戏中类选择、分段或存档兼容验收通过。


## 全文首轮构建与覆盖审计（2026-10-04）

当前profile额外固定原版WoTPawns.int与WoTTraps.int的大小/SHA-256；构建仍从用户原版读取，生成资源增至6个。没有固定“4文件”的安装假设，集成验证按实际manifest文件数执行。

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

locale.config.native_ui指向native-ui.json，默认构建接入Preferences子字段导入器；本批新增13个原版hash固定的.int输入，PATCH共19资源，不依赖旧手工文件。省略native_ui配置可关闭该阶段。原生UI使用Windows字体，而非游戏字库；新增译文的字体覆盖会在validate --font中检查。新语言需同步树根标题及所有Caption/Parent；详见[原生高级选项](docs/NATIVE_ADVANCED_OPTIONS.md)。
