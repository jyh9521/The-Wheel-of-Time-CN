# 设置动态值补漏（2026-10-04）

## 已完成的修改

循环竞技场关卡和高级选项下拉列表的英文显示已补全。配置中的机器值不翻译，界面中文和原始值分开处理；实机切换与持久化还需在1080p下测试。

- `menuStartArenaServer.UpdateValues`第4项原来直接把bool转成字符串，现在调用既有`GetOnOffStr`，读取同一套“开／关”译文。VM长度406→411，两个分支仍落在有效边界，7个输入/保存函数逐字节不变。该函数有条件分支，但此次插入点位于两处分支目标之后，不需要改变这两个目标；工具仍核对全部分支，并支持按VM增量重定位。
- `FPropertyItem.OnItemSetFocus`的6处下拉项添加调用只在传入显示文字时查表；bool、enum及class选择均保持原顺序。
- `FPropertyItem.ReceiveFromControl`的1处`FindString`调用同样查显示表，使原始enum/class名称仍可匹配已翻译的下拉项；bool仍按原序号选择。
- `FPropertyItem.SendToControl`只在下拉分支调用`SetValue`前反查原始值；原始`SetValue`函数、序列化、共享`WComboBox`方法和自由文本编辑分支均未修改。翻译表反向映射必须唯一，重复译文或原始/显示值重叠会使构建报错。
- 只用现有7项值表：True/False、High/Medium/Low、游戏控制台显示占位与English (International)。没有新增语言专用代码。未知值保持原样；设备/API、类名、地图名及自定义字符串不做猜测性替换。

## 版本与位置

原版Window.dll大小397312字节，SHA-256为`781a7572871ac6a96929f4f50d286c5362651dadfcb6b4e0124c7bb360cc6e61`。原始调用字节、RVA与arena函数hash见`profiles/gog-v68.json`。

新增编辑调用点RVA：0x19FBD、0x19FCE、0x1A07C、0x1A0E4、0x1A10B、0x1A41A（添加）；0x1CA34（查找）；0x1C751（下拉回写）。既有.locale显示段同时保存正向与反向UTF-16查找表；所有新增代码使用相对跳转/调用和位置无关表地址，不添加导入或运行时DLL。

## 验证与重建

构建入口不变，原版只读；20个生成资源中，与上一构建相比只有WOT.u和Window.dll改变。159项单元测试通过；730项x86模拟覆盖两个基址、显示/反查、未知值回退、寄存器和栈清理，以及全部8处编辑适配调用。UCC加载修改包编译自有证明类：0错误、0警告。这些是离线结果，不等于真实Windows控件和配置持久化已通过。

```powershell
python -m tools.validate.menu_values modified --reference GAME/System/WOT.u --package OUT/resources/System/WOT.u
python -m tools.validate.native_display --dll OUT/resources/System/Window.dll --report OUT/NATIVE_DISPLAY_DIFF.json
```

退出游戏后才能更新测试副本。1080p下检查循环关卡开关；高级选项选择开/关、高/中/低，退出重进核对保存，并确认INI仍保留原始True/False和档位名称。无需修改普通教程入口。原版和自定义值不能被中文标签覆盖。
