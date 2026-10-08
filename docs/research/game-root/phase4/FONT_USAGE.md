# 字体使用位置（原始脚本静态证据）

> 历史开发与测试记录：下述测试数、待办、验收状态和产物名称对应记录时的构建，不代表正式版当前状态。v1.0 已完成完整通关测试且未发现补丁问题；正式文件为 `WoT-CN-v1.0.exe`。当前说明见 [项目主页](../../../../README.md)、[安装说明](../../../PORTABLE_INSTALLER.md)和[显示限制](../../../KNOWN_ISSUES.md)。

字体机制：Unreal UFont 字页 + P8 Texture + Palette；原 `.u` 导出的脚本只读。

|位置|行号|调用|
|---|---|---|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\Legend\LegendCanvas_ScriptText_0.uc|81|`if( SizeX < 512 && !bForce )`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\Legend\LegendCanvas_ScriptText_0.uc|94|`TempFont = Font( DynamicLoadObject( "WOT.F_WOTReg08", class'Font', true ) );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\Legend\LegendCanvas_ScriptText_0.uc|100|`else if( instr( FontStr, "F_WOTIta14" ) != -1 )`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\Legend\LegendCanvas_ScriptText_0.uc|103|`TempFont = Font( DynamicLoadObject( "WOT.F_WOTReg14_S", class'Font', true ) );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\ArenaScoreBoard_ScriptText_0.uc|128|`Canvas.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\BaseHUD_ScriptText_0.uc|679|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\BaseHUD_ScriptText_0.uc|1009|`GenericMessages[0].F = Font'WOT.F_WOTReg14';`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\BaseHUD_ScriptText_0.uc|1075|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\BaseHUD_ScriptText_0.uc|1261|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\BaseHUD_ScriptText_0.uc|1363|`Canvas.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\BattleHUD_ScriptText_0.uc|36|`LegendCanvas(C).DrawTextAt( ( C.SizeX - XL ) / 2, YL * 3, SelectMessage, font'WOT.F_WOTReg14', false ); // draw two lines above the Scoreboard header`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\BattleScoreBoard_ScriptText_0.uc|131|`Canvas.SetFont( Font( DynamicLoadObject( "WOT.F_WOTReg08", class'Font' ) ) );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\BattleScoreBoard_ScriptText_0.uc|171|`Canvas.SetFont( Font( DynamicLoadObject( "WOT.F_WOTReg08", class'Font' ) ) );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\Credits_ScriptText_0.uc|25|`C.SetFont( font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|85|`C.SetFont( font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|106|`C.SetFont( font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|107|`LegendCanvas(C).DrawTextAt( 0, TitleOffsetY, Inv.Title, font'WOT.F_WOTReg30' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|117|`LegendCanvas(C).DrawTextAt( 0, InfoOffsetY, RarityRareStr, font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|119|`LegendCanvas(C).DrawTextAt( 0, InfoOffsetY, RarityUncommonStr, font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|121|`LegendCanvas(C).DrawTextAt( 0, InfoOffsetY, RarityCommonStr, font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|136|`C.SetFont( font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|137|`LegendCanvas(C).DrawTextAt( WindowClipSizeX-XL1-XL2, InfoOffsetY, default.ChargesStr, font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|168|`C.SetFont( Font( DynamicLoadObject( "WOT.F_WOTIta14", class'Font' ) ) );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\InventoryInfoWindow_ScriptText_0.uc|190|`LegendCanvas(C).DrawTextAt( 0, WindowClipSizeY-SubTitleOffsetY, SubTitle, font'WOT.F_WOTReg14', false, false );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\MenuHUD_ScriptText_0.uc|16|`C.SetFont( Font'WOT.F_WOTReg30' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuLoad_ScriptText_0.uc|82|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuLoad_ScriptText_0.uc|87|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuLong_ScriptText_0.uc|49|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuMain_ScriptText_0.uc|89|`LegendCanvas(C).DrawTextAt( 2, C.SizeY - 16, class'Version'.static.GetVersionStr(), font'WOT.F_WOTReg14', false, true );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuSlot_ScriptText_0.uc|31|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuWOT_ScriptText_0.uc|225|`C.SetFont( Font'WOT.F_WOTReg30' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuWOT_ScriptText_0.uc|240|`C.SetFont( Font'WOT.F_WOTReg30' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuWOT_ScriptText_0.uc|244|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\menuWOT_ScriptText_0.uc|385|`C.SetFont( Font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\MessageTrigger_ScriptText_0.uc|68|`Font'WOT.F_WOTReg14',`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\uiConsole_ScriptText_0.uc|112|`C.SetFont( font'F_WOTReg14', true ); // force full-size font for following size calculations`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\uiConsole_ScriptText_0.uc|188|`C.SetFont( font'F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\uiConsole_ScriptText_0.uc|308|`C.SetFont( font'F_WOTReg30' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTCanvas_ScriptText_0.uc|13|`#exec Font Import File=Fonts\UI\F_WOTReg08.pcx		Name=F_WOTReg08`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTCanvas_ScriptText_0.uc|14|`#exec Font Import File=Fonts\UI\F_WOTIta14.pcx		Name=F_WOTIta14`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTCanvas_ScriptText_0.uc|15|`#exec Font Import File=Fonts\UI\F_WOTReg14.pcx		Name=F_WOTReg14`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTCanvas_ScriptText_0.uc|16|`#exec Font Import File=Fonts\UI\F_WOTReg30.pcx		Name=F_WOTReg30`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTCanvas_ScriptText_0.uc|17|`#exec Font Import File=Fonts\UI\F_WOTReg14_S.pcx	Name=F_WOTReg14_S`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTCanvas_ScriptText_0.uc|18|`#exec Font Import File=Fonts\UI\F_WOTReg30_S.pcx	Name=F_WOTReg30_S`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|63|`strFont = "WOT.F_WOTReg08";`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|66|`strFont = "WOT.F_WOTIta14";`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|69|`strFont = "WOT.F_WOTReg14";`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|73|`strFont = "WOT.F_WOTReg30";`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|76|`strFont = "WOT.F_WOTReg14";`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|215|`C.SetFont( font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|218|`LegendCanvas(C).DrawTextAt( 0, TitleOffsetY, WTWItem.Title, font'F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|279|`C.SetFont( font'WOT.F_WOTReg14' );`|
|C:\GOG Games\The Wheel of Time\work\phase1\scripts\WOT\WOTTextWindow_ScriptText_0.uc|334|`LegendCanvas(C).DrawTextAt( 0, Max( C.CurY+SubTitleMarginY, WindowClipSizeY-SubTitleOffsetY), WTWItem.SubTitle, font'F_WOTReg14', false, false );`|
