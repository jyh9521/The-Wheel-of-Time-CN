# Controls 全部行显示验收

日期：2026-10-03。输入为 b09c00c 的37条草稿构建，不增译文、不修改字库/渲染器/脚本逻辑。

## 方法

新增语言无关 `--sweep`，行数由QA配置驱动。进入Controls后捕获第1行，再发送10次Down分别捕获其余10行，不发送Left/Right，不在条目上Enter，因此不改变选项值。普通单帧模式保留原标签/行为；未配置的视图拒绝sweep。离线计划为30次原/改探针，Controls每次含11帧，但计划不是执行结果。

完整隔离runtime从原安装历史文件名清单复制277个当前文件，不复制旧work/backup/tools/docs；原安装只读。每次原/改对照使用同一原配置，只在副本设置请求分辨率，完成后副本WoT.ini/User.ini恢复原配置。

## 该阶段结果

- 1080p修改版11张逐行帧均人工检查：11项标签、标题、11条帮助中文可见，当前文本未见空白、乱码或边缘截断；长帮助仍以一行容纳。
- 1080p原版第1/11行人工对照；右侧True/False、Medium、灵敏度、准星及晃动条保留原样。
- 1366×768与2560×1440各执行同样原/改逐行探针；人工抽查代表性长帮助及首/末行，具体审查帧见结果索引，不冒充逐帧OCR/全游戏验收。
- 三种best-match原生模式逐一与请求匹配；截图是3840×2160桌面捕获，不能当作4K内部渲染测试。
- 六次探针、66张截图，进程退出0；人工审查与自动visual_review=pending分开记录。
- 新增6项合成测试，总52项通过；资源差分独立安装/校验/回滚通过，原安装全5126文件不变。

该阶段当前Controls文本没有触发需修复的显示问题，因此没有为此改译文或字体。所有37条仍为draft，UI可见不是译文已审稿。

## 重现

```powershell
python build.py test
python -m tools.validate.runtime --game-dir "GAME" --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view options --sweep --original
python -m tools.validate.runtime --game-dir "GAME" --runtime-dir build/runtime --build-dir build/zh-CN --out build/qa --resolution 1920x1080 --view options --sweep
```

1366x768 / 2560x1440同参数切换。此命令会启动隔离游戏副本。截图、日志、完整资源与Windows字体生成物只在被忽略build；源码只保留证据文件名、SHA和审查范围。结果索引见CONTROLS_QA_RESULTS.json。

## 未覆盖

右侧动态英文值尚未本地化；自定义键位子页面、Hardware页、完整游戏战斗/存档/切图/网络未验收；4K仍为已知问题、不适配，推荐1080p。下一项可小范围补齐单人菜单标签/帮助并沿用同一工具链。
