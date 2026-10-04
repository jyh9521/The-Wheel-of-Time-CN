# 原生高级选项窗口汉化（2026-10-04）

## 归属与范围

这是WinDrv打开、Window模块绘制的早期Unreal原生Windows属性窗口，不是`.utx`按钮图片，也不使用游戏Canvas字库。此前核心1002条的范围未覆盖该窗口；该批作为独立语言数据扩展，不能把旧覆盖报告当作全游戏英文清零证明。

已处理13个`.int`文件中的31条活动Preferences记录，以及48条普通文案。包括高级选项标题、高级/音频/显示/驱动程序/编辑器/游戏设置/手柄/网络/渲染分类、已注册子分类、ClassCaption、相关窗口按钮和属性窗口通用标题。九个主分类之外“高级”下还包含文件系统、游戏引擎设置、按键别名等子树。

全部显示数据位于`locales/zh-CN/native-ui.json`，普通文案仍按原条目身份、源hash、控制符回填；Preferences仅改Caption和Parent。Parent虽会显示，也承担分类树关联，因此必须与中文Caption和根标题同步修改。Class、Category、Immediate、Object、名称、数值和原配置键不翻译。Language/LangId/SubLangId保持原样。

## 本地二进制只读证据

| 模块 | SHA-256 |
| --- | --- |
| Window.dll | 781a7572871ac6a96929f4f50d286c5362651dadfcb6b4e0124c7bb360cc6e61 |
| WinDrv.dll | 43076c7c4492654fb71fbeb7c4a83d4c870f7db0ad7421ada75a7912a06af964 |
| Core.dll | 94f55e23624333ed95f7cbe4026dd98f7219eb3e3ae5da8310763f901b4e3702 |

已验证：WinDrv.dll RVA 0x7B27起调用LocalizeGeneral，使用Window/AdvancedOptionsTitle；0x7B52调用WConfigProperties构造器并传递译后的标题。Window.dll FConfigItem::Expand主体RVA 0x25AE0通过GetPreferences展开树。Core.dll UObject::GetPreferences主体RVA 0x5A600按Parent字符串匹配并返回登记数据；这说明不能只翻Caption而留下英文Parent，否则子树断开。

已验证：Window.dll FPropertyItem::GetCaption主体RVA 0x18510从FName表复制名称；FCategoryItem::GetCaption主体RVA 0x1DAC0也从FName复制名称，函数内没有Localize调用。高可信推断：不少展开后的参数名和属性分类仍是原生反射标识，普通`.int`译文不能直接替换这层。尚未验证所有构造和枚举调用路径，不将其写成全部属性永远不可本地化的定论。

该阶段没有修改DLL/EXE，没有重命名属性、类别或配置键。后续若需要全面中文参数名，应另行研究显示名称适配，不能靠修改原配置键来冒险替换。

## 构建与验证

默认构建接入`tools/import/preferences.py`。输出仍为原版hash守卫的PATCH.json，该批资源从6个增为19个；此前6个汉化资源的输出hash逐一一致，图片按钮和字幕时钟模块不受影响。

```powershell
python build.py --locale zh-CN --game-dir GAME --subtitle-source SUBTITLES --font FONT --out build/advanced-options/fixed
python -m tools.validate.preferences --source GAME/System --locale-data locales/zh-CN/native-ui.json
python -m tools.validate.preferences --source build/advanced-options/fixed/resources/System --baseline GAME/System --locale-data locales/zh-CN/native-ui.json
```

已验证31条元数据及48条文案与预期逐条一致，树根和Parent/Caption连通，所有其他条目保持原内容；19文件独立副本安装/核验/回滚通过。原版文件未变。134项自动测试通过。静态校验和回滚不等于真实原生窗口的显示验收，这一阶段只做了离线验证，未运行游戏。

## 尚待确认

- 完整退出游戏再重新打开高级选项，避免引擎已缓存英文Preferences。
- 用1080P确认标题、主分类、子分类、按钮能显示中文。
- 展开后的原生参数标识仍可能是英文；这一层尚未汉化。
- 我截图中的高DPI行高/文字截断是独立布局问题，该批没有修改原生字体或行高。

## 深层参数与裁切的后续实现（2026-10-04）

此前.int仅元数据阶段仍保留；当前补充Window.dll显示适配，见TECHNICAL.md末节。GetCaption RVA 0x1854D/0x1DAFD及Draw直接名字路径0x18F2E包装查表。Draw值路径0x19195仅改栈上临时缓冲；GetHeight 0x198A0/0x1D4D0返回32；GetDividerWidth 0x1F5A0最小320。全部输入先检查原版SHA，精确预期字节在profile，适配只生成复制DLL差分。

274个显示名称与7个值映射来自locale数据，通用代码不含中文术语。未知名称回退原文，原FName表/配置键不修改。602个CPU模拟断言覆盖两种加载基址及实际跳转包装；没有启动游戏。请在1080p确认展开、滚动、裁切、编辑、保存。原生编辑框保留原机器值，系统DPI超过当前32像素行高时仍可能需要后续调整。
