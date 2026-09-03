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

## 可选扩展练习：文件整理

老师可以选择其中一个案例，也可以让学生按顺序完成三个案例。三个
案例彼此独立，在一个文件夹中的操作不会影响另外两个。只使用以下
命令生成的合成练习文件，不要用真实的 Downloads 文件夹练习。

在下面的练习中，**预览（preview）**只展示建议，不移动文件；
**计划（plan）**是保存建议移动操作的文件；**冲突（conflict）**是
为了安全而跳过的操作；**操作日志（journal）**记录实际执行结果。
其他术语请参阅 Local Document Organizer 的
[入门术语表](../../local-document-organizer/README.md#beginner-terminology)。

每条 seed 命令都会拒绝删除或替换已有的输出目录。重复练习时，请
保留之前的作业，并用 `--output` 指定一个新路径，例如
`--output .local-state/course-demo/student-files-attempt-2`。

### 1. 学生文件：只预览

**目的。** 了解清晰可读的文件名和扩展名规则如何生成计划，并观察
无法确定类别的文件如何留在原处。

**准备。** 生成一份新的合成学生文件案例：

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario organizer-student-files
```

**命令。** 扫描 incoming 文件夹。这条命令只查看并提出建议，不会
移动文件。

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py scan --folder .local-state/course-demo/lesson-2-organizer-student-files/incoming
```

**Codex 示例提示。**

```text
使用 $local-document-organizer 预览学生文件练习文件夹。解释每个建议分类，把不确定的文件留在原处。不要移动任何文件。
```

**预期结果。**

- `tuition-invoice.txt` -> `Invoices/`
- `school-reading.md` -> `School/`
- `internship-resume.txt` -> `Resumes/`
- `random-download.zzz` 留在原处
- 预览不会移动任何文件

**思考问题。** 为什么把未知文件留在原处，比猜测一个类别更安全？

### 2. 自由职业者规则：自定义分类

**目的。** 观察更具体的文件名规则如何改善分类，并理解规则顺序
为什么会改变结果。

**准备。** 生成一份新的合成自由职业者案例：

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario organizer-freelancer-rules
```

**命令。** 先使用默认规则生成第一次预览：

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py scan --folder .local-state/course-demo/lesson-2-organizer-freelancer-rules/incoming
```

一开始，`client-meeting-notes.txt` 会进入 `Notes`，因为通用的文本
扩展名规则匹配了 `.txt`。在规范源文件
`skills/local-document-organizer/references/classification-rules.csv` 中，
把下面这一行加在通用 `ext-text` 规则之前：

```csv
keyword-meeting,Meetings,filename_keyword,meeting|minutes,medium,true
```

再次扫描或调用 Skill 前，先从规范包刷新已安装的 Skill 副本：

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 2
```

再次运行同一条扫描命令，生成一份新计划。不要修改已经审阅或批准的
现有计划。

**Codex 示例提示。**

```text
使用 $local-document-organizer 比较加入 Meetings 规则前后的自由职业者练习预览。解释每个文件匹配了哪条规则。不要应用任何一个计划。
```

**预期结果。**

- 发票仍在 `Invoices/`
- 协议仍在 `Contracts/`
- 会议记录从 `Notes/` 变为 `Meetings/`
- 网站项目想法仍在 `Notes/`
- 规则采用首条匹配结果，因此顺序很重要

如果不打算保留这项仓库修改，请在练习后恢复该规则。手动删除
`Meetings` 规则后，再运行一次相同的 setup 命令，使已安装副本与
规范包保持同步。

**思考问题。** 为什么更具体的会议规则必须放在通用 `ext-text`
规则之前？

### 3. 安全恢复：冲突与撤销

**目的。** 使用合成文件练习审批、重名保护、部分成功结果和撤销，
不让真实文件承担风险。

**准备。** 生成一份新的合成安全恢复案例：

```bash
python3 skills/course-support/scripts/seed_demo.py --scenario organizer-safe-recovery
```

**命令。** 扫描 incoming 文件夹：

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py scan --folder .local-state/course-demo/lesson-2-organizer-safe-recovery/incoming
```

预览会建议把 `invoice-august.txt` 移到 `Invoices/`。这仍然只是建议；
真正 apply 时，系统才会安全检查并执行同名冲突保护。

**Codex 示例提示。**

```text
使用 $local-document-organizer 预览安全恢复练习文件夹。解释建议移动操作和已有发票造成的冲突，然后等待我明确批准，再执行任何操作。
```

审阅预览后，把 `<printed-plan-path>` 替换为扫描命令实际打印的计划
路径，包括其中生成的标识符：

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py apply --plan <printed-plan-path> --confirm ORGANIZE
```

**apply 后的预期结果。**

- 发票移动操作记录为 `conflict`
- 已有的 CAD 120 发票不会被覆盖
- 修订后的 CAD 145 发票仍留在源位置
- 咖啡收据和支出备注成功移动
- 符合条件的移动成功，但存在冲突，因此运行状态为 `partial`
- `mystery.zzz` 留在原处

接下来，把 `<printed-journal-path>` 替换为 apply 实际打印的操作日志
路径：

```bash
python3 skills/local-document-organizer/scripts/course_organizer.py undo --log <printed-journal-path> --confirm UNDO
```

**undo 后的预期结果。**

- 只有成功移动的文件返回原位置
- 发生冲突的发票不会被错误移动
- 两个版本的发票内容都保持不变

**思考问题。** 为什么 undo 要依据操作日志，而不是尝试撤销原始
预览中的每一项建议？

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

远端工作流：样例步骤明确设置 `inherit_course_access: true`，仅继承同一课程 API 的 scoped credential。审批 manifest hash 时一并检查此字段。其他步骤默认不继承凭据；缺少访问权限时应认证失败，不能自动改为写本地。不得转发数据库或其他平台凭据。
