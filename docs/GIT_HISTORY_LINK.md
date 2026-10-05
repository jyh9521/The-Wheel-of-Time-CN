# Git 历史衔接（2026-10-03）

- 从现有远端 `https://github.com/jyh9521/The-Wheel-of-Time-CN.git` 完整克隆Git元数据，以 `origin/main` 的 `dee6e61b6df8d037dbb021cf6b3a0c9db4022a8b` 为基底。
- 新工作区当前分支 `main`，跟踪 `origin/main`；迁移文件覆盖层保留并进入暂存区，尚未commit/push。没有使用git init创建本项目新历史，没有改写旧commit，没有强推。
- 远端主分支与此前迁移所用基底相同，因此没有分叉或需要解决的内容冲突；3份格式/陷阱/已知问题文档采用大写文件名，Git识别为重命名，不是删除研究内容。
- LICENSE与LICENSE-translations.md沿用远端贡献者声明和许可，不用新模板覆盖已有归属。模板版本仍保存在本地迁移备份中。
- `.gitignore` 保留AGENTS与LOCALIZATION_STANDARD的本地忽略规则；根build/dist/out与原版System/Maps/Textures/Sounds/Music/Movies/Help/Save/backup树忽略，常见原版包/媒体/程序/字体扩展名忽略，GOG安装文件、缓存、临时/解包目录忽略。
- `/build/` 使用根锚定规则，通用源码 `tools/build/pipeline.py` 不受误伤。没有将游戏目录作为Git仓库。
- 分支历史、忽略矩阵、暂存文件审计、合成测试与独立规则回滚记录在被忽略的 `build/git-link/VERIFICATION.txt`。不启动游戏，也不改旧游戏工作区。

## 提交与推送

该阶段只准备并暂存变更。确认后可普通commit，再fetch并检查是否仍能fast-forward；若origin/main前进则先合并/变基与复测，不使用force或force-with-lease绕过检查。当前检查通过只说明当前快照可提交；它不保证未来远端不会更新。

## 该阶段检查结果

45/45应排除路径通过，9/9源码路径保留；46项合成测试通过。基于rename检测为新增20、普通修改5、重命名并更新3、内容删除0；索引无冲突项。HEAD与origin/main ahead/behind为0/0，9个历史commit列表完全一致。仅准备提交；远端未来更新时需重新fetch并合并检查。

## 提交完成记录

确认后，迁移成果以 `3df21560e62169101f0e2df7460a974e81e18758` 提交，信息为 `Standardize project structure and preserve reproducible build workflow`，随后普通push并fetch，main与origin/main为0/0。上文“尚未commit/push”描述的是此前衔接准备阶段；没有强推或改写历史。随后继续Controls离线草稿，见CONTROLS_POC.md。
