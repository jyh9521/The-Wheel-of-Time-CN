# Controls 标签与帮助：离线扩充

日期：2026-10-03。基于迁移提交 `3df21560e62169101f0e2df7460a974e81e18758`，保持旧游戏目录只读。

## 范围

- 当前草稿从19增至37；前19条逐字段保持不变。
- 新增 `WoT.int / menuOptions / MenuList[4..11]` 共8项：始终鼠标视角、自动坡度视角、视角自动回正、准星、视角晃动、启用摇杆、血腥效果、玩家名称。
- 新增 `HelpMessage[2..11]` 共10条。标题与先前首3项/第1条帮助不重写。
- Controls合计23字段全部有draft译文；这不是完整游戏翻译率，也不是已审稿。
- True/False、准星索引、灵敏度等右列运行时值保持原样，不修改bool处理、键位alias、存档、地图或脚本。

## 离线验证

validate读取匹配原版并核对源ID、SHA-256、字符长度/控制符元数据；字体cmap覆盖检查通过。
按37条实际译文生成233个新增字形/字体，6字体、11张新增P8贴图；其他8371个原export与bytecode不变，原Latin映射/Page0保留。
重新读取全部int后确认只有37个所选字段变化，未选字段的ID/顺序/正文不变。
四个资源的差分在独立副本apply/verify/restore，另以可执行ROLLBACK.sh恢复；原版四输入仍匹配profile。合成测试46项保持通过。
严格校验应因37条未审稿失败，不能当成正式Release。

## 实机状态与下一步

**这一阶段只做了离线验证，未运行游戏。** 先前19条的1080p代表帧证据仍保留在menu-poc.md；不能用它证明该阶段新增字形或每条帮助已完成显示验收。

下一步使用隔离副本在1080p进入Controls，逐行观察；按Escape → Down → Down → Enter进入第一页，第n行追加n-1次Down。只选择条目，不按左右键或回车改变设置。观察11项标签、各帮助的换行/截断、原右侧值、原版同配置对照与正常退出；之后抽查1366/1440。4K继续列为已知问题，不适配。

## 重建

```powershell
python build.py test
python build.py validate --locale zh-CN --game-dir "GAME" --font "FONT"
python build.py --locale zh-CN --game-dir "GAME" --font "FONT" --out build/controls-poc
python -m tools.validate.integration --game-dir "GAME" --build-dir build/controls-poc --out build/controls-rollback
```

输入资源版本与字体授权要求仍见BUILDING.md及LICENSING.md。生成资源/差分/字库PNG只在本地build目录，不作为源码提交。

## 后续验收

本页保留当时的离线阶段结论。2026-10-03已完成Controls有限实机显示检查，范围、逐帧审查与未覆盖项见[CONTROLS_QA.md](CONTROLS_QA.md)；译文仍为草稿。
