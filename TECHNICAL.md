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
生成器使用全部实际用字的共同bbox保留完整源墨迹与标点纵向bearing，再按共同比例适配原版行高；旧baseline_anchor仅兼容覆盖检查，不再控制裁剪边界。
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
保留原 GUID、imports、原名称字节/flags；字体生成阶段其他8371原导出记录与正文逐字节验证；后续字幕坐标补丁单独修改一个Function字段，最终其他8370导出逐字节保持。
受选Font导出 size/offset、页数/纹理引用、CPP、纹理尺寸、像素量/lazy-end及包表须同步。Font生成阶段的bytecode_unchanged不代表字幕位置修复后的最终包；BUILD_REPORT另列resource_edits。
重读输出验证所有原Latin映射及新增glyph矩形、纹理引用、绝对lazy-end。
详见 docs/FILE_FORMATS.md；不依赖纯手工十六进制。

### 6. EXE / DLL / hooks

早期资源阶段无 EXE/DLL 修改；当前新增 Window.dll 的版本守卫显示适配，见本文末节。仍无 EXE 修改或进程注入。此前只读反汇编记录作为历史证据保留。
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

复用本项目dee6e61已验证工具链，而非重做汉化。旧游戏根目录phase1–5研究归档于docs/research/game-root；全文路径和来源散列见docs/migration-manifest.json。历史低分辨率、12px小字和277/277结论只适用于当时实验；当前profile/QA仍以1080p和原始7/8px小号配置为准，4K不适配。生产构建不依赖旧backup/work/研究截图。迁移后的离线重建不等同该阶段实机验收。详见docs/MIGRATION_AUDIT.md。

## Controls 完整标签/帮助草稿（离线）

WoT.int/menuOptions含MenuTitle、MenuList[1..11]、HelpMessage[1..11]共23个独立localized字段；现以源ID/SHA/长度为地址全部回填。新增18条不涉及硬件页、按键alias、右侧布尔/数值、游戏配置或脚本逻辑。仅在副本重建与回滚验证，未新增该阶段实机证据；选中第2..11行后显示各帮助的宽度/换行仍待1080p优先QA。

## Controls 后续实机显示验收（2026-10-03）

上述离线阶段的待验项已补充有限实机证据：原/改各在1366×768、1920×1080、2560×1440运行一次，每次选中11行、正常退出0。1080p修改版11条帮助逐帧人工审查，其他两种分辨率各审查第1/2/3/5/10/11行；当前文本未见乱码、空白或截断。右侧动态值保留原文，不改脚本、字体或译文；这不证明全部菜单、存档、战斗及Windows版本组合。可配置只读菜单sweep与单帧探针共存；自动记录仍保留visual_review=pending，人工结论另存。详见[验收方法](docs/CONTROLS_QA.md)与[散列索引](docs/CONTROLS_QA_RESULTS.json)。

## 字形边界与字幕上边距修复（2026-10-03）

已验证：单“汉”bbox不是全字库边界。源字体14px时“汉”top=4、“重”top=2，旧14×14栅格在渲染前裁掉重顶部。新方案先计算全部实际使用字符的共同bearing/边界，并与64px边框参考画布比对源墨迹，再Lanczos整体适配原槽位高度；不是逐字裁边，也不是像素完全无损变换。保留ASCII原始映射/位图与原行高，防止双列/StrLen单行判定回归。

字幕另有资源内显示字段变更：WOT.u/BaseHUD.DrawMessages，Function导出5095、2614字节，body+1979（原包绝对992669）float32-le 0→24；最终8370个其他原导出不变。原脚本的ScaleValY(24)仍保留，当前SetPos是固定24原生像素，不声称使用该缩放变量；仅1080p验收。字段工具先检查原游戏hash、目标Function完整hash、上下文、原始值，未知版本失败；等长修改不动跳转、TOC、函数长度、计时或玩法。EXE/DLL仍无改动，但不能再声称最终资源全部bytecode不变。方法与证据见[GLYPH_LAYOUT_FIX.md](docs/GLYPH_LAYOUT_FIX.md)。

## 全字幕专项进展（2026-10-03）

当前49条草稿；保留原37条，补译教程Tes_02～Tes_13。教程原版80条英文均非空，但中文仅13/80；其余对白817空键须分类恢复，不能等同817句缺文。新译文已静态构建验证，实际后续触发/时序、剧情视频与全对白覆盖待验。详见[字幕覆盖报告](docs/SUBTITLE_COVERAGE.md)。

## 可选字幕来源构建进展

已支持--subtitle-source，经manifest校验后保守合并245条恢复来源；locale中独立保存245条结构化字幕，其中12条新中文草稿、233条待译。默认49条构建保持兼容，启用来源时61条已有译文/294条条目。源层已接入生产构建，但全中文、全触发与同步验收尚未完成；1080p原地90秒仅确认开场，不能代表后续关卡。详细流程见docs/SUBTITLE_COVERAGE.md。


## 当前字幕来源策略（2026-10-03）
采用社区优先完整并集：所有同key冲突使用社区值，原版独有key保留。详见 [COMMUNITY_SOURCE_POLICY](docs/COMMUNITY_SOURCE_POLICY.md)。旧保守合并描述仅为历史记录。

## 单音频多段字幕

Tes_01的社区补全文本作为完整来源保留。将其翻译一次拼接显示会提前泄露后段台词；现有WOTPlayer只在ClientHearSound时调用一次SubtitleMessage，.int没有时间码语法。实验性LocalePlayer继承原AesSedai，为指定音频触发相对Level.TimeSeconds的分段字幕，旧声音与未配置字幕委托原实现；不是对原代码注入hook。原地图、语音和程序不改，需显式Class URL选择，实机兼容仍待验证。详见[SUBTITLE_SEGMENTS](docs/SUBTITLE_SEGMENTS.md)。


## 2026-10-03 分段测试记录与独立时钟候选

以专用Game+Class入口测试时，后半段字幕未出现。保存的WoT.log确认
LocaleTutorial、LocalePlayer已生效，因此不是入口未启用。此前全局Player.Tick
推进序列的方案未通过实机验收；原包PlayerPawn脚本存在PlayerTick路径，原生玩家
Tick分发差异是高可信待验证原因，不作为已实测的根因。

候选实现改由独立LocaleSubtitleClock Actor.Tick推进同一序列，不改译文、时间码、
原地图、语音或默认入口。新增sequence start、clock tick active、cue编号/时间/文本长度、
其他对白取消序列日志，用于区别回调未执行、文本为空和提前取消。静态源码连线测试与
原版UCC编译不等同实机验证；后续仍需1080p专用入口重测，暂停/死亡/切图/存档尚待验收。

已核对，之前凭听音回忆的那句实际是Be steadfast，采用现有“坚定你的意志”，
不再追查或额外添加Please stand back字幕。前面的候选调查记录保留为历史。

## 已审查的可读 @ 文本（2026-10-04）

已验证的调用路径：Legend.WOTInventory将Description与Quote声明为localized string；WOT.InventoryInfoWindow.Draw把两字段直接交给C.DrawText，Quote另设F_WOTIta14字体。Engine.Canvas.DrawText为native(465)，脚本层未对这三段执行名称/资源查找或变量替换。该证据支持将forget、grunt及The flows just... vanished.认定为玩家可读正文，而非资源ID。native层的@最终显示/引号处理仍未作实机确认，不将具体引号行为写成已验证事实。

该批仅处理AngrealInvDistantEye.Description、AngrealInvMinion.Description、AngrealInvAbsorb.Quote。逐行literal_token_translations声明审核过的source/translation带@片段；markup_delimiter_count保留整行@数量。源文件source_sha256、source_length、tokens保持原值；源文预检核验注释对应真实源文及分隔符数量，翻译校验把声明片段还原后比较全部控制码数量/顺序。正文与边界均保留，其他未知@片段不获自动豁免。禁止用这项机制放行%s、{0}、转义等真正控制码，或批量翻译未知@标记。相关负例测试见tests/test_literal_spans.py。

不要全局删除@保护，也不要把中文重新计算为source token/hash。之前三段英文原样保留属于历史保守处理，现由精确条目审核取代。正式字形、换行及物品信息界面显示仍由1080P实机QA确认。

## 界面可见标识文案收尾（2026-10-04）

该批仅修改四个本地化显示字段，源文ID、hash、长度和控制码不变：Windows.EditCommand显示为“&使用关卡编辑器编辑”（保留&助记标记）；WOTPlayer.CantPlaceResourceStr改为“部署失败 ”（保留用于拼接的末尾空格）；MissionObjectives.Title的通用基类“任务XX”改为“任务目标”，不改各关卡的实际标题；MyrddraalSwordAngreal.PickupMessage改为“警告：你发现了魔达奥剑的伤害效果！”。

已验证：原脚本WoTPawns.MyrddraalSwordAngreal说明该类为魔达奥剑持续伤害图标的占位适配器，空BecomePickup函数明确用于阻止拾取/可见，因此不把该诊断文本杜撰成玩家能拾取的新法器名称。WOT.WOTPlayer中的CantPlaceResourceStr是localized String，原ServerSpawn提示调用处已注释；替换提示正文不修改函数名。MissionObjectives继承WOTTextWindowInfo，基类Title是通用显示文案，不含插值控制码；实际关卡由MissionObjectives01等子类提供标题，未发现需要保留XX的运行时替换脚本。基类触发及Windows外壳标签的实机显示仍未专门确认。

核心1002条为已填充的中文草稿，而非全游戏文本覆盖证明。按键名称、网络缩写和机器使用的控制码/类名仍保留；视频、地图内嵌文字及未提取的硬编码文本尚待全面审计。不得将该次四项收尾描述为已经完成全游戏全文本汉化。

## 图片文字审计补充（2026-10-04）

已只读检查101个本地资源包，3581个Texture首级mip成功解码，发现场景挂毯与城堡编辑按钮中的图片英文。具体资源、地图导入证据及尚未辨读的小字见[图片文字审计](docs/TEXTURE_TEXT_AUDIT.md)。45个原版地图是`.wot`，没有直接导出的Texture；这不排除外部贴图上的英文。图像文字不属于`.int`字符串，也不随字库替换变为中文。未修改资源或启动游戏。

## 八张按钮纹理回填

仅汉化Load/Play/Roam/Save图片按钮，其他图像文字保留。八个Texture均为64×64、P8、单mip，Palette为包内引用；只在文字面板中重新量化像素，保留全部包表、对象引用、属性、调色板和像素数组长度。工具先检查每个完整Texture导出体SHA-256，再确认字体覆盖和宽高约束，最后重开资源并比较所有非目标导出体。生成输入是此前字体和显示字段构建的WOT.u副本，整个构建仍从经校验的原版开始。已验证差分安装和隔离副本回滚；未宣称实机按钮显示/操作验收。

## 原生高级选项补翻（2026-10-04）

原生高级选项窗口由WinDrv/Window模块处理，与Canvas字库、图片按钮不同。已新增31条Preferences显示字段和48条普通窗口文案；同步Caption/Parent以保留分类树，Class/Category/Immediate与配置键不变。直接FName显示的原生属性/类别名称尚待研究。二进制只读证据、地址、hash和层级见[NATIVE_ADVANCED_OPTIONS](docs/NATIVE_ADVANCED_OPTIONS.md)。

## 操作设置布尔值显示修复（2026-10-04）

**已验证（静态/编译）**：`menuOptions.DrawValues` 六个位置使用 BoolToString（0x54），绕过既有 `menuLong.GetOnOffStr`。槽位2/4/5/6/9/11分别为反转鼠标、始终鼠标视角、自动坡度视角、视角自动回正、启用摇杆、玩家名称显示。适配器只把显示表达式改为调用现有本地化函数，复用 `WoT.int [menuLong] OnText/OffText`（zh-CN：开/关）。bool操作数不变；九个其他操作设置函数以及GetOnOffStr的函数体保持原样；配置中的True/False不变。

原函数SHA-256、表达式偏移及操作数放在`profiles/gog-v68.json`，由`src/patch/display_expressions.py`匹配后追加函数体并重建导出表。包版本v68、名字表、导入表、对象数量与GUID保持不变；全包其他导出体逐一比较。未知版本或重复应用会报错，不直接修改EXE/DLL/地图。

最小自编UCC夹具`tests/fixtures/LocaleDisplayProbe.uc`确认虚函数调用与bool操作数的序列化，以及每个替换增加5字节VM长度。DrawValues序列化函数体240→258字节，ScriptSize 293→323；二者不同是紧凑索引在加载时展开造成的。UCC加载重建包并编译夹具通过。**待验证（游戏内）**：1080p六项开关显示、切换及退出后持久化；没有自动启动游戏。

## 设置深层属性与制作人员页（2026-10-04，当前实现）

**已验证（离线）**：纹理细节getter保留控制台读取及TextureDetail原值，仅把返回表达式接入GetLowMediumHighStr；Low/Medium/High映射0/1/2，19个其他硬件设置函数不变。UCC自编表达式VM大小48，对原getter的VM增量40（82→122）。非标准配置值显示为低档位，但原值不被覆盖；当前支持原版三档。

**已验证（离线）**：Credits是WOT.u内的Class默认属性，不是图片或外部版权文本。保留204个原位置、角色对应演员及贡献者姓名；新增204空行、205署名。FString改为UTF-16序列化；CreditsText.StrProperty的ArrayDim 204→206与PostRender两处ArrayCount常量必须同步，不只补写默认文本。该属性维度位于导出体+4，不是+5；默认CreditsText标签流从Class体+339开始，数组索引128以上用双字节标签索引。UCC加载重建包并编译自编夹具通过；完整滚动结束/退出仍待实机验收。

**已验证（离线）**：Window.dll的FPropertyItem.GetCaption、FCategoryItem.GetCaption和FPropertyItem.Draw有独立FName显示路径；只改GetCaption并不足够。原生行高函数返回16，列分隔宽度默认128且可由注册表覆盖。该批在经完整SHA校验的构建DLL副本增加位置无关.locale段，映射274个显示名及7个显示值；行高设32，GetDividerWidth最低320并允许更宽。姓名/FName、属性键、配置、共享GetPropertyText和SetValue不改；值映射只改Draw局部缓冲。未知显示名原样回退。没有改EXE/WinDrv.dll、没有进程注入，没有新增运行时依赖DLL。

两种镜像基址的602项x86模拟覆盖中文/未知值/空串、寄存器栈平衡、属性/类别/直接绘制、值缓冲、行高/分隔线。PE进口表及原文件中批准范围外的字节均保持原样。**待验证（实机）**：高级选项展开、滚动、编辑器位置、点击保存与各DPI缩放；固定32不是任意DPI自动缩放，当前只验1080p。全部生成资源仍通过差分安装/隔离回滚，不提交完整DLL。

## 动态提示与视频轨复核

教程MessageTrigger实例字符串可通过显示入口精确匹配翻译而不改地图；键名只包裹DrawValues三个读取操作数，VM与6个分支同步更新，改键/保存函数不变。详见[UI_TEXT_FOLLOWUP](docs/UI_TEXT_FOLLOWUP.md)。FMV原版含28个独立text轨，标签eng不代表正文英语；QuickTime路径、已证实/待验证边界见[FMV_SUBTITLES](docs/FMV_SUBTITLES.md)。

## 设置编辑值与循环关卡补漏

已补上循环竞技场关卡和高级选项下拉列表的显示、查找与反向回写适配，原始配置值保持不变。此前对应待办由本节更新；159项测试、730项CPU模拟、UCC加载通过，1080p实机切换与保存待验。实现、位置及命令见[设置动态值补漏](docs/SETTINGS_VALUES_FIX.md)。未知标识、设备/API与自定义值仍保留原样。

## FMV 完整字幕更新（2026-10-05）

已在游戏内确认 PoC 中文显示。沿用经版本校验的 WinDrv 第一 text 轨选择，完整 14 片的 769 样本中 628 条非空对白现已有中文初稿，其余保持空白清除。批量构建只追加一个 mdat、重写中文轨的 stsz/stco、语言/字体/范围字段；原始媒体和 stts 时间轴不变。Mission_05 具有两种 stsd 与第 23 chunk 起的描述切换，不能套单描述 PoC。文本范围从 20 增至 44，高度同步写入 tkhd；最长句及双行受控原生绘制通过，完整游戏布局、听校和通关仍待测试。源码和边界见 [FMV 正式测试](docs/FMV_FULL_QA.md)。下面保留早期 PoC 研究记录，状态以本更新为准。

## FMV 原生文字轨最小实验

已建立哈希校验的单样本 UTF-16 副本实验与 32 位 QuickTime 只读打开探针。
原音视频不变，独立回滚 SHA 一致；原版/修改/回滚均通过旧运行库打开。
PlayMovie 的字幕轨选择另受语言索引减 3 控制，不能靠 MOV enabled 标志直接解决。
实际中文字形、独立字幕选择与游戏内播放尚待验证；没有安装视频或修改 WinDrv.dll。
字段、RVA、命令及证据分级见 [FMV 研究](docs/FMV_SUBTITLES.md)。

### 实际中文字形验证更新

已在独立 QuickTime 播放器的 1920×1080 离屏图中确认实际中文绘制。
BOM-only 会乱码；添加 encd=0x100 和 media language=33 后显示正确。
字幕 matrix 只在测试进程中移到视频下方，GWorld 黑色背景消除了 OFF 白条。
独立预览入口可重建，172 项测试通过；可见播放与游戏内字幕选择接入仍待验。

### 游戏内字幕选择最小 PoC

仅在物理隔离的 WinDrv.dll 副本把 RVA 0xFC97 的语言索引减 3 改为零基第一文字轨选择，
原音轨代码与 Language=int 不变；Intro 使用同一条已显示的中文样本。
179 项离线测试通过，游戏内显示仍待实际运行确认。原版资源不改；全文 FMV 翻译暂停，
先完成 [游戏内 FMV 验证](docs/FMV_GAME_QA.md)。

## FMV 私有字体适配验证

旧 QuickTime 已识别并绘制进程私有加载的思源黑体子集。字体 cmap 覆盖与 OS/2 脚本标记需要同时校验；MOV Unicode 编码保持不变。已完成 PIC 加载代码、16 场景 CPU 检查、原生绘制和独立回滚，实际游戏内中文字幕显示已确认；完整通关和播放控制路径仍待验收。版本门禁、PE 字段关联与证据边界见 [本地字体验证](docs/FMV_LOCAL_FONT.md)。

## 原生高级设置范围

原字节属性编辑器统一提供 0–255，但整体细节、最大细节、血腥效果的原版菜单范围分别为 0–2、0–4、0–3。版本守卫的 Window.dll 适配按属性声明所有者限制滑块和数值输入，保持其他原生字段与序列化不变。完整证据、未确认范围及验收边界见 [范围审计](docs/ADVANCED_SETTINGS_RANGES.md)。

## 地图实例显示文本

已验证：MessageTrigger.Messages 写在地图 actor 的序列化属性中，普通启动不会经过可选 LocalePlayer 的 GenericMessage 翻译入口。默认工具链现以白名单 FString 属性回填解决；只追加改变的 actor body 与 export table，头部只改 ExportOffset，其他导出逐字节验证。UTF-16 长度以 code unit 计数并包含 NUL。地图几何和事件逻辑不改，完整指纹及独立回滚均验证。扫描范围、覆盖与待确认字段见 [地图文本覆盖](docs/MAP_TEXT_COVERAGE.md)。

## 字幕专用 HUD 与字体

已验证：新增 SubtitleFont 而不改现有 Font；Subclass 的 DrawMessages 先调用原绘制路径，单独绘制并发字幕并恢复 Canvas 状态。唯一既有导出变化为 giWOT.HUDType 默认属性，显式指向 SubtitleRuntime.SubtitleHUD。原生 commandlet 已验证交叉包加载，真实视口排版仍待验收。原单槽覆盖与可选入口缺失导致的开场整句合并由此分离解决。详见 [字幕显示](docs/SUBTITLE_DISPLAY.md)。
