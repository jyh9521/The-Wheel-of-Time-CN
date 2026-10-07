# 绿色汉化安装包

## 安装流程

打开 WoT-zh-CN-Portable.exe，选择包含 System、Maps、Movies 的 GOG 游戏根目录。点击“校验文件”；文件版本和包内数据校验通过后，“安装补丁”才可点击。安装结束会重新校验输出文件。此后沿用 GOG 原游戏快捷方式或 System\WoT.exe 启动，不需要专用启动脚本。

不写注册表，不创建系统卸载项、开始菜单项或桌面快捷方式。仅在临时目录展开安装数据，并在游戏目录保存汉化资源与 `.localization-backup\player-test` 原件备份。无需 Python；界面使用系统 .NET Framework，后台使用系统 Windows PowerShell，不弹出命令行窗口。

## 修改范围

87 个资源：普通文本/地图显示字段/按钮图像、顶部专用 18px 字幕、原尺寸菜单和说明、14 段 FMV 中文字幕、向导中文按钮及思源黑体改名子集。MOV 在安装时通过差分合并字幕，不修改系统 QuickTime、不重编码画面或音频。游戏自身首次配置/视频设置向导也包含在补丁中；第三方 dxcfg/nGlide 配置工具保持不变。

仅开启 User.ini 中 bSubtitles 并将 WoT.ini 的 Language 设为 int，不复制开发配置、按键或存档，不自动改变分辨率。推荐在游戏中选择 1920×1080。WoT.exe、默认地图入口和原启动快捷方式保持不变。Mission_10 无对白，不添加字幕。

## 校验与恢复

选择目录后的校验不修改游戏文件。未知/改动过的原版文件、缺失文件或损坏安装数据会使安装停止。实际安装再次校验输入；所有输出先在独立临时目录重建并核对，再备份与写入。捕获到写入异常时恢复本次已写入资源。运行中不要强制结束进程或断电；恢复依赖备份目录，不应删除备份。

需要撤回补丁时，重新打开同一 EXE，选择原游戏目录，点击“恢复原版”。恢复前核对备份和当前资源，额外修改不会被静默覆盖。恢复会还原安装前配置，存档保留；该操作不是系统卸载程序。对已有不同版本的备份，应先使用对应原安装包恢复。

### 参考译名更新测试包（2026-10-07）

`WoT-zh-CN-Portable-ReferenceRefresh.exe` 包含本次参考译名、开场前四条字幕及里斯琳前后空格修正，重新生成随包思源黑体子集。普通 UI 字号不变，顶部游戏字幕仍为专用 18px，FMV 绘制大小不变。

已有旧版补丁时，先退出游戏，使用对应旧安装包恢复原版，再用新包验证文件并安装补丁。恢复会还原旧补丁安装前的设置，但不删除存档。若需保留测试期间调整的按键或显示设置，更新前另存 `System/User.ini` 与 `System/WoT.ini`。

旧包恢复后可能保留旧 `STATE.json`。新包仅在所有目标资源匹配原版 SHA-256 且补丁新增文件均不存在时，允许验证和安装；仍处于旧补丁状态或混合状态时继续拒绝，不绕过版本校验。该识别不删除旧备份，实际安装仍先完整重建、验证全部输出，再备份并写入。

本地测试版本尚未完成通关验收。字体/派生字库发布许可边界仍见 LICENSING.md，不作为公开 Release 上传。

## 重建与验证

```powershell
python tools/build/package_portable_installer.py --source-package <已验证差分ZIP> --game-dir <原版目录> --window <向导汉化后的Window.dll> --out dist/WoT-zh-CN-Portable.exe --work build/portable-installer
python tools/validate/portable_installer_qa.py --game-dir <原版目录> --exe dist/WoT-zh-CN-Portable.exe --manifest build/portable-installer/DIFF_FILE.json --work build/portable-installer-qa
```

源码界面位于 src/installer/PortableInstaller.cs；安装引擎为 assets/templates/player-test.ps1。构建使用 Windows .NET Framework C# 编译器，无需额外下载安装器框架。语言数据和显示层继续沿用既有 locale 工具链。最终 EXE 内嵌差分，而非完整原程序、视频或游戏包。

自动化入口仅用于验证：`--headless check|apply|verify|restore <游戏目录> <结果日志>`；直接双击始终打开选目录界面，不自动安装、不自动启动游戏。

## 界面样式

安装器采用 WinForms 自绘的 Material Design 3 风格：浅色卡片、圆角操作按钮和明确的主操作层级。安装后端、版本验证、备份和恢复机制保持不变；不附带网页运行时、图标库或额外界面字体。原生按钮保留键盘操作与焦点提示，高对比度模式回退系统控件绘制。当前截图验证不等同于全部 DPI 与辅助功能验收。

## 安装器提示语言

安装器自有提示统一由 `locales/zh-CN/installer-ui.json` 提供。系统异常按异常类型转换为中文提示和十六进制错误代码，不直接显示系统 `Exception.Message`。目录选择、恢复确认及错误窗口采用自有中文界面；文本框禁用系统语言的右键菜单，仍保留键盘复制粘贴。目录与文件名称保持原样。操作系统自身弹窗不属于安装器界面。文化环境模拟分别使用 zh-CN、en-US 和 ja-JP，实际不同语言 Windows 的完整操作验收仍需独立测试。
