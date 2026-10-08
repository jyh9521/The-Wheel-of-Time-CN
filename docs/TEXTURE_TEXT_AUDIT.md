# 图片文字只读审计（2026-10-04）

> 历史开发与测试记录：下述测试数、待办、验收状态和产物名称对应记录时的构建，不代表正式版当前状态。v1.0 已完成完整通关测试且未发现补丁问题；正式文件为 `WoT-CN-v1.0.exe`。当前说明见 [项目主页](../README.md)、[安装说明](PORTABLE_INSTALLER.md)和[显示限制](KNOWN_ISSUES.md)。

## 范围与结论

检查本地 GOG 原版 `Textures/*.utx`、`System/*.u`、`Maps/*.wot`：36 个贴图包、20 个脚本/资源包、45 个地图，共 101 个包。地图实际扩展名是 `.wot`，该批地图没有直接导出的 Texture 对象，但会引用外部贴图。

3581 个 Texture 导出均成功解码为首级 mip 的 RGB 预览；其中 65 个名称识别为字体页，未纳入图片英文检查。已逐页查看其余 3516 张贴图的 55 张总览，并放大重点候选。另有 83 个程序纹理子类（WetTexture 43、FireTexture 32、IceTexture 5、WaveTexture 3）仅登记，未模拟动态效果。

**确实存在烘焙在图片中的英文，现有 `.int` 中文译文不会改变它们。** 缩略图筛查不是逐像素 OCR，也不是全流程游戏验收；小字可能仍有遗漏。全部 101 个源包的 SHA-256 在检查结束时一致。没有启动游戏，没有修改原包、地图或现有汉化运行目录。

## 已确认英文图像

| 包 / 对象路径 | 内容 | 静态引用证据 | 后续处理 |
| --- | --- | --- | --- |
| `AesSedaiT.utx / Ornament.TpstWall1880a` | 挂毯上缘哥特字体英文，256×256 | `Arena_03.wot` 导入该贴图 | 场景图片汉化候选；先完整辨读 |
| `AesSedaiT.utx / Ornament.TpstWall1880b` | 挂毯下缘哥特字体英文，256×512 | `Arena_03.wot` 导入该贴图 | 与上一贴图可能构成同一挂毯，属于待验证拼接关系 |
| `WOT.u / UI.I_Load`、`UI.M_Load` | `Load` | `LoadInventory` 脚本导入这对纹理 | 城堡编辑功能的图片按钮候选 |
| `WOT.u / UI.I_Play`、`UI.M_Play` | `Play` | `PlayInventory` 脚本导入这对纹理 | 同上 |
| `WOT.u / UI.I_Roam`、`UI.M_Roam` | `Roam` | `RoamInventory` 脚本导入这对纹理 | 同上，翻译前确认该模式含义 |
| `WOT.u / UI.I_Save`、`UI.M_Save` | `Save` | `SaveInventory` 脚本导入这对纹理 | 同上 |

共两张场景挂毯纹理与八张按钮纹理。挂毯文字因源分辨率和字体而尚未完整转录，不凭零散辨读结果编造整句。Inventory 脚本的注释把这些类与 Citadel Editor HUD 联系起来，但注释可能遗留，实际入口和显示仍待验证。

导入表证明资源关联，不证明它在某次游玩中一定可见。

## 含细小字迹的候选（不等同已恢复英文原文）

| 对象 | 可见内容 | 地图关联 |
| --- | --- | --- |
| `WoTDecorations.u / Skins.JOpenBookA0`、`Skins.JOpenBookA1` | 128×128 的书页/封面细小文字与图案 | `OpenBookA` 对象放置于 `Battle2_04`、`Mission_05a`、`Mission_05b`、`Mission_12b`、`Mission_17` |
| `ScottT.utx / PaprPapr1131`、`PaprPapr1132` | 手写纸张，字迹细小 | `Mission_05a.wot`、`Mission_17.wot` 导入 |
| `ScottT.utx / PaprPapr1133` | 装饰手稿文字；语言尚未确认，不直接当作英文 | 同上 |

`PaprPapr1134` 是空白旧纸，`PaprPapr1135` 是建筑草图；未发现需要翻译的普通英文句子。`JamesT.utx / WoodSign3100c` 名称含 Sign，但图片只有红色叉号，不是英文告示。

## 标志、品牌和编辑器标记

- `UBrowser.u / Icons.BannerAd` 包含 `UNREAL TOURNAMENT` 标志。`UBrowserBannerAd` 有绘制调用，但不能由基础类存在推断本游戏实际展示；先保留品牌图像。
- `WoTDecorations.u / Skins.JCylinder0` 包含 Mountain Dew 包装英文；原脚本把它设为 Cylinder 网格的默认贴图。七个地图存在 Cylinder 实例，但实例可能覆盖 Skin/Multiskins，**尚未证明游戏中会显示该包装**，不把普通圆柱实例全部称为饮料罐。
- `MatthiasT.utx / clan`、`ocrana` 是带 `OCRANA` 标志的图像。`Mission_07a.wot` 导入 `clan`；`ocrana` 未在该批地图导入中找到。名称不作新专有名词翻译。
- DeveloperT、ForsakenT、ScottT 中有 `CLIP / ZONE / SKYBOX / climb` 类型标记；Editor.u 有 `BAD SIZE`，Legend.u 有 `AT / ST / SST`，WOT.u 有 `TH` 编辑图标。属于开发/编辑用途候选，不纳入剧情文案，不更改技术标识。
- Ways/TheWays 的符文、纹章和花纹不直接判为英文。

## 可复现检查

依赖现有 Python 环境与 Pillow；从仓库根目录运行：

```powershell
python -X utf8 -m tools.extract.texture_audit --game-dir "C:/GOG Games/The Wheel of Time" --out build/texture-audit
python -X utf8 -m unittest discover -s tests -p test_texture_audit.py
```

输出目录必须位于原版游戏目录之外。`INVENTORY.json` 保存文件名、大小、版本、SHA-256、对象路径、首级 mip 尺寸、解码状态和预览索引；`MAP_REFERENCES.json` 保存地图 Texture/Class 导入及导出对象。`images/` 保存原尺寸预览，`overview_*.jpg` 是总览，`candidates_*.jpg` 仅按名称辅助筛选；实际挂毯不在名称关键词候选中，不能只看候选表。

图片、总览和原包均不提交到源码仓库，工具与报告可提交。导出工具为只读，没有图片回填功能。

## 按钮汉化范围与实现

图片文字处理范围限定为按钮汉化。挂毯、书页、纸张、品牌和标志保留原样；上面的审计结果保留作研究资料，不再安排挂毯和纸张的翻译。

按钮汉化只将 `UI.I_*` 与 `UI.M_*` 的 Load/Play/Roam/Save 八张纹理改为“载入/游玩/漫游/保存”。`Roam` 在玩家脚本中对应 `CitadelRoamMode`，采用漫游而非普通剧情模式名称。中文标签数据位于 `locales/zh-CN/texture-labels.json`；通用构建器为 `tools/font/build_texture_labels.py`，原资源对象指纹为 `profiles/texture-labels.json`。

采用固定大小 P8 像素回填：保留64×64尺寸、原调色板、单级mip、对象编号、包表和文字区域外像素；文字面板背景由上下无字石纹行插值重建，中文由开发者自行提供的字体确定性栅格化后映射回原调色板。没有重新绘制整张按钮，没有修改共享调色板、脚本逻辑、地图或EXE/DLL。字体依赖及发布许可仍遵循 LICENSING.md。

默认构建已接入标签阶段；输出 `TEXTURE_LABEL_DIFF.json` 和八张原尺寸预览。静态范围验证确认旧中文版本与新版本只有这八个纹理对象发生变化。独立副本通过六文件差分安装/核验/回滚，源游戏不变；游戏内按钮布局、状态切换及操作仍待1080P实测，这一阶段只做了离线验证，未运行游戏。
