# 长菜单、中文字幕实机验证及资源工具开发

## 结果（2026-10-02）
**中文菜单、长帮助说明、教学关卡字幕均已实际显示。发现的两类资源问题已修复并复测。**

|测试命令|资源/输入|画面结果|游戏及探针退出码|
|---|---|---|---|
|`python tools\phase3_probe.py BASELINE`|中文int+原字体，Esc→Enter|中文行缺失，ASCII END-123可见|0|
|`python tools\phase3_probe.py MODIFIED`|128字字体+中文int，Esc→Enter|新游戏、两行长帮助、END-123完整可见；英文菜单保留|0|
|`python tools\phase3_probe.py SUBTITLE`|原Tutorial、自然开场语音、无移动/控制台|Tes_01中文字幕两行显示，第32秒仍可见|0|
|`python tools\phase3_probe.py ROLLBACK`|原资源与配置，Esc→Enter|New Game和原英文帮助恢复|0|

原安装277/277文件哈希保持；EXE/DLL、地图、脚本字节码、声音和视频均保持不变。该阶段仅当前主机实测。

## 问题与修复
### 1. 大字体贴图导致崩溃
早期512×512单mip纹理触发：`D3D Driver: Encountered oversize texture without sufficient mipmaps`，进程退出1。
修复：只生成不超过256×256的字图，按Unicode页跨atlas分组；当前128个字形/字号生成4个Texture（14px一张、30px三张）。构建器显式拒绝更大单mip字图，并增加回归测试。没有修改渲染器或EXE。

### 2. 字幕触发测试选择
Tes_02在原地等待72秒期间未捕获，因此切换为自然开场必然出现在该次测试中的Tes_01。Tes_02恢复原值，仍只改一条字幕；没有改地图或触发事件。

### 3. 中文字幕过早消失
原代码按 `Max(MinMessageDuration, Len(LocalizedStr)*MessageDurationSecsPerChar)` 决定时长。中文译文90字符，比原英文350字符短；未处理时第4/8秒可见、第14秒已消失。
原Sound PCM采样数据1378182字节、单声道16bit/22050Hz、44100字节/秒，时长约31.251秒。
修复原型：可选 `--preserve-subtitle-length` 仅在字幕 `.int` 值外加双引号并在引号内追加260个ASCII空格，使Len保持350，可见译文仍90字符。实测第14/25/32秒仍显示，没有新增可见符号或丢失译文。该方法保留原字符计时，不是逐词/逐帧同步；CSV/JSON保留干净译文，构建时生成空格并在manifest记录。

## 当前修改字段与资源
- WoT.int `[menuSinglePlayer] MenuList[2]`：新游戏。
- WoT.int `[menuSinglePlayer] HelpMessage[1]`：进入“试炼”教学关卡，熟悉《时光之轮》的基本操作。中文长文本显示验证：移动、观察、跳跃与法器使用；请确认自动换行后文字完整，末尾标记 END-123 可见。
- WoTsubtitles.int `[DialogA] Tes_01`：伊莱娜，要加入白塔，你必须接受试炼。眼前这件特法器正是为此准备的。依次穿过它的每一道拱门，你将直面自己最深的恐惧。不要惊慌，留心听我的声音，我会引导你走下去。你的训练就从这里开始。
- WOT.u仅F_WOTReg14/F_WOTReg30两个原Font对象扩充字页，并追加4个P8 Texture；CPP仍256，原Page0逐字节保持。
- 8375个其他原导出记录及内容逐字节保持。Import、原名称、GUID保持；表指针/数量和generation计数按新增资源更新，纹理lazy-array绝对终点已验证。
- 中文文本为UTF16LE BOM。长帮助含QA内容，人物译名/术语为测试译文，不是全文翻译稿。

|原文件|修改副本|方法|可逆|
|---|---|---|---|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WOT.u|C:\GOG Games\The Wheel of Time\work\phase3\modified\System\WOT.u|Font字页+小型P8 atlas追加|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoT.int|C:\GOG Games\The Wheel of Time\work\phase3\modified\System\WoT.int|2条键值，精确回写|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoTsubtitles.int|C:\GOG Games\The Wheel of Time\work\phase3\modified\System\WoTsubtitles.int|1条译文+可选时长保留|是|

原WOT.u SHA256：`8e670c5b58110a31367029a9801ad38c89a587aa82d1786dec4451815b7746fb`。
修改SHA256：`695f713fc3c9e3fbb0d1c69e1759affe52db940062ad577c8ea94a8784a55fd3`。

## 实机截图
![长菜单](C:\GOG Games\The Wheel of Time\docs\phase3\MODIFIED.png)
![字幕第32秒](C:\GOG Games\The Wheel of Time\docs\phase3\SUBTITLE_032.png)

## 新增/完善工具
|工具绝对路径|功能|
|---|---|
|C:\GOG Games\The Wheel of Time\tools\font_builder.py|实际字集→BMP字页/小atlas；同页多字保留、缺字检查、原ASCII保留、版本指纹与资源结构校验|
|C:\GOG Games\The Wheel of Time\tools\subtitle_timing.py|可选源文长度保留；可见译文/追加空格/有效长度记录|
|C:\GOG Games\The Wheel of Time\tools\localization_build.py|CSV/JSON→占位符/原文校验→UTF16 int→字形→ZIP及资源manifest|
|C:\GOG Games\The Wheel of Time\tools\patch_manager.py|工作副本的安装、SHA256验证、原资源备份、恢复；拒绝未知文件与不匹配目标|
|C:\GOG Games\The Wheel of Time\tools\test_phase3.py|13项自动测试，包含大贴图回归与安装/恢复错误路径|

安装工具在另一独立fixture中apply→verify→restore均成功；3资源恢复字节一致。ROLLBACK.sh亦在独立副本恢复5个资源/配置文件，cmp通过。

## 交付
- 中文菜单启动：`C:\GOG Games\The Wheel of Time\work\phase3\Launch_MenuTest.cmd`；字幕启动：`C:\GOG Games\The Wheel of Time\work\phase3\Launch_SubtitleTest.cmd`。
- 测试ZIP：`C:\GOG Games\The Wheel of Time\work\phase3\build\ChineseDisplayTest.zip`，只含3个System资源及patch_manifest.json。
- 修改文件：`C:\GOG Games\The Wheel of Time\work\phase3\modified\System\WOT.u`。
- Font差异：`C:\GOG Games\The Wheel of Time\docs\phase3\FONT_DIFF.json`；字幕时长差异：`C:\GOG Games\The Wheel of Time\docs\phase3\TIMING_DIFF.json`。
- 验证：`C:\GOG Games\The Wheel of Time\docs\phase3\VERIFICATION.txt`；回滚：`C:\GOG Games\The Wheel of Time\work\phase3\ROLLBACK.sh`。
- CSV/JSON：`C:\GOG Games\The Wheel of Time\work\phase3\test_translations.csv` / `C:\GOG Games\The Wheel of Time\work\phase3\test_translations.json`。

从 `C:\GOG Games\The Wheel of Time` 可复现：
```powershell
python tools\localization_build.py --table work\phase3\test_translations.csv --out work\phase3\build --preserve-subtitle-length
python tools\test_phase3.py
```

## 后续技术工作
当前继续保留小规模路线，不开始全文翻译。还需处理30px字体某Unicode页超过64字的容量问题、SizeX<512会替换的_S字体、其余HUD/斜体字体、更多字幕的时序与连续覆盖。当前构建器会对单页容量溢出报错，不静默丢字；本包128字不代表全汉字覆盖。当前两行换行可用，但未验证所有中文行首/行尾标点禁则。

可复用后续任务：
```text
沿用当前已验证小atlas与UTF16 int链路，在隔离副本中完善高密度字页方案和_S字体，保持全部原英文映射及非Font资源。先做单页超过64字的固定测试，再实机确认菜单/字幕与回滚；继续使用现有CSV/JSON、时长保留选项和安装校验工具，不开始全文翻译或修改EXE/DLL。
```
