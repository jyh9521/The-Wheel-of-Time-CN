# 游戏内 FMV 字幕最小验证（2026-10-05）

## 先验证游戏，再翻译全片

独立播放器的中文显示已经确认，但它不代表游戏原播放器能够显示。
我先暂停整片 FMV 翻译，准备真正使用 WoT.exe → WinDrv.PlayMovie 的隔离测试入口。
没有自动启动游戏，游戏内验收仍以实际画面为准。

## 本次修改及原因

原版 WinDrv.dll 的完整 SHA-256 为
`43076c7c4492654fb71fbeb7c4a83d4c870f7db0ad7421ada75a7912a06af964`，大小 327680。
PlayMovie 在 RVA `0xFC97` 用 `83 C7 FD`（add edi,-3）把语言索引转换为文字轨索引。
int 索引 0 因而得到 -3，不匹配任何文字轨。
我仅在**隔离 DLL 副本**将这三字节改为 `33 FF 90`（xor edi,edi; nop），
让文字轨选择固定为第一轨。紧接着的原始代码将此值保存为字幕选择索引。
原音轨选择循环在更早的地址执行，相关指令不变；Language=int 和 LanguageExt 顺序也不变。

新 DLL SHA-256 为
`527dbb216ee20b339db3b3b1c929642a8fcb64b790df4e1bfed6ab6f98df83ef`。
源版检查、RVA→文件位置映射、预期指令检查、修改后哈希和回滚均有工具实现。
本版 RVA 恰与文件位置相同，不假定以后所有版本都如此。

这不是中文字符串写入 DLL，也不是新增 DLL 注入。真正的字幕仍在 MOV 的原生 text 轨。
技术需求是让字幕与配音语言独立选择，其他语言也可以复用；本次 PoC 固定第一轨，
没有做成发布版的语言选择界面或总开关。它对这个测试副本的其他有文字轨视频同样生效，
因此不能据此发布全游戏补丁。

## 隔离范围

- 输入可以是原版游戏目录，或已经完成现有汉化安装的独立目录。
- 我本次使用 build/runtime，保留已有菜单/字幕/字体成果。
- 工具将 System、Maps、Textures、Sounds、Music、Movies 做物理复制，不使用共享硬链接。
- 不复制存档目录，测试目录使用自己的空 Save。
- 本次复制 257 文件，只有 System/WinDrv.dll、Movies/Intro.mov、System/WoT.ini 三个批准文件改变。
- 254 个其他文件与输入逐字节一致；没有修改源目录。
- 配置只将窗口模式也统一为 1920×1080；全屏 1080p 和英文语言设置保持。
- Intro.mov 仍只在第 1–7 秒有一句中文测试，其他样本不改。音视频数据未重编码。
- 原 DLL、MOV 和配置副本位于生成目录的 .fmv-baseline；全部生成物受 .gitignore 排除。

## 可重建准备

```powershell
python -m tools.build.build_fmv_game_probe build --source "GAME_OR_LOCALIZED_COPY" --locale zh-CN --out build/fmv-game-qa
```

需要项目现有 Python/pefile 依赖；字形由用户系统的候选字体提供。
工具不依赖旧研究目录、独立预览播放器 EXE 或已经修改的 MOV：从指定源目录的
原版 WinDrv.dll 和 Intro.mov 重新生成两项修改。必须使用全新输出目录；不覆盖旧实验或未知版本。
工程源码为 src/patch/movie_player.py 和 tools/build/build_fmv_game_probe.py；
版本门禁在 profiles/fmv-player.json，中文样本与字体/编码语言配置仍在 locales/zh-CN。

## 我的游戏验收步骤

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "FULL_REPO_PATH/build/fmv-game-qa/LAUNCH_GAME.ps1"
```

入口校验隔离 DLL 和 MOV 哈希，然后在隔离 System 目录运行 `.\WoT.exe Entry`。
它不会调用独立 QuickTime 预览程序。

1. 在主菜单选择 **重播开场**（第五项；原版对应 Replay Intro）。
2. 第 1–7 秒观察“中文字幕显示测试：时光之轮”，记录是否可见、乱码、裁切及位置。
3. 确认仍是英文配音。随后出现原轨外文是预期现象，实验没有翻译整部视频。
4. 用游戏原来的空格暂停/继续、Esc 跳过，确认返回菜单正常；再次重播检查重复进入。
5. 若没有字幕，截图或记录现象，并保留隔离 System/WoT.log；不改原游戏目录尝试修复。

菜单原脚本 menuMain.ProcessSelection 的第 5 项先调用 `MP3 STOP`，再调用
`PlayMovie Intro.mov`；WinDrv 原事件循环检查空格与 Esc。本次没有改这些调用/输入路径。

## 已验证与待验证

**已验证（离线）**：完整源哈希门禁；DLL 只改变三字节；新指令的十组 x86 CPU 模拟；
原版/修改/回滚索引检查；独立 DLL/MOV 回滚；257 项资源复制范围；启动脚本解析；179 项测试。
回滚副本恢复原 DLL 完整 SHA 和原 -3,-2,-1,0,1 文字索引映射，游戏测试目录仍保持修改状态。

**待验证（游戏）**：WinDrv 真实启用轨道后的字幕绘制、1080p 实际视频画面布局、配音、
暂停、跳过、菜单恢复和重复播放。独立预览已确认中文，但本报告不据此宣称游戏内通过。
游戏验收通过后再设计可配置字幕选择、处理完整时轴与正式 FMV 翻译。

四项本地事务记录为 MODIFIED_FILE.dll、DIFF_FILE.json、VERIFICATION.txt、可执行 ROLLBACK.sh。
回滚脚本只输出新的 DLL 验证副本，不写回源游戏或静默改变已准备的测试入口。
原生 MOV 结构与旧 QuickTime Unicode 编码问题见 [FMV 研究](FMV_SUBTITLES.md)。
# 正式测试入口更新（2026-10-05）

我已在游戏内确认最小中文样本可以显示。14 段剧情视频的完整字幕已经制作并导入 `build/formal-game`，新的入口是该目录的 LAUNCH_GAME.ps1；单句 `build/fmv-game-qa` 保留为实验记录，不作为正式测试入口。完整范围、当前待确认项和构建命令见 [FMV_FULL_QA.md](FMV_FULL_QA.md)。下文为最小验证阶段的历史记录。
