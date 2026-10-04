# FMV字幕调查（2026-10-04）

## 已验证事实

旧研究脚本mov_text_export.py已有文字轨发现；本轮复核原版，并整理为tools/extract/movie_text.py，不依赖旧工作目录或硬编码ffprobe路径。未修改视频，未转录整部游戏。

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
