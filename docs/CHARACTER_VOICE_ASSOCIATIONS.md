# 波莱恩与凯琳：角色与语音关联审计

日期：2026-10-04。译名以根目录 GLOSSARY.md 为准。该次只读取原版资源，不启动游戏，不修改地图、语音或视频。

## 已验证事实

- 原版 WOT.u 制作人员数组：Poleine 对应 Carolyn Stewart；Kyrin 对应 Kathleen Bober。这是配音角色署名，不是台词索引。
- 本游戏地图扩展名是 `.wot`，不是 `.unr`。该次实际解析全部45个 `.wot` 包的名称表；Poleine 仅出现在 Mission_16.wot，Kyrin 未出现。前次仅扫描 `.unr` 的结果不覆盖实际地图，此次补齐。
- Mission_16.wot：导出1976（1-based）SitterGrey0，类 SitterGrey；Tag 属性（NameProperty）=Poleine，Event=LoseBigCounter；MultiSkins 的显式覆盖含 WOTPawns.Skins.JSitterBrown1。因此不能仅按 SitterGrey 的类名判断其画面服色或小说宗派身份。
- WoTPawns.u：SitterGrey 继承 Sitter；Sitter 的默认 SoundTableClass 指向 SoundTableSitter；SoundTableSitter 继承 SoundTableSister。该通用音效表继承链不等于 Carolyn Stewart 的逐条配音录音索引。
- Mission_16 的 AnimationDispatcher0/1/2/4/5/6 含 DialogA.Grn_01～Grn_05 引用。按 AnimationEvent 中的 AnimationSourceTag 解码，目标是 wounded01～wounded06，而非 Poleine，不能把这些声音直接归给波莱恩。
- WOT.u 的 AnimationDispatcher.ScriptText 与原编译资源保存了实现证据：按 AnimationSourceTag 查找 Actor，再通过 AnimationSource.PlaySound(EventList[i].Sound) 播放。故映射须核对具体目标 Tag，不能只按同关卡、空间距离或声音前缀判断说话人。
- 原版、社区及安装后 `.int` 中均没有这两个名字的文本命中；这不证明角色没有说话，也不证明字幕缺失。

## 高可信线索（非本地资源确认）

2000年的独立西班牙语攻略将 Kyrin 描述为开场中与主角谈论白袍众的助手，并将 Poleine 描述为后期防守场景需要保护的人物。前者支持“凯琳属于开场过场配音”的调查方向，但攻略是二手资料，不是字幕/语音绑定的最终证据。原版 Movies 中存在 Intro.mov、Mission_00.mov 等 QuickTime 文件；该次未播放这些文件，未将具体视频文件与凯琳绑定。

参考：https://dardoaventuras.com/aventura/Eresmas/WheelTime.html

## 仍未验证

- 哪些具体声音由 Carolyn Stewart 为波莱恩录制；通用 Sitter/Sister 音效不自动等于此角色的专属台词。
- 凯琳对应哪个视频、哪几个时间段，以及这些对白是否已经被现有视频字幕方案覆盖。
- 预渲染片段与游戏内 NPC 是否共用配音素材。

## 后续最小验证

1. 按视频启动事件与已有过场研究记录确定开场实际使用的文件，再逐句核对凯琳的发言；不自动整部转录或重编码。
2. 继续追踪 Poleine Tag 的剧情事件及继承的音效表；将情节对白、战斗喊声、受伤/死亡音效分开记录。
3. 只有完成目标 Actor/片段/字幕 key 的证据链后，才登记明确说话人。资源标识 Poleine/Kyrin 不汉化；玩家可读文本仍统一为波莱恩/凯琳。

## 输入指纹

- `Maps\Mission_16.wot`：5281706 bytes，SHA-256 `05d5cc5d086d26d102c0cccaaf26967084582cc9319b8a7ab14f33c363385eb5`
- `System\WoTPawns.u`：17136920 bytes，SHA-256 `b72f1ae59c2216305890d1a628e7e946eec42509d3d1708f0ce7d146457058af`
- `System\WOT.u`：9588318 bytes，SHA-256 `8e670c5b58110a31367029a9801ad38c89a587aa82d1786dec4451815b7746fb`
