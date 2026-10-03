# 《时光之轮》本地化工程 / The Wheel of Time Localization

## 项目简介

面向 **The Wheel of Time (1999, Legend Entertainment) GOG 版**的资源级本地化工程。
当前目标是简体中文 `zh-CN`，技术层供其他语言复用，而不是一次性中文补丁。

## 支持版本与状态

- 支持本项目已记录指纹的 GOG 英文资源；Windows 10/11 为目标平台。
- 当前为 **116条基础草稿 + 可重建工具链**；启用社区来源时128条已有译文，教程80/80已译，仍不是完整汉化。
- 已验证 Unicode 菜单、Inventory 标题/正文/斜体引文、教学首句字幕。
- 新增主菜单及Controls小规模PoC，最新验证记录见 [菜单PoC](docs/menu-poc.md)。
- 合成测试不需要游戏；真实构建和集成需自行提供原版游戏与覆盖字体。
- **推荐玩家使用 1920×1080（1080p）游玩。** 后续开发 QA 只检查1920×1080；1366×768、1440p留给翻译完成后的玩家验收。历史对照保留。
  4K 下原版固定像素字体/UI 偏小，列为已知问题，不再做专项适配。
  最新结果与剩余问题见 [QA](docs/qa.md)，不能把桌面截图尺寸当作游戏内部模式。

当前首轮正文覆盖状态（2026-10-04）：基础757条，加社区补全245条，合计1002条非空草稿；含全部325条有原文字幕、菜单/帮助/任务说明、法器说明及单位/陷阱说明。另165条格式控制、资源类名、按键标签或None标记保留。此前42条源文相同的待确认条目现已按维护者确认译名回填；剩余审计清单中的专名与三段可读英文已按确认结果修订，四处玩家可见诊断/模板/编辑器标签亦已改为中文，机器标识和键名保留；视频/地图/硬编码及全流程QA尚未全部覆盖。详见[全文批次与剩余工作](docs/FULL_TRANSLATION_BATCH.md)。

## 下载

源码：本仓库。玩家成品将放在 [GitHub Releases](https://github.com/jyh9521/The-Wheel-of-Time-CN/releases)。
**目前没有完整汉化正式 Release**，不要把开发构建误认为成品。
仓库不提供游戏本体、原程序、整包资源或 Windows 字体。

## 安装 / 使用

现阶段先按 [BUILDING.md](BUILDING.md) 从原版构建，在独立副本验收。
构建成功后会产生资源副本及版本校验的差分包：

```powershell
python install.py apply --bundle build/zh-CN/PATCH.json --target "D:/Games/WoT-QA"
python install.py verify --bundle build/zh-CN/PATCH.json --target "D:/Games/WoT-QA"
python install.py restore --bundle build/zh-CN/PATCH.json --target "D:/Games/WoT-QA"
```

`apply` 只接受匹配原版指纹；先备份所有目标，再写入并重读。
回滚从目标副本 `.localization-backup/` 恢复，不需要作者的私人备份目录。
备份勿删除。安装后自行在 User.ini 的 `[WOT.WOTPlayer]` 中启用 `bSubtitles=True`。
安装器不修改 EXE、DLL、启动器、地图、玩法或配置文件。

## 技术摘要

本版本支持 UTF-16 LE BOM `.int`；中文缺字来自位图字体覆盖，不需要 GBK 或引擎 hook。
工具保留原字体 0–255 映射，将 Font 的 CharactersPerPage 从 256 改为 64，
按实际译文生成不超过 256×256 的 P8 atlas，并追加资源及重建目录表。
六个 Font 对象改变；另有一个字幕绘制Y坐标常量从0改为24px，8370个其他原导出保持。
这是 **Unreal/WoT 适配层限制**，不是所有游戏的通用格式。

## 仓库结构

- `locales/<locale>/`：译文与语言配置；当前 `zh-CN`。术语唯一基准为根目录 `GLOSSARY.md`。
- `profiles/`：已知游戏版本指纹、字体名/尺寸、调色板色彩与游戏约束。
- `tools/{extract,import,font,pack,build,validate}/`：语言无关工具。
- `src/patch/`：差分格式；`src/runtime/` 目前无 hook 实现。
- `docs/`：规范、逆向结构、踩坑、已知问题、QA。
- `tests/`：不含游戏资产的合成测试。
- `assets/`：配置模板、字体使用说明，不包含未授权字体。
- `build/`、`dist/`、`out/`：生成物，Git 忽略。

## 从源码重建

```powershell
python -m pip install -r requirements.txt
python build.py --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf"
```

完整依赖、输入、输出、可重复性和测试见 [BUILDING.md](BUILDING.md)。

## 参与翻译 / 添加语言

编辑结构化译文与术语，运行 `python build.py validate --locale zh-CN`。
新增 `locales/ja-JP/`、`ko-KR/` 或 `zh-TW/` 的数据与配置即可复用工具，
但要提供覆盖字体并完成实机验收；未声称这些语言已经游戏内验证。
参阅 [TRANSLATING.md](TRANSLATING.md) 与 [TECHNICAL.md](TECHNICAL.md)。
本地维护指令文件不在公开仓库中跟踪。

## 译名与翻译参考

本汉化的《时光之轮》世界观、人名、地名、组织名及魔法体系等专有名词，主要参考中文出版版的既有译名体系，并以时光之轮中文 Wiki（灰机 Wiki）整理的中文资料进行检索、核对与统一。正传中文译本译者为李镭，前传《新春》译者为王密。游戏原创内容在既有译名体系基础上另行翻译。

中文出版版提供既有译名体系；灰机 Wiki 是粉丝维护的中文资料库，用于核对和统一这些既有译法，并非官方 Wiki 或官方译名来源。

项目根目录的 [GLOSSARY.md](GLOSSARY.md) 是本项目**唯一术语基准（single source of truth）**，翻译与校对均应以其为准。参考资料用于辅助查证，不另设与该文件并行的术语基准。

参考链接：

- [时光之轮中文 Wiki](https://twot.huijiwiki.com/wiki/首页)
- [《时光之轮1·世界之眼》中文出版信息](https://book.douban.com/subject/2061650/)
- [项目内部术语表](GLOSSARY.md)

## 已知问题

字幕 897 个键中 817 个原文为空；地图实例文字、部分硬编码 UI、视频轨道不在当前构建范围。
字体仍沿用原版固定像素尺寸；4K UI 偏小保留为已知问题，建议切换1080p。
当前继续1080p菜单、Inventory和字幕覆盖验证，不为4K改引擎或缩放系统。
字形完整边界适配保留原版行高，教程字幕留出24px上边距，见[字形与字幕位置修复](docs/GLYPH_LAYOUT_FIX.md)。当前字幕长度补偿不是音频时间码同步。详见 [known-issues](docs/KNOWN_ISSUES.md)。

## 开发与测试进展

以下保留各阶段的迁移、字幕、教程及 QA 记录；阶段记录中的数据反映当时进度，当前总体状态见前文“支持版本与状态”。今后新增开发进展统一放在本节，保持“许可”和“致谢”位于文末，“致谢”为最后一节。

### 工作区迁移

新正式工作区已复用现有工具链并审计旧游戏目录；旧原件保留，生成物不迁移。迁入内容、旧脚本原位保留原因与独立重建证据见[迁移审计](docs/MIGRATION_AUDIT.md)。迁移没有重新翻译，也没有启动游戏。

Controls的11项标签及11条帮助已完成草稿回填和1080p逐项显示验收；1366×768、1440p完成代表帧抽查，详见[Controls显示QA](docs/CONTROLS_QA.md)。37条仍待译文审稿，并非完整汉化。

### 全字幕专项进展（2026-10-03）

当前49条草稿；保留原37条，补译教程Tes_02～Tes_13。教程原版80条英文均非空，但中文仅13/80；其余对白817空键须分类恢复，不能等同817句缺文。新译文已静态构建验证，实际后续触发/时序、剧情视频与全对白覆盖待验。详见[字幕覆盖报告](docs/SUBTITLE_COVERAGE.md)。

### 可选字幕来源构建进展

已支持--subtitle-source，经manifest校验后保守合并245条恢复来源；locale中独立保存245条结构化字幕，其中12条新中文草稿、233条待译。默认49条构建保持兼容，启用来源时61条已有译文/294条条目。源层已接入生产构建，但全中文、全触发与同步验收尚未完成；1080p原地90秒仅确认开场，不能代表后续关卡。详细流程见docs/SUBTITLE_COVERAGE.md。

### 教程翻译批次（2026-10-03）

Tes_01～Tes_80已全部有中文草稿；本轮追加67条，原49条保持。基础译文116条，启用社区来源时361条中128条已有译文、233条待译。文本完成不等于实机验收：本轮未启动游戏，由用户在1080p检查完整教程及分支。测试方法和80键清单见[TUTORIAL_QA.md](docs/TUTORIAL_QA.md)。本地差分预览包包含标准库安装器，安装/核验/回滚已验证；未发布公共Release。

### 全文首轮文本批次（2026-10-04）

新增874条草稿，原128条生产译文保留。源文身份与控制符已校验，原版/社区字幕并集仍为900键、325非空。构建扩展为6个经原版指纹验证的资源，字库随全部文本重建。开场分段已获维护者实机确认，其他章节、长句布局及剧情视频仍需专项QA。此阶段不是全游戏100%完成声明，见[批次报告](docs/FULL_TRANSLATION_BATCH.md)。

### 图片按钮汉化（2026-10-04）

维护者选择仅汉化四种按钮及配套纹理：载入、游玩、漫游、保存，共八张。挂毯、书页、纸张和品牌标志保持原样。构建已接入现有工具链，范围及回滚已静态验证；1080P游戏内按钮显示与操作尚待确认。详见[图片文字审计](docs/TEXTURE_TEXT_AUDIT.md)。

## 许可

自编工具 MIT，原创译文 CC BY-SA 4.0，字体/依赖各遵循自身许可；
游戏原文和资源不在上述授权范围。详见 [LICENSING.md](LICENSING.md)。

## 致谢

Legend Entertainment 的原作；GOG 发行版本；Unreal/Unreal Tournament 同时代的标准
localization / Font 机制为研究参考；Pillow 与 fontTools 提供字形处理。
当前无上游研究仓库；现有本地阶段研究的发现与失败记录没有改写成他人的贡献。
