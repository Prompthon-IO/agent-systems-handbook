---
name: customer-email-assist
description: 用最少的 token 审阅带标签的 Gmail 客户支持线程。适用于 Codex 需要把 Gmail 同步到本地 SQLite 问题队列、先执行确定性的清洗和分类、只把模型调用保留给 JSON-only 的消息理解和草稿字段生成，并支持 dashboard 审阅、客户审批与本地单操作员回复发送的时候。
---

# Customer Email Assist

使用这个技能来操作 `customer-email-assist-starter` 示例，并尽量减少
模型 token 消耗。

## 必需的运行时输入

- `CUSTOMER_EMAIL_ASSIST_GMAIL_LABEL`
- `CUSTOMER_EMAIL_ASSIST_POLICY_PATH`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- 可选 `CUSTOMER_EMAIL_ASSIST_DB_PATH`

## 硬性规则

只在以下两种场景使用模型 token：

1. 理解清洗后的客户邮件内容
2. 生成回复模板字段 JSON

不要把模型调用用于 Gmail 抓取、HTML 清理、引用历史移除、签名裁剪、
客户匹配、SQLite 写入、分析统计、过滤、分页或发送队列执行。

## 确定性命令

相对于该入门项目目录解析路径。

```bash
npm run init-db
tsx scripts/customer-email-assist.ts apply-send-queue
tsx scripts/customer-email-assist.ts prepare-inbound-batch
tsx scripts/customer-email-assist.ts persist-understanding --input /tmp/understanding.json
tsx scripts/customer-email-assist.ts prepare-draft-batch --policy "$CUSTOMER_EMAIL_ASSIST_POLICY_PATH"
tsx scripts/customer-email-assist.ts render-save-drafts --input /tmp/draft-fields.json
```

## 工作流

1. 先运行 `apply-send-queue`。
   - 如果某个已批准线程在 Gmail 中已经有人类回复过，脚本会把该 issue
     标记为 `resolved`，且不会重复发送。
   - 否则脚本会发送已批准的渲染回复，并将 issue 结束。
2. 运行 `prepare-inbound-batch`。
   - 只抓取带标签的 Gmail 线程。
   - 每个批次最多保留四条清洗后的来信。
   - 跳过被 ignored 的客户。
3. 只用一次模型执行 `understand`。
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
4. 保存该 JSON，并运行 `persist-understanding --input <file>`。
5. 运行 `prepare-draft-batch --policy <file>`。
   - 这一步每个 issue 只提取少量政策证据行。
6. 只用一次模型执行 `draft-fields`。
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
7. 保存该 JSON，并运行 `render-save-drafts --input <file>`。
8. 在 dashboard 中让用户编辑已渲染的草稿、批准发送、标记完成、批准
   待审核客户、忽略客户，或更新客户描述。

## 保护措施

- 保持模型输入短小。不要发送完整线程历史。
- 不要把原始政策文档发送给模型；只发送 `prepare-draft-batch` 选出的
  政策证据行。
- 除非用户明确编辑并批准最终回复，否则不要把 `handoff_required`
  案例放进自动发送路径。
- 对被 ignored 的客户，后续同步运行中应视为不可操作。
