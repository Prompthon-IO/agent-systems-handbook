# Lesson 2 — 文件整理、资料理解、工作流自动化

[英文版](../lessons/lesson-2.md)为规范来源，本页保持相同流程和安全边界。只使用合成文件，不使用真实 Downloads。课程包先合入 `develop`；正式 Handbook 发布是另一项操作。

## 学习目标

Organize 负责文件位置；Understand 负责有来源的知识笔记；Automate 负责工具顺序、审批点与运行状态。先解释三个职责，再组合工作流。

## 准备（5 分钟）

在包含课程代码的 fork/clone 根目录运行：

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 2
python3 skills/course-support/scripts/seed_demo.py
python3 skills/course-support/scripts/course_store.py context
```

第一条命令列出三个 Codex Skill 名称；第二条在 `.local-state/course-demo/lesson-2/` 创建数据，不覆盖旧作业。incoming 中有发票、学校资料和未知扩展名；research 中有重复资料和容量冲突。此时是本地演示身份，不代表已登录生产账号。

## 课堂练习（20–30 分钟）

1. 让 `$local-document-organizer` 扫描 `.local-state/course-demo/lesson-2/incoming`，查看计划与分类数量。预览不移动文件。增加一条分类规则，再生成新预览。
2. 明确批准计划后，执行 `course_organizer.py apply --plan <计划路径> --confirm ORGANIZE`。检查本地操作日志；执行 `course_organizer.py undo --log <日志路径> --confirm UNDO` 恢复。对比内容与哈希，确认重名文件未被覆盖。
3. 让 `$personal-knowledge-capture` 理解 `.local-state/course-demo/lesson-2/research`，使用笔记 id `weekly-note`。应看到三个来源、两个唯一文本、一项重复和 20/24 的容量冲突。检查引用，不凭空决定哪个来源更权威。
4. 只修改一份合成资料，再用同一 note id 运行。对比版本、哈希和修改时间。让 Codex 在保留引用的前提下完善抽取式初稿；确定性脚本只能识别显式“字段:值”冲突。
5. 定义并预览组合流程：

```bash
python3 skills/personal-workflow-automation/scripts/workflow.py define --file skills/personal-workflow-automation/examples/weekly-workflow.json
python3 skills/personal-workflow-automation/scripts/workflow.py preview --workflow weekly-course
```

审阅完整 argv 列表后，用输出的 SHA-256 执行 `run --workflow weekly-course --confirm <sha256>`。流程完成分类后，在理解资料前暂停。批准后执行 `retry --workflow weekly-course --run-id <run-id> --confirm <sha256> --approve-step synthesize`，不会重复已完成的分类步骤，也不会创建后台任务。等待审批的退出码为 3，不代表流程完成。笔记从正文提取要点，只对 `synthesis-rules.json` 中配置的单值字段检查矛盾；独立行动项不算冲突。

缩写命令均位于对应包的 `scripts/`。`--workspace student-02` 等共享参数放在子命令前，三个包使用相同上下文。

## 持久化与证据

```bash
python3 skills/course-support/scripts/course_store.py runs
python3 skills/personal-knowledge-capture/scripts/course_knowledge.py show --note-id weekly-note
```

核对组织、工作区、服务端或本地 actor、状态、来源哈希、产物、事件和版本。不能只看脚本退出成功。后台已配置课程访问后，在子命令前加 `--storage prompthon` 并回读。后台未就绪时必须明确失败；本地 HTTP 测试不等于 Neon 已部署。

## 修改与重置

每名学生修改一条 canonical 分类规则或审批点，重新安装、展示变化，并提交到自己的 fork。不提交 `.local-state`、生成的 `.agents`、个人资料或凭据。

先 undo 文件移动，再清理课程记录。先运行 `course_store.py reset` 预览；用 `reset --confirm demo-student` 仅清理该本地工作区的课程行。日志与原文件保留。换一个新目录生成演示数据，不删除旧作业。

## 教师提示

建议准备 5 分钟，预览/恢复与引用 10 分钟，审批/重试 10 分钟，证据检查 5 分钟。确认学生能区分暂停、失败和成功。可注入无害的命令失败；超时或中断后的副作用未经检查不可直接重试。远程课程开始前必须配置服务端确认的 demo/course 权限，见[后台依赖](../references/backend-dependency.md)。
