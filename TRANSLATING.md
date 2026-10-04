# 翻译规则

## 来源、格式、编码

原文从自己持有的原版 `.int` 导出。JSON 是 UTF-8；CSV 为 UTF-8 BOM。
locale 中的 strings.json 使用：file、section、key、occurrence、source_sha256、source_length、
tokens、translation、status（draft/reviewed）。原文散列按解码后的精确 UTF-8 文本计算，
不去掉引号内尾空格。完整原文仅在本地导出目录，仓库不收整包英语资源。
游戏目标编码由 config.json 设置；已实测本 GOG `.int` 使用 UTF-16 LE BOM。
无 BOM 的英文高字节目前按 cp1252 解释，检测报告应写“assumed”，不能仅凭字节猜测认证。

ID 由 `(file, section, key, occurrence)` 组成，重复英文可以共享翻译建议，但回填不能合并 ID。
转换工具接受导出的 CSV 或 JSON；空 translation 保持原值，strict 校验视为待完成。

## 换行、占位符、控制符、富文本

- 不输入实际 CR/LF、NUL、双引号；当前 line-based importer 明确拒绝未验证的语法。
- 保留 `{0}`、printf（%s/%d 等）、`$n`、`^xx`、`<tag>`、`\0`、反斜杠转义、
  `@Name@`、WoT `%f=2`、`%b` 等标记，默认数量和顺序完全相同。
- 未知控制代码也先保留。当前扫描器不能证明枚举了所有语法；遇到未识别的 `%...`、
  反斜杠、标签或异常控制字符，记录来源，扩展检测器与测试后才导入，不能先删除。
- `\n` 等字面转义保留原样，不承诺引擎一定把它变成换行。游戏 Canvas 自行折行。
- `[Public] Object/Preferences` 为结构化注册信息，当前禁止整值翻译。
  类名、对象路径、包名、音频对象名、资源引用、输入 alias 不可当正文翻译。

## 长度 / 槽位 / UI 宽度

当前 `.int` 回填为可变长，不存在已经证实的固定字节槽；不要捏造固定槽限制。
BMP UTF-16 对本实现一个字形对应一个代码单元；非 BMP 与代理区间明确拒绝。
默认 4096 字符是工具防误输入上限，不是已证实的引擎最大长度。
可针对条目设置 max_characters 或 max_bytes（包含目标编码 BOM）作为项目约束。
设置 sync_group 可要求关联条目译文一致；未知关联需先调查，不自动猜。

字宽由生成矩形宽度决定，正体为配置像素尺寸，斜体包含剪切余量，非 TTF proportional advance。
后续只在1080p检查菜单帮助、Inventory与字幕折行；其他分辨率延后由我验收；
长句不能只通过字符数判断不截断。4K不再作为当前验收目标。
原版 UI 使用固定像素字体；4K 变小属于需记录的可读性问题，不是编码失败。

## 字幕与术语

源字幕计时按 Len；配置可保留原文长度，由构建器生成引号内尾 ASCII 空格。
**译文文件不要手工补空格**；此方法只避免短译文明显缩短，不是精准音频同步。
当前49条为技术PoC草稿；此前37条含19条起始文本、Controls其余8项标签和10条帮助，该阶段新增12条教程字幕。人名、地名、法器/技能名及所有专有名词严格以根目录[GLOSSARY.md](GLOSSARY.md)为唯一术语基准，翻译、校对和发布说明开始前必须读取。旧glossary.json仅保留兼容指针，不再维护独立词库。未收录专名先查项目资料和中文Wiki，未确认则统一记入GLOSSARY.md的待确认清单；语境冲突先报告，不覆盖已定词条。
没有英文原文的空字幕不能根据 key 编造对白，不自动转录全游戏。

## 添加其他语言

复制 assets/templates/locale-config.json 至 locales/<locale>/config.json，
填写 locale、profile、encoding、字体padding和TTC索引；
新增 strings.json；术语与语言对应关系仍统一维护在根目录GLOSSARY.md中，不建立并行词库。字形边界由全部实际用字共同确定；旧baseline_anchor仅兼容覆盖检查，不控制对齐。
提供 cmap 覆盖该语言的字体；现工具只覆盖 BMP、无复杂 shaping/bidi 实现。

```powershell
python build.py validate --locale ja-JP --font "D:/Fonts/source-font.otf"
python build.py --locale ja-JP --game-dir "D:/GOG Games/The Wheel of Time" --font "D:/Fonts/source-font.otf"
```

同样适用于 ko-KR / zh-TW。此接口可复用，不代表其他语言已实机通过。
审校后 status 改为 reviewed，再运行 validate --strict；字体检查必须传 --font。
验证会检查重复 ID、源文变化、已识别控制符、编码、BMP、长度、关联组、缺字；
传入 --game-dir 的 validate 会只读检查全部条目ID、原文hash、原文长度和控制符元数据（包括未译条目）。
回填先对所有原文完成预检，再写任何输出副本；后续再检查结构化元数据与重建后的资源关系。

## 迁移译文的保留

迁移时保留此前正式19条draft，不重新翻译或覆盖；后续Controls增补18条形成当前37条。旧游戏work/phase5/test_translations.json的7条测试译文整理为research/phase5-strings.json，保存ID/控制符和原文SHA/长度，不收录完整英文原表，也不自动并入生产表。其帮助文是历史实验变体，与当前帮助译文不同；审稿时人工选择，避免同时回填同一ID。

## 字形与上边距

不要通过添加空格/换行、裁切“重”等单字来补偿字体或字幕布局。工具收集译文字符后完整渲染，共同bearing保证句号位置，按游戏profile适配原行高；新语言仍需自行选择覆盖字体并在1080p验收。字幕上边距由技术profile的显示坐标字段负责，译文、长度补偿、标点与控制码不为此改写。

## 教程字幕增补

2026-10-03保留既有37条并新增Tes_02～Tes_13，当前49条draft；教程中文13/80。英语来源为本地原安装，中文时序与触发仍待1080p验收。参见docs/SUBTITLE_COVERAGE.md；全字幕覆盖是独立发布门槛，不凭中文显示PoC宣布完成。

## 外部来源字幕译文

新增locales/<locale>/subtitles.json，由config.subtitle_rows指定；只有启用--subtitle-source时加载。source_layer绑定已核验manifest.id；source_sha256、source_length及tokens来自保守合并后的英文，不能改成原版空字符串hash，也不能用中文文本充当英文长度。当前245条：12条draft，233条pending；基础strings.json的49条完整保留。补译后用同一--subtitle-source运行validate --font，完整验收前strict仍应失败。术语“暗影生物”等该阶段短句为候选翻译，需结合剧情与全局术语审校。

## 教程翻译批次（2026-10-03）

Tes_01～Tes_80已全部有中文草稿；该阶段追加67条，原49条保持。基础译文116条，启用社区来源时361条中128条已有译文、233条待译。文本完成不等于实机验收：这一阶段只做了离线验证，未运行游戏，完整教程及分支留待我在1080p检查。测试方法和80键清单见[TUTORIAL_QA.md](docs/TUTORIAL_QA.md)。本地差分预览包包含标准库安装器，安装/核验/回滚已验证；未发布公共Release。

## 开场缺段修正

Tes_01原非空文本也会缺段：该阶段仅经双source hash批准采用社区完整432字符，译文由subtitle_overrides组合，Len补偿使用432而非350。完整版教程构建需--subtitle-source；其余条目不动。详见[TUTORIAL_INTRO_FIX.md](docs/TUTORIAL_INTRO_FIX.md)；80/80非空key不等于音频全段覆盖。


## 当前字幕来源策略（2026-10-03）
采用社区优先完整并集：所有同key冲突使用社区值，原版独有key保留。详见 [COMMUNITY_SOURCE_POLICY](docs/COMMUNITY_SOURCE_POLICY.md)。旧保守合并描述仅为历史记录。


## 术语校验与审校边界

config.terminology指向唯一Markdown词表及目标语言列。带--game-dir的build/validate在源文预检之后按该词表检查已译条目的已定术语；英文大小写、直/弯引号及常见复数可归一用于匹配，原文件文本不归一。较长专名优先匹配，避免ter'angreal误匹配angreal。无游戏来源时检查器仅核验词表结构，不能凭hash恢复英语。自动匹配不是语义审稿，新专名、泛称和上下文冲突仍需人工审核。待确认项保持草稿，不冒充confirmed；占位符等仍由原验证器按精确数量和顺序校验。

## 全表审计命令

除生产build/validate外，可使用同一词表对已导出的原文目录和指定译文目录进行只读审计：

```powershell
python -m tools.validate.terminology --glossary GLOSSARY.md --target-column 中文译名 --source-dir ORIGINAL/System --catalog locales/zh-CN/strings.json locales/zh-CN/research/phase5-strings.json --out build/terminology-base.json
```

社区译文和覆盖表应传入经profile核验的合并英文目录，不能用原版空来源替代。此命令同时校验控制符与来源元数据，不自动改译文。README和发布说明需人工检查专名语境，不以英文关键词扫描声称全部语义已验证。

## 非空草稿与完成度

历史首轮快照（以下保守处理已由文末精确审核更新）：2026-10-04首轮覆盖1002条核心玩家文本。未知专名保留英文并登记GLOSSARY，不用临时音译冒充既定译名。@forget@、@grunt@、@The flows just... vanished.@仍按现有保护规则原样保留，待证明其是否只是引号标记后再处理；不能为通过校验删控制符。validate的0空译文不代表全中文。运行tools.validate.text_coverage查看源文相同条目与遗漏，并逐项处理混合译文中的英文。

## 已确认能力名与语境审核（2026-10-04）

译名以GLOSSARY.md为唯一依据。能力名称与普通词义分开：Shift能力为瞬移，键名不翻译；Sister直呼为姐妹，单位/两仪师身份为两仪师；artifact先核对明确指代，未证实类型时不自动升级为特法器。五种元素编织采用词表规定的火/风/水/地/魂之力编织，单数和同义描述沿用。Sever/Fork/Unravel/Aura of Unraveling固定为隔断/分流/解构/解构领域。普通动作导致关键词误报时，必须在唯一词表记录精确ID与source SHA例外；当前爆裂结界解体及小说引文污染不是相应能力名称。

## 已审查的可读 @ 文本（2026-10-04）

已验证的调用路径：Legend.WOTInventory将Description与Quote声明为localized string；WOT.InventoryInfoWindow.Draw把两字段直接交给C.DrawText，Quote另设F_WOTIta14字体。Engine.Canvas.DrawText为native(465)，脚本层未对这三段执行名称/资源查找或变量替换。该证据支持将forget、grunt及The flows just... vanished.认定为玩家可读正文，而非资源ID。native层的@最终显示/引号处理仍未作实机确认，不将具体引号行为写成已验证事实。

该批仅处理AngrealInvDistantEye.Description、AngrealInvMinion.Description、AngrealInvAbsorb.Quote。逐行literal_token_translations声明审核过的source/translation带@片段；markup_delimiter_count保留整行@数量。源文件source_sha256、source_length、tokens保持原值；源文预检核验注释对应真实源文及分隔符数量，翻译校验把声明片段还原后比较全部控制码数量/顺序。正文与边界均保留，其他未知@片段不获自动豁免。禁止用这项机制放行%s、{0}、转义等真正控制码，或批量翻译未知@标记。相关负例测试见tests/test_literal_spans.py。

不要全局删除@保护，也不要把中文重新计算为source token/hash。之前三段英文原样保留属于历史保守处理，现由精确条目审核取代。正式字形、换行及物品信息界面显示仍由1080P实机QA确认。

## 图片按钮标签

只翻译我选定的Load/Play/Roam/Save按钮，分别为载入/游玩/漫游/保存；其他图像文字维持原样。八个对象身份不翻译，I/M配套纹理保持相同译文。标签布局在locales/<locale>/texture-labels.json中配置；当前64×64贴图的文字面板为[10,19,54,40]，字号16，超出面板则构建报错，不截断文字。新增语言可复用栅格化和P8回填工具，不把CP936或中文字形写死在通用代码中。不要通过扩大贴图或修改共享调色板绕过限制；另行研究后再改动。专有名词仍以GLOSSARY.md为准。

## 原生高级选项补翻（2026-10-04）

原生高级选项译文位于locales/<locale>/native-ui.json。Preferences只允许改Caption/Parent，并保留分类树链接；禁止改Class、Category、Immediate、Object和配置键。普通文案仍保留占位符及&助记标记。原生反射参数名不是可直接翻译的配置键，不机械替换。详情见[原生高级选项](docs/NATIVE_ADVANCED_OPTIONS.md)。

## 动态设置值

布尔开关的显示术语使用`WoT.int [menuLong] OnText/OffText`。不要翻译配置或脚本中的True/False，以及用于比较/写回的High/Medium/Low。显示适配由技术层完成，不新增与既有开/关重复的语言硬编码。玩家自定义名称、数字、设备/资源标识按具体用途保留。

## 原生属性显示表与制作人员页

native-properties.json的key是原属性/类别标识，只翻译value。values表只用于绘制的局部缓冲，不替换配置或下拉编辑器的机器值。未知标识原样保留，补充key须先确认对应属性含义。

credits.json以slot和原文SHA关联默认数组，保持原204条順序及` - `右侧原贡献者姓名、@标记、空白行。新增署名使用独立末尾行，不冒充原作者。专名按GLOSSARY.md；Poleine与Kyrin现已由我确认，统一读取GLOSSARY.md的波莱恩与凯琳；不得另造同义音译。

## 动态键名与教程提示

key-names.json的键是机器名，只改显示值，不改KEYNAME/KEYBINDING/SET Input命令。字母、数字、F键帽保留；Shift键不是能力瞬移。tutorial-prompts.json用actor/slot/source SHA关联原地图，覆盖所有实际可输出提示，保留F2/F5/F6/数字及原有前缀，不启用//注释对白。35条提示仍为draft，严格校验不得冒充审校通过。FMV导出原文暂留build，优先核对英文音轨而非把外语轨误当英文。

## 项目文档的口吻

项目说明、开发记录和发布说明以我（伯翎飞云）的作者口吻撰写。个人选择和实机测试写“我决定”“我测试时发现”，工具行为和技术事实直接说明，不写成对项目作者的第三人称汇报。面向玩家、开发者的操作说明保留读者视角；第三方贡献、引用和署名如实保留。调整措辞不改变历史数据，也不把离线检查写成实机通过。
