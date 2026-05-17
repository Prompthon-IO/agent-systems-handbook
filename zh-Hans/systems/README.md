# 系统

这个版块聚焦于面向生产的系统性问题，这是本仓库区别于更轻量的智能体课程和 cookbook 仓库的主要机会之一。

## 这里包含什么

- 上下文工程
- 协议互操作
- 评估
- 可观测性
- 可靠性
- 安全与治理
- 部署与运维

## 编辑意图

这个版块中的页面应当超越演示。目标是解释智能体系统如何作为真实的软件系统运行，具备接口、追踪、边界以及运维权衡。

## 当前页面

- [上下文工程](./context-engineering.mdx): 说明系统如何写入、选择、
  压缩和隔离上下文，以实现可靠的多步骤工作。
- [智能体界面协议与生成式 UI](./agent-ui-protocols-and-generative-ui.mdx):
  说明 AG-UI 与 A2UI 如何把面向用户的交互从工具协议和智能体协议中分离出来。
- [协议与互操作](./protocols-and-interoperability.mdx): 说明工具访问、
  智能体协作和网络发现如何协同工作。
- [评估与可观测性](./evaluation-and-observability.mdx): 说明如何
  衡量能力，并解释面向生产的智能体系统中的失败。

## 示例 starter

- [Weather MCP Server Starter](./examples/weather-mcp-server-starter/index.mdx):
  一个面向协议的轻量工具服务草图，用于未来的互操作示例。
