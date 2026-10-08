# 文档索引

## 正式版入口

- [项目主页](../README.md)：支持版本、下载、安装与显示限制。
- [安装与恢复](PORTABLE_INSTALLER.md)：`WoT-CN-v1.0.exe` 的使用、根目录 `backup` 和存档保留机制。
- [已知问题与显示限制](KNOWN_ISSUES.md)：仅保留原版高分辨率下文字偏小的显示特性。
- [构建与复现](../BUILDING.md)、[参与翻译](../TRANSLATING.md)、[唯一术语表](../GLOSSARY.md)。
- [许可边界](../LICENSING.md)、[开发与测试进展](STATUS.md)。

正式版 v1.0 已完成完整通关测试，未发现补丁相关问题。当前发布文件名为 `WoT-CN-v1.0.exe`；发布页另提供 `Manual.pdf`。历史 ZIP、CMD、探针和阶段性 EXE 名称只用于复现当时流程，不作为当前下载安装入口。

## 历史记录与技术资料

历史记录保留测试数、失败方案与当时未完成项，不代表正式版状态。当前状态以项目主页、安装说明和显示限制为准。

- [高级设置范围审计](ADVANCED_SETTINGS_RANGES.md)
- [波莱恩与凯琳：角色与语音关联审计](CHARACTER_VOICE_ASSOCIATIONS.md)
- [社区优先字幕合并](COMMUNITY_SOURCE_POLICY.md)
- [Controls 标签与帮助：离线扩充](CONTROLS_POC.md)
- [Controls 全部行显示验收](CONTROLS_QA.md)
- [制作人员页术语确认记录](CREDITS_PENDING_TERMS.md)
- [文件格式笔记（当前 GOG / WOT.u v68）](FILE_FORMATS.md)
- [Mission_04 动画卡住调查（2026-10-07）](FMV_FREEZE_TRIAGE.md)
- [剧情视频中文字幕与正式测试](FMV_FULL_QA.md)
- [游戏内 FMV 字幕最小验证（2026-10-05）](FMV_GAME_QA.md)
- [FMV 本地字体子集验证（2026-10-05）](FMV_LOCAL_FONT.md)
- [FMV字幕调查（2026-10-04）](FMV_SUBTITLES.md)
- [全文件文本覆盖审计](FULL_TEXT_AUDIT.md)
- [全文首轮文本批次（2026-10-04）](FULL_TRANSLATION_BATCH.md)
- [Git 历史衔接（2026-10-03）](GIT_HISTORY_LINK.md)
- [字形顶部与教程字幕位置修复](GLYPH_LAYOUT_FIX.md)
- [历史问题与阶段性验收记录](HISTORICAL_ISSUES.md)
- [地图提示与文本覆盖](MAP_TEXT_COVERAGE.md)
- [主菜单与 Controls：第二批小范围 PoC](menu-poc.md)
- [项目迁移与审计报告](MIGRATION_AUDIT.md)
- [原生高级选项窗口汉化（2026-10-04）](NATIVE_ADVANCED_OPTIONS.md)
- [直接覆盖版通关测试包](OVERLAY_TEST_PACKAGE.md)
- [重复踩坑 / 必须保持的约束](PITFALLS.md)
- [单人通关测试包](PLAYER_TEST_PACKAGE.md)
- [工程迁移与高分辨率 QA（2026-10-03）](qa.md)
- [> 历史审计快照：下文保留批准前证据与建议。当前处理结果见文末，唯一有效术语以GLOSSARY.md为准。](REMAINING_TERMS_AUDIT.md)
- [逆向研究索引](reverse-engineering.md)
- [设置动态值补漏（2026-10-04）](SETTINGS_VALUES_FIX.md)
- [全字幕覆盖工程（2026-10-03）](SUBTITLE_COVERAGE.md)
- [字幕专用显示层](SUBTITLE_DISPLAY.md)
- [字幕可读性与字号专项](SUBTITLE_READABILITY.md)
- [教程开场字幕分段（实验性资源模块）](SUBTITLE_SEGMENTS.md)
- [GLOSSARY唯一术语基准与既有译文审校（2026-10-03）](TERMINOLOGY_AUDIT.md)
- [图片文字只读审计（2026-10-04）](TEXTURE_TEXT_AUDIT.md)
- [开场遗漏段落：Tes_01来源修正](TUTORIAL_INTRO_FIX.md)
- [教程字幕测试批次：80/80译文（2026-10-03）](TUTORIAL_QA.md)
- [动态界面文本补漏（2026-10-04）](UI_TEXT_FOLLOWUP.md)

## 早期逆向研究

- [phase1 / REPORT_zh-CN](research/game-root/phase1/REPORT_zh-CN.md)
- [phase2 / REPORT_zh-CN](research/game-root/phase2/REPORT_zh-CN.md)
- [phase3 / PRE_RUNTIME_REPORT](research/game-root/phase3/PRE_RUNTIME_REPORT.md)
- [phase3 / REPORT_zh-CN](research/game-root/phase3/REPORT_zh-CN.md)
- [phase4 / FONT_USAGE](research/game-root/phase4/FONT_USAGE.md)
- [phase4 / REPORT_zh-CN](research/game-root/phase4/REPORT_zh-CN.md)
- [phase5 / REPORT_zh-CN](research/game-root/phase5/REPORT_zh-CN.md)

## 链接维护

本地文件与标题锚点可通过以下命令重新检查：

```powershell
python -m tools.validate.documentation_links --report build/documentation-links.json
```

追加 `--external` 可检测外部网址。外站返回 HTTP 403 表示访问被拒绝，不等同于链接不存在，也不作为访问正常的证明；这类参考资料保留来源地址，不据此更换未经核实的来源。
