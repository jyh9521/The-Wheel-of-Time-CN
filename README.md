# 《时光之轮》本地化工程 / The Wheel of Time Localization


## 项目简介

**The Wheel of Time（1999，Legend Entertainment）GOG 版**的汉化补丁与可重建本地化工具链。当前目标为简体中文 `zh-CN`；技术层尽量保持语言无关，以便后续扩展其他语言。

## 支持版本与当前状态

支持项目已记录指纹的 GOG 英文资源，目标平台为 Windows 10/11。简体中文补丁 v1.0 已正式发布，完整通关测试已完成。推荐 1024×768 分辨率，最高不建议超过 1920×1080；4K 不作专项适配。

详细进展见 [STATUS.md](docs/STATUS.md)。

## 下载

正式版：[v1.0 发布页](https://github.com/jyh9521/The-Wheel-of-Time-CN/releases/tag/v1.0)，提供 `WoT-CN-v1.0.exe` 与 `Manual.pdf`。
源码：本仓库。仓库不提供游戏本体、原程序、整包资源或 Windows 字体。

## 安装 / 使用

打开绿色安装器 → 选择 GOG 游戏根目录 → 验证文件 → 安装补丁。安装完成后使用原游戏快捷方式启动游戏。不写注册表，不创建系统卸载项，无需手动运行 CMD。

安装和恢复前自动保存当前设置与存档快照；原始资源与进度快照保存在游戏根目录 `backup`。恢复原版仅还原补丁资源，保留当前设置与存档。备份目录应保留。

推荐 1024×768，最高不建议超过 1920×1080。详细操作、旧版备份迁移和恢复说明见[绿色安装包](docs/PORTABLE_INSTALLER.md)。原版游戏 FMV 播放仍依赖可用的 QuickTime 运行时；补丁写入字幕与实际播放是不同环节。

源码构建与差分工具操作见 [BUILDING.md](BUILDING.md)，历史测试记录见 [FMV 正式测试](docs/FMV_FULL_QA.md)。

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

完整通关测试已完成，未发现补丁相关问题。高分辨率下界面文字偏小是原版固定像素字体的显示特性，并非补丁引入；推荐 1024×768，最高不建议超过 1920×1080。详见 [显示限制](docs/KNOWN_ISSUES.md)。

## 更多开发与测试进展

更详细的开发日志、测试结论、字幕覆盖进展、教程翻译进展、迁移审计与专项 QA，请见：

- [文档索引](docs/README.md)
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
