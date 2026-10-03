# 技术实现与证据层级

## 已验证事实

本地研究对象的 WOT.u 为 UE 包版本 68；原版 SHA-256、大小见 profiles/gog-v68.json。
它有 5550 个名称、8377 个导出，大小 9,588,318 字节。
研究读取 128 个 UE 包（版本61/63/68）未出现包表解析错误。
工具使用标准 UE1 名称/导入/导出、compact index、Font/Texture 结构，而非从零发明文本格式。
本地未找到需要修改程序才能显示中文的证据。

### 1. 文本存储与范围

|内容|位置|
|---|---|
|主菜单 / Options / 帮助 / HUD / 任务目标|System/WoT.int 的对应类节；包内 localized 默认值与部分字面量仍在 WOT.u|
|New Game|WoT.int → menuSinglePlayer.MenuList[2]，不是主菜单第一层|
|Inventory 法器说明|Angreal.int；兵种 WoTPawns.int；陷阱 WoTTraps.int|
|语音字幕|WoTsubtitles.int，Sound 包名为节、对象名为 key|
|地图实例剧情/锁门/教程提示|Maps/*.wot 的属性；不是 .unr。地图 localization 待单独验证|
|浏览器 / 原生窗口 / 渲染器配置|WoTBrowser/UBrowser/Core/Window/Engine/D3DDrv 等 .int|
|图形文字 / 预渲染字幕|Texture 资源与 Movies/*.mov，不能靠 .int 统一覆盖|

扫描 29 个 .int 得到 2345 条键值（含注册元数据/空值），并不都是待翻正文。
地图只读分析得到579个非空字符串属性，正文候选含203 Messages、48 Title、8 Content、7 Message；
URL/路径等需排除。脚本硬编码候选129处仍须人工筛选。
BattleScoreBoard.DrawHeader 的 Game Type/Map Title/Author/Ideal Player Load 字面量已定位，
未在当前 PoC 改动。不要宣称四个资源覆盖全游戏。

### 2. 文件格式与编码

`.int` 是 INI 类 localization 配置，不只有字符串表，还含 `[Public] Object/Preferences` 元数据。
早期 UE 包名称字符串用 compact 有符号长度：正值为字节字符串，负值为 UTF-16 长度。
原版 .int 多为 ASCII；高字节英文按 cp1252 解码是当前已匹配内容的假定。
实际原生测试 UTF-16 LE BOM 能显示中文；UTF-8 作为工程数据编码，不冒充游戏读入已验证编码。
无须 CP936、GBK、非 Unicode 区域设置或双字节引擎补丁。

### 3. 字体、映射、metrics 与渲染

游戏 Canvas 主要读取 WOT.u 内 Font 对象；并非游戏菜单走 Windows GDI。
UWindowFonts.utx 也含 Font，但不等于 WOT 所有界面的字体。
Font 页引用 Texture 对象，矩形 `(x,y,w,h)` 各为 little-endian int32。
字符由原生路径按 `codepoint // CharactersPerPage` 和余数索引。
原字体 CPP256，仅有一页，中文字体映射缺失，UTF-16 `.int` 单独替换时中文空白而 ASCII 正常。

新资源 CPP64；保留 Page0 的256条原记录，并加3个指向同一原贴图的64记录页，
确保原字符0–255语义不变。高 Unicode 页生成64槽记录；不用修改字符索引函数。
当前只处理 U+0100..U+FFFF 中实际用字，不能处理代理对、动态完整Unicode或复杂连写。

六个字体来自游戏 profile：Reg14=14、Reg30=30、Reg14_S=7、Reg30_S=15、Ita14=14、Reg08=8。
取消以320x240为目的的12px默认修改，保持游戏原字号，不改符号/按键专用 Font。
斜体适配器对 Ita14 使用0.22剪切、扩宽矩形；其他字体正体方格字宽。
生成器依 locale 的 baseline_anchor 对齐，不再把“汉”硬编码在核心；保留标点纵向bearing。
不是完整 OpenType shaping/kerning/比例字宽实现。支持其他语言应选择字体并重新验收。

Texture 使用原调色板的 P8 像素；透明索引与原字体共享，抗锯齿映射到游戏金色调色板。
单 mip atlas ≤256×256，自动分页/多atlas；超过此限而不补 mip 链曾实机崩溃。
详见 [格式](docs/FILE_FORMATS.md) 与 [坑点](docs/PITFALLS.md)。

### 4. 字幕结构、长度与覆盖

WOTPlayer.ClientHearSound → bSubtitles → 声音外层包名/对象名 →
Localize(package, sound, WOTSubtitles, true) → SubtitleMessage → BaseHUD → Canvas。
字幕单槽可被后续声音覆盖，部分声音路径过滤 WOT/Angreal；不能声称所有发声都是字幕。
原文件897键、80非空、817空；567键可与该安装的 Sound 对象精确匹配。
Tes_01 对应 DialogA.Tes_01，教学开始自然触发；显示时间按文本 Len 而非固定声轨时间码。
原句350字符，PoC90字符时补260个引号内ASCII空格；不修改音频/脚本/时长公式。
统计使用字符/UTF-16代码单元而非编码字节；BMP约束下两者数值一致。

### 5. 封包与相关字段

生成器复制原包、追加 Font/Texture 数据与名称/导出表；更新表偏移、计数和最后一代 generation计数。
Texture lazy-end 是绝对文件偏移，必须与像素数组一起计算；仅改纹理像素不够。
保留原 GUID、imports、原名称字节/flags；其他8371原导出记录与正文逐字节验证。
受选Font导出 size/offset、页数/纹理引用、CPP、纹理尺寸、像素量/lazy-end及包表须同步。
重读输出验证所有原Latin映射及新增glyph矩形、纹理引用、绝对lazy-end。
详见 docs/FILE_FORMATS.md；不依赖纯手工十六进制。

### 6. EXE / DLL / hooks

**无 EXE/DLL 修改位置，无注入、无 hook。** 原生反汇编研究用于确认机制，不是发布补丁偏移。
当资源方案已可行时不引入引擎补丁。src/runtime 当前只是职责边界说明，不虚构运行时代码。
差分安装修改四个资源并可回滚，原程序、地图、存档格式、画质和GOG启动器不变。

## 高可信推断

同样的 BMP 字符映射技术可用于繁体、假名及韩文，只要字体覆盖、槽位容量与UI宽度允许。
这是资源结构与合成测试支持的推断，不是完整游戏其他语言运行结果。
标准 localization 可以减少语言专用改包；本地曾实测 Language=zht + WoT.zht 菜单覆盖。
当前工程入口先重建 .int 以延续多界面 PoC，不把内部三字母扩展名当成 BCP47 locale。

## 待验证 / 未实现

- 独立 locale 扩展覆盖全部包、地图实例导出/回退、批量资源注册元数据子字段。
- 存档加载/长时间战斗/多关卡/联网/全中文计分板、Windows10与11分别验收。
- 完整字幕文本恢复、社区补全版本来源/权限/映射；原空键不能凭名恢复对白。
- 视频原生播放器是否能正确选轨/读入新增中文 text track；外挂SRT未证明支持。
- 更大atlas mip链、动态字体、复杂shaping、UI高DPI縮放。

已验证和未验证不得混写；最新工程与分辨率证据见 docs/qa.md。

## 主菜单 / Controls PoC 补充

原脚本研究确认 menuMain 的第3项Controls实际进入 menuOptions，其标题为CONTROLS，
因此 options 测试视图是操作设置页，而非图形/声音Hardware页。
menuOptions先按Default.MenuList画左列，再把同一数组改为运行时bool/数字等值画右列；
不能把右列TRUE/FALSE误认成.int标签未回填。当前只改左列的前三项、标题和第一条帮助。
新校验把source_sha256/source_length/tokens与实际原文逐项对照，缺条目或元数据不一致在回填前失败。

## 工作区迁移记录

复用本项目dee6e61已验证工具链，而非重做汉化。旧游戏根目录phase1–5研究归档于docs/research/game-root；全文路径和来源散列见docs/migration-manifest.json。历史低分辨率、12px小字和277/277结论只适用于当时实验；当前profile/QA仍以1080p和原始7/8px小号配置为准，4K不适配。生产构建不依赖旧backup/work/研究截图。迁移后的离线重建不等同本轮实机验收。详见docs/MIGRATION_AUDIT.md。

## Controls 完整标签/帮助草稿（离线）

WoT.int/menuOptions含MenuTitle、MenuList[1..11]、HelpMessage[1..11]共23个独立localized字段；现以源ID/SHA/长度为地址全部回填。新增18条不涉及硬件页、按键alias、右侧布尔/数值、游戏配置或脚本逻辑。仅在副本重建与回滚验证，未新增本轮实机证据；选中第2..11行后显示各帮助的宽度/换行仍待1080p优先QA。
