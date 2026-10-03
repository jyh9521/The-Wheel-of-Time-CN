# 第五阶段：实机验收、小字号与Inventory修复

日期：2026-10-03。用户明确允许启动独立游戏副本后执行。原安装277/277文件哈希保持，所有游戏进程已正常关闭。

## 结论
- **中文菜单、Inventory标题/正文/斜体引文、教学开场字幕已实机显示。**
- 小字号原7px中文字形在同文对照中偏糊；测试副本将F_WOTReg14_S新增中文字形提升至12px，同一320×240菜单说明明显更清晰。
- F_WOTReg08新增中文字形也以12px构建；其中文计分板尚未实测。
- F_WOTIta14新增中文由正体改为0.22剪切的倾斜字形，字形框扩至18×14以容纳偏移；真实Inventory中的引文已经显示。
- **320×240 Inventory最终复测通过**：早期立即切换F2时，修改版和原资源均捕获黑屏。按F3关闭初始任务目标窗口后曾捕获PRECACHING中间画面，再增加10秒等待后，原英文与最终中文字库均完整显示标题、说明、引文和提示。修复的是测试进入/等待流程，未修改渲染器或引擎。早期失败证据保留，不计为通过。
- 修正了中文字图的标点基线：此前逐字形按bbox顶端裁切，导致逗号/句号位置上浮；现在统一汉字基线并保留字形原bearing。句号低位对齐回归及最终Inventory/字幕画面均通过。

## 实际游戏测试
|命令|输入|画面结果|探针/游戏退出码|
|---|---|---|---|
|`python tools\phase5_probe.py BASELINE`|原WOT.u+中文测试int；Esc→Enter|中文缺失，英文菜单及END-123可见|0/0|
|`python tools\phase5_probe.py MODIFIED`|新字库+测试int；Esc→Enter|新游戏、中文说明及英文菜单可见|0/0|
|`python tools\phase5_probe.py SMALL_BEFORE`|旧7px构建器、相同字集/文本、320×240|笔画较糊；同文对照基线|0/0|
|`python tools\phase5_probe.py LOWRES`|新12px字形、相同文本、320×240|中文说明与END-123可辨，菜单未截断|0/0|
|`python tools\inventory_probe5.py INV_CHINESE`|Mission_01；1→F2；无移动/控制台|气流冲击、两行正文、斜体引文、按F2继续可见|0/0|
|`python tools\phase5_probe.py SUBTITLE`|原Tutorial自然开场；声音开启|Tes_01两行中文字幕；第8/14/25秒可见，第32秒已消失|0/0|
|`python tools\phase5_probe.py ROLLBACK`|原资源/配置；Esc→Enter|New Game和英文帮助恢复|0/0|
|`python tools\inventory_probe5.py INV_ROLLBACK`|原资源；Mission_01；1→F2|Air Pulse和原英文说明/斜体引文恢复|0/0|
|`python tools\inventory_probe5.py INV_LOWRES`|早期修改资源；立即切换F2|历史黑屏捕获，最终探针检测失败；未计通过|1/0|
|`python tools\inventory_probe5.py INV_LOWRES_ORIGINAL`|原资源；同320×240立即切换F2|历史黑屏捕获，未计通过|1/0|
|`python tools\inventory_probe5.py INV_LOWRES_SETTLED`|最终字库；320×240；F3→1→F2；额外等待10秒|完整中文标题、两行说明、引文及提示|0/0|
|`python tools\inventory_probe5.py INV_LOWRES_ORIGINAL_SETTLED`|原资源；同样步骤与等待|原英文标题、说明、引文及提示恢复|0/0|

所有游戏命令都在 `C:\GOG Games\The Wheel of Time\work\phase5\runtime\System` 执行。原渲染设备保持；低分辨率测试只在副本调整Viewport尺寸，结束后配置已恢复1024×768原值。

## 修改资源与字段
共7条QA译文，不是全文汉化或已定稿术语。

|原文件|修改副本|字段/方法|可逆|
|---|---|---|---|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WOT.u|C:\GOG Games\The Wheel of Time\work\phase5\modified\System\WOT.u|6个Font的CPP64/字页；追加18张P8小字图；小字号12px，中文斜体18×14|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoT.int|C:\GOG Games\The Wheel of Time\work\phase5\modified\System\WoT.int|menuSinglePlayer.MenuList[2]、HelpMessage[1]、InventoryInfoWindow.SubTitle；UTF16LE BOM|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\Angreal.int|C:\GOG Games\The Wheel of Time\work\phase5\modified\System\Angreal.int|AngrealInvAirBurst.Title、Description、Quote；UTF16LE BOM|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoTsubtitles.int|C:\GOG Games\The Wheel of Time\work\phase5\modified\System\WoTsubtitles.int|DialogA.Tes_01测试译文+原源文字符长度保留|是|

379字形/字体，6个字体，共2274个新增字形映射。原0～255共1536个字符映射、各Font原Page0逐字节保持；8371个其他原导出记录和内容保持。CPP64方案和256个密集码位的资源映射回归继续通过。EXE/DLL、脚本字节码、地图、音频、视频均未修改。

原WOT.u SHA256：`8e670c5b58110a31367029a9801ad38c89a587aa82d1786dec4451815b7746fb`。
修改SHA256：`aa6a0f0c5865c830b0616ffbb29b80ad50ea1a87c10b13cf3c827861d44770a1`。

字幕仍使用350字符源长度保留原型，本轮以进程启动时间计第25秒仍显示，第32秒已消失；此前phase3截图的第32秒不等于当前运行的同一语音时刻。**不把源长度保留宣称为逐帧/完整语音时长同步。**

## 实机截图
![Inventory中文标题/正文/斜体引文](C:\GOG Games\The Wheel of Time\docs\phase5\INV_CHINESE.png)
![320×240 Inventory完整复测](C:\GOG Games\The Wheel of Time\docs\phase5\INV_LOWRES_SETTLED.png)
![320×240小字号修复后](C:\GOG Games\The Wheel of Time\docs\phase5\LOWRES.png)
![同文7px修复前](C:\GOG Games\The Wheel of Time\docs\phase5\SMALL_BEFORE.png)
![字幕第25秒](C:\GOG Games\The Wheel of Time\docs\phase5\SUBTITLE_025.png)

## 自动检查与恢复
- `python tools\test_phase3.py`：13项通过；`python tools\test_phase4.py`：10项通过；`python tools\test_phase5.py`：14项通过，共37项。
- 新测试包含四资源ZIP/CRC/哈希、安装→验证→恢复、拒绝被改动的Angreal.int、中文字形倾斜尺寸及12px下限。
- 独立installer-test中的4资源恢复为原备份；独立rollback-test中的4资源+2配置通过ROLLBACK.sh恢复字节一致。
- 游戏内ROLLBACK及INV_ROLLBACK也确认英文菜单和物品说明恢复。
- 截图探针补充纯色/黑屏检测：该失败返回1并保留原始日志，不再把“进程正常退出”误当作界面测试成功。

## 工具与测试包
- C:\GOG Games\The Wheel of Time\tools\font_builder_v3.py：六字体、中文小字号12px、倾斜中文字形扩框、CPP64和原字形检查。
- C:\GOG Games\The Wheel of Time\tools\localization_build_v3.py：菜单/字幕/Angreal三张int表→字库→4资源ZIP。
- C:\GOG Games\The Wheel of Time\tools\patch_manager_v3.py：四资源版本校验、安装、恢复。
- C:\GOG Games\The Wheel of Time\tools\inventory_probe5.py：原生1/F2输入；自己的游戏进程；黑屏探针失败记录。
- C:\GOG Games\The Wheel of Time\tools\verify_phase5.py：读取已有实机证据，跑37项离线检查和独立回滚，恢复副本默认配置；本工具不启动游戏。
- 测试ZIP：C:\GOG Games\The Wheel of Time\work\phase5\build\ChineseInventoryTest.zip。

可复用离线构建命令：
```powershell
Set-Location 'C:\GOG Games\The Wheel of Time'
python tools\localization_build_v3.py --table work\phase5\test_translations.json --glyph-table work\phase5\font_strings.json --out work\phase5\build --preserve-subtitle-length
python tools\verify_phase5.py
```

## 交付与下一步
四份证据：C:\GOG Games\The Wheel of Time\work\phase5\modified\System\WOT.u、C:\GOG Games\The Wheel of Time\docs\phase5\FONT_DIFF.json、C:\GOG Games\The Wheel of Time\docs\phase5\VERIFICATION.txt、C:\GOG Games\The Wheel of Time\work\phase5\ROLLBACK.sh，均已重新打开/检查。

独立回滚命令：`& "C:\Program Files\Git\bin\bash.exe" -lc 'test -x work/phase5/ROLLBACK.sh && work/phase5/ROLLBACK.sh work/phase5/rollback-test/System'`。输入：独立副本4份修改资源及2份原配置。字面输出：`ROLLBACK PASS: 6 resource/config files byte-identical to backup; exit 0`，退出0。

修改资源保留于modified/System、build/System、runtime/System，原安装未覆盖。后续继续测试中文Reg08路径、更多Inventory对象和长多行小号文本；这些项目通过后再扩大正式翻译覆盖。本轮仅当前主机验证，不代表Windows10/其他系统语言均已认证。

最终MODIFIED、LOWRES、INV_CHINESE、INV_LOWRES_SETTLED、SUBTITLE记录包含四资源SHA256，验证器要求它们逐一匹配最终交付资源。修改前字库/脚本和早期截图保存在work/phase5/pre-fix与docs/phase5/pre-punctuation。
