# FMV字幕调查（2026-10-04）

## 已验证事实

旧研究脚本mov_text_export.py已有文字轨发现；该阶段复核原版，并整理为tools/extract/movie_text.py，不依赖旧工作目录或硬编码ffprobe路径。未修改视频，未转录整部游戏。

- 17个MOV中14个各有两条QuickTime text轨：共28轨、1538样本，1256个去除空白后非空（两种语言合计，不是1256句不同对白）。
- 文本在独立轨道，不是这些文字被烧录在画面；这不证明所有帧均没有其他图像文字。
- GtLogo.mov、Logo.mov、Mission_10.mov没有文本轨。Logo不据此认定漏剧情；Mission_10另需内容核对。
- 视频为SVQ1，声音为QuickTime IMA ADPCM；文字codec_tag为text。Mission_05有两个subtitle流没有codec_name，但提取成功，不能仅按codec_name过滤。
- ffprobe语言标签标eng，实际正文可辨为意大利语/西班牙语。不能把标签当英文原文证据。按Mac Roman暂解码并明确标assumed；保留sample位置，未知字符需回到原字节核对。
- sample首16位大端值是文字字节长度；尾部样式扩展不是正文。导出PTS/duration/offset/size，保留空白及消失间隔。
- WinDrv.dll包含PlayMovie导出、QuickTime.qts和theQuickTimeDispatcher标识；菜单调用PlayMovie Intro.mov。证据指向QuickTime播放路径，外挂SRT自动加载接口尚未验证。

## 优先技术路线

优先只新增/替换原生text轨，不重编码视频或音频：复用时轴→核对英文音轨/原文→翻译→生成sample→同步重建stsz/stsc/stco/mdat等关联结构→验证语言、启用状态及播放。

Apple说明文字sample有16位长度前缀，alternate group与enabled flags影响自动选择。现代subtitle规范的UTF-8/UTF-16支持不证明1999年Windows legacy text handler支持中文；须先验证原生text而非tx3g、字体名称/脚本、位置/字宽以及轨道选择。游戏内位图字库不能直接视为视频字体。

- [Apple Text sample data](https://developer.apple.com/documentation/quicktime-file-format/text_sample_data)
- [Apple Subtitle sample data](https://developer.apple.com/documentation/quicktime-file-format/subtitle_sample_data)
- [Apple Modifier tracks / alternate groups](https://developer.apple.com/library/archive/documentation/QuickTime/RM/MovieInternals/MTTimeSpace/F-Chapter/6ModifierTracks.html)

意/西语轨可作时序、内容参考，不作为英文原声唯一原文。没有英文脚本时先小范围核对英文音轨；不默认整部ASR。专名以GLOSSARY.md为准，凯琳/波莱恩具体片段尚未绑定。

若原生text不支持中文，再研究可关闭的叠加层；不立即烧录/重压。实验只用副本，验证音视频payload逐字节不变并可恢复。

## 可复现提取

```powershell
python -m tools.extract.movie_text --movies GAME/Movies --ffprobe PATH/ffprobe.exe --out build/movie-text
```

输出MANIFEST含视频原大小/SHA和流信息，stream JSON含时间码/原文。输出仅存忽略的build目录，不提交MOV或完整原始字幕。当前是资源/接口研究及可复现导出，不是已安装的中文FMV补丁。

## 原生播放器的字幕选择（追加研究）

我进一步检查了 GOG 原版 `System/WinDrv.dll`，SHA-256 为
`43076c7c4492654fb71fbeb7c4a83d4c870f7db0ad7421ada75a7912a06af964`。
以下地址均为 RVA，不是文件偏移；镜像基址为 `0x11100000`。没有修改 DLL。

**已验证（静态代码）**：PlayMovie 导出跳板 `0x10FA` 指向 `0xF910`。
它按照客户端 LanguageExt 数组匹配语言索引；原配置顺序为 int、frt、det、itt、est。
音轨循环在 `0xFC10–0xFC8F`；文字轨循环在 `0xFC95–0xFD48`。
`0xFC97` 的 `83 C7 FD` 从语言索引减去 3，`0xFCBB` 与从 0 开始的文字轨序号比较，
`0xFCBE` 生成启用布尔值，`0xFCC3` 调用 `0x18680`。
该包装函数使用 QuickTime dispatcher selector `0x20046`，与已安装 QTMLClient.dll
导出的 SetTrackEnabled 一致；文字轨查找使用 FourCC `text`。

**高可信推断（尚待游戏内验证）**：在这份原版配置下，int 的索引是 0，减 3 得到 -3，
不匹配任何文字轨，因此游戏会关闭文字轨。itt 选择第一文字轨，est 选择第二文字轨。
这解释了“文件中存在字幕，但英语游戏不显示”的路径；仅修改 MOV 的 enabled 标志，
预计会被播放器重新关闭。直接把全局语言改成 itt 还会改变配音选择，不作为中文补丁方案。
字幕语言需要与 UI/英文配音独立选择；若后续采用播放器适配，应限制在视频文字轨选择路径，
保留原音轨选择、可关闭开关及哈希门禁。当前未做此适配。

## UTF-16 最小副本实验

我以原版 Intro.mov 的第三条轨道、零基样本 1 做实验，只写入
“中文字幕显示测试：时光之轮”，并非整段正式译文。
原版 SHA-256：`5e302003dc82904f3392d9661214ce5ba8344ecf3bc29c13e3bb4929ec523764`。
样本时间为 1–7 秒，沿用原时间表。

- 通用工具：`tools/pack/movie_text_probe.py`；语言数据：`locales/zh-CN/fmv_probe.json`。
- 原 sample 为 16 位字节长度 + Mac Roman 文本 + styl/ftab/orig 扩展；新 sample 为长度 + FEFF BOM + UTF-16BE。
- 我移除了**这个样本**的旧样式/字体表/旧正文扩展，以免旧字符范围及 font override 残留；其他样本不变。
- 我仅修改该轨 stsz 的样本大小、stco 的 chunk 偏移、tkhd 的 enabled 位，
  并把 stsd 的等长 Pascal 字体名 Geneva 改为 SimHei。字体配置只是本次中文候选，通用工具不固定中文字体。
- 新文本放到文件尾追加的 mdat；旧 mdat、所有音视频轨和原 stts/stsc 时间/分块表不变。
- 工具只支持已确认的 version-0 tkhd、32 位 stco、一个样本/chunk 和一个 description。
  扩展大小 atom、其他分块结构及未知版本明确报错；这是实验工具，不是任意 MOV 重封装器。
- 修改副本 57,350,620 字节，SHA-256
  `801bde6cf281127800348c256abab4e653d5c15acd160d75173aaadc7124ff3a`。
  原版 57,350,582 字节；独立副本回滚后完整 SHA 与原版一致。

**已验证（旧 QuickTime 原生打开，不是现代 ffprobe）**：我用 32 位只读探针
`tools/validate/quicktime_open_probe.cs` 加载本机 GOG 的 QTSystem/QTMLClient.dll，
没有启动游戏或播放窗口。原版、副本、回滚副本均成功打开 6 条轨道：原版文字轨 3/4
均关闭；实验副本轨 3 开启、轨 4 关闭；回滚恢复原状态。Python 回读新样本为正确中文。

**未验证**：旧 text handler 的中文实际绘制、字体解析/缺字、字宽、位置、换行、透明度、
暂停/跳过/切换/结束稳定性，以及游戏是否按上述静态路径重新关闭轨道。
“QuickTime 能打开”和“中文能回读”均不等于“中文字幕已经在游戏里显示”。
我没有安装该副本，没有重编码音视频，没有改 EXE/DLL、原视频或当前汉化运行目录。

## 重现实验

在仓库根目录运行，输出目录须事先建立，目标文件必须不存在：

```powershell
New-Item -ItemType Directory -Force build/fmv-research
python -m tools.pack.movie_text_probe build --input "GAME/Movies/Intro.mov" --config locales/zh-CN/fmv_probe.json --output build/fmv-research/MODIFIED_FILE.mov --diff build/fmv-research/DIFF_FILE.json
python -m tools.pack.movie_text_probe probe --input build/fmv-research/MODIFIED_FILE.mov --track 3 --sample 1
python -m tools.pack.movie_text_probe restore --input build/fmv-research/MODIFIED_FILE.mov --diff build/fmv-research/DIFF_FILE.json --output build/fmv-research/rollback-copy.mov
python -m unittest discover -s tests -p test_movie_text_probe.py -v
```

原生只读探针使用 Windows .NET Framework 4 的 csc，必须 `/platform:x86`，不随补丁安装：

```powershell
& "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe" /nologo /platform:x86 /out:build\fmv-research\quicktime_open_probe.exe tools\validate\quicktime_open_probe.cs
& .\build\fmv-research\quicktime_open_probe.exe "QT/QTSystem" "FULL_PATH/Intro.mov"
```

探针需要用户已有的 QuickTime 运行库；路径作为参数，不复制或发布运行库。
输出固定注明 `rendering=NOT_TESTED`。实验差分及四项本地记录保存在忽略的 build/fmv-research，
不把完整视频或原版对白提交到仓库。下一步先离屏绘制一条中文并检查实际字形，
再验证独立字幕选择，不急于批量翻译/重封装所有视频。

格式依据：[Apple legacy text sample data](https://developer.apple.com/documentation/quicktime-file-format/text_sample_data)
说明字节长度及样式扩展；[Apple text sample description](https://developer.apple.com/documentation/quicktime-file-format/text_sample_description)
说明默认文字区域及 Pascal 字体名。格式文档不替代旧运行库实测。

## 独立 1080p 原生字幕预览入口

我已经进一步验证实际绘制：此前仅带 BOM 的 UTF-16 副本**确实会乱码**。
这纠正了“能回读就可能直接显示”的假设，但不删除前一阶段的打开实验记录。
Apple [QA1400](https://developer.apple.com/library/archive/qa/qa1400/_index.html)
指出 Text Media Handler 还需要 Unicode 编码属性，并建议指定 media language。
我在新样本追加 12 字节 `encd` atom，其 32 位大端值为 `0x100`
（kTextEncodingUnicodeDefault），并把该轨 mdhd 的 Mac 语言码设为 33。
**已验证**：旧版 Windows QuickTime 在 1920×1080 离屏帧中实际画出了
“中文字幕显示测试：时光之轮”，不是另用 GDI/HTML 叠字伪装原生字幕。

新副本大小 57,350,632 字节，SHA-256 为
`65cb0fa434398f73ea6e5af77efb47ff13b21ae868e1eba2dc5ae5372c02310f`。
旧 BOM-only 副本留在 build/fmv-research 作为实验记录；新的可测试副本在 build/fmv-preview。
通用样本生成器现在写入 encd；中文媒体语言码和 SimHei 字体名仍只在 locale 配置中。
Windows 字体由用户系统提供，不复制或发布微软字体。

独立播放器 `tools/validate/quicktime_player.cs` 用 QTMLClient 原生解码和文字 handler
画入 32 位 ARGB GWorld，WinForms 只展示已生成的像素，不另行翻译/绘制字幕。
我在内存中单独启用第一条音轨（本版英语）及第一条文字轨，关闭自动 alternate 选择；
字幕 matrix 的 Y 平移为视频高度，得到 640×500 的视频+文字区域，再等比缩放至 1080p。
这些是**测试播放器**内的设置，没有修改 WinDrv.dll，没有证明游戏原入口已经能显示。

我还修复了关闭文字轨时出现白色条带的问题：GWorld 的 QuickDraw 背景色必须设为黑色。
同一播放器实例的开启/关闭/重播/样本前空白测试通过，字幕区域亮像素分别为
2966/0/2966/0；开启与关闭的帧差仅在 `(795,1037)–(1128,1062)`。
独立回滚恢复原 MOV 完整字节，原版与回滚的原生截图像素也一致。
原来的五条其他轨、48 个其他字幕样本、旧 mdat 均未改动。

### 构建与启动

```powershell
python -m tools.build.build_fmv_preview --game-dir "GAME" --locale zh-CN
# 若注册表未提供运行库路径，显式追加 --qt-dir "QT/QTSystem"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "FULL_REPO_PATH/build/fmv-preview/PLAY_FMV.ps1"
```

构建命令不自动播放，也不安装进游戏。需要 Windows .NET Framework 4 的 32 位编译目标，
以及用户已有的 GOG QuickTime 运行库。入口先校验测试 MOV 与播放器 SHA。
未知 MOV 原版 SHA、未知生成文件内容均报错，不覆盖原版或静默采用其他版本。
现有生成物不同则改用新的 `--out` 目录；相同的 JSON 允许 CRLF/LF 排版差异。
脚本仍可以从干净仓库加原版游戏目录重建，不依赖此前研究副本。

### 我的测试清单

1. 运行 PLAY_FMV.ps1，**不是游戏启动命令**。观察第 1–7 秒的一条测试中文，随后它应被下一条样本替换。
2. 后续仍是原字幕轨的意大利语内容；这个入口只有一句中文，不是正式全视频汉化。
3. 用空格暂停/继续，R 从头重播，C 关闭/开启字幕，Esc 退出窗口。
4. 确认英文配音、口型/画面、中文缺字/裁切、字幕切换与窗口退出，截图记录异常。

**已验证**：原生离屏中文字形、ON/OFF 清除与重播、空白时间段、回滚、启动脚本解析与哈希、
172 项自动测试。**待实机验证**：可见窗口实时播放流畅度、实际听到的配音、手动按键、
全片结束、游戏内原播放器接入。默认游戏构建仍未安装视频，不能将此入口等同成品补丁。

我另外运行了静音的离屏时间钟测试：StartMovie 后时间前进，StopMovie 后保持不动，
跳回开头以及跳转片尾后的 IsMovieDone 状态均通过。首个 300ms 固定等待窗口曾因启动延迟失败，
加入 Windows 消息处理并延长到 700ms 后观测停止/暂停时间同为 2.250 秒。
这验证受控启停与片尾路径，不替代完整观看、实际配音听感或可见窗口验收；正常 play 模式不静音。

## 下一阶段顺序：游戏内最小验证优先

我暂不开展整片翻译。独立播放器已经显示中文，接下来先用隔离 WoT.exe 的
“重播开场”验证 WinDrv 原生路径。三字节字幕选择 PoC、复制范围、启动与验收说明见
[游戏内 FMV 验证](FMV_GAME_QA.md)。没有修改原版安装；游戏内结果仍待实测。
