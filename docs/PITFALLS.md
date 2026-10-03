# 重复踩坑 / 必须保持的约束

1. **Unicode不等于有字库**：仅换UTF16 `.int` 曾中文空白、ASCII正常；先检查Font映射。
2. **大atlas缺mip**：512单mip曾报 `D3D Driver: Encountered oversize texture without sufficient mipmaps`。
   默认256上限；不能只依据驱动宣传的2048上限放大。
3. **CPP与Latin**：仅把256改64会破坏ASCII页/槽；保留Page0并补1..3切片且逐字形比较。
4. **绝对lazy-end**：追加Texture后它不是局部offset，必须与export.offset同步。
5. **标点bbox顶对齐**：逐字按bbox.y0裁切会把句号抬高；按locale代表字形统一基线并保留bearing。
6. **字幕Len计时**：短译文90字替换350字会提前消失；补偿仅构建生成、不能假装精确同步。
7. **启动路径空格**：老引擎曾把绝对WoT.exe路径误拆成Commandlet；切换System后用 `.\WoT.exe` 启动。
8. **截图≠模式**：桌面3840截图不证明内部4K；看Best-match模式日志，之后人工看UI。
9. **Inventory异步加载**：Mission_01先显示任务目标，F3关闭后按1/F2，再多等10秒。
   黑屏/预缓存帧不能算字体通过，原版也需同输入对照。
10. **字体/engine导出分层**：脚本字面量存在不代表修改Font需要改字节码；逐字节验证非Font导出。
11. **PowerShell/日文Windows编码**：Python默认stdout可能cp932；中文测试结果应明确UTF8输出。
12. **窗口退出流程**：不要先关闭DirectDraw代理窗口再主窗口；新QA曾在已显示Inventory后退出报
    `DDERR_NOEXCLUSIVEMODE/ReTestCooperativeLevel`。保留失败证据，先关闭自己的主窗口并做原版对照。
13. **Gitignore递归匹配**：`build/` 会同时忽略 `tools/build/` 源码。
    根生成物必须写 `/build/`，并在干净克隆中验证构建模块确实入库。

## 工作区迁移陷阱

- 根目录相对ROOT的旧脚本搬到tools子目录后会错误寻找backup/work。保留旧原件，生产入口复用已参数化框架，不靠复制旧生成物凑齐依赖。
- .gitignore中的build/会连tools/build也忽略；改为/build/、/dist/、/out/，干净源码集检查tools/build/pipeline.py存在。
- 历史大小写文件名与新FILE_FORMATS/PITFALLS/KNOWN_ISSUES在Windows上应合并、更新链接，不建立大小写冲突副本。
- 历史低分辨率成功与277/277散列属于当时记录，不覆盖后续分辨率决策，也不据此恢复用户INI。

- Windows下Python的text=True stdin会将LF转成CRLF，git check-ignore --stdin可能把CR当作路径字符，导致假阴性与带\r的引用输出。忽略规则探针使用UTF-8字节stdin（或NUL分隔），不要把测试工具传输问题误报为.gitignore失效。
