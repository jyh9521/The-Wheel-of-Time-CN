# 《时光之轮》本地化工程 / The Wheel of Time Localization


## 项目简介

**The Wheel of Time（1999，Legend Entertainment）GOG 版**的汉化补丁与可重建本地化工具链。当前目标为简体中文 `zh-CN`；技术层尽量保持语言无关，以便后续扩展其他语言。

## 支持版本与当前状态

支持项目已记录指纹的 GOG 英文资源，目标平台为 Windows 10/11。首轮普通文本、教程及带文本轨 FMV 已完成中文草稿，并导入完整测试副本；本轮审计仍发现硬编码标签和窗口回退文案待补齐，尚未确认100%覆盖；测试与补漏继续进行，尚未发布正式 Release。推荐 1920×1080，后续开发 QA 仅检查 1080p；4K 不作专项适配。

详细进展见 [STATUS.md](docs/STATUS.md)。

## 下载

源码：本仓库。玩家成品将放在 [GitHub Releases](https://github.com/jyh9521/The-Wheel-of-Time-CN/releases)。
**目前没有完整汉化正式 Release**，不要把开发构建误认为成品。
仓库不提供游戏本体、原程序、整包资源或 Windows 字体。

## 安装 / 使用

本地通关测试提供小体积绿色 EXE：选择 GOG 游戏目录 → 校验文件 → 安装补丁；完成后沿用原游戏快捷方式或 System/WoT.exe。不写注册表，不创建系统卸载项，无需手动运行 CMD。使用与恢复方法见[绿色安装包](docs/PORTABLE_INSTALLER.md)。此前[直接覆盖包](docs/OVERLAY_TEST_PACKAGE.md)保留为测试方案记录。当前尚非公开 Release。

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
安装器不修改 EXE、启动器、地图、玩法或配置文件；当前高级选项显示适配包含经原版指纹校验的 Window.dll 差分，可回滚。

包含全部 FMV 的完整测试副本及核验、回滚方式见 [FMV 正式测试](docs/FMV_FULL_QA.md)。当前完整测试入口附带思源黑体子集，游戏内字幕显示已确认；字体构建与私有加载说明见 [本地字体验证](docs/FMV_LOCAL_FONT.md)。

## 技术摘要

本版本支持 UTF-16 LE BOM `.int`；中文字形通过可重复生成的 Unreal 位图字体资源提供。文本提取、校验、字体生成、封包重建与安装差分分层实现，并以原版 SHA-256 指纹限制修改范围。

FMV 使用原生 QuickTime 文本轨及可回滚的播放器轨道选择适配，保留时间轴，音视频不重编码。游戏专用限制与逆向依据见 [TECHNICAL.md](TECHNICAL.md)，完整 FMV 构建见 [正式测试说明](docs/FMV_FULL_QA.md)。

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

译文仍为初稿，全流程剧情同步、长文本布局与通关稳定性待正式测试。字体沿用原版固定像素尺寸，4K 界面偏小；推荐 1080p。FMV 依赖系统 QuickTime 与配置字体，其他语言尚未完成实机验收。详见 [已知问题](docs/KNOWN_ISSUES.md)。

## 更多开发与测试进展

更详细的开发日志、测试结论、字幕覆盖进展、教程翻译进展、迁移审计与专项 QA，请见：

- [开发与测试进展](docs/STATUS.md)
- [QA 记录](docs/qa.md)
- [字幕覆盖报告](docs/SUBTITLE_COVERAGE.md)
- [教程 QA](docs/TUTORIAL_QA.md)
- [迁移审计](docs/MIGRATION_AUDIT.md)

## 许可

自编工具 MIT，原创译文 CC BY-SA 4.0，字体/依赖各遵循自身许可；
游戏原文和资源不在上述授权范围。详见 [LICENSING.md](LICENSING.md)。

## 致谢

Legend Entertainment 的原作；GOG 发行版本；Unreal/Unreal Tournament 同时代的标准
localization / Font 机制为研究参考；Pillow 与 fontTools 提供字形处理。
当前无上游研究仓库；现有本地阶段研究的发现与失败记录保留原有归属。
