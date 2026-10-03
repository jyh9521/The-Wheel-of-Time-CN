# 三字中文位图字体验证（2026-10-02）

## 结论
实际游戏单人菜单已显示 **新游戏**。原版字体配合同一份中文 `.int` 时该行空白；补入三字后可见；恢复原资源后 **New Game** 再次可见。三次正式对照均正常退出，退出码0。

本菜单路径的中文显示不需要修改 EXE/DLL，也不需要 GBK 双字节绕行。最少侵入路线是 **UTF-16LE BOM 本地化文本 + Unicode 字符索引的多页位图字体**。本次只验证三字菜单，未扩展到全文、剧情或所有字体。

## 修改记录
|原资源|工作修改|原因/方法|可逆|
|---|---|---|---|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WoT.int|C:\GOG Games\The Wheel of Time\work\phase2\modified\System\WoT.int|仅 `[menuSinglePlayer] MenuList[2]` New Game→新游戏；UTF-16LE BOM|是|
|C:\GOG Games\The Wheel of Time\backup\phase1-original\System\WOT.u|C:\GOG Games\The Wheel of Time\work\phase2\modified\System\WOT.u|仅 F_WOTReg14、F_WOTReg30 的原 Font 对象扩充字页，追加两个 Texture 对象|是|

原 WOT.u SHA256：`8e670c5b58110a31367029a9801ad38c89a587aa82d1786dec4451815b7746fb`。
修改 WOT.u SHA256：`915afbfaf58ae7212c230165a478076651a4ba47e8e1faf9328a5e607ce66eda`。

## 资源结构
- 原 Font：1页，256字符/页，每字4个int32矩形字段 StartU/StartV/USize/VSize。
- 两个 Font 各扩展到111页；无使用的新增页保持空，无额外空纹理分配。
- 戏U+620F：页98/槽15；新U+65B0：页101/槽176；游U+6E38：页110/槽56。
- 新增 P8 遮罩纹理：14px字体使用256×128；30px字体使用256×256。每个 Font 的三个字页共享一张新增纹理。
- 复用原金色 Palette；微软雅黑仅在本机栅格化三字，没有打包字体文件。当前外观是验证字体，不是最终美术设计。
- 原 Page0 的纹理引用和全部字符矩形逐字节保持。其余8375个原导出条目及序列化内容保持；Import表、原名称及GUID保持；脚本/类/函数字节码保持。
- 追加序列化数据、名称表与导出表，并更新对应表指针/数量及generation计数；修正新Texture的绝对lazy-array结束偏移。
- 30px菜单字形已实机确认；14px字形通过资源结构检查，尚未单独进入14px中文UI验证。

## 实际测试
命令均从 `C:\GOG Games\The Wheel of Time` 执行，具体日志、输入、退出状态见 `C:\GOG Games\The Wheel of Time\docs\phase2\VERIFICATION.txt`。

|命令|输入资源|可见结果|退出码|
|---|---|---|---|
|`python tools\phase2_probe.py BASELINE`|中文int+原字体|中文行空白，英文菜单可见|0|
|`python tools\phase2_probe.py MODIFIED`|中文int+三字字体|新游戏可见，英文菜单可见|0|
|`python tools\phase2_probe.py ROLLBACK`|原int+原字体|New Game恢复|0|

每次子进程执行 `.\WoT.exe Entry -nosound`，Escape→Enter 进入单人菜单，截图后WM_CLOSE关闭。不进入新游戏，不创建存档，不验证声音。
独立回滚在另一副本 `C:\GOG Games\The Wheel of Time\work\phase2\rollback-test\System` 执行，四文件cmp成功。
前两次基线启动/截图失败（原资源DirectDraw错误、随后Recovery Mode），已如实记入验证记录；随后正式对照成功。尚未验证Windows10、其他Windows语言、全部分辨率或长时间游戏稳定性。

### 中文截图
![新游戏](C:\GOG Games\The Wheel of Time\docs\phase2\MODIFIED.png)

## 交付与使用
- 中文测试启动：`C:\GOG Games\The Wheel of Time\work\phase2\Launch_ChineseFontTest.cmd`。进入游戏后按Esc→Enter查看。
- 回滚：`C:\GOG Games\The Wheel of Time\work\phase2\ROLLBACK.sh`；仅允许phase2工作副本的System目标，恢复WOT.u/WoT.int/WoT.ini/User.ini。
- 修改文件：`C:\GOG Games\The Wheel of Time\work\phase2\modified\System\WOT.u`；配套文本：`C:\GOG Games\The Wheel of Time\work\phase2\modified\System\WoT.int`。
- 差异清单：`C:\GOG Games\The Wheel of Time\docs\phase2\FONT_DIFF.json`。
- 验证记录：`C:\GOG Games\The Wheel of Time\docs\phase2\VERIFICATION.txt`。
- 构建器：`C:\GOG Games\The Wheel of Time\tools\font_minimal_patch.py`。

原安装277/277原文件SHA256未改变。最终隔离runtime保留中文测试资源；rollback-test保留已恢复原资源。

## 下一步
先验证一个较长中文菜单和一条字幕的换行、字宽与其他字号。然后从实际翻译字集生成Font各字页，逐一确定全部菜单/HUD/字幕使用的Font对象，保持ASCII页不变；不先塞入整个GB2312，也不先改引擎。

可复用任务提示：
```text
仅在隔离工作副本中，使用已验证的UTF-16LE localization及多页UFont方案，增加一个长菜单文本与一条已有字幕的中文测试。按实际字集生成字形，保留全部原ASCII页、字节码和未涉及资源，实测换行/字号/屏幕显示，并在另一副本回滚。不要开始全文翻译。
```

## 后续字集工具开发
81字/两个字号的CSV/JSON构建和回滚通过静态测试，本轮长文本及字幕实机确认待完成。详见 `C:\GOG Games\The Wheel of Time\docs\phase3\REPORT_zh-CN.md`。

## 最新长菜单与字幕复测
128字/字号的长菜单与Tes_01中文字幕已实机显示，大贴图和字符计时时长问题已修复；13项自动测试和原资源回滚通过。详见 `C:\GOG Games\The Wheel of Time\docs\phase3\REPORT_zh-CN.md`。
