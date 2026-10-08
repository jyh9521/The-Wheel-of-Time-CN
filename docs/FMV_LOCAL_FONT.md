# FMV 本地字体子集验证（2026-10-05）

> 历史开发与测试记录：下述测试数、待办、验收状态和产物名称对应记录时的构建，不代表正式版当前状态。v1.0 已完成完整通关测试且未发现补丁问题；正式文件为 `WoT-CN-v1.0.exe`。当前说明见 [项目主页](../README.md)、[安装说明](PORTABLE_INSTALLER.md)和[显示限制](KNOWN_ISSUES.md)。

## 当前结论

已完成思源黑体 2.005 的静态 Regular 子集、进程私有加载及旧 QuickTime 原生绘制验证。字体随独立游戏副本放在 `Fonts/WotFmv.ttf`，不依赖永久安装黑体。1146 个字符包含当前 628 条 FMV 译文所需字符与基础 ASCII；1182 个字形，304788 字节，缺字检查为 0。

2026-10-05，实际游戏内的本地字体中文字幕显示已确认。完整通关测试入口采用 `build/local-font-game/LAUNCH_GAME.ps1`；此前的 `build/formal-game` 与原版目录保持不变。全部视频的配音同步、跳过、重播、返回地图及完整通关稳定性仍待 1080p 正式测试。受控绘制、CPU 检查与游戏内显示确认分别记录，不互相替代。

## 字体来源与许可

来源：Adobe `source-han-sans`，版本 2.005，release commit `a4f7cf94edfb9d7ffbdfc4841de276358bd7e0f2`。具体下载地址、17749860 字节的源文件与 SHA-256 见 `profiles/fmv-font-source.json`。

只保留所需字符，并将可变字体实例化为 400 字重的静态 TrueType 字体。主字体名称改为 `WotFmv`，不占用系统 SimHei 名称。新名字与原 text 描述的 Geneva 同为六个 ASCII 字节，满足当前等长字体名槽限制。

原版权与 OFL 元数据保留，发布时附带 `assets/fonts/SourceHanSans-OFL.txt` 的同一许可证。子集字体继续使用 SIL OFL 1.1，不能归入项目工具的 MIT 或译文的 CC BY-SA。完整源字体与生成字体均留在忽略的 build 目录；字体来源不改写为项目原创。[上游许可证](https://github.com/adobe-fonts/source-han-sans/blob/master/LICENSE.txt)

## 已验证：加载与编码兼容

- 同一 MOV、同一 162.5 秒画面，无加载时 QuickTime 查询 `WotFmv` 得到 `id=0; resolved=System`。
- 使用实际补丁 DLL 的新增代码注册字体后，查询得到 `id=638; resolved=WotFmv`；字体注册返回两个字符集字体面，成功状态缓存。
- 同输入的音画区域像素一致，字幕区域像素不同；原生抽帧已确认中文正文正常，不出现此前的方框。
- 进程结束后，新的进程再次查询得到 `id=0; resolved=System`，没有永久安装字体。
- 14 段剧情视频最长字幕的原生绘制均成功；最底两行像素保持黑色。该边界检查只检测底边，不等同于全部字形、长句和游戏布局人工验收。
- 同步字段及原音画 mdat 不变；独立副本恢复的 14 个 MOV 和 WinDrv.dll 与原版逐字节一致。正式副本仍通过原有校验。

### OS/2 字符集标记的坑

普通子集流程将源字体的 `ulCodePageRange1` 从 `0x60060107` 裁为 `0x1`，旧 QuickTime 虽能找到字体，部分汉字仍显示方框；原生字体直接绘制及 cmap 检查证明对应字形实际存在。保留全部上游 CJK 标记又出现整行方框。

此版本在 locale 专用实验配置中指定 `0x40001`（Latin-1 与简体中文代码页标记），原生绘制恢复正常。通用子集工具通过可选参数接收标记，不硬编码中文；其他 locale 必须单独验证其标记。MOV 正文仍是 FEFF + UTF-16BE / encd=0x100，**不是把字幕改为 GBK**。标记影响旧播放器的字体脚本选择，不能用它代替 cmap 缺字校验。

## 游戏适配位置与理由

原版 GOG WinDrv.dll SHA-256：`43076c7c4492654fb71fbeb7c4a83d4c870f7db0ad7421ada75a7912a06af964`。仅匹配该版本才构建。

PlayMovie 在 RVA `0xF982` 调用原 InitializeQTML 包装函数 `0x17E50`，预期字节 `E8 C9 84 00 00`。该五字节 call 重定向到新 `.lfcode` 的 PIC 代码；注册完成后尾跳回原包装函数，原参数及调用约定保持。原 text 选择三字节适配沿用已有方案。

新增代码通过 WinDrv 模块路径定位 `System/../Fonts/WotFmv.ttf`，使用 GetModuleFileNameW，支持路径中的 Unicode；在 QuickTime 初始化前调用 AddFontResourceExW(FR_PRIVATE)。注册发生在播放函数中，不在 DllMain 或加载器锁内，也不是启动器进程注册后期待字体被继承。

代码与状态分别位于 RX `.lfcode`、RW `.lfdata`，不新增 RWX 节。NumberOfSections、SizeOfCode、SizeOfInitializedData 和 SizeOfImage 同步更新；原 IAT 结构、重定位表、音轨路径及 EXE 保持。PIC 代码通过已有 Kernel32 IAT 解析 API，不新增外部 DLL 文件。加载失败保持原播放流程，不永久安装字体；测试启动脚本会提前检查字体 hash。

16 项 CPU 场景验证了重定位基址、Unicode/正反斜杠路径、长路径拒绝、成功缓存、缺字体/API、寄存器/标志/栈保持，共 106 次受控 API 调用。原生探针使用真实 PE 映射和相同新增代码，仅在探针内存中将原 Qt 初始化尾目标替换为 ret，避免执行 UE 构造器；随后由原生 QuickTime 绘制。这项受控检查只验证加载代码，不替代实际游戏验收；后续实际游戏内字幕显示已确认，完整播放控制路径仍待测试。

## 重建

先按 BUILDING.md 构建普通资源及完整 `build/formal-game` 副本。源字体可从上述固定 commit 获取，SHA-256 必须匹配记录；不依赖系统 SimHei 的字体文件。

```powershell
python -m tools.font.build_subset --source "SOURCE_FONT.ttf" --translations locales/zh-CN/fmv --out build/font-subset/WotFmv.ttf --family WotFmv --license assets/fonts/SourceHanSans-OFL.txt --code-page-mask 0x40001
python -m tools.build.build_local_font_poc build --source-game build/formal-game --original-game "GAME" --font build/font-subset/WotFmv.ttf --config locales/zh-CN/fmv/local-font-poc.json --out build/local-font-game --locale zh-CN
python -m tools.build.build_local_font_poc verify --input build/local-font-game
```

源字体路径、字体名、字符扫描与子集参数分层；通用构建器不依赖私人目录。Game 表示指纹匹配的原版游戏目录。输出必须为新目录，原版和正式副本均不改动。

合成测试：`python -m unittest discover -s tests`。额外 CPU 验证需要 `unicorn==2.1.4`；原生探针需 Windows .NET Framework 4 的 x86 csc、系统 QuickTime，源码位于 tools/validate/local_font_native.cs 与 quicktime_player.cs。不在补丁中分发 QuickTime。

## 游戏内验收与回滚

运行 `build/local-font-game/LAUNCH_GAME.ps1`，从“新游戏”开始完整通关测试。只测 1920×1080；检查各章节字幕、FMV 配音同步与跳过/重播/返回、设置保存、存档/读档、切图、战斗和长文本布局。该目录具有独立 Save；此前测试目录保持不变。问题记录应包含关卡、操作步骤、截图，字幕问题另记对应台词或视频时间。

```powershell
python -m tools.build.build_local_font_poc rollback --input build/local-font-game --out build/local-font-restored-files
```

回滚输出原版文件到另一份新副本，不撤销当前完整测试目录。MODIFIED_FILE.dll、DIFF_FILE.json、VERIFICATION.txt 与可执行 ROLLBACK.sh 位于实验游戏根目录。字体实验尚未合入默认构建，也尚未制作为覆盖式发布包。

## 游戏运行后的配置校验

默认校验仍要求所有构建文件哈希一致。游戏会保存 System/WoT.ini 与 System/User.ini；运行后可显式添加 `--allow-runtime-config`，仅允许这两份未被补丁修改的配置变化，并报告文件名。MOV、DLL、字体及其他资源仍严格校验；不覆盖配置或存档。回滚命令也支持该参数，仍只将原版 MOV/DLL 输出到新的恢复目录。

```powershell
python -m tools.build.build_local_font_poc verify --input build/local-font-game --allow-runtime-config
python -m tools.build.build_local_font_poc rollback --input build/local-font-game --out build/local-font-restored-files --allow-runtime-config
```
