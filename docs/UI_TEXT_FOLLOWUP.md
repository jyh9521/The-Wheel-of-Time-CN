# 动态界面文本补漏（2026-10-04）

## 已定位与已构建

- 教程中央按键提示存于Tutorial.wot的MessageTrigger.Messages实例，不在WoTsubtitles.int。只读提取35条实际可输出非空提示，按地图SHA、actor/slot/source SHA绑定译文。只忽略首字符处的//；原有一条前缀为“ //”，译文保留前缀，不改变判断。
- LocalePlayer.GenericMessage仅精确匹配源串后更换显示文字，未知消息原样交给原函数。坐标、居中、亮度、字体和持续时间完整转交；不修改地图、触发时序或按键。仍须使用现有LocaleTutorial+LocalePlayer入口，普通原版教程类不会启用此适配。
- menuKeyboard.DrawValues显示来自KEYNAME的机器名；只包裹3个显示数组操作数，用引擎Localize读取WoT.int新增KeyNames表。10个输入/改键/保存函数逐字节不变，原始数组和命令不翻译。
- 表覆盖Console/Actor.EInputKey的259个不同名称及_等待标记。两枚举的4个JoyPov方向项不同，覆盖两套名称。Engine.dll GetKeyName分支检查0≤键号<255，从枚举FName取得去掉IK_前缀的名称；版本绑定，不泛化到未知引擎。
- 自有UCC KeyMapped证明包裹增加22个VM字节；DrawValues VM229→295。6个分支同步重定位并用窄范围解析器校验，原函数SHA和原始操作数必须匹配。只更新文件长度而不更新VM分支会破坏控制流。
- 字母、数字、F1等键帽标识保留，鼠标、方向、标点、小键盘及手柄键本地化。Shift键不是瞬移能力。未知版本需扩充profile，不静默放行。
- Engine.int补Console的Loading/Saving/Connecting/Paused/PrecachingMessage及PlayerPawn.QuickSaveString，共6条。uiConsole.PrintActionMessage采用WOT.F_WOTReg30；不改进度状态机。
- 气流冲击引文由“重重撞在石头上”改为“重重撞上石头”。当前F_WOTIta14测得整句宽418→399像素，句号保留；1080P实际换行仍需截图验收。

## 设置残留与验收范围

核心/字幕覆盖审计1002条：0漏项、0原文相同，165条结构/标识保留；不等于全部动态值或实机验收。原生高级选项编辑控件的机器值、未知反射属性、设备/API、自定义名称及数字需分开处理。竞技场循环关卡bool显示仍是另一处已知遗漏，本轮未改其带循环函数，不宣称所有设置英文清零。

## 重建与验证

基础build.py命令不变，字库输入同时包含键名/提示。另行重建LocaleRuntime后，以旧ADDON.json核验并恢复旧插件，再应用新插件；不覆盖未知文件。

```powershell
python -m tools.validate.key_display --original GAME/System/WOT.u --modified OUT/resources/System/WOT.u
python -m tools.build.subtitle_runtime build --game-dir GAME --locale zh-CN --out ADDON_OUT
```

编译、回读、VM分支、字体覆盖、输入函数不变及隔离回滚属于离线证据。教程触发、改键后退出重进、载入/保存/预缓存与引文布局须1080P实机验收。
