# 构建与复现

## 环境

工具：Python **3.14**（本地验证 3.14.2），Pillow 12.2.0、fonttools 4.63.0。
Windows 10/11 上执行原版游戏实机 QA；Linux CI 只跑合成测试及译文校验。
不使用 Python `-O`，资源完整性断言必须启用。
无需 Unreal SDK、编译器、QuickTime 重编码工具或预编译补丁 DLL。

## 用户自行提供的输入

1. 一份未修改的 GOG 安装；4 个必需资源见 `profiles/gog-v68.json`：
   `System/WOT.u`、`WoT.int`、`WoTsubtitles.int`、`Angreal.int`。
   文本提取可额外读取 System 里的其他 `.int`；完整游戏副本仅实机 QA 使用。
2. 一份允许用于所选用途、覆盖译文字符的 TTF/OTF/TTC 字体；通过 `--font` 指定。
   TTC 子字体索引来自 locale 配置。字体不捆绑。
   本地 PoC 用 Windows 自带字体验证，**不是再分发字体授权**。
   若用其他字体，原资源与字符映射仍可重建，但像素及输出散列会改变；须重新验收。
3. 原版版本、大小、SHA-256 必须匹配 profile；未知版本首先研究并新增 profile，不能绕过检查。

## 全新克隆 → 构建

```powershell
git clone https://github.com/jyh9521/The-Wheel-of-Time-CN.git
cd The-Wheel-of-Time-CN
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python build.py test
.venv/Scripts/python build.py validate --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf"
.venv/Scripts/python build.py --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf"
```

字体与游戏路径均由使用者提供；不依赖 `work/phase*`、作者备份或手改资源。
输出必须在原安装之外，默认 `build/<locale>/`，可通过 `--out` 指定。
生产构建前运行 `validate --strict`：当前十九条均为 draft，因此严格验收应失败，不能伪装已审校。

## 产物

- `resources/System/`：仅发生变化的资源副本；本地使用，不提交完整游戏资源。
- `FONT_DIFF.json` + atlas PNG：字形映射、矩形/字宽、字体改动与预览。
- `PATCH.json`：版本化 COPY/LITERAL 差分，安装前后 SHA-256 校验。
- `BUILD_REPORT.json`：原/改文件大小与散列、字体文件散列、依赖版本、语言配置/译文散列、字幕补偿。
- `build/qa/`：可选的原生运行日志、截图和记录；生成物不推送。

差分和字库仍可能包含字体衍生数据/游戏结构数据，**本地构建不自动批准再分发**。
发布前选择可再分发字体、审查差分、添加许可与玩家说明。
目前没有预编译二进制工具或正式安装包；所有工具都是 Python 源码。

## 可重复构建与回滚

同一 profile、译文、配置、字体 SHA-256/TTC 索引、Python 与依赖版本，应产生相同资源和差分。
构建记录保存这些输入身份；资源中不嵌入私人路径或运行时间。

```powershell
python build.py --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf" --out build/repeat
python -m tools.validate.integration --game-dir "D:/GOG Games/The Wheel of Time" --build-dir build/zh-CN --out build/rollback-test
```

集成测试在独立四资源副本中执行原始读取、差分安装、逐字节校验、恢复，并保留已构建资源不变。
不启动游戏。安装器会拒绝用户随后编辑过的资源，避免覆盖修改。
回滚只能证明资源恢复，不能代替真实运行、存档/切图/战斗验收。

## 文本工作流

```powershell
python build.py extract --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --out out/extract
# 编辑 strings.csv 的 translation 列；同源重复行可参考 duplicates.json，不能丢失各 ID。
python -m tools.import.catalog out/extract/strings.csv out/translation.json
# 评审后将所选条目并入 locales/<locale>/strings.json，不把完整原文导出文件提交仓库。
python build.py validate --locale zh-CN --font "D:/Fonts/source-font.ttf"
python build.py --locale zh-CN --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.ttf"
```

## 实机 QA（必须显式运行）

自行复制完整原版为独立 `build/runtime/`；脚本检查其不是源安装或其子目录。

```powershell
python -m tools.validate.runtime --game-dir "D:/GOG Games/The Wheel of Time" --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view menu
```

当前 QA 分辨率：1366x768、1920x1080、2560x1440；`--resolution` 默认1920x1080。
4K仅保留既有测试证据和已知问题，不再进入主动测试/适配矩阵。
可先离线生成原/改资源对照计划，不会启动游戏：

```powershell
python -m tools.validate.qa_policy --locale zh-CN --out build/qa-plan.json
```

矩阵与推荐值维护在 `profiles/qa-policy.json`，对所有语言共用；计划以1080p优先。
视图：main（主菜单）、menu（单人菜单）、options（Controls）、inventory、subtitle；`--original` 跑未改资源对照。
脚本只发送键盘到前台的自己启动窗口，关闭自己的主窗口；测试时保持窗口前台，不操作其他应用。
日志必须出现相应 `Best-match display mode`；JSON 的窗口截图尺寸仅表示桌面捕获面积。
画面是否有字、裁切、换行、标点和清晰度必须人工观察。
