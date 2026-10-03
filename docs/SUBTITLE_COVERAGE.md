# 全字幕覆盖工程（2026-10-03）

目标：教程、主线剧情、NPC对白及剧情视频的中文字幕全部覆盖；仅让中文显示不是完成标准。当前未达到全覆盖。

## 已验证事实

- 本地GOG WoTsubtitles.int：897键，817空，80非空。空项也包含叫喊、受击等非语言声音，不能把817都当成缺失对白。
- **DialogA.Tes_01～Tes_80全部有英文文本**。Tutorial.wot静态引用47个DialogA语音，Tutorial_Citadel.wot引用17个，均能关联非空英文；另外16个Tes键不能据此说从不触发。
- 前一轮37条草稿只含Tes_01的中文。本轮保留原37条，新增Tes_02～Tes_13共12条，49条总计；教程中文13/80，其余67条待译。伊莱娜沿用既有Tes_01写法，仍待术语审校。
- 用户报告后续字幕不出现：**尚未复现与解决**，不能因为原文存在就宣称显示正常。本次检查原安装User.ini的bSubtitles=True，但这不证明用户运行副本使用同一配置。
- 1198个Sound导出与45地图的静态索引：80对应非空字幕、487对应空字幕、631无对应字幕键；330个字幕键未匹配当前Sound导出。计数是资源身份覆盖，不是对白/事件覆盖率，Sound分组按S.Outer.Name关联。
- 审计读取System的20个.u、Sounds的27个.uax、Maps的45个.wot及字幕表，共93输入，重读SHA不变。地图import仅证明关联，不解析触发实例、顺序、次数、动态加载或实际播放。

## 上游文本来源

TigerTheGreat于2022-04-17发布[OldUnreal全字幕补丁帖](https://www.oldunreal.com/phpBB3/viewtopic.php?p=100242)，作者说明填充游戏内字幕而不含QuickTime视频。本次网页可读取，但匿名附件不可见，需要维护者取得文件后再作比较。作者宣称全覆盖不是本项目实测结论；帖中也讨论了DialogA语音版本差异，必须核对输入hash。

旧研究目录的0_wotsubtitles.int再次比较：897键/80非空，可恢复候选0，**不是完整补全英语版**。其他语种表只能提供比对线索，不能直接伪造英语原文，也未接入生产构建。补丁作者署名与授权未核实前不作为本项目原创资源提交。

## 可复现工具

```powershell
python -m tools.validate.subtitle_coverage --game-dir "GAME" --strings locales/zh-CN/strings.json --out build/subtitle-coverage/current
# 可重复传--reference来比较用户自行取得的补全字幕文件
python -m tools.validate.subtitle_coverage --game-dir "GAME" --out build/subtitle-coverage/reference --reference "SUBTITLE_FILE"
```

COVERAGE.json包含输入大小/SHA、Sound身份、空/缺键、译文状态、静态地图关联、孤立键。不给静态记录标runtime_verified=True；case-insensitive重复键报错，不静默选最后一条。完整英文仍只在用户本地，不提交资源或原表。

## 接下来按顺序验收

1. 在1080p隔离副本沿教程实际触发Tes_02及后续对白，记录声音key、加载字幕资源SHA、字幕开关、出现/消失时刻。不能只停在开场36秒截图。
2. 完成80条教程翻译并审校，覆盖提示分支、长句折行、连续语音、暂停、死亡重试、关卡切换；未播放分支明确列待验。
3. 取得社区英语补全表，比较新增/空/多余/重复key，核对对应Sound与版本，保留来源与许可；按真实缺文项补录人工校对，不批量ASR整个游戏。
4. 区分场景音效/非语言叫声/可理解对白。为每条必需对白建立有来源文本、中文、音频关联、显示触发、时间覆盖的验收状态，不能用非空率代替。
5. 视频单列：已有研究17个MOV，其中14个有其他语言文本轨；不经WoTsubtitles.int。英文恢复、中文字幕播放方案和逐片核对待完成，不重编码视频。
6. 全字幕Release门槛：必需对白无未审校/无缺文/无未验触发；视频单独清单完整。当前Len计时/单槽覆盖仍需专项验证，必要时先证明缺陷再增加最小资源实现。

## 本轮验证边界

72项自动测试通过；49条源hash/编码/占位符/字体校验通过，331字形/字体、6字体、14新增纹理可构建；4资源安装/回滚一致，原版输入不变。新12条未进行实机逐条显示或音频同步验收，不沿用前一轮18帧结果证明新译文。

## 用户提供社区文件后的核对

本轮收到用户自行下载的WoTsubtitles.int，24,213字节，SHA-256 `d221624a71eae5fdd7c3a2f7ff8cf6541ef4b510f7c34e659ed8890128e7bae1`。结构为883键/325非空；与原版比较，242空键可补、3新增键、17原键省略、3已有文本变化（Tes_01/Tes_15/Tes_51）。这不是可以无条件整表替换的文件。

语言无关工具采用保守合并：仅填原空键，新增键须匹配本地Sound对象；原有非空文本始终保留，省略键不删除。245项全部匹配Sound，合并副本900键/325非空（575空），原80条非空保持，现有49条中文和源hash不变。其余空键/无键Sound仍需区分音效与对白；不宣称所有1198个Sound都是语音或325非空即全覆盖。

3新增键为Myr_GetHelp1、Myr_OrderGuardSeal1、Sis_OrderKillIntruder1；冲突、保留项、输入/输出SHA与每条新增原文SHA见[来源清单](COMMUNITY_SUBTITLE_SOURCE.json)。帖子作者署名沿用TigerTheGreat，附件再分发权限尚未确认：仓库仅保留原创工具与身份元数据，不提交完整社区英文表。

```powershell
python -m tools.validate.subtitle_coverage --game-dir "GAME" --out build/subtitle-coverage/current
python -m tools.import.subtitle_source --original "GAME/System/WoTsubtitles.int" --reference "DOWNLOADED_SUBTITLES" --inventory build/subtitle-coverage/current/COVERAGE.json --out build/community-subtitles/merged
```

已验证74项自动测试、93输入只读SHA与独立副本回滚；合并副本保留在build/community-subtitles/merged，原游戏和下载文件不变。**目前是英语恢复研究副本，不是中文全字幕补丁，也尚未接入生产build。** 后续需以外部参数配置带hash的来源层，在原版版本校验之后合并、翻译、校验、生成最终差分；明确处理新增键的源预检及长度来源，不用直接替换profile原版hash绕过检查。实机显示与同步只在1080p逐项验收。

## 来源层正式接入（本轮）

新增`build.py --subtitle-source PATH`，由profiles/subtitle-source.json固定社区输入大小/SHA及47个Sound承载包的大小/SHA。仍先验证原版四资源，随后在自动清理的独立临时目录复制.int、保守合并，再验证译文源hash/长度/控制符；最终差分始终以未修改原版为基线，不需要覆盖游戏目录或更改原版profile。

locale可配置subtitle_rows（本项目subtitles.json）；245条来源译文与基础49条分开保存。首批12条战斗短句为draft，233条待译：启用来源时294个条目、61条已有译文；默认构建仍只处理基础49条。未译来源文本保留恢复英语，不能把它描述成完整中文。所有原有49条保持不变。当前只绑定已审计的一份WoT社区来源，别的版本必须先添加/审核manifest，不静默接受。

extract、validate、build共用同一来源准备流程。extract的完整原文/CSV仅写用户本地build；仓库只存译文、身份、原文hash/长度/控制符。构建报告subtitle_source.production_build_integrated=true表示已接入产物，runtime_verified仍为false。

已验证82项合成测试；默认构建与上轮49条四资源字节相同；带来源的两次独立构建四资源相同；347字形/字体、6字体、15新增纹理；安装和独立回滚均一致。strict保持失败，不能把233条未译/草稿描述为完成。

1080p实机扩展采样10/20/45/60/90秒正常退出0；人工检查20/45/60/90秒，20秒首句可读且边距保留，之后仍停在起始场景，无字幕。没有移动，不证明Tes_02触发失败，也没有证明新增12条战斗短句已播放。完整教程路径、长句折行、字幕持续时间及连续声音仍待验。证据摘要见SUBTITLE_SOURCE_QA.json，原始截图保留本地build。

最后字体覆盖检查发现未译英文的弯引号U+2019也需要追加字形。启用来源时，字体扫描和cmap验证同时覆盖译文与实际保留英文，而非只扫描中文；最终347字形。前述90秒候选为346字形，保留其证据；最终字体另做1080p开场复测，后续触发仍未验。

## 教程翻译批次（2026-10-03）

Tes_01～Tes_80已全部有中文草稿；本轮追加67条，原49条保持。基础译文116条，启用社区来源时361条中128条已有译文、233条待译。文本完成不等于实机验收：本轮未启动游戏，由用户在1080p检查完整教程及分支。测试方法和80键清单见[TUTORIAL_QA.md](TUTORIAL_QA.md)。本地差分预览包包含标准库安装器，安装/核验/回滚已验证；未发布公共Release。

## 开场缺段修正

Tes_01原非空文本也会缺段：本轮仅经双source hash批准采用社区完整432字符，译文由subtitle_overrides组合，Len补偿使用432而非350。完整版教程构建需--subtitle-source；其余条目不动。详见[TUTORIAL_INTRO_FIX.md](TUTORIAL_INTRO_FIX.md)；80/80非空key不等于音频全段覆盖。
