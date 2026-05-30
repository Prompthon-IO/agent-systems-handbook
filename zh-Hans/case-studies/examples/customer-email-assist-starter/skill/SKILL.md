---
name: customer-email-assist
description: 用 connector-first、最少 token 的方式审阅 Gmail 客户支持线程。适用于 Codex 需要通过 Codex Gmail connector 读取 Gmail、把清洗后的消息导入本地 SQLite 问题队列、先执行确定性的清洗和分类、只把模型调用保留给 JSON-only 的消息理解和草稿字段生成，并支持 dashboard 审阅、客户审批与排队回复处理的时候。
---

# Customer Email Assist

使用这个技能来操作 `customer-email-assist-starter` 示例，并尽量减少
模型 token 消耗。

## 必需的运行时输入

- `CUSTOMER_EMAIL_ASSIST_POLICY_PATH`
- 可选 `CUSTOMER_EMAIL_ASSIST_DB_PATH`

正常工作流中的 Gmail 认证应通过 Codex Gmail connector 完成。不要要求用户
为了常规使用配置本地 Google OAuth 环境变量。

## 硬性规则

只在以下两种场景使用模型 token：

1. 理解清洗后的客户邮件内容
2. 生成回复模板字段 JSON

不要把模型调用用于 Gmail 抓取、HTML 清理、引用历史移除、签名裁剪、
客户匹配、SQLite 写入、分析统计、过滤、分页或发送队列执行。

## 确定性命令

相对于该入门项目目录解析路径。

```bash
npm run setup-local
tsx scripts/customer-email-assist.ts import-prepared-batch --input /tmp/prepared-inbound.json
tsx scripts/customer-email-assist.ts persist-understanding --input /tmp/understanding.json
tsx scripts/customer-email-assist.ts prepare-draft-batch --policy "$CUSTOMER_EMAIL_ASSIST_POLICY_PATH" --out /tmp/draft-batch.json
tsx scripts/customer-email-assist.ts render-save-drafts --input /tmp/draft-fields.json
```

## 工作流

1. 使用 Codex Gmail connector 搜索邮箱。
   - 优先使用窄查询，例如 `newer_than:1d -in:spam -in:trash -category:promotions`。
   - 只读取入选的客户来信内容。
   - 每个批次最多保留四条清洗后的来信。
2. 构建 `/tmp/prepared-inbound.json`，格式为 `PreparedInboundItem[]`。
   - 只包含 `gmailThreadId`、`gmailLastInboundMessageId`、`subject`、
     `cleanBody`、`receivedAt` 和 customer 字段。
   - 如果本地数据库已知道某个客户是 ignored，则跳过。
3. 运行 `import-prepared-batch --input <file>`。
   - 这会写入 SQLite issue，并用确定性兜底模板生成草稿，不需要本地 Gmail OAuth。
4. 只有当硬逻辑不够时，才使用模型执行 `understand`。
   - 只读取 JSON 批次输出。
   - 只返回 JSON。
   - 每条记录字段：
     - `gmailThreadId`
     - `gmailLastInboundMessageId`
     - `customerEmail`
     - `customerName`
     - `subject`
     - `receivedAt`
     - `originalMessageText`
     - `classification`
     - `summary`
     - `urgency`
     - `actionSuggestion`
5. 如果使用了模型输出，保存该 JSON，并运行 `persist-understanding --input <file>`。
6. 运行 `prepare-draft-batch --policy <file>`。
   - 这一步每个 issue 只提取少量政策证据行。
7. 只有当兜底模板不够时，才使用模型执行 `draft-fields`。
   - 只读取草稿批次 JSON。
   - 只返回 JSON。
   - 每条记录字段：
     - `issueId`
     - `classification`
     - `draftFields.customerName`
     - `draftFields.acknowledgement`
     - `draftFields.nextStep`
     - `draftFields.policyEvidence`
     - `draftFields.signoff`
8. 保存该 JSON，并运行 `render-save-drafts --input <file>`。
9. 在 dashboard 中让用户编辑已渲染的草稿、通过带 undo 倒计时的方式批准
   发送、对仍在排队的回复取消批准、标记完成、批准待审核客户、忽略客户，
   或更新客户描述。
10. 对于 connector 模式下仍处于 `approved_to_send` 的 issue，使用 Codex
    Gmail connector 创建或发送回复，然后把 issue 标记为 resolved。

## 高级本地 OAuth Adapter

仓库仍保留直接 Gmail API adapter，供明确需要 standalone local integration
的团队使用。它属于高级路径，不应作为默认设置展示。

高级变量：
- `CUSTOMER_EMAIL_ASSIST_GMAIL_LABEL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `CUSTOMER_EMAIL_ASSIST_OPERATOR_EMAIL`
- `GOOGLE_REDIRECT_URI`

dashboard 的 `Connect Gmail` 按钮会在 Google consent callback 之后把
refresh token 写入本地状态。`GOOGLE_REFRESH_TOKEN` 仍可作为手动兜底变量，
但不是 web-app 流程必需项。

高级命令：

```bash
npm run sync:oauth
tsx scripts/customer-email-assist.ts prepare-inbound-batch --out /tmp/prepared-inbound.json
tsx scripts/customer-email-assist.ts apply-send-queue
```

当这个高级本地 OAuth 路径已连接时，dashboard 的 `Approve & Send` 动作会在
undo 倒计时结束后立即执行确定性的发送路径。没有 OAuth 连接时，dashboard
会把 issue 保持在 `approved_to_send`，而不是尝试未认证的发送。

## 保护措施

- 保持模型输入短小。不要发送完整线程历史。
- 不要把原始政策文档发送给模型；只发送 `prepare-draft-batch` 选出的
  政策证据行。
- 除非用户明确编辑并批准最终回复，否则不要把 `handoff_required`
  案例放进自动发送路径。
- 对被 ignored 的客户，后续同步运行中应视为不可操作。
