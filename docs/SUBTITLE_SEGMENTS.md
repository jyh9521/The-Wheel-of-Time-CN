# 教程开场字幕分段（实验性资源模块）

> 历史开发与测试记录：下述测试数、待办、验收状态和产物名称对应记录时的构建，不代表正式版当前状态。v1.0 已完成完整通关测试且未发现补丁问题；正式文件为 `WoT-CN-v1.0.exe`。当前说明见 [项目主页](../README.md)、[安装说明](PORTABLE_INSTALLER.md)和[显示限制](KNOWN_ISSUES.md)。

## 已验证事实

Tes_01是31.251秒的单个WAV。社区来源有432字符，当前中文包含开场和第一次试炼说明；WOTPlayer.ClientHearSound一次调用SubtitleMessage显示整条文字，因此拼接后的补全文字必然提前出现，不能用缩短空格或新建无事件调用的字幕key修复。

Tutorial.wot的AnimationDispatcher4通过tutorial_1触发intro_text_01并播放DialogA.Tes_01；MessageTrigger19保留7条带//前缀的英语文字，MessageSettings中有相对延迟。MessageTrigger脚本跳过//开头文字且连Sleep也跳过，因此旧表中的24秒分段信息只是历史设计数据，不是现行运行中的计时路径。原地图与语音该阶段未修改。

仅对Tes_01的31秒片段运行本地已缓存的small模型进行时序辅助识别，没有转录整部游戏。识别结果与已有英文文本对应，专名采用已有文本而非ASR拼写。时间点仍属于需实机验收的估计：

| 相对语音开始 | 字幕 |
|---|---|
| 0.00–22.72秒 | 原开场段落 |
| 22.72–23.88秒 | 无字幕间隔 |
| 23.88–26.02秒 | 第一次试炼，面对的是过去。 |
| 26.94–28.76秒 | 归途只会出现一次。 |
| 28.76–30.82秒 | 坚定你的意志。 |

这些分段相连还原原有中文，未删除社区补全。字幕通过生命期自行消失；迟到帧跳过已经结束的段落，不把所有段落重新同时输出。其他声音按原路径播放；其他已本地化对白会取消待播序列。时间基于Level.TimeSeconds，暂停与掉帧等行为仍须实机测试。

## 实验模块与限制

新增LocaleRuntime.LocalePlayer继承原AesSedai，只重载字幕调度入口并委托原声音/玩家行为，不改原EXE、DLL、地图或语音。它是一个明确启用的实验模块，不是已经验收的正式默认补丁。修改玩家类的兼容性（状态、死亡、切图、存档、联网）尚未实机确认，当前只测试全新教程，不用于正式存档或多人。基础汉化构建与普通教程入口未被替换；不声称普通入口已自动分段。

工具、源码与语言数据分离：src/runtime/LocaleRuntime/Classes/LocalePlayer.uc、tools/build/subtitle_runtime.py、locales/zh-CN/subtitle-cues.json。UCC及必要输入SHA-256由profiles/subtitle-runtime.json固定；编译在独立build目录中完成，需要指定的原版输入，不再分发编译器或原包。GOG UCC命令为Editor.MakeCommandlet，不是未经注册的make；独立目录需要Default.ini和DefUser.ini及Engine.Engine.EditorEngine配置。编译退出0仍须核对Success字样与产物存在，避免“Commandlet make not found”返回0被误认为成功。

```powershell
python -X utf8 -m tools.build.subtitle_runtime build --game-dir "C:/GOG Games/The Wheel of Time" --locale zh-CN --out build/subtitle-timing-audit/fixed
python -X utf8 -m tools.build.subtitle_runtime apply --bundle build/subtitle-timing-audit/fixed/ADDON.json --target build/runtime
python -X utf8 -m tools.build.subtitle_runtime verify --bundle build/subtitle-timing-audit/fixed/ADDON.json --target build/runtime
# 完整退出游戏后，从隔离副本System目录启动专用测试入口：
.\WoT.exe "Tutorial?Game=LocaleRuntime.LocaleTutorial?Class=LocaleRuntime.LocalePlayer"
```

这一阶段只做了离线验证，未运行游戏，Class URL是否被当前单人模式接受以及实际逐段显示仍待实机确认；先查看System/WoT.log是否出现LocaleRuntime subtitle scheduler active。若未出现，记录为类选择未生效，不混同时间码错误。保持1080p。

退出游戏后用同一bundle执行restore，移除仅属于本模块、hash匹配的两个新增文件；不改原始文件或配置，不删除未知文件。旧差分汉化维持原状态。

## “Please stand back”调查

原版/社区.int、教程MessageTrigger文字和相关脚本未找到这句。开场Tes_01最后一句为Be steadfast，对应“坚定你的意志”，位于约28.76–30.82秒。开场AnimationDispatcher4只有一次Tes_01语音调用，Amyrlin模型类没有独立开门对白；候选Aes_Taunt6局部识别是笑声，未补造成对白。当前没有证明存在独立Please stand back句，不能据听音时的近似回忆添加未确认英文key。还需核对开门前后约10秒的录音或录像；若确是另一个声音对象，再沿该对象映射补全字幕。ASR只辅助定位，不替代音频核对。

## 原模式强制玩家类的静态发现

giTutorial继承giMission；giMission.Login强制WOTPawns.AesSedai，单独Class URL确定会被覆盖。因此增加明确选择的LocaleTutorial适配类，继承原教程规则，只在Login绕过强制原类的一层，委托giWOT的原登录路径并保留team=0、名字和AesSedai标签。专用URL必须同时指定Game与Class，不改地图DefaultGameType或默认INI。这一实验方案涉及玩家类选择适配，尚未实机验收；默认模式保持原样，不称为已发布修复。

## 编译与本地验证补充

100项测试通过；LocalePlayer与LocaleTutorial经原版UCC编译，0错误0警告，两个独立输出目录重建.u和.int逐字节一致。UCC随机生成的自有新包GUID在UE1 v68固定summary位置36..51按其余包内容SHA-256规范化；未改原包GUID，不是修改原引擎。独立目标安装、核验、回滚通过，修复生成物保留；原游戏目录5126文件未变。

两个新增模块文件已放入本地build/runtime/System，未改默认入口或配置，未启动游戏。测试必须使用本文的Game+Class URL；普通新游戏/教程仍走旧显示路径。各语音分段仍待1080p实机确认，尚未确认为正式修复。


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

## 2026-10-03 开场实机验收

通过专用Game+Class入口重测独立字幕时钟版，确认“现在没问题了”。这次实测确认了开场字幕的分段显示和出现时机；不扩展为存档、切图、死亡、联网或全部剧情字幕通过。普通菜单入口仍未替换。
