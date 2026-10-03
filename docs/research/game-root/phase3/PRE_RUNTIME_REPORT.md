# 按字集构建字体与长文本/字幕测试包

## 当前结果
- **开发完成，实机显示待确认。** 三字菜单成功结论保留；本轮81字并未取得成功游戏截图。
- CSV/JSON → 占位符/源文校验 → UTF-16LE BOM `.int` → 字集提取 → 多页 Font/Texture → 校验 → ZIP 测试包链路已执行。
- 两个字号各81个非ASCII字形，包含中文标点；原ASCII页不变，8375个其他原导出条目及其字节内容不变，无字节码/EXE/DLL/地图修改。
- 8项自动测试通过；独立副本回滚后5文件与备份字节相同；原安装277/277原文件SHA256不变。

## 本轮文本
|文件/节/键|测试文本|
|---|---|
|WoT.int / menuSinglePlayer / MenuList[2]|新游戏|
|WoT.int / menuSinglePlayer / HelpMessage[1]|进入“试炼”教学关卡，熟悉《时光之轮》的基本操作。中文长文本显示验证：移动、观察、跳跃与法器使用；请确认自动换行后文字完整，末尾标记 END-123 可见。|
|WoTsubtitles.int / DialogA / Tes_02|别让恐惧支配你，伊莱娜。穿过那道拱门。|

长帮助说明包含QA文字及末尾END-123标记，不是最终译文。其余原键值全部保留。

## 字体实现与修正
- 从译文提取去重字集，不先导入整套GB2312。
- TrueType cmap与非空栅格检查；缺字、非BMP字符和未知WOT.u版本指纹会报错。
- 多个字落在同一Unicode页时累积写入同一字符表，避免早期三字原型直接推广后互相覆盖。
- 按Unicode页组织字形、跨atlas分组，单页字符不跨Texture；atlas不足时追加多张纹理。已测试256×256强制分包。
- 本包F_WOTReg14使用256×256，F_WOTReg30使用512×512；各追加一张P8遮罩Texture，复用原Palette。
- 字符页数由最大Unicode页决定；本包全角标点位于第255页，因此共256页，CharactersPerPage仍256。只为实际使用页分配字符表，空页不分配纹理。
- 保持原名称、Import表与GUID；追加资源数据及新名称/导出表并更新指针、计数、generation；修正绝对lazy-array终点与纹理尺寸/位数。

## 显示路径的文件证据
- 菜单帮助：menuWOT.DrawHelpPanel → F_WOTReg14；ClipX为屏幕宽度80%，StrLen计算高度，DrawText排版。
- 字幕：WOTPlayer.ClientHearSound → Localize(S.Outer.Name,S.Name,WoTsubtitles) → SubtitleMessage → BaseHUD.DrawMessages → F_WOTReg14，宽度80%。中文字符串长度还影响显示时间。
- Tutorial.wot原SoundDispatcher16的事件go_on_coward引用DialogA.Tes_02，第一项延迟50秒；事件自然触发与当前测试字幕显示尚未实机确认。
- LegendCanvas在SizeX<512时可能换用_S字体；本构建器当前只支持已确认的F_WOTReg14/F_WOTReg30，低分辨率_S和其他字体尚待扩展。

## 实机测试状态
原字体BASELINE启动就遇到原版DirectDraw TestCooperativeLevel错误，后续进入Recovery Mode；截图出现OSError screen grab failed。成功启动画面尚未取得，因此未把故障归因于中文字体，也未为绕过它改渲染器。
当前有独立失败attempt日志和JSON。MODIFIED/SUBTITLE/ROLLBACK本轮实机测试未执行。此前phase2成功截图只能证明三字菜单，不能代替本轮长帮助和字幕验证。

## 文件修改记录
|原文件|修改文件|原因/方法|可逆|
|---|---|---|---|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WOT.u|C:\GOG Games\The Wheel of Time\work\phase3\modified\System\WOT.u|两Font追加81字，多页映射与两个P8纹理；其他导出内容保持|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoT.int|C:\GOG Games\The Wheel of Time\work\phase3\modified\System\WoT.int|2个测试字符串，CSV/JSON精确定位回写，UTF16LE BOM|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoTsubtitles.int|C:\GOG Games\The Wheel of Time\work\phase3\modified\System\WoTsubtitles.int|仅DialogA.Tes_02，原英文已有来源；UTF16LE BOM|是|

原包SHA256：`8e670c5b58110a31367029a9801ad38c89a587aa82d1786dec4451815b7746fb`。
修改包SHA256：`ed66617e5795ab65df7a6f060ed2ad61f4f94f390d3d2a6bc2c80647014fb8ca`。

## 使用与开发入口
- 菜单隔离启动：`C:\GOG Games\The Wheel of Time\work\phase3\Launch_MenuTest.cmd`；Esc→Enter，选中Tutorial看底部长帮助，确认END-123及换行。
- 字幕隔离启动：`C:\GOG Games\The Wheel of Time\work\phase3\Launch_SubtitleTest.cmd`；加载原Tutorial，触发相应对白后检查字幕；bSubtitles=True已保留。
- 测试ZIP：`C:\GOG Games\The Wheel of Time\work\phase3\build\ChineseDisplayTest.zip`；只含3个System资源和patch_manifest.json，未安装到原游戏。
- 回滚：`C:\GOG Games\The Wheel of Time\work\phase3\ROLLBACK.sh`；仅phase3 work内目标，恢复3资源+2配置。已经另一副本执行验证。
- CSV：`C:\GOG Games\The Wheel of Time\work\phase3\test_translations.csv`；JSON：`C:\GOG Games\The Wheel of Time\work\phase3\test_translations.json`。
- 差异：`C:\GOG Games\The Wheel of Time\docs\phase3\FONT_DIFF.json`；完整记录：`C:\GOG Games\The Wheel of Time\docs\phase3\VERIFICATION.txt`。

从游戏根目录可复现：
```powershell
python tools\localization_build.py --table work\phase3\test_translations.csv --out work\phase3\build
python tools\test_phase3.py
```
构建器：`C:\GOG Games\The Wheel of Time\tools\localization_build.py`；字体工具：`C:\GOG Games\The Wheel of Time\tools\font_builder.py`。

## 自动测试
8项覆盖CSV/JSON逐字节一致、恰好3项值变化、BMP限制、字体源缺字拒绝、同页多字不覆盖、多atlas分包、未知版本拒绝、原ASCII和所有非Font原导出内容保持。ZIP通过CRC及资源SHA256验证。

## 下一步执行提示
```text
先确认桌面和原版DirectDraw启动正常，再仅在phase3隔离副本运行BASELINE/MODIFIED/SUBTITLE/ROLLBACK。核查長帮助末尾END-123、14px中文字号、标点换行、Tes_02事件字幕与英文保留。没有实机截图时保持待确认状态，不把上一轮三字成功外推为全文成功。不要改EXE/DLL、地图或开始全文翻译。
```
