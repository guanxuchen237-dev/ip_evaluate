# SKILLS.md - 网络文学 IP 平台开发技能库

> **核心原则**：所有生成的代码必须符合“平静科技”设计规范和“代理式 AI”架构标准。

---

## 1. 核心开发 (Core Development)

### Skill: agent-development (智能体开发规范)
```yaml
name: agent-development
description: |
  当需要创建新的 AI 智能体 (Agent) 时使用此 Skill。
  涵盖 Persona 定义、工具绑定及 Human-above-the-loop 审计日志。

触发场景:
  - 创建新的业务智能体 (如风控官、星探)
  - 编写 Agent 的 Prompt 模板
  - 实现 Agent 之间的通信逻辑

触发词: 创建智能体, Agent, Persona, CrewAI, LangChain