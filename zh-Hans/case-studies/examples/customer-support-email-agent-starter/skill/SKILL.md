---
name: local-customer-email-reply
description: 审阅客户来信，以本地政策或 FAQ 文档为依据起草安全的投诉和咨询回复。
---

# 本地客户邮件回复

当用户希望智能体审阅客户邮件，并根据本地文档路径（例如
`/Users/example/support-policy.md`）起草回复时，请使用此技能。

## 必填输入

- `EMAIL_PATH`: 包含来信客户消息的本地 `.txt`、`.md`、`.json` 或 `.eml` 文件
- `POLICY_PATH`: 包含支持政策、FAQ、退款规则或升级处理指引的本地 `.md`、`.txt` 或其他可读文本文件
- 可选 `DRAFT_PATH`: 应写入回复草稿的本地路径

## 工作流

1. 从 `EMAIL_PATH` 读取来信。
2. 从 `POLICY_PATH` 读取依据文档。
3. 提取客户姓名、问题、期望结果、订单或账户标识符、紧急程度和情绪。
4. 将消息归类为以下之一：
   - `complaint`
   - `query`
   - `refund_request`
   - `billing_issue`
   - `handoff_required`
5. 仅依据本地文档起草回复。
6. 如果请求的操作不受文档支持，不要臆造政策。将案例标记为 `handoff_required`。
7. 返回：
   - `summary`
   - `classification`
   - `policy_evidence`
   - `reply_subject`
   - `reply_body`
   - `needs_human_review`

## 保护措施

- 除非本地文档明确允许，否则绝不要承诺退款、积分、替换或法律结果。
- 绝不要暴露内部备注或隐藏推理过程。
- 保持回复简短、平静，并面向客户。
- 对辱骂、安全、拒付、监管、隐私或删除相关案例进行升级处理，交由人工审核。
- 将缺失或薄弱的政策依据视为需要转交处理的案例。
