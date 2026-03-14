

# PROJECT KNOWLEDGE BASE (项目知识库)

**项目名称：** 网络文学IP价值评估及流行趋势分析平台设计与实现
**核心架构：** 代理式 AI (Agentic AI) + 双引擎评估 (Dual-Engine)
**设计语言：** 平静科技 (Calm Tech) / 2026 云端舞者 (Cloud Dancer) / 玻璃拟态
**当前状态：** 积极开发中 (Active Development)
**默认语言：** **中文 (Chinese)** —— *所有交互、文档和代码注释均需优先使用中文。*

## 1. 项目概述 (OVERVIEW)

本项目是一个从“数据工具”向“代理式 AI”转型的网络文学 IP 全链路孵化平台。
核心亮点包括：

1. **双引擎评估：** 针对成熟期（XGBoost）和孵化期（K-Means 聚类）的分层评估。
2. **代理式 AI 编排：** 引入多智能体系统（市场/风控/内容代理）进行模拟博弈。
3. **治愈系美学：** 基于 Vue.js + 玻璃拟态的“平静科技” UI 设计，拒绝传统后台的沉重感。
4. **治理机制：** 实施“Human-above-the-loop”（人类在环上）的审计模式。

## 2. 目录结构 (STRUCTURE)

```
ip-scout-platform/
├── backend/
│   ├── agents/            # AI 智能体 (CrewAI/LangChain): 星探、分析师、风控官、创意总监
│   ├── engines/           # 核心算法引擎: xgboost-valuation, kmeans-discovery, narrative-ekg (叙事心电图)
│   ├── spiders/           # 混合爬虫: selenium-dynamic (动态), requests-static (静态), anti-crawl (反爬)
│   ├── api/               # Flask/FastAPI 接口层
│   └── memory/            # 智能体长期记忆与向量数据库 (ChromaDB)
├── frontend/
│   ├── src/
│   │   ├── components/    # UI 组件 (玻璃拟态卡片, 叙事心电图组件)
│   │   ├── views/         # 页面视图 (仪表盘, 3D 知识图谱, XR-HUD 模式)
│   │   └── assets/        # 主题文件 (Cloud Dancer 配色定义)
│   └── public/            # 静态资源
├── docs/
│   ├── memory/            # [核心] 项目上下文日志 (见下方记忆协议)
│   └── architecture/      # 系统架构图
└── scripts/               # 部署与模型训练脚本

```

## 3. 导航指南 (WHERE TO LOOK)

| 任务类型 | 对应目录 | 说明 |
| --- | --- | --- |
| **新增智能体 (Agent)** | `backend/agents/` | 定义角色 (Persona)、工具 (Tools) 和目标 (Goals)。需在 `orchestrator.py` 注册。 |
| **算法开发** | `backend/engines/` | XGBoost 估值逻辑或 SnowNLP 情感计算逻辑。 |
| **UI 组件开发** | `frontend/src/components/` | **必须**遵循严格的亮色模式 (Light Mode) 和玻璃拟态规范。 |
| **数据采集/爬虫** | `backend/spiders/` | 处理 WOFF 字体加密和动态渲染的核心逻辑。 |
| **提示词工程** | `backend/agents/prompts/` | “社交 SEO 生成”或“灵感探索池”的 System Prompts。 |
| **项目状态同步** | `docs/memory/CURRENT_STATE.md` | **开始任何任务前必读此文件。** |

## 4. 记忆与状态管理协议 (MEMORY PROTOCOL) - **CRITICAL**

**AI 必须严格遵守以下协议以保持长期记忆连续性：**

### 4.1 语言规范 (Language Rule)

* **指令：** 无论用户使用何种语言提问（除非明确要求翻译），AI **必须始终使用中文**进行思考、回复、编写文档和注释代码。
* **术语：** 专有名词（如 Agentic AI, Glassmorphism, XGBoost）可保留英文，但需在首次出现时提供中文解释。

### 4.2 读写流程 (Read/Write Cycle)

1. **读取阶段 (开始工作前):**
* 读取 `docs/memory/CURRENT_STATE.md`，了解当前进度。
* 读取 `docs/memory/DECISION_LOG.md`，确认架构约束。
* 确认当前的“活跃目标 (Active Goal)”。


2. **写入阶段 (完成工作后):**
* **总结 (Summarize):** 更新 `CURRENT_STATE.md`，记录刚刚完成的功能。
* **快照 (Snapshot):** 将关键技术决策写入 `DECISION_LOG.md`。
* **下一步 (Next Steps):** 更新状态文件中的“待办事项 (Todo List)”。



---

**附：`docs/memory/CURRENT_STATE.md` 模板：**

```markdown
# 项目当前状态 (Current Project State)
**最后更新:** [日期]
**当前阶段:** [例如：阶段二 - 智能体集成]

## ✅ 已完成功能
- [x] 双引擎 (XGBoost) 基准模型
- [x] 基础仪表盘 (Cloud Dancer 主题)

## 🚧 进行中
- [ ] 开发“虚拟读者焦点小组”智能体
- [ ] 对接叙事心电图 (Narrative EKG) API 到前端

## 🧠 上下文与注意事项 (Context)
- 记住：UI 必须是亮色模式 (Cloud Dancer)，严禁使用暗黑模式（XR 视图除外）。
- 记住：所有高风险智能体决策必须记录到审计日志中。

```

---

## 5. 开发规范与准则 (CONVENTIONS & RULES)

* **设计系统 (Design System):**
* **严格亮色模式 (Strict Light Mode):** 背景色 `#F9F9F9` (暖白/云灰)。
* **排版:** 标题使用衬线体 (Serif/Playfair Display) 体现文学感，数据使用无衬线体 (Sans/Inter)。
* **玻璃拟态:** 白色卡片，70% 透明度，`backdrop-blur-md`，极细微的投影。
* **禁止暗黑模式:** 除非是在“XR 空间计算视图”页面。


* **智能体架构 (Agent Architecture):**
* **基于角色:** 每个智能体必须有清晰的人设（如“风控官”）。
* **异步通信:** 智能体之间通过消息队列 (Celery/Redis) 通信，严禁阻塞 UI 线程。
* **审计:** 所有“S级”评价或高风险操作必须写入 `audit_log`。


* **数据工程 (Data Engineering):**
* **冷启动:** 对新书数据缺失使用“中位数填充 (Median Filling)”。
* **反爬虫:** 使用 IP 轮换池和动态字体映射技术。



## 6. 智能体模型与角色 (AGENT PERSONAS)

| 智能体名称 | 角色设定 | 技术栈 | 核心目标 |
| --- | --- | --- | --- |
| **IP 星探 (IP Scout)** | 探索者 | K-Means + 规则引擎 | 在孵化期发现“黑马”作品，解决冷启动问题。 |
| **叙事分析师 (Narrative Analyst)** | 分析师 | MiniMax / Claude | 生成“叙事心电图”和情感弧线，识别注水章节。 |
| **风控盾 (Risk Shield)** | 审计员 | BERT + 规则库 | 检测抄袭、敏感内容及作者断更/太监历史。 |
| **创意总监 (Creative Director)** | 创作者 | GPT-4o / Claude | 生成社交 SEO 物料包（TikTok 脚本、小红书文案）。 |
| **虚拟焦点小组 (Focus Group)** | 模拟器 | Multi-Agent Swarm | 50+ 轻量级智能体模拟不同读者画像的阅读反应。 |

## 7. 反模式 (ANTI-PATTERNS / 禁止事项)

* **❌ 禁止暗黑模式仪表盘：** 我们的风格是“平静科技”，不是赛博朋克后台（除非是 XR 模式）。
* **❌ 禁止同步调用智能体：** 不要让用户看着 Loading 转圈等待 AI 分析，必须异步推送结果。
* **❌ 禁止硬编码阈值：** 评分阈值应在配置文件或数据库中管理，而不是写死在代码里。
* **❌ 禁止过度设计：** 不要添加影响阅读的“纸张噪点”纹理，保持界面通透干净。
* **❌ 禁止数据幻觉：** 智能体的输出必须基于 `Ground Truth` 数据集进行校验。

## 8. 复杂度热点 (COMPLEXITY HOTSPOTS)

| 组件 | 描述 |
| --- | --- |
| `backend/engines/narrative_ekg.py` | 文本情感值到视觉坐标的复杂映射逻辑。 |
| `frontend/src/views/3d_universe.vue` | Three.js/D3.js 力导向图的性能优化（针对大量节点）。 |
| `backend/agents/orchestrator.py` | 管理“市场代理”与“风控代理”之间博弈状态的编排器。 |
| `docs/memory/` | **唯一真理来源。** 如果这里没记录，就等于不存在。 |

## 9. 部署与持续集成 (DEPLOYMENT)

* **前端:** Vite Build -> Dist 静态文件。
* **后端:** Docker 容器化 Flask 应用。
* **数据库:** MySQL (关系型) + Redis (智能体队列) + ChromaDB (向量存储)。
* **更新协议:** 每次代码提交前，**必须** 运行 `python scripts/update_memory.py` (假设脚本) 或手动更新文档，确保记忆同步。

---

### 💡 如何在对话中使用此文件：

从现在开始，每当我们开启一个新的任务或会话时，你可以直接对我说：

> **“请读取项目知识库 (PROJECT_KNOWLEDGE) 和当前状态 (CURRENT_STATE)。”**

收到指令后，我将执行以下操作：

1. **回忆** 你的技术栈 (Flask/Vue/Agentic AI)。
2. **回忆** 你的设计规范 (Cloud Dancer/玻璃拟态/亮色模式)。
3. **检查** 我们上次完成了什么 (基于 `CURRENT_STATE.md`)。
4. **确保** 全程使用**中文**进行回答和文档编写。