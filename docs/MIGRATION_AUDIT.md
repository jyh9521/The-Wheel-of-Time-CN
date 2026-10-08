# 项目迁移与审计报告

> 历史开发与测试记录：下述测试数、待办、验收状态和产物名称对应记录时的构建，不代表正式版当前状态。v1.0 已完成完整通关测试且未发现补丁问题；正式文件为 `WoT-CN-v1.0.exe`。当前说明见 [项目主页](../README.md)、[安装说明](PORTABLE_INSTALLER.md)和[显示限制](KNOWN_ISSUES.md)。

日期：2026-10-03。仅迁移、审计、离线重建与独立副本安装/回滚；未启动游戏，未新增翻译。

## 来源与取舍

- 新正式源码目录：`C:\Users\noway\Downloads\The-Wheel-of-Time-CN`。入口规范和18份模板/占位文件先完整保存于本地 `build/migration/destination-before/`。AGENTS.md 与 LOCALIZATION_STANDARD.md 保持原文，不进入待提交源码集。
- 旧工作区：`C:\GOG Games\The Wheel of Time`，5126个文件已建立逐文件SHA-256、大小与修改时间基线；迁移不写入、不删除旧文件。
- 上一轮正式工程：`C:\Users\noway\Documents\GitHub\The-Wheel-of-Time-CN`，复用已提交的 `dee6e61b6df8d037dbb021cf6b3a0c9db4022a8b`，不是重新实现汉化。它是本项目先前版本，不是外部上游。该目录也保留不动。
- 新目录起初不是Git checkout，只有规范模板；该阶段没有初始化/替换Git历史、commit或push。后续同步应保留上述现有历史，避免将迁移重新伪装成从零开发。

## 从游戏目录复制/整理的文件

|旧路径（相对游戏目录）|新源码路径|处理|
|---|---|---|
|`docs/phase1/REPORT_zh-CN.md`|`docs/research/game-root/phase1/REPORT_zh-CN.md`|verbatim historical report; old absolute links intentionally historical|
|`docs/phase2/REPORT_zh-CN.md`|`docs/research/game-root/phase2/REPORT_zh-CN.md`|verbatim historical report; old absolute links intentionally historical|
|`docs/phase3/PRE_RUNTIME_REPORT.md`|`docs/research/game-root/phase3/PRE_RUNTIME_REPORT.md`|verbatim historical report; old absolute links intentionally historical|
|`docs/phase3/REPORT_zh-CN.md`|`docs/research/game-root/phase3/REPORT_zh-CN.md`|verbatim historical report; old absolute links intentionally historical|
|`docs/phase4/FONT_USAGE.md`|`docs/research/game-root/phase4/FONT_USAGE.md`|verbatim historical report; old absolute links intentionally historical|
|`docs/phase4/REPORT_zh-CN.md`|`docs/research/game-root/phase4/REPORT_zh-CN.md`|verbatim historical report; old absolute links intentionally historical|
|`docs/phase5/REPORT_zh-CN.md`|`docs/research/game-root/phase5/REPORT_zh-CN.md`|verbatim historical report; old absolute links intentionally historical|
|`work/phase5/test_translations.json`|`locales/zh-CN/research/phase5-strings.json`|preserve 7 translations/IDs/tokens; replace English sources with SHA-256 and length; not part of active build|
|`docs/phase1/original_manifest.json`|`docs/research/game-root/original-manifest.json`|copy historical filename/size/SHA metadata; not a claim of current configuration equality|

7份阶段研究Markdown保留原始措辞、旧绝对链接和当时的测试结论。尤其历史320×240/12px和277/277原版一致记录只是当时事实，不作为当前QA要求或当前配置一致声明。原Manifest只是文件名/大小/散列元数据，不含游戏内容。

## 已有正式工程复用

共52个此前Git管理的工程文件复制进新目录（排除已有两份许可文件）；包括build.py、install.py、requirements、CI、profiles、src/patch、文本导出/回填、字体/封包/校验工具、42项原有测试、19条现有草稿/术语/配置与QA研究。详细逐文件清单与来源SHA见 [migration-manifest.json](migration-manifest.json)。

docs/file-formats.md、pitfalls.md、known-issues.md合并为要求的 FILE_FORMATS.md、PITFALLS.md、KNOWN_ISSUES.md；活跃工程文档链接同步，避免Windows大小写不敏感时形成两个真相。新目录原许可文件保留，许可边界按项目实际资料整理。新增迁移审计工具与4项合成测试，技术层没有语言硬编码。

## 留在旧目录的内容与原因

|类别|文件数|处理与原因|
|---|---:|---|
|original-game-backup|277|原版277文件备份：原位保留；新构建不依赖它。|
|original-game-or-distribution|273|原版程序、资源、GOG安装/卸载文件：只读输入，不提交。|
|generated-evidence|336|截图、字库PNG、字形manifest、运行日志/检查报告：原位证据，不迁移生成物。|
|technical-research|7|研究Markdown：复制7份归档，原件不动。|
|runtime-generated|2|游戏运行日志：保留，不作为源码。|
|game-user-configuration|2|WoT.ini/User.ini：玩家设置，原位保留，不恢复历史配置。|
|temporary-cache|14|Python缓存等：保留不删除，不提交。|
|legacy-project-source|36|旧开发工具/补丁/配置准备/测试脚本：依赖脚本所在根目录、backup/phase1-original和work/phase*；原位保留。正式构建改用已有参数化框架。|
|generated-or-extracted-work|4163|工作副本、生成ZIP/资源、完整英文导出/反编译脚本等：保留旧目录，不提交。|
|legacy-project-source-snapshot|10|旧脚本pre-fix/阶段快照：保存失败路线和修复历史，不加入生产导入路径。|
|research-translation-or-qa-data|6|阶段翻译表及密集QA字集：原表原位保留；phase5的7条译文另存研究格式，旧Help测试变体不会覆盖当前正式19条草稿。|

类别是按路径/类型判定的审计分组，不声称work内所有文件均为原创，也不声称原安装现有玩家配置与出厂完全相同。完整5126条清单在本地 build/migration/old-before.json；旧脚本36份及工作快照10份的具体路径与散列已写入源码迁移manifest。

### 旧工具与正式工具对应

|旧工具|正式入口/替代|
|---|---|
|int_tool.py|tools/extract/int_files.py、tools/import/int_files.py及catalog模块|
|ue1_scan.py的包结构解析|tools/pack/ue1.py|
|font_builder_v3.py|tools/font/build_font.py + profiles中的字体配置|
|localization_build_v3.py|build.py、tools/build/pipeline.py|
|patch_manager_v3.py、ROLLBACK.sh|install.py apply/verify/restore；独立目标参数|
|subtitle_timing.py|通用回填器中的可配置preserve-source-length|
|runtime/inventory/phase探针|tools/validate/runtime.py，显式game/runtime/build/output参数|
|map_audit.py、mov_text_export.py、旧全局扫描|原位置保留；通过GAME目录定位；不是现有PoC构建依赖，MOV工具还绑定本机ffprobe，待独立参数化|

旧命令不从新目录复制后执行，因为父目录ROOT会错误地指向新源码树。需要复查旧流程时将GAME设为旧工作区，定位GAME/tools，阅读其参数与副作用；该阶段不调用旧准备/写入脚本。新的生产构建只通过 --game-dir 引用原资源，不引用旧生成物。

## 原版内容排除清单

System中的EXE/DLL/U、原版INT/INI；Maps的UNR/WOT；Textures的UTX；Sounds的UAX/音频；Music的UMX/音频；Movies的MOV；Help/GOG/EULA/卸载资源；backup完整游戏副本；work中的完整抽取源码/英文表/测试游戏副本都不进入源码集。输出差分和字体衍生数据留在被忽略build目录，公开分发另行许可审查。

## 可重建程度与验证

- 新目录独立构建：通过。19条草稿不变，162字/字体，6字体、8新贴图、8371其他export不变；只依赖新源码、指纹匹配的原版4资源、Python依赖和开发者自行提供的字体。
- 原版→安装→校验→回滚：在build/migration/rollback-test独立四资源副本执行，未安装到游戏根目录。
- 干净源码副本→构建：不复制旧build/work/backup，输出与当前生成的4资源和PATCH.json逐字节比较；结果记录于本地VERIFICATION.txt。
- 全目录迁移后审计：再次比较5126个文件的SHA-256/大小/mtime与基线，结果记录于VERIFICATION.txt。
- 原安装4个输入资源通过profile指纹；历史277文件manifest中WoT.ini/WoT.log可能因玩家配置/运行历史变化，不擅自恢复。

## 后续缺项

1. Git历史衔接已完成，基于原origin/main；迁移成果已普通推送为3df2156，此项完成。
2. 构建需要显式开发者自行提供覆盖字体；若要只用“干净仓库+原版游戏”（依赖安装后不再额外给字体），需选择可再分发字体、带许可引入并重新QA。现有Windows字体不打包。
3. 19条草稿审稿，正式Release字体/差分审计、玩家安装包与说明、存档/切图/战斗等验收。它们是发布缺项，不是当前PoC重建缺项。
4. 字幕817空项、完整对白恢复、MOV文字轨/外挂显示、动态布尔与其余UI仍待后续专项；该阶段不扩展翻译或修改游戏逻辑。
5. 推荐1080p；1366/1440为主动矩阵，4K作为已知问题，不再适配。

## 可复用命令

```powershell
$Game = "C:/GOG Games/The Wheel of Time"
$Font = "C:/Windows/Fonts/msyh.ttc" # 自行提供；不代表公开再分发许可
python -m pip install -r requirements.txt
python build.py test
python build.py --locale zh-CN --game-dir "$Game" --font "$Font"
python -m tools.validate.integration --game-dir "$Game" --build-dir build/zh-CN --out build/rollback-test
# 显式安装到指定副本；该次只测试独立fixture
python install.py apply --bundle build/zh-CN/PATCH.json --target "D:/Games/WoT-copy"
python install.py restore --bundle build/zh-CN/PATCH.json --target "D:/Games/WoT-copy"
```

详细入口、源文件及字体要求见 [BUILDING.md](../BUILDING.md)。

## 最终观察结果

- 合成测试：46/46通过；validate：19条、0未译、19待审稿（仅PoC表）。
- 干净源码集：73个文件，不含AGENTS/本地标准、旧生成物或原版资源；独立构建4个资源和PATCH.json字节一致。
- 旧工作区：5126/5126文件SHA-256、size和mtime不变；零写入、零删除。
- 独立安装/回滚与可执行ROLLBACK.sh：退出0；New Game → 新游戏 → New Game；修改构建保留。
- strict校验：预期退出1，19条draft未假装审稿。
- 全命令、输入、字面输出和退出状态保存在本地build/migration/VERIFICATION.txt。

迁移后后续Controls扩充见CONTROLS_POC.md；本报告19条/73文件等为迁移验收时的历史快照，不是后续汉化实时进度。
