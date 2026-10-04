# 重复踩坑 / 必须保持的约束

1. **Unicode不等于有字库**：仅换UTF16 `.int` 曾中文空白、ASCII正常；先检查Font映射。
2. **大atlas缺mip**：512单mip曾报 `D3D Driver: Encountered oversize texture without sufficient mipmaps`。
   默认256上限；不能只依据驱动宣传的2048上限放大。
3. **CPP与Latin**：仅把256改64会破坏ASCII页/槽；保留Page0并补1..3切片且逐字形比较。
4. **绝对lazy-end**：追加Texture后它不是局部offset，必须与export.offset同步。
5. **标点bbox顶对齐**：逐字按bbox.y0裁切会把句号抬高；旧方案按单个代表字形统一基线仍会切掉更高的字（例如14px“重”高于“汉”2px）。现按全部请求字形完整边界统一基线，再整体适配原版行高，不能逐字顶对齐。
6. **字幕Len计时**：短译文90字替换350字会提前消失；补偿仅构建生成、不能假装精确同步。
7. **启动路径空格**：老引擎曾把绝对WoT.exe路径误拆成Commandlet；切换System后用 `.\WoT.exe` 启动。
8. **截图≠模式**：桌面3840截图不证明内部4K；看Best-match模式日志，之后人工看UI。
9. **Inventory异步加载**：Mission_01先显示任务目标，F3关闭后按1/F2，再多等10秒。
   黑屏/预缓存帧不能算字体通过，原版也需同输入对照。
10. **字体/engine导出分层**：脚本字面量存在不代表修改Font需要改字节码；逐字节验证非Font导出。
11. **PowerShell/日文Windows编码**：Python默认stdout可能cp932；中文测试结果应明确UTF8输出。
12. **窗口退出流程**：不要先关闭DirectDraw代理窗口再主窗口；新QA曾在已显示Inventory后退出报
    `DDERR_NOEXCLUSIVEMODE/ReTestCooperativeLevel`。保留失败证据，先关闭自己的主窗口并做原版对照。
13. **Gitignore递归匹配**：`build/` 会同时忽略 `tools/build/` 源码。
    根生成物必须写 `/build/`，并在干净克隆中验证构建模块确实入库。

## 工作区迁移陷阱

- 根目录相对ROOT的旧脚本搬到tools子目录后会错误寻找backup/work。保留旧原件，生产入口复用已参数化框架，不靠复制旧生成物凑齐依赖。
- .gitignore中的build/会连tools/build也忽略；改为/build/、/dist/、/out/，干净源码集检查tools/build/pipeline.py存在。
- 历史大小写文件名与新FILE_FORMATS/PITFALLS/KNOWN_ISSUES在Windows上应合并、更新链接，不建立大小写冲突副本。
- 历史低分辨率成功与277/277散列属于当时记录，不覆盖后续分辨率决策，也不据此恢复用户INI。

- Windows下Python的text=True stdin会将LF转成CRLF，git check-ignore --stdin可能把CR当作路径字符，导致假阴性与带\r的引用输出。忽略规则探针使用UTF-8字节stdin（或NUL分隔），不要把测试工具传输问题误报为.gitignore失效。

## 字形与字幕布局修复

- 仅增大中文Font矩形高度会使Controls左列比原ASCII右列行高更大，累积错位；StrLen中文字高度大于原“X”也会把单行帮助判为多行、丢失居中。2026-10-03首版候选已出现这两项回归，保留本地候选/截图，不采用。技术层profile使用preserve-legacy行高，先完整渲染再按同一比例适配全部字形。
- 字形裁剪和字幕贴顶是不同层。BaseHUD.DrawMessages计算Y=ScaleValY(24)，却对字幕调用SetPos(0,0)。只移动字形位图不能修正字幕块坐标；同样不能通过逐字裁边/加入空格假装修复。当前仅替换经原导出SHA与上下文验证的float Y常量，字幕Len计时与分支不变。

## 开场缺段修正

Tes_01原非空文本也会缺段：本轮仅经双source hash批准采用社区完整432字符，译文由subtitle_overrides组合，Len补偿使用432而非350。完整版教程构建需--subtitle-source；其余条目不动。详见[TUTORIAL_INTRO_FIX.md](TUTORIAL_INTRO_FIX.md)；80/80非空key不等于音频全段覆盖。

## 字幕完整来源不等于正确分段

把Tes_01社区后段拼在同一显示条目会让后段在开场就出现。不要凭新增key假定游戏会自行调用，也不要把//注释MessageTrigger的历史MessageDelay当作正在执行的时间码。现行脚本跳过注释的同时跳过Sleep，恢复注释将改变调度，不能静默修改地图。局部ASR的英文专名可能错误，固定译文仍以已有源文和GLOSSARY为准。UCC未知commandlet可退出0；必须检查成功日志与新产物。详见[SUBTITLE_SEGMENTS](SUBTITLE_SEGMENTS.md)。


## 2026-10-03 用户分段测试反馈与独立时钟候选

用户以专用Game+Class入口测试后，后半段字幕未出现。保存的WoT.log确认
LocaleTutorial、LocalePlayer已生效，因此不是入口未启用。此前全局Player.Tick
推进序列的方案未通过实机验收；原包PlayerPawn脚本存在PlayerTick路径，原生玩家
Tick分发差异是高可信待验证原因，不作为已实测的根因。

候选实现改由独立LocaleSubtitleClock Actor.Tick推进同一序列，不改译文、时间码、
原地图、语音或默认入口。新增sequence start、clock tick active、cue编号/时间/文本长度、
其他对白取消序列日志，用于区别回调未执行、文本为空和提前取消。静态源码连线测试与
原版UCC编译不等同实机验证；后续仍需1080p专用入口重测，暂停/死亡/切图/存档尚待验收。

用户已确认其近似回忆指的是Be steadfast，采用现有“坚定你的意志”，
不再追查或额外添加Please stand back字幕。前面的候选调查记录保留为历史。

## 已审查的可读 @ 文本（2026-10-04）

已验证的调用路径：Legend.WOTInventory将Description与Quote声明为localized string；WOT.InventoryInfoWindow.Draw把两字段直接交给C.DrawText，Quote另设F_WOTIta14字体。Engine.Canvas.DrawText为native(465)，脚本层未对这三段执行名称/资源查找或变量替换。该证据支持将forget、grunt及The flows just... vanished.认定为玩家可读正文，而非资源ID。native层的@最终显示/引号处理仍未作实机确认，不将具体引号行为写成已验证事实。

本批仅处理AngrealInvDistantEye.Description、AngrealInvMinion.Description、AngrealInvAbsorb.Quote。逐行literal_token_translations声明审核过的source/translation带@片段；markup_delimiter_count保留整行@数量。源文件source_sha256、source_length、tokens保持原值；源文预检核验注释对应真实源文及分隔符数量，翻译校验把声明片段还原后比较全部控制码数量/顺序。正文与边界均保留，其他未知@片段不获自动豁免。禁止用这项机制放行%s、{0}、转义等真正控制码，或批量翻译未知@标记。相关负例测试见tests/test_literal_spans.py。

不要全局删除@保护，也不要把中文重新计算为source token/hash。之前三段英文原样保留属于历史保守处理，现由精确条目审核取代。正式字形、换行及物品信息界面显示仍由1080P实机QA确认。

## 图片审计解析陷阱（2026-10-04）

- 沿用字体特定样本中`None == 0`的假定，会让其他资源包属性解析失败；终止判断必须查询本包名称表。
- 仅在版本`>63`跳过lazy-array字段，会把本游戏版本63贴图像素错读；本地63/68样本都需要该字段。
- 仅按Sign/Book等资源名筛选会漏掉TpstWall挂毯等图像英文；需要总览筛查。
- 地图导入、Actor放置、默认网格Skin与游戏实际可见纹理不是同一层证据；Cylinder实例可能覆盖默认皮肤。

## 原生高级选项补翻（2026-10-04）

高级选项窗口标题来自Window.General.AdvancedOptionsTitle，且译后的标题用于分类树根。只翻标题或Caption、不同步Parent会断开分类树；不能把Category等反射标识一并翻译。Preferences会被引擎缓存，文件更新后需要完整退出游戏。

## 菜单布尔值不是可批量替换的英文字符串

`True/False`既是显示转换结果也是配置机器值。不要修改Core.dll的BoolToString或替换.ini布尔值；只修复菜单的显示表达式，复用GetOnOffStr。`High/Medium/Low`也参与配置比较与写回，后续应在显示返回值一侧映射，不改控制逻辑。

序列化脚本字节数不是VM ScriptSize，紧凑对象/名字索引会展开；必须用UCC夹具验证。紧凑索引可以跨字节（如最后一个bool属性引用`7b14`），不要把末字节当成下一个opcode。当前适配器仅支持已审计直线函数，含跳转的竞技场函数不能直接套用同一替换策略。

## 深层设置与Credits关联字段

1. 原生属性Draw直接取FName，未必走GetCaption；只改caption函数会让实际绘制仍英文。
2. 原生列宽会读注册表，单改构造默认值可能被旧值覆盖；当前在GetDividerWidth设下限，允许用户继续拉宽。
3. 字体已经按系统DPI放大而原行高固定16，导致文字上下裁切；不能只加宽窗口。当前32像素是1080p测试候选，不是所有DPI验收结论。
4. 不在共享GetPropertyText里翻译True/False，否则编辑与配置保存可能读取中文机器值。当前只改Draw的临时文本；聚焦编辑框/下拉选项仍可能显示原始机器值。
5. Credits只新增默认条目而不增ArrayDim或ArrayCount，会越界或漏显。属性头包含可变长度紧凑索引，实际ArrayDim是体+4；错误+5已由守卫拒绝，未写入原版。

6. 安装器最初只允许.u/.int，会在20文件包预检时拒绝Window.dll（任何写入前）。现仅额外允许profile中大小/SHA和profile id均匹配的System/Window.dll；其他DLL/EXE仍拒绝。补丁包资源类型扩展需要同步安装器预检与回滚测试。
