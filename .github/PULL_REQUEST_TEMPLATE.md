## Summary

Describe the change in 2-5 sentences. Keep the scope concrete.

## Target Branch

- Normal contributor work targets `develop`.
- Release PRs target `main` only when opened by `dprat0821` from same-repository `develop`.
- `main` is the production Mintlify branch and should not receive direct feature PRs.

## Pull Request Stage

Select the current GitHub stage and remove the other line.

- Draft — work or required checks remain; review is not requested yet.
- Ready for review — the scoped change and required checks are complete.

If substantial revisions are still in progress after feedback, convert the pull
request back to a draft. See
[Changing the stage of a pull request](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/changing-the-stage-of-a-pull-request).

## Repository track

If you link an Issue using `Closes #<issue-number>`, its classification is inherited; leave
both lists unchecked. Otherwise select exactly one option in each list by
changing `[ ]` to `[x]`. The workflow applies the labels for you. No label
permissions or AI classification are needed. Do not rename the backtick values.
If you also select values for a linked Issue, they must agree with its labels.
See [classification help](https://github.com/Prompthon-IO/agent-systems-handbook/blob/develop/.github/contribution-classification.md) for examples and troubleshooting.

- [ ] `explorer` — Articles, research, and learning content / 文章、研究与学习内容
- [ ] `practitioner` — Skills, templates, and workshop materials / Skill、模板与工作坊材料
- [ ] `builder` — Engineering implementations and repository tools / 工程实现与仓库工具

## Work kind

Select the most specific kind of contribution. For example, a Skill with code
and documentation uses `skill-package`; a repository workflow change uses `ci`.
关联已分类的 Issue 时无需重复选择；直接提交 PR 时，每组选一项，系统自动补标签。

- [ ] `article` — Article / 文章
- [ ] `radar-note` — Radar note / 动态观察
- [ ] `case-study` — Case study / 案例研究
- [ ] `reference-note` — Reference note / 参考资料
- [ ] `reading-path` — Reading path / 学习路径
- [ ] `translation` — Translation / 翻译
- [ ] `workflow` — Reusable workflow / 可复用工作流
- [ ] `prompt` — Prompt / 提示词
- [ ] `template` — Template / 模板
- [ ] `skill-package` — Skill package / Skill 包
- [ ] `tool-showcase` — Tool showcase / 工具展示
- [ ] `workshop-material` — Workshop material / 工作坊材料
- [ ] `bug` — Bug / 缺陷
- [ ] `bug-fix` — Bug fix / 缺陷修复
- [ ] `feature` — Feature / 功能
- [ ] `demo` — Demo project / 演示项目
- [ ] `docs` — Documentation update / 文档更新
- [ ] `test` — Tests / 测试
- [ ] `ci` — Repository CI / 仓库自动检查
- [ ] `script` — Script / 脚本
- [ ] `enhancement` — Other improvement / 其他改进

## Placement

- Target path:
- Links or indexes updated:
- Related issue:

## Source Lineage

List the outside sources, imported references, or existing repo pages that shaped this change.

## Review Checklist

- [ ] The contribution type is explicit.
- [ ] The file or folder is in the correct path for that artifact type.
- [ ] I followed the matching template or contributor guidance where relevant.
- [ ] The change stays repo-native and does not copy upstream material into public tracked paths.
- [ ] Citations, source notes, or attribution boundaries are clear where needed.
- [ ] Relevant README, reading-path, or contributor links were added or updated for discoverability.
- [ ] If I added or revised a practitioner skill package, it includes a human-facing `README.md` and an agent-facing `SKILL.md`.
- [ ] Status and maintenance expectations are clear.
- [ ] The linked Issue supplies classification, or I selected one track and work kind above; all changed paths fit that track.
- [ ] If I changed example code, I ran `python3 scripts/verify_example_projects.py`.
- [ ] If I renamed files or changed paths, I ran `python3 scripts/check_filename_casing.py`.
