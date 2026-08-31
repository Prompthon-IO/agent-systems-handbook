# 第 3 课：Build → Test → Deploy

目标是得到可运行网页、真实浏览器证据，并在课程账号已准备好的条件下得到真实 Vercel preview URL。localhost、模拟测试结果和未核实的链接都不等于已发布。

## 课前准备与五分钟起步

安装基础包和三个技能：`python3 skills/course-support/scripts/setup_course_skills.py --lesson 3`。准备 Python 3.10+、Node.js，按 [Test README](../../webapp-testing/README.md) 安装指定 Playwright 和 Chromium；Windows 使用虚拟环境的 `Scripts/python.exe`。每位学员使用独立 demo workspace。

先运行 [Build README](../../web-builder/README.md) 中的两条 preview/build 命令，再运行 Test 的浏览器命令。预期生成三个本地文件、桌面和手机两张截图，以及仅显示在页面上的虚构表单确认。请实际打开截图；表单不会发送邮件或保存报名。

## 25 分钟练习

1. 0–5 分钟：修改 brief 的受众或一个页面区块，检查用途、风格和约束。
2. 5–12 分钟：在新目录构建页面，核对变更与基本构建结果；已有项目保留原框架和手工修改。
3. 12–18 分钟：运行真实浏览器测试，检查点击、填表、控制台和两种视口；故意改错一个断言，观察失败步骤，再修复。
4. 18–25 分钟：在老师预先配置的 Git-linked Vercel demo 项目中提交代码、记录构建并重测，获准后创建 preview，用 [Deploy](../../vercel-deploy/README.md) 核实项目、commit、READY 和真实页面内容。

变化练习：把风格改为 `bold-contrast`，或修改标题并同步测试断言；源码变化后旧测试证据不得用于发布。

## 老师检查、边界与重置

课前准备专用 Vercel demo 项目及首次部署，避免新项目首次部署变成 production；不要使用 handbook 网站的生产项目。没有账号时完成本地 Build/Test 和 Deploy 模拟案例，明确标记“未获得真实 preview URL”，不能把合成域名当成上线证据。真实生产发布必须额外批准。

检查 build run、test id、截图引用和 provider 返回的 deployment id/URL/commit，而不是只看 Agent 的总结。远端只保存元数据；截图和源码留在本地/Git。课程 API/Neon 后端仍由 Web App 的依赖事项负责，未部署时明确使用 local。

通过共享 reset 命令先预览，再按 workspace 确认。重置会清除该工作区各课的课程记录，不删除源码、截图或 Vercel 部署。可换新 workspace 和输出目录重做；不明确的发布结果必须回读恢复，不可盲目再次提交。
