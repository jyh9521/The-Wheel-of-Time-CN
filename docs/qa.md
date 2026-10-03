# 工程迁移与高分辨率 QA（2026-10-03）

## 当前结论

工程入口从全新原版四资源重建；源配置/译文/字体身份写入报告。
7条草稿，实际使用134个新增BMP字形/字体，6字体、8个追加P8纹理；其他8371原导出未变。
合成测试29条通过，重复构建四资源与差分逐字节相同；差分安装/验证/独立回滚通过。
干净克隆重新构建四资源及PATCH.json逐字节一致，克隆内独立安装/回滚通过。
原安装277/277散列保持。未改EXE/DLL/地图/玩法，未进行大规模翻译。

## 分辨率结果

|真实 best-match 模式|菜单|Inventory|教学字幕|说明|
|---|---|---|---|---|
|1366×768|中文新游戏与帮助可见|标题/正文/斜体/提示可见|本轮未跑|下限；不再测320×240|
|1920×1080|可见，未见当前PoC裁切|可见，正文正常折行|20秒中文可见|主要验收样本|
|2560×1440|可见|可见|20秒中文可见|固定像素文字占屏变小|
|3840×2160|可见|可见|20秒中文可见|中文正常，但明显偏小，不能算UI可读性完成|

共15次成功原生探针：11次修改资源（4菜单+4Inventory+3字幕），4次原资源对照
（1080p菜单、1366 Inventory、4K Inventory、4K字幕）；都正常退出0。
对应模式日志均匹配请求，而截图面积全为3840×2160桌面，两者不能混淆。
人工观察代表性settled帧与字幕20秒帧；其他定时帧保存供复查，不虚构逐帧OCR验收。
原英文4K Inventory和字幕同样明显偏小，属于原UI固定像素机制，而非中文编码失效。
**下一项应研究语言无关的UI/字体缩放，不能只把中文字变大造成Latin/布局不一致。**

## 命令与输入

```
python -m tools.validate.runtime --game-dir GAME --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view menu
```

替换resolution为上表值、view为inventory/subtitle；--original保留同配置原资源对照。
menu启动 `.\WoT.exe Entry -nosound`，Escape、Enter；Inventory启动
`.\WoT.exe Mission_01 -nosound`，F3关闭初始目标、1选当前手位、F2资料，额外等待10秒。
subtitle启动 `.\WoT.exe Tutorial`，无移动/控制台输入，10/20/25/36秒截图；自身主窗口WM_CLOSE。
每个成功结果均有 `RUNTIME PASS: <label>; native_exit=0; visual_review=pending` 字面探针输出；
pending是探针自动结果，不是人工审查结论。结构索引和证据hash见qa-results.json。

## 失败记录与修正

- 首次修改版1366 Inventory画面已捕获，但退出码1；日志
  DDERR_NOEXCLUSIVEMODE → ReTestCooperativeLevel/UD3DRenderDevice::Lock。
  原流程同时关闭自己所属的主窗口和DirectDraw代理；调整为只先关闭主窗口。
  原/改1366 Inventory及之后各模式退出0；这是探针退出流程修正，不是补丁引擎修复的证明。
  首次失败的截图/JSON/log以.attempt1后缀留在本地生成目录。
- 紧接着首次原资源对照未找到游戏主窗口，原生退出0，探针失败；可能是前次异常后的恢复对话框，
  该原因是推断。后续原资源对照重跑显示正常，未计入15次成功。
- 最初移植遇到默认cp932读源/输出失败，明确UTF8读写后解决；未把测试工具异常归为游戏崩溃。

## 边界

这不是所有菜单/HUD、全部剧情、存档/切图/战斗/联网或多显卡/多Windows版本完整验收。
4K可读性未解决；当前不发布玩家成品。不提交游戏截图/整包资源/Windows字库生成物。
