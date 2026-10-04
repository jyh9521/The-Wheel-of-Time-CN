# 第四阶段：字库容量扩展与离线开发

## 当前结果
改为离线开发后，所有操作仅涉及工作副本、自动测试和安装恢复 fixture，没有再启动游戏。

- 同一个旧 Unicode 页内 U+4E00～U+4EFF 的连续 **256 个汉字**，在六种字体中全部通过资源映射检查。
- 该阶段总字集 **372 个字形/字体**、6 个字体、15 张不超过256×256的P8单mip字图。
- 自动检查2232个新增字形映射、1536个原字符映射；**8371个其他原导出记录及其内容保持不变**。
- 新测试10项、上一阶段回归13项全部通过。
- 独立安装 fixture 的apply→verify→restore完成；另一独立副本通过可执行ROLLBACK.sh恢复5文件。
- 原安装277/277文件哈希保持；EXE/DLL、地图、声音、视频、脚本字节码均未修改。

这些结果证明离线构建、资源结构及可逆性，不代表每个字形/界面均已实机验收。

## 关键修复：CharactersPerPage
旧构建器以256为字页大小；30px字号的256×256图最多容纳64个32×32格子，因此同一页内请求超过64个字会报`Atlas too small for one Unicode page`。

新构建器把六个Font对象的 `CharactersPerPage` 改为 **64**。引擎原有Font路径按 `page=codepoint//CPP`、`slot=codepoint%CPP` 取字；该阶段只调整资源属性和字页，没有修改该引擎代码。

- 原Page0的纹理引用、256个矩形记录逐字节保留。
- 追加三个旧字符页，各引用同一张原纹理，分别使用原64～127、128～191、192～255矩形。
- 原0～255字符经过新页算法仍得到完全相同的纹理与矩形。
- 每个新汉字页至多64字，30px字体单页总能容纳在256×256图内；空页保持空对象引用。
- 使用实际所需字集按需生成，未预先加入整个GBK/Unicode库；只支持BMP字符，缺字/代理项/非BMP会在构建前检查。

## 六种字体
|资源|测试中文字形高度|原用途/证据|
|---|---:|---|
|F_WOTReg30|30|菜单、Inventory标题|
|F_WOTReg14|14|菜单帮助、Inventory正文、HUD字幕/提示|
|F_WOTReg30_S|15|SizeX<512时的菜单字号替换|
|F_WOTReg14_S|7|SizeX<512时的正文/斜体回退|
|F_WOTReg08|8|计分板、小号回退|
|F_WOTIta14|14|Inventory说明中的斜体Font对象|

高度来自原字体大写字符矩形，不是按文件名猜测。原英文斜体矩形保持；**F_WOTIta14新增中文目前使用微软雅黑正体字形，真正的中文倾斜与截切处理留待后续**。F_Key、F_Charge、F_Element等图标字体保持原样。

完整原脚本路径、行号与调用见 [C:\GOG Games\The Wheel of Time\docs\phase4\FONT_USAGE.md](C:\GOG Games\The Wheel of Time\docs\phase4\FONT_USAGE.md)。

## 测试文本与保留范围
四条MenuList各含18个连续码位QA字形，共72字，用于跨64页边界观察；它们不是正式菜单译文。另保留上一阶段长中文帮助和一条Tes_01测试字幕，合计6个int值变化。

`.int` 使用UTF16LE BOM，字幕保留上一阶段可选的引号内尾随空格计时原型；CSV/JSON源译文不含填充。当前测试ZIP只包含三份资源和manifest，不包含启动脚本，也不会自动运行游戏。

## 实机证据与待验项
在改为离线开发之前，该阶段留有BASELINE、MODIFIED、LOWRES三个历史探针记录，进程正常退出0；密集菜单72字和长帮助曾被捕获。LOWRES日志为320×240，小号长帮助的清晰度仍有局限。

改为离线开发后没有再做字幕、新斜体Inventory界面、Reg08界面或游戏回滚启动测试。

待之后手动验收：
1. 7px小字号复杂汉字的可读性及适合的短帮助译文。
2. Inventory正体/斜体、Reg08计分板、原英文界面导航。
3. CPP64下的长字幕与持续时间回归。
4. 256个密集QA字形逐段屏显；Windows10及其他系统语言。

## 工具与复用命令（仅离线）
- C:\GOG Games\The Wheel of Time\tools\font_builder_v2.py：CPP64、六字体、指纹/缺字/字页/原字符检查。
- C:\GOG Games\The Wheel of Time\tools\localization_build_v2.py：CSV/JSON→精确int回写→字库→ZIP/manifest；可追加独立QA字集。
- C:\GOG Games\The Wheel of Time\tools\test_phase4.py：10项资源检查；不会启动WoT.exe。
- C:\GOG Games\The Wheel of Time\tools\verify_phase4.py：基线、新旧回归、独立恢复、277原文件检查及证据落盘；不会启动WoT.exe。

```powershell
Set-Location 'C:\GOG Games\The Wheel of Time'
python tools\localization_build_v2.py --table work\phase4\test_translations.json --glyph-table work\phase4\glyph_table.json --out work\phase4\build --preserve-subtitle-length
python tools\verify_phase4.py
```

原有phase3构建器、字体成果与报告保留，不改变其CPP256结论。测试包：C:\GOG Games\The Wheel of Time\work\phase4\build\ChineseFontCapacityTest.zip。

## 修改与恢复记录
|原文件|修改副本|原因/方法|可逆|
|---|---|---|---|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WOT.u|C:\GOG Games\The Wheel of Time\work\phase4\modified\System\WOT.u|六Font.Pages与CPP64；追加15个小atlas|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoT.int|C:\GOG Games\The Wheel of Time\work\phase4\modified\System\WoT.int|5条QA菜单/帮助；UTF16LE|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoTsubtitles.int|C:\GOG Games\The Wheel of Time\work\phase4\modified\System\WoTsubtitles.int|1条字幕测试；源长度保留|是|

原WOT.u SHA256：`8e670c5b58110a31367029a9801ad38c89a587aa82d1786dec4451815b7746fb`。
修改SHA256：`bac54ab1376c33dc3744f06e2ef55b3f08b7fa3a2c2cda5553736b96e07ac42c`。

交付四文件：
- MODIFIED_FILE：C:\GOG Games\The Wheel of Time\work\phase4\modified\System\WOT.u
- DIFF_FILE：C:\GOG Games\The Wheel of Time\docs\phase4\FONT_DIFF.json
- VERIFICATION.txt：C:\GOG Games\The Wheel of Time\docs\phase4\VERIFICATION.txt
- ROLLBACK.sh：C:\GOG Games\The Wheel of Time\work\phase4\ROLLBACK.sh

BASELINE命令 `python tools\baseline_dense_phase4.py`，输入原WOT.u与密集QA字集，输出`BASELINE PASS: old builder rejects dense page: Atlas too small for one Unicode page`，退出0（断言预期错误）。

MODIFIED命令 `python tools\test_phase4.py`，输入新资源与ZIP，输出`Ran 10 tests`、`OK`，退出0；每次运行的原始完整输出在VERIFICATION.txt及MODIFIED_OFFLINE.txt。

ROLLBACK命令 `& "C:\Program Files\Git\bin\bash.exe" -lc 'test -x work/phase4/ROLLBACK.sh && work/phase4/ROLLBACK.sh work/phase4/rollback-test/System'`，输入独立副本3份修改资源及2份原配置，输出`ROLLBACK PASS: 5 resource/config files byte-identical to backup; exit 0`，退出0。

恢复状态：5文件与原备份字节一致；没有以启动游戏作为该阶段恢复行为验证。modified/System和runtime/System保留修改资源，runtime配置恢复原值。
