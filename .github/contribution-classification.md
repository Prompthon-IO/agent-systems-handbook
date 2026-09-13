# Contribution classification

## For contributors

Issue forms have required **Repository track** and **Work kind** dropdowns.
Choose the type of work you intend to contribute; the Issue intake workflow
applies the labels without using a language model. Fixed-purpose forms, such as
Skill Package and Bug Report, already constrain those choices.

For a PR, either link a classified Issue with a closing keyword and its real
number, or select exactly one checkbox under **Repository track** and **Work
kind** in the PR template. Leave both lists unchecked when inheriting complete
Issue labels. If an Issue only has a track, select the missing work kind in the
PR. Existing PR labels also work. Values supplied in multiple places must agree.

- Explorer: articles, research and learning content.
- Practitioner: Skills, templates and workshop materials.
- Builder: engineering implementations and repository tools.

All three tracks may update the root `docs.json` alongside their contribution.
Reviewers check the navigation and site configuration changes; normal review
and required validation still apply. Other files remain subject to the track
allowlist.

The path policy still applies. Choosing Builder does not allow a Skill-only PR
to change arbitrary paths, and classification does not grant approval or merge
permission. The existing Issue proposal/claim process still governs scope;
classification inheritance does not replace maintainer acknowledgement.

If a selection is missing, unknown or checked more than once, edit the PR
description and save it to rerun the check. If a linked Issue or existing PR
label conflicts, the check names the conflicting sources. Correct the selection
or ask a maintainer to correct the label; the bot never silently replaces it.
A title, free-form description, or file path is never used to guess labels.

## For maintainers

`prompthon-track-guard` reads live PR metadata, resolves fixed choices, validates
all changed paths, adds missing classification labels, reads them back, and
finishes the required check in the same run. It replaces its previous failure
comment after success. There is no dependency on a second `labeled` event from
`GITHUB_TOKEN`. Runs for a PR are serialized; metadata is checked again before
writing labels. Only base-branch scripts run in `pull_request_target`; PR code
is not checked out or executed by this privileged workflow.

All linked local Issues must agree if they supply a value. Multiple track or
kind labels are errors. Only known `track:*` and `kind:*` values are added;
unrelated labels remain untouched. Errors writing or reading back labels fail
the check. A failure to write a status comment cannot hide the check result.

Merge the workflow change into `develop` before expecting contributor PRs
against `develop` to use it. The templates and Issue workflow must also reach
the default branch through the normal release PR before GitHub offers the
updated forms/templates by default. Existing open PR descriptions are not
rewritten; contributors can copy the new selection sections into them, or
maintainers can supply both classification labels. The release exception for
same-repository `develop` to `main` is unchanged; release authorization remains
the responsibility of the separate release gate.

## 简体中文说明

创建 Issue 时，在必填下拉框选择贡献轨道和具体类型；系统按固定规则补标签，
不使用语言模型。Skill 包、缺陷报告等专用表单已限制相应选项。

提交 PR 时，关联一个已分类的 Issue 即可继承其标签，无需重复勾选；直接提交
PR 时，在 **Repository track** 和 **Work kind** 中各勾选一项。Issue 如果只有
轨道，可在 PR 中补选具体类型。已有 PR 标签也可提供分类，但各处的值必须一致。

- Explorer：文章、研究与学习内容。
- Practitioner：Skill、模板与工作坊材料。
- Builder：工程实现与仓库工具。

三个轨道都可以在贡献 PR 中修改根目录的 `docs.json`。导航与站点配置变更由
审阅者把关，仍须完成正常 Review 和必需校验；其他文件继续受各轨道路径范围限制。

漏选、多选、未知值时，编辑 PR 描述后保存即可重跑。与已有标签冲突时，检查会
指出来源；修正自己的选择，或请维护者修正标签。系统不会根据标题、正文或路径
猜测分类，不会覆盖不一致的标签。路径检查、Issue 范围确认、正式 Review 与合并
权限仍然保留。标签通过不代表 PR 已被批准或已上线。

工作流会在一次运行中完成分类、路径校验、补标签和回读，不依赖机器人打标签
再次触发工作流。修改进入 develop 后才用于该分支的 PR；更新的 GitHub 默认
表单和模板还需要按正常发布流程进入默认分支。已有 PR 的描述不会自动重写，
可复制新的选择区块，或由维护者补齐两个标签。
