# 字形顶部与教程字幕位置修复

日期：2026-10-03；输入为66eeeec的37条草稿，译文保持不变。

## 根因与修改

1. **已复现字形裁剪**：微软雅黑14px，“汉”bbox top=4，“重”top=2。旧实现以“汉”顶部为所有字形的绘制原点，先写入14×14小画布，“重”顶部两行墨迹被丢弃。当前233个字形中还有其他顶部/底部超界，不能只修一个“重”。
2. **完整栅格与行高分离**：收集全部实际用字的共同bbox，保留标点bearing；先对照64px边框参考画布检查完整源墨迹，然后按共同纵向比例Lanczos适配原版行高（14/30/7/15/14/8）。这是整体抗锯齿适配，不是裁掉超界行，也不声称像素无损。ASCII原始映射与位图不变。
3. **已复现字幕贴顶**：BaseHUD.DrawMessages源码计算Y=ScaleValY(24)，但字幕仍用Canvas.SetPos(0,0)。当前仅将该调用的float32 Y常量0改为固定24原生像素，不改变字幕原文/Len计时、分支、跳转、函数长度或玩法。
4. **工程化保护**：坐标字段由语言无关profile驱动，工具检查原版资源hash、完整Function hash、上下文、原值和等长读回；不修改EXE/DLL。完整资源包的脚本字节码现在有这一项显示常量修改，不能沿用以前“全部字节码不变”的结论。

字段：WOT.u导出5095，BaseHUD.DrawMessages，body+1979；原包绝对992669仅供研究参考。2614字节函数，00000000→0000c041，float 0→24。最终改变六个Font与一个Function显示字段，8370个其他原导出逐字节保持；三个.int与上轮构建逐字节一致。

## 被拒绝的候选

第一版扩大中文字形矩形，完整笔画恢复且字幕移到下方，但Controls左右两列行高不同、累计错位；中文字行高比原“X”大，单行帮助被误判为多行而取消居中。该候选不作为最终输出，本地build/glyph-layout/candidate与native-after证据保留。最终方案使用技术profile.font_line_height_policy=preserve-legacy，与具体语言分离。

## 1080p验收

- 修复前：主菜单、Inventory、教程字幕各一次；截图显示教程字幕紧贴顶部。
- 最终版：主菜单、Inventory、教程字幕、单人菜单、Controls各一次，共18帧均人工检查；Controls含11行帮助，教程为10/20/25/36秒采样。
- 当前“重”、中文标题/正文/斜体引文的顶部笔画可见；Controls两列重新对齐，帮助保持单行居中，未见当前样本新的空白/截断。
- 教程字幕不再贴上边缘；20秒帧中央80%金色像素带由桌面y=0..22移到y=51..72，辅助印证人工检查与24原生像素偏移。桌面3840×2160截图不代表4K测试，所有原生日志均为1920×1080。
- 五次最终探针正常退出0，68项自动测试通过，独立安装/回滚与同输入重建字节一致。
- 自动visual_review=pending与人工结论分开记录，不把正常退出当作视觉通过。
- 原游戏目录只读，旧5126文件审计不变。玩家配置不覆盖；副本INI恢复当前原安装配置。

结构与边界：[GLYPH_LAYOUT_STRUCTURE.json](GLYPH_LAYOUT_STRUCTURE.json)。
逐帧SHA/审查范围：[GLYPH_LAYOUT_QA.json](GLYPH_LAYOUT_QA.json)。
本地原始日志/截图及完整验证在被忽略build/glyph-layout；仓库不提交游戏资源或字体。

## 重现与边界

```powershell
python build.py --locale zh-CN --game-dir "GAME" --font "FONT" --out build/zh-CN
python build.py test
python -m tools.validate.runtime --game-dir "GAME" --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view subtitle
python -m tools.validate.runtime --game-dir "GAME" --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view options --sweep
```

运行runtime会启动隔离游戏。当前开发只检查1080p，其他分辨率安排在汉化完成后验收；4K仍是已知问题。固定24px不是响应式布局方案，其他字幕、多人HUD、完整存档/战斗/切图未全覆盖；37条译文仍为draft。
