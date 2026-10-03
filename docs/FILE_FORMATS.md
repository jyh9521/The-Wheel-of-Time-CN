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
