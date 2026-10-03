# 逆向研究索引

## 研究来源与移植

2026-10-02/03 对维护者本地 GOG 安装做只读扫描、原生反汇编与独立运行。
没有已知上游研究仓库，因此无可填的 upstream commit；不编造引用。
前五阶段本地 Python 工具的包解析、line-based .int、CPP64 atlas方案、基线/斜体修复迁入通用工具。
研究产物不依赖作者私人目录；可由自己游戏重新生成文本索引/包表。未提交完整原脚本源码。

## 结构证据

- 包读取：128包、0解析失败；Font26个、Sound1198个。
- System20个.u、29个.int；Maps45个.wot；Textures36个.utx；Sounds27个.uax；Music10个.mp3；Movies17个.mov。
- menuWOT.DrawHelpPanel 用Reg14，menuLong用Reg30；BaseHUD消息用Reg14。
- InventoryInfoWindow用Reg30标题、Reg14正文、Ita14引用、Reg14提示、F_Element元素标签。
- LegendCanvas的低分辨率替代字体条件为Canvas.SizeX<512；当前目标>=1366，这不是验收路径。
- 当前font插件保留原Legacy映射及其他原export正文；v68结构见file-formats。

## 原生机制定位（研究信息，不是待打补丁的地址）

历史反汇编将WrappedPrint定位为Engine.dll RVA 0x693E0，UFont对象CPP字段+0x28、页相关字段+0x2C/+0x30。
这些来自当时样本；项目未绑定该DLL为补丁输入，不能给别的引擎版本直接套这些地址。
资源重读及中文实机显示独立验证了CPP页/槽机制，发布方案无需改原生代码。

## 字幕和视频研究边界

Sound包名/对象名能直接定位字幕key；897条/817空不是完整对白资料库。
曾比较社区关联语言文件：英语80非空，德语321、西语332、意语630非空（键总数也不同）。
这些只是结构覆盖比较，不等于找到完整英语补丁、兼容承诺或得到再分发许可。
未批量ASR，没有按其他语言内容自动伪造英语原文。

17个MOV中14个含意大利语/西班牙语legacy QuickTime text轨，共28轨。
存在带时间信息的文本来源，不全是硬字幕；Mission_10.mov未发现这种字幕轨。
视频对话不经WoTsubtitles.int。当前不重编码、不修改视频、不声称外挂SRT可用。
其他3视频是否有画面文字/对白覆盖须逐片验证；新增轨的中文原生播放未完成。

## 复现入口

build.py extract：生成全部.int目录索引、编码字段、重复值分组。
tools.pack.ue1.Package：包表读取；tools.font.build_font：重建与结构断言。
每次发现新的来源/关联/错误，补充技术文档、可复现fixture和验证记录，而非只写开发日志。
