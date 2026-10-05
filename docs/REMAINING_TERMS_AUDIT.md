> 历史审计快照：下文保留批准前证据与建议。当前处理结果见文末，唯一有效术语以GLOSSARY.md为准。

# 剩余术语与英文残留审计（2026-10-04）

## 该阶段范围与结论

这是审计与待确认记录，不是第二份正式术语库。唯一术语基准仍是根目录 [GLOSSARY.md](../GLOSSARY.md)。该阶段没有把建议自动升级为已确认译名，没有修改任何译文、原文hash、控制符、构建资源或游戏文件，没有启动游戏。

按社区优先来源策略组合strings、subtitles和subtitle-overrides，审计1002条实际生产文本（覆盖表的相同ID不额外计数）。扫描整条英文与中文内部的拉丁字母，逐项区分专名、按键、缩写、受保护标记与诊断标识，并与词表待确认项交叉检查。

- 12个英文待处理专名，涉及22个不同文本ID。
- 6组已有中文草稿但尚未正式确认的名称，与上述12项合计18组主要命名待办。
- 已有的语境草稿和普通元素词另列，不能因为不含英文就忽略。
- 该次覆盖当前核心生产目录，不声称视频、地图实例或硬编码文本已全部盘点。

## 1. 英文待处理专名：完整清单

“推荐处理”是该阶段审计意见，不是已经回填的译文。只有确认后才统一更新GLOSSARY并回填。标注“资料线索”的网页不是出版社原页，不能据此宣称纸质出版版逐页认证。

| 英文 | 推荐处理 | 当前出现位置 / 条目数 | 核对结果与需要决定的问题 |
|---|---|---|---|
| Cuendillar | 昆达雅石 | WoT.int：Seal、SealInventory的Title/Description；AngrealInvBalefire.Description，共5条 | 灰机Wiki《光影歧路》使用昆达雅石，公开中文名词资料也给出对应；不要把材质名称直接译成特法器。[S1][S2] |
| Manetherendrelle | 曼埃瑟兰河 | MissionObjectives01.Title/Content[3]、WOTTransitionMapInfo00.NextText，共3条 | 网上转载的中英名词表有该对应；属于待出版版复核的资料线索，不是新造音译。[S3]；后续回填注意避免“曼埃瑟兰河河岸” |
| Machin Shin | 黑风 | MissionObjectives08.Content[9]/Content[11]、AngrealInvIllusion.Description，共3条 | 英文Wiki明确同指Black Wind；当前相邻任务已有“黑风”译文。建议统一别称而不另造音译；此建议是跨资料与游戏语境的推断。[S4] |
| Mountains of Mist | 迷雾山脉 | MissionObjectives15.Content[4]、WOTTransitionMapInfo12b.NextText，共2条 | 查到相关中文用法及小说转载线索；不把其他作品的同名山脉当作本游戏的证明。[S5][S6] |
| Cerist | 瑟瑞斯特（候选音译） | MissionObjectives12.Content[3]/Content[10]，共2条 | 游戏人名，原文指临终告知探险队去向的女性；游戏演职员表可核对拼写，未确认中文出版既定译名。只提出这一种候选，不回填。[S7] |
| Sephraem | 瑟芙蕾姆（候选音译） | MissionObjectives17.Content[3]，共1条 | 游戏人名，原文明确称该角色为叛徒；演职员表可核对拼写，未确认既定中文译名。只提出这一种候选，不回填。[S7] |
| Halfmen | 半人（待确认别称） | AngrealInvChampion.Quote，共1条 | 小说引文中的Myrddraal别称，应先确定是否保留出版别称；不是新怪物。已定Myrddraal → 魔达奥不覆盖、不改写；当前中文出版别称证据仍需补强。[S8] |
| Bornhald | 伯恩哈 | QuestionerInventory.Quote，共1条 | 灰机Wiki主要人物列杰夫拉·伯恩哈，此前参考的人物清单也有Bornhald对应；该句只出现姓氏，不擅自补全名字。[S9][S10] |
| Elaida | 爱莉达 | SitterInventory.Quote，共1条 | 灰机Wiki主要人物及多本书籍页面使用爱莉达；双语中文资料也能核对Elaida身份。[S9][S11] |
| Chosen | 暂待核对出版尊称，不直接并为“弃光魔使” | DialogA.Myr_14/Myr_25，共2条 | 暗影阵营对白的尊称，不是普通chosen动词。现有网上旧译文章虽有中文线索，但译名体系不同，暂不据此锁定。源文WarderInventory.Description中的chosen是普通“被选中”，不算本专名。[S12] |
| The Hand of the Light | 圣光之手 | QuestionerInventory.Description，共1条 | 灰机Wiki《裁判团》明确记录自称圣光之手。[S13] |
| The Hand that digs out Truth | 挖掘真相之手（候选描述译法） | 与上项在同一Description，共1条 | 灰机Wiki解释其挖掘真相的自我描述，未确认这句扩展称谓有固定出版短名；不要凭空把它当成另一组织。[S13] |

条目计数按ID，不按单词出现次数；两个Hand称谓位于同一条说明，因此上表加总为23次“术语-条目对应”，但只有22个不同条目。

## 2. 已有中文草稿：一起确认，避免下一轮再漏问

| 英文 / 游戏资源身份 | 当前唯一草稿（建议沿用） | 需要确认的边界 |
|---|---|---|
| Elayna | 伊莱娜 | 游戏主角；与小说Elayne → 伊兰不同，不合并。[S7] |
| Air Pulse / AngrealInvAirBurst | 气流冲击 | 名称是Air Pulse，AirBurst为不可翻译的资源标识 |
| Light Globe / Light Sphere / AngrealInvLightGlobe | 光球 | 当前同一套教程与物品资源沿用同一中文；是否还有别的实体仍以资源/游戏证据为准 |
| Fire Shield | 火焰护盾 | 已有名称草稿；火之力编织的元素译法已经确认，不等于物品名称自动另改 |
| Reflect | 反射 | 固定能力名与普通“反射投射物”的动词分开 |
| Fireball | 火球 | 固定物品名与普通火球攻击描述分开 |

## 3. 已译中文但仍需登记/语境复核的项目

这些已在GLOSSARY的待确认文字中登记，不属于12个残留英文专名，也不再机械计作“漏译英文”。

- Light（信仰概念）现用光明；Seal现用封印；Shadowspawn现用暗影生物。
- Great Lord / Dark Lord现依指代使用暗帝。指代已定Dark One时不另造同义名；尊称的叙事差异是否需要表现另待校对。
- Mother对玉座的敬称现用母亲，不表示生母；建议单独核对出版称呼后再锁定称呼规则。
- 裸词Earth/Air/Fire/Water/Spirit与已确认的“地/风/火/水/魂之力编织”分开审核。现有裸词草稿地/气/火/水/魂，不能误以为所有Air都属于元素编织，也不能未经确认就把全部气改为风。
- Questioner现用审问者；灰机Wiki组织页标题为裁判团、首领称至高裁判者。单位称呼与集团名并不必然相同；需确认是否把该单位正式名称调整为裁判者，确认前保留审问者，不覆盖现有词表。[S13]
- Trolloc Wars现用兽魔人战争；灰机Wiki历史页采用这一译法，可按已有资料统一登记。[S14]
- Black Wind现用黑风，建议与Machin Shin一起统一登记，而不是把它误列成不同实体。[S4]

## 4. 非专名的英文/拉丁残留

1002条中106条含ASCII拉丁字母，下面按优先级互斥分类，合计106，不能把它们全部报成未译英文。

| 分类 | 条目数 | 处理 |
|---|---:|---|
| 待处理英文专名 | 22 | 上面12项 |
| 按键/技术缩写 | 29 | Enter、ESC、TAB、F1/F2/F3、WASD、ISDN、56K等；键帽字母不是漏译专名，回车键等说明可在后续UI统一校对 |
| 受保护片段/控制码 | 50 | 多数是%b等；不能因扫描出字母就删除标记 |
| 编辑器/诊断标识 | 3 | WOTEd、ServerSpawn()、MyrddraalSwordAngreal；原始资源/函数名与可读文本分层，是否实际出现须另核对触发路径 |
| 通用模板标识 | 1 | MissionObjectives.Title中的“任务XX”，不是人物名 |
| 残留测试标记 | 1 | menuSinglePlayer.HelpMessage[1]结尾的END-123，原文没有这个标记；是应清理的测试遗留，不是需要命名的术语 |

受保护50条中，下面3条有明确可读英文正文，另列技术待办：

1. AngrealInvDistantEye.Description：@forget@。
2. AngrealInvMinion.Description：@grunt@。
3. AngrealInvAbsorb.Quote：@The flows just... vanished.@。

@Fire@、@Message@可能涉及键绑定/格式替换，不与上述普通词混为一谈。当前保留不是证明这些标记都不可翻译；需要先追踪文本窗口的@处理逻辑，再对引号样式与替换语法分层、调整保护器并回归测试。该阶段不删除或翻译这些片段。

## 5. 后续来源的边界

英文剧情资料还提到Poleine、Rislyn，但它们在当前1002条生产来源中没有字面命中。它们属于以后视频对白来源调查的新增待查角色，不把网上剧情摘要当成当前游戏字幕原文，也暂不编造中文名字。[S15]

本清单是“当前生产译文 + 当前词表已登记待确认项”的完整交叉审计；不是全游戏视频/地图原文都已恢复的证明。遇到后续新增来源，应对新来源做同样扫描与去重。

## 6. 证据、复现与保护

本地审计产物：build/remaining-terms-audit/AUDIT.json。包含全部106条Latin命中ID、分类、源文hash、译文快照、各候选词的源文引用及输入目录hash。不提交完整英文资源表。

运行本地审计脚本：

```powershell
$env:PYTHONPATH=(Get-Location).Path
python -X utf8 build/remaining-terms-audit/scan.py
```

脚本属于该次忽略目录中的研究辅助，不是承诺长期维护的生产入口。该命令重建只读扫描快照；分类表由该次逐项审核产生，不将正则表达式匹配冒充语义审核。专名扫描不能只使用Unicode的\b边界，因为中文紧贴英文时也属于\w，会漏掉Cuendillar封印等形式。

所有生产译文、覆盖表及GLOSSARY在该阶段开始/结束时均作SHA-256比较，保持一致。后续确认后，只将确定规则归入GLOSSARY，并由原构建器完成回填/字库/验证，不在本报告另维护生效词库。

## 参考资料

- [S1 光影歧路（灰机Wiki）](https://twot.huijiwiki.com/wiki/光影歧路)：昆达雅石用法。粉丝资料，不是出版社原页。
- [S2 时光之轮词汇资料（百度百科）](https://bkso.baidu.com/item/时光之轮/8814343)：Cuendillar对应，辅助线索。
- [S3 中英译名对照表网络转载](https://3g.99csw.com/book/7929/274468.htm)：Manetherendrelle对应；仅术语线索，出版版尚未逐页核验。
- [S4 Machin Shin（英文粉丝Wiki）](https://wot.fandom.com/wiki/Machin_Shin)：同指Black Wind；不据此声称中文出版音译已确认。
- [S5 Mountains of Mist中文用法线索](https://zh.wikipedia.org/wiki/迷霧山脈)：只使用末尾对乔丹作品的明确指向，不混入托尔金设定。
- [S6 世界之眼第26章网络转载](https://99csw.com/book/7927/274324.htm)：迷雾山脉中文用法；不是出版社原页。
- [S7 游戏演职员表](https://www.mobygames.com/game/637/the-wheel-of-time/credits/windows/)：Elayna、Cerist、Sephraem英文拼写；不提供既定中文译名证明。
- [S8 英文名词资料转载](https://www.yingyuxiaoshuo.com/book/253b126c66e417d1/chapter/51)：Halfman/Myrddraal别称关系；中文别称还需核对。
- [S9 主要人物（灰机Wiki）](https://twot.huijiwiki.com/wiki/主要人物)：伯恩哈、爱莉达。
- [S10 参考的繁中人物清单](https://www.ptt.cc/bbs/Fantasy/M.1570904515.A.61A.html)：Bornhald姓氏对应。
- [S11 双语世界之眼剧情整理](https://thewheeloftime.fandom.com/zh/wiki/世界之眼)：Elaida/爱莉达对应。
- [S12 旧译体系介绍](https://www.trzj.org/stories/article/a-brief-introduction-to-wheel-of-time/abitwot-1/2/)：Chosen相关语义线索；与项目当前译名体系不同，不直接引入。
- [S13 裁判团（灰机Wiki）](https://twot.huijiwiki.com/wiki/裁判团)：圣光之手及挖掘真相的描述。
- [S14 历史（灰机Wiki）](https://twot.huijiwiki.com/wiki/Portal:历史)：兽魔人战争用法。
- [S15 游戏剧情资料（英文粉丝Wiki）](https://wot.fandom.com/wiki/The_Wheel_of_Time_(video_game))：后续视频角色线索。

网页核对使用当次可检索内容；部分直达词条未返回正文，因此没有将这些页面写为已验证证据。没有获得纸质出版物或出版社完整术语表；以上明确区分资料线索、身份推断、现有草稿和待决定命名。

## 批准后的解决结果（2026-10-04）

已采纳本报告的建议；剩余专名及六项原有草稿已移入GLOSSARY.md确认表。Chosen两句敬称采用“获选者”，普通chosen按语义译“被选中”并加入精确源文hash例外。Questioner单位统一“裁判者”；普通reflect动词保留“反射”且不强制能力名匹配。Mother玉座尊称保留“母亲”，不表示亲缘。

该批修改28条正文，包括已批准专名、风元素标签、教程帮助测试尾标及三段可读@文本；原有源文ID、hash、长度及tokens未改变，仅三条新增经过源文预检的literal_token_translations/markup_delimiter_count注释。END-123已移除，帮助文案重新按英文原义整理。不改原版游戏、不改EXE/DLL，不启动游戏。已存在的教程独立计时插件不变。

该批不宣称视频、地图内嵌字样或所有硬编码英文已经清零；Enter/ESC/WASD等键名和WOTEd、ServerSpawn()等标识继续保留。核心1002条仍为draft而非实机全面reviewed，完整流程QA仍是发布条件。
