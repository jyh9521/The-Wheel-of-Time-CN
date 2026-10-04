# 文件格式笔记（当前 GOG / WOT.u v68）

## Unreal package header

little-endian `<IHHIiiiiii>`，magic `0x9e2a83c1`。

|绝对偏移|字段|
|---:|---|
|0|magic u32|
|4 / 6|package version / licensee version u16|
|8|flags u32|
|12 / 16|name count / name table offset i32|
|20 / 24|export count / export table offset i32|
|28 / 32|import count / import table offset i32|
|36..51|GUID，保持|
|52|generation count i32|
|56起每8字节|export count、name count；追加时同步最后一代|

compact index 首字节6数据位，0x80符号，0x40继续；后续字节7数据位、0x80继续。
name 条目为有符号compact长度字符串 + u32 flags。
import：compact cp、cn，i32 outer，compact name。
export：compact class、super，i32 outer，compact name，u32 flags，compact size，非零size再跟compact offset。
正对象索引=export index+1，负索引=-(import index+1)，0=None。
解析器不是所有版本编辑器；原始指纹是修改门槛。

## Font 对象

当前受改6Font的属性流以None=compact0结束，其后：
compact page_count；各页 compact texture_object_index、compact char_count、char_count×16字节矩形；
最后 i32 CharactersPerPage。不能把这个偏移套用到所有 Engine.u Font，其属性前缀可能不同。

受改Font原版 index（1-based）：35 Reg14、1096 Reg30、8211 Reg14_S、8212 Ita14、8213 Reg08、8377 Reg30_S。
原版1页256矩形、CPP256；新CPP64。保留Page0原始记录，并补页1..3切片维持Latin。
字符槽 `(cp % CPP)*16`，页 `cp//CPP`；空Unicode页 `(texture=0,count=0)`。
字宽使用矩形w；斜体余量并入w。

## Texture / Palette

属性tag有compact名称、类型/size标记；struct/array等可能附带索引。
本适配器复制已验证原字体Texture属性，更新UBits/VBits/USize/VSize/UClamp/VClamp。
属性结束后：u8 mip_count=1；i32 lazy_end_absolute；compact pixel_count；P8像素；i32宽/高、u8 UBits/VBits。
`lazy_end_absolute = export.offset + pixel_data_end_in_export`。
Palette：None属性终止、compact256、256×RGBA；保持原调色板引用。
普通字形 atlas ≤256，cell为较大维度+2，纹理power-of-two分组。多页共享一个atlas引用。
必须同步：像素数量/尺寸/位数/裁剪/Font页纹理索引/导出size/offset/新名称/导出与代际计数。

## localization / 差分

.int：区段/key=value，有重复key。occurrence从1开始；引号内尾空格属于值。
工程strings.json不存整包原文，以解码原文UTF-8 SHA-256定位来源。
UTF-16LE BOM输出保留未选条目字符内容与换行；目标整个文件编码变化是预期，不宣称未选行原始字节不变。

PATCH.json是localization-bundle-v1，含每文件copy-literal-v1。
COPY记录原文件offset/size；LITERAL为zlib9/base64及解压size。
这是公开可读格式，不是加密或隐蔽编码；只针对资源差分，不转换对话内容。
每文件保存原/改SHA256与size，安装器重建及重读一致后接受。
JSON本身无签名，只使用可信构建来源；Release前须另做来源/内容/字体许可审核。

## 迁移审计格式

migration-manifest.json逐文件保存origin/source/destination/source_sha256/method；旧源码快照只记录路径、大小、mtime、SHA。build/migration/old-before.json为5126文件的本地全目录基线；迁移工具以相同字段比较新增、删除与修改，输出必须位于被审计树之外。原始游戏277文件manifest是历史元数据，不是当前配置恢复指令。

## 字形栅格 / 显示字段

字体栅格使用共同source_bounds和origin；manifest记录raster_height、最终height及vertical_fit_scale。最终Font矩形height保持原槽位行高；源墨迹参考检查发生在整体纵向适配之前。非等比纵向适配可能改变抗锯齿像素，不冒充像素无损。

profile.resource_edits为语言无关显示字段：resource、export、export_sha256、offset（导出body相对）、type=float32-le、expected、value、context_offset/context_hex。当前字幕字段为导出5095 body+1979，原始00000000→0000c041，即0→24，函数等长2614字节。原包绝对992669只作研究记录，不用于盲写；运行工具按解析后的导出offset定位。FONT_DIFF是字体阶段；BUILD_REPORT.resource_edits记录之后的字段差分，最终hash位于PATCH/BUILD_REPORT。

## 已审查的可读 @ 文本（2026-10-04）

已验证的调用路径：Legend.WOTInventory将Description与Quote声明为localized string；WOT.InventoryInfoWindow.Draw把两字段直接交给C.DrawText，Quote另设F_WOTIta14字体。Engine.Canvas.DrawText为native(465)，脚本层未对这三段执行名称/资源查找或变量替换。该证据支持将forget、grunt及The flows just... vanished.认定为玩家可读正文，而非资源ID。native层的@最终显示/引号处理仍未作实机确认，不将具体引号行为写成已验证事实。

该批仅处理AngrealInvDistantEye.Description、AngrealInvMinion.Description、AngrealInvAbsorb.Quote。逐行literal_token_translations声明审核过的source/translation带@片段；markup_delimiter_count保留整行@数量。源文件source_sha256、source_length、tokens保持原值；源文预检核验注释对应真实源文及分隔符数量，翻译校验把声明片段还原后比较全部控制码数量/顺序。正文与边界均保留，其他未知@片段不获自动豁免。禁止用这项机制放行%s、{0}、转义等真正控制码，或批量翻译未知@标记。相关负例测试见tests/test_literal_spans.py。

不要全局删除@保护，也不要把中文重新计算为source token/hash。之前三段英文原样保留属于历史保守处理，现由精确条目审核取代。正式字形、换行及物品信息界面显示仍由1080P实机QA确认。

## P8纹理只读解析补充（2026-10-04）

本地样本的属性列表终止符必须由包自己的名称表查找`None`，不能假定其名称索引永远是0。Texture通过Palette对象引用取得256项FColor调色板；每项4字节，RGB预览使用前三个通道，未模拟透明/遮罩显示。属性列表后依次读取紧凑索引mip数量、首级lazy-array的32位字段、紧凑索引像素数量、像素、32位宽高及后续字段。本地版本63与68均有该32位lazy-array字段，不能仅对大于63的版本跳过。工具仅解码首级P8图像，不支持资源重建；该观察不外推为所有Unreal版本通用布局。

## 固定大小按钮回填

该阶段八张UI纹理均有包内Palette引用、一个64×64 P8 mip。只修改像素数组指定面板范围，不移动导出体，不重写lazy-array字段、包表或调色板。源导出体指纹由profiles/texture-labels.json固定；该工具明确拒绝外部Palette、多mip或不匹配的导出体，不能直接当作通用贴图封包器。

## 原生高级选项补翻（2026-10-04）

Preferences是结构化登记数据，不是普通整行字符串。通用导入器严格解析本地平坦括号字段语法，仅允许Caption/Parent子字段回填，源行hash不符、重复字段、嵌套/未知语法或控制符缺失时失败；Category仍是属性过滤标识，Parent必须与Caption及译后的根标题一致。

## v68菜单显示表达式与ScriptSize

空属性流UFunction的头部依次含None、SuperField、Next、ScriptText、Children、FriendlyName的紧凑索引，然后Line/TextPos/ScriptSize三个int32。字段偏移必须解析，不应固定使用17。当前受指纹约束的直线DrawValues用0x54执行bool→string；改为0x1B + helper FName紧凑索引 + 原bool表达式 + 0x16，保留尾部函数元数据。

**已验证**：UCC自编夹具的VM ScriptSize从10变15。FName在VM中占4字节而非磁盘紧凑索引长度；六个包装各加5，原DrawValues ScriptSize 293→323，磁盘体240→258。新函数体追加到构建副本末尾，导出表仅改该对象size/offset；summary ExportOffset（24）指向重建导出表。不新增对象，不改世代计数。当前适配器不是完整字节码反编译器，仅支持明确审计过的无跳转函数。

## Credits默认数组和原生显示段

WOT.u的CreditsText默认为204项。每条Class默认标签由紧凑name索引18、StrProperty类型13+size编码、可选数组索引、FString长度及数据构成。首项没有array flag，后续索引<128单字节，128～16383用两字节；UTF-16 FString负长度按16位码元计数，标签Size按包含长度前缀的字节数。新增2行需要StrProperty ArrayDim及PostRender的两处ByteConst ArrayCount同步204→206。

Window.dll（x86 PE）的.locale段含自编查表代码与UTF-16键/显示串。代码CALL/POP取得当前位置，表内只存相对偏移，原导入表/重定位表保持原样；两个加载基址的执行验证通过。更新NumberOfSections/SizeOfImage/SizeOfCode以及新段头，CheckSum置零。原文件完整hash先验证，跳转点逐字节校验；原文件其他字节不改。RVA和对应期待字节以profiles/gog-v68.json为准，不用于未知版本。

## MessageTrigger实例与QuickTime文本样本

v68带RF_HasStack的actor属性前缀：Node compact、StateNode compact、ProbeMask u64、LatentAction i32、Node非零时CodeOffset compact；其后属性流。Messages的StrProperty保留array slot与FString正ANSI/负UTF16长度。只读实现tools/extract/map_messages.py。QuickTime legacy text sample为大端u16文字字节长度+正文+可选扩展，不把尾部样式翻译成正文；时轴/包偏移/长度保留，当前没有实现MOV重建器。

## 设置显示/原始值的双向映射

我已补上循环竞技场关卡和高级选项下拉列表的显示、查找与反向回写适配，原始配置值保持不变。此前对应待办由本节更新；159项测试、730项CPU模拟、UCC加载通过，1080p实机切换与保存待验。实现、位置及命令见[设置动态值补漏](SETTINGS_VALUES_FIX.md)。未知标识、设备/API与自定义值仍保留原样。
## Legacy MOV 单样本文字实验

我确认 Intro.mov 文字轨采用 stsz 显式大小、stco 32 位偏移、stsc 每 chunk 一个样本。
最小工具在尾部追加 mdat，只更新一个样本的大小/偏移和字体名/启用位，保留原时间表。
文本长度字段以字节为单位；旧 styl/ftab/orig 扩展不直接沿用于新正文。
完整字段、限制、原版哈希和重现命令见 [FMV 研究](FMV_SUBTITLES.md)。

Unicode 样本现在额外写入 `00 00 00 0C 65 6E 63 64 00 00 01 00`：
长度 12、类型 encd、kTextEncodingUnicodeDefault=0x100。
本次 mdhd version 0 的 atom+28 字段写 Mac 简体中文语言码 33（两个字节 00 21）；
该值来自 locale 配置，不是通用工具固定值。真实旧 QuickTime 绘制与可逆验证见上述研究报告。
