# 贡献指南

本仓库接受针对 Prompthon Agentic Labs 的多种公开贡献形式。

第一个要问的问题不是“文章还是代码？”而是“你要添加的是什么类型的成果物？”

## 支持的贡献类型

- `lab article`：位于 `foundations/`、`patterns/`、
  `systems/`、`ecosystem/` 或 `case-studies/` 中的常青页面
- `radar note`：位于 `radar/` 中的简短、按时间范围限定的现场更新
- `source project`：位于某条 lane 本地 `examples/` 子路径下、由仓库维护的示例或 starter
- `curated reference note`：位于 `contributor-kit/reference-notes/` 下的结构化来源地图、汇总或阅读笔记

`publications/` 不是第一波社区贡献的入口。请将其视为成熟实验室页面的编辑扩展区域。

## 从这里开始

在起草任何内容之前，请先使用对应指南：

- [贡献者工具包](./contributor-kit/index.mdx)
- [GitHub Issue Guide](./contributor-kit/github-issue-guide.mdx)
- [Article Guidelines](./contributor-kit/article-guidelines.mdx)
- [Radar Note Guidelines](./contributor-kit/radar-note-guidelines.mdx)
- [Source Project Guidelines](./contributor-kit/source-project-guidelines.mdx)
- [Reference Note Guidelines](./contributor-kit/reference-note-guidelines.mdx)
- [Review Checklist](./contributor-kit/review-checklist.mdx)

## 共享工作规则

- 保持公开内容为仓库原生内容。将 `references/` 下导入的材料作为来源输入，而不是可发布的文案。
- 不要将上游的正文、截图、图表或大段代码内容复制到受追踪的公开路径中。
- 在写作之前先选对 lane 或贡献类型。
- 遵循对应模板，不要自行发明自定义格式。
- 将你的贡献从相关 lane 的 README 或贡献入口链接出去，以便他人发现。
- 只要外部材料影响了贡献内容，就要记录来源脉络。

## 每种贡献应放在哪里

- Lab 文章直接放在相关的 lane 文件夹中。
- Radar 笔记放在 `radar/` 中。
- Source projects 仅放在以下位置：
  - `patterns/examples/`
  - `systems/examples/`
  - `ecosystem/examples/`
  - `case-studies/examples/`
- Curated reference notes 放在 `contributor-kit/reference-notes/` 中。

不要在 v1 中于 `foundations/` 下创建 `examples/`。
不要在 `references/` 中添加由贡献者创建的材料。

## Issue 提交

在提交 issue 之前，请先使用 [GitHub Issue Guide](./contributor-kit/github-issue-guide.mdx)。其中说明了内容提案、source-project 提案、仓库功能请求、流程变更和 bug 应该使用哪种仓库 issue 表单。

## 共享 PR 流程

1. 选择贡献类型。
2. 使用对应模板将工作放到正确的文件夹中。
3. 从相关 README 中添加或更新链接。
4. 打开一个带有简短范围摘要的 PR。
5. 在请求合并之前，根据共享检查清单审查变更。

## 审核标准

每项公开贡献都应通过 [Review Checklist](./contributor-kit/review-checklist.mdx) 中的检查：

- 类型和位置正确
- 模板完整
- 采用仓库原生的写作或结构
- 署名边界安全
- 交叉链接有用
- 状态和维护预期清晰
