# 主菜单与 Controls：第二批小范围 PoC

日期：2026-10-03。当前仍处于技术验证与工具链阶段，不是完整汉化或玩家 Release。

## 变更

- 在原有 7 条草稿基础上新增 12 条，共 19 条；全部保留原文件、section、key、occurrence、原文 SHA-256、长度和控制符元数据。
- `WoT.int / menuMain / MenuList[1..7]`：单人游戏、多人游戏、操作设置、硬件设置、重播开场、制作人员、退出游戏。
- `WoT.int / menuOptions`：标题、首三项标签和第一条帮助文字。其余 Controls 项目和帮助仍为英文。
- 原有新游戏、帮助、物品说明和教学字幕不扩展为批量翻译。
- 通用回填器新增全表只读源元数据预检：ID、原文散列、字符长度、控制符必须与实际原版匹配，包括尚未翻译的条目；在输出写入之前完成。带 `--game-dir` 的 validate 同样检查这些项目。
- 运行时探针增加 `main` 与 `options` 视图。语言无关 QA 策略现在覆盖 5 个视图，离线计划为 3 种分辨率 × 5 视图 × 原/改资源，共 30 项；计划不代表全部已执行。

## 该阶段实际验证

合成测试 42 项通过（新增 7 项源预检测试）。validate 返回 19 条、0 条未翻译、19 条待审稿；这个数字只针对 PoC 表，不是整个游戏的翻译进度。严格发布校验仍应拒绝待审稿。

构建使用原版 GOG 指纹文件和本机自行提供的字体：每种字体 162 个新增字符，6 个字体对象、8 个新增贴图；8371 个其他原始 export 不变，原 Latin 映射、Page0 和 bytecode 保留。四个生成资源都通过 delta 回放与独立副本回滚；原安装的这四个源资源散列保持不变。

|真实引擎模式|资源|视图|原生退出|人工观察|
|---|---|---|---|---|
|1920×1080|原版|main|0|原英文主菜单对照|
|1920×1080|原版|options|0|原 CONTROLS 页面与右侧值对照|
|1920×1080|修改版|main|0|七项中文可见，代表帧未见乱码、空白或裁切|
|1920×1080|修改版|options|0|中文标题、首三项与第一条帮助可见，代表帧未见裁切|
|1920×1080|修改版|inventory|0|标题、正文、斜体引用及 F2 提示回归可见|
|1920×1080|修改版|subtitle|0|约 21 秒中文可见，约 37 秒已消失|

该阶段只重新执行上述六项 1080p 探针，没有重新执行 1366/1440p，也没有 4K/320×240 测试。历史矩阵见 [qa.md](qa.md)，历史结果保留原样。

截图来自 3840×2160 桌面捕获；引擎 best-match 日志确认为 1920×1080，因此截图面积不等于游戏内部渲染分辨率。自动探针的 `visual_review=pending` 只表示它未自动判断文字；上表是随后人工检查代表帧的结果，不是逐帧 OCR，也不是字幕音频精确同步验收。

## Controls 的结构发现

`menuMain` 第三项进入 `menuOptions`，原标题是 CONTROLS；探针中的 `options` 指操作设置，不是第四项 Hardware 的画质/音频设置。

脚本路径与原/改截图相互支持：`DrawMenu` 先用 `Default.MenuList` 绘制左侧标签，再给同名数组赋运行时布尔/数字值用于右侧列。因此右侧 True/False 和灵敏度数值继续显示英文/数字，不属于 `.int` 回填失败。该阶段没有改变设置值或该逻辑；动态布尔本地化仍待独立研究。

## 重现

在仓库根目录执行，GAME 与 FONT 通过构建参数提供：

```powershell
python build.py test
python build.py validate --locale zh-CN --game-dir "GAME" --font "FONT"
python build.py --locale zh-CN --game-dir "GAME" --font "FONT" --out build/menu-poc
python -m tools.validate.integration --game-dir "GAME" --build-dir build/menu-poc --out build/menu-rollback
python -m tools.validate.runtime --game-dir "GAME" --runtime-dir build/runtime --build-dir build/menu-poc --out build/menu-poc/qa --resolution 1920x1080 --view main
python -m tools.validate.runtime --game-dir "GAME" --runtime-dir build/runtime --build-dir build/menu-poc --out build/menu-poc/qa --resolution 1920x1080 --view options
```

运行时命令会启动隔离副本；加 `--original` 得到原资源对照。`main` 输入 Escape；`options` 输入 Escape、Down、Down、Enter。探针只操作自身游戏进程。

结构结果与本地证据文件散列见 [menu-poc-results.json](menu-poc-results.json)。截图、完整游戏包、Windows 字体生成物及补丁 payload 留在被忽略的 build/，不进入源码 Git。

## 剩余事项

- 19 条译文尚待术语/措辞审稿；Controls 其他标签、帮助、动态布尔值尚未汉化。
- 推荐 1080p；4K 固定像素 UI 偏小作为已知问题，不继续适配。
- 没有 EXE/DLL 改动、hook、地图/玩法变更；没有全剧情、存档/切图/战斗稳定性验收。
- 字体公开分发仍需明确的再分发许可；该阶段本机字体只用于验证。
