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
以1080p优先，并覆盖1366x768/2560x1440的菜单帮助、Inventory与字幕折行；
长句不能只通过字符数判断不截断。4K不再作为当前验收目标。
原版 UI 使用固定像素字体；4K 变小属于需记录的可读性问题，不是编码失败。

## 字幕与术语

源字幕计时按 Len；配置可保留原文长度，由构建器生成引号内尾 ASCII 空格。
**译文文件不要手工补空格**；此方法只避免短译文明显缩短，不是精准音频同步。
当前十九条为技术 PoC 草稿；新增12条仅覆盖主菜单及Controls少量字段。人名、地名、法器/技能名以 glossary.json 的审校版本为准，
当前 glossary 是候选词，不冒充官方译名；正式翻译前评审并冻结一致写法。
没有英文原文的空字幕不能根据 key 编造对白，不自动转录全游戏。

## 添加其他语言

复制 assets/templates/locale-config.json 至 locales/<locale>/config.json，
填写 locale、profile、encoding、font.baseline_anchor 和 TTC 索引；
新增 strings.json、glossary.json。baseline_anchor 是该语言字体对齐的代表字形，
例如具体语言维护者选择的汉字/假名/韩文字，不写入通用代码。
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

locales/zh-CN/strings.json保留此前正式19条draft，不重新翻译或覆盖。旧游戏work/phase5/test_translations.json的7条测试译文整理为research/phase5-strings.json，保存ID/控制符和原文SHA/长度，不收录完整英文原表，也不自动并入生产表。其帮助文是历史实验变体，与当前帮助译文不同；审稿时人工选择，避免同时回填同一ID。
