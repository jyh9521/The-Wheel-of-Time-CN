# 高级设置范围审计

> 历史开发与测试记录：下述测试数、待办、验收状态和产物名称对应记录时的构建，不代表正式版当前状态。v1.0 已完成完整通关测试且未发现补丁问题；正式文件为 `WoT-CN-v1.0.exe`。当前说明见 [项目主页](../README.md)、[安装说明](PORTABLE_INSTALLER.md)和[显示限制](KNOWN_ISSUES.md)。

## 已确认范围

GOG v68 原生属性编辑器为所有未绑定枚举的 ByteProperty 建立 0–255 滑块。
这个范围来自存储类型，不等于游戏菜单接受的语义范围。整体细节等级超过 2 时，
`menuConfiguration.GetDetailClass` 会执行断言，硬件设置菜单因此退出。

| 属性 | 编辑范围 | 证据与处理 |
| --- | --- | --- |
| MasterDetailLevel | 0–2 | GetDetailClass 仅接受三个分支；原版菜单 Min(2, ...) |
| MaxDetailLevel | 0–4 | 原版 menuConfiguration.ProcessRight 明确 Min(4, ...) |
| GoreDetailLevel | 0–3 | 原版 menuOptions.ProcessRight 明确 Min(3, ...) |
| MaxNumDecals | 0–4095 | 原版菜单上下限；整型输入框，不是 255 滑块 |
| ParticleDensity | 0–255 | 原版菜单与 ByteProperty 控件范围一致，不缩小 |
| SoundVolume / MusicVolume | 0–255 | 原版菜单范围，不缩小 |

表中后三个等级和贴花上限是原版菜单的编辑契约；不意味着每个越界值都会崩溃。
已复现的崩溃证据指向整体细节等级。贴花数量 0 是有效值，不自动改成默认值。

## 遍历与证据边界

扫描 System 内 `.int` 的 31 条 Preferences 声明、现有 274 个显示标识、
383 条匹配的包属性或原生属性注册声明；记录 49 个包/DLL 输入散列。
原生属性类型通过注册 vtable 的 Core 属性方法确认，不按字段名猜类型。

已识别的裸字节滑块包括三个等级、粒子密度、音效音量和音乐音量。
SkinDetail、TextureDetail、OutputRate、Glide RefreshRate 是绑定枚举的字节属性，
继续使用原生枚举列表，不改成任意数值输入。布尔选项继续使用开/关列表。

浮点、整型、字符串、数组、驱动名称和按键绑定不具有统一的“最大安全值”。
目前缺少明确消费逻辑证据的字段保持原控件行为，并在完整清单中标记未确认；
不把存储容量当作性能建议，也不编造全局上限。分辨率、帧率、网络参数和旧显卡
驱动选项尤其受运行环境影响。枚举值显示与保存转换保持现有实现。

只读审计命令（额外依赖 capstone 5.0.7）：

```powershell
python -m tools.validate.advanced_settings_audit --game-dir "D:/GOG Games/The Wheel of Time" --out build/property-audit/INVENTORY.json
```

清单逐项保留标识、声明类型、注册位置、ScriptText 引用与散列、确认范围或未确认状态。
完整游戏源码和 DLL 不进入仓库。

## 实现

通用实现位于 `src/patch/property_limits.py`，版本数据位于
`profiles/gog-v68.json` 的 `native_properties.integer_limits`。
范围与语言无关；生产构建的原生窗口阶段自动使用这些规则。

- 原 Window.dll 大小、SHA-256、原指令检查后才生成新副本。
- `OnItemSetFocus` RVA 0x19B58 修改非枚举字节滑块最大值。
- `FPropertyItem.SetValue` RVA 0x18D00 在 ImportText 前检查四个整型字段。
- 按 `Engine.Client` 声明所有者、原属性名匹配，不影响同名无关属性。
- 越界、负数、非整数、超长数字和空输入被拒绝，原生刷新路径恢复当前值。
- 不修改引擎属性序列化、反射名称、游戏逻辑、FMV、字体或存档。
- 保持现有高级设置汉化、行高、列宽和枚举回写转换。

外部手工改 INI 或控制台命令不经过这个属性编辑器，仍需配置校验。
这不是引擎对任意配置来源的全局校验。

## 当前测试副本

已更新 1.5 倍字体测试副本，原安装未修改。现有 MaxDetailLevel=255 调整为 4，
GoreDetailLevel=255 调整为 3；MasterDetailLevel 保持已恢复的 2，MaxNumDecals=0 保留。
安装清单同步更新 Window.dll 散列，启动前完整性校验继续启用。

215 项单元测试通过；范围适配 104 项 x86 CPU 检查、原生显示 730 项检查通过，
覆盖两个加载基址、合法/越界输入、无关字段、栈与寄存器。
独立副本回滚恢复原 DLL、配置和清单，并再次复现原控件 255 上限。
本轮未启动游戏，滑块操作、越界输入恢复、硬件菜单切换与设置保存尚待 1080p 实机验收。
