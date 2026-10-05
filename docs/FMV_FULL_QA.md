# 剧情视频中文字幕与正式测试

## 当前范围

已在游戏内确认最小中文样本可以显示，并按这条原生 QuickTime 路径制作完整字幕。
17 个 MOV 中，14 个有剧情文本轨：共 769 个时间样本，其中 628 条非空对白、141 个空白间隔。
这 628 条都已写入中文初稿；Mission_04 三处角色名 Risline 统一为“里斯琳”，以 GLOSSARY.md 为准。
译文完成和受控绘制检查不等同于全流程剧情、英文配音同步及通关验收。

GtLogo、Logo 是品牌片头，保持原样。Mission_10 没有文本轨：画面抽样显示逃脱、传送石和白袍众场景；
仅对这段无文本来源的视频运行本机已缓存的语音检测，结果只有一条高无语音概率的“You”，
不足以认定是实际对白，没有据此编造字幕。后续完整观看已确认无对白，保持原片，无需字幕。

## 原文与译名

原片内置意大利语和西班牙语文本轨。ffprobe 虽报告 eng，实际内容不是英语；
没有把语言标签当英文原文。时间轴、空白间隔和条目 ID 沿用游戏原片，中文参考两种文本轨，
专名以根目录 GLOSSARY.md 为准，游戏原创内容在这个体系下翻译。
另外针对 Intro 后段、Mission_04 议事段和 Mission_05 墓穴指引抽取短英语音轨片段核对。
局部自动识别支持“毁灭男性导引者”和 Tracer → 追迹的含义，不代替整部英语逐句听校；原音频片段和识别输出仅留 build。

## 可重复构建

从干净仓库、原版游戏、字体及社区字幕源重建普通汉化资源，再一并导入新的完整游戏：

```powershell
python build.py --game-dir "GAME" --font "FONT.ttf" --subtitle-source "COMMUNITY/WoTsubtitles.int" --locale zh-CN --out build/formal-qa-resources
python -m tools.build.build_fmv build --game-dir "GAME" --runtime-dir "GAME" --resource-build build/formal-qa-resources --out build/formal-game --locale zh-CN
python -m tools.build.build_fmv verify --input build/formal-game --locale zh-CN
```

GAME 提供完整原版游戏和 MOV，resource-build 提供当前源码新构建的 20 个汉化资源，
安装器核对原/改哈希后同时导入菜单、字幕、字体、图片按钮和高级设置补漏。
不指定 resource-build 时也可把 runtime-dir 指向已有汉化副本；其 MOV 和 WinDrv.dll 仍须匹配原版指纹。
输出必须是新目录，工具物理复制六类资源，不启动游戏，不修改输入目录。
源码与配置无需旧研究目录、build/runtime 或预览 EXE：

- tools/pack/movie_text.py：文本表解析、批量 Unicode 重建和时间轴/媒体完整性检查。
- tools/build/build_fmv.py：17 片版本检查、字幕安装、完整副本校验与独立回滚。
- profiles/fmv-movies.json：大小、SHA、轨 ID、样本指纹、非空标记和时间，不含原片或原对白全文。
- locales/zh-CN/fmv/*.tsv：零起始样本 ID、制表符、中文译文；空白样本不填写。
- locales/zh-CN/fmv/config.json：字体名称、Mac 语言码、行宽和双行高度。

上述基础构建引用系统 QuickTime 和 SimHei。当前完整测试入口改用附带思源黑体子集的 `build/local-font-game/LAUNCH_GAME.ps1`，实际游戏内中文字幕显示已确认，不需要永久安装 SimHei；追加构建步骤与字体许可见 [本地字体验证](FMV_LOCAL_FONT.md)。此前 `build/formal-game` 保留，不覆盖旧副本。
新的语言复用工具，但须配置合适字体、语言码与行宽；等长 Pascal 字体名槽是当前实现限制。

## 验证与回滚

原版与回填后每条字幕的开始时间、持续时间相同；原始 mdat 整段保持字节一致，音频/视频不重编码。
Mission_05 的前后两种 text 描述都换用目标字体，stsc 在第 23 个 chunk 切换描述的结构保留。
全部 14 片原生 QuickTime 最长字幕抽帧打开成功，另用隔离的 76 字测试样本验证双行完整显示。
完整字幕批次的 187 项自动测试通过；译名与文档整理后 190 项自动测试通过；原版恢复副本的 14 个 MOV、WinDrv.dll、WoT.ini 与输入逐字节一致。

```powershell
python -m tools.build.build_fmv rollback --input build/formal-game --out build/formal-fmv-restored-files
```

回滚只输出另一份新文件副本，不撤销正在准备正式测试的汉化游戏，也不覆盖原游戏。
build/formal-game 的 MODIFIED_FILE.mov、DIFF_FILE.json、VERIFICATION.txt、ROLLBACK.sh 是事务证据；
真实游戏使用 Movies/ 下的同一回填内容。生成物全部留在 build，不进 Git。

## 正式游戏测试入口

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "FULL_REPO_PATH/build/local-font-game/LAUNCH_GAME.ps1"
```

这次是完整游戏入口，不是独立预览，也不是只有一句中文的旧 PoC。主菜单“重播开场”检查完整 Intro，
再从新游戏开始，检查各关卡前后视频。只测 1920×1080；音频仍选原英文轨。
旧测试存档未自动复制，新目录有独立 Save。空格暂停、Esc 跳过仍使用游戏原路径。

记录问题时写下视频/关卡、约第几秒、听到的英语和截图，重点检查漏句、时机、换行裁切、
暂停/跳过/重播、返回菜单或地图及存档读档。Mission_10 已确认无对白，无需额外补写字幕。
原游戏目录与 build/fmv-game-qa 的单句实验都保留，但正式测试改用此完整入口。
