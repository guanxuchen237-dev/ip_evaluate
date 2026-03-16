# 📖 IP Lumina 项目核心上下文

这是一份为了保留开发记忆而生成的上下文文档，供后续 AI 助手在新的对话中快速恢复状态。（遵循《中文原生协议 v5.0》）

## 🛠️ 技术栈
- **前端网页**: Vue 3 (Composition API), Vite, Tailwind CSS, Lucide Icons, 原生 SVG 绘制图表
- **后端服务**: Python Flask, PyMySQL (操作数据库)
- **数据抓取**: Selenium / Playwright (规避封禁), Requests, BeautifulSoup4, fake_useragent
- **数据库**: MySQL (主库：`qidian_data`, 纵横库：`zongheng_analysis_v8`, 密码均为 `root`)
- **机器学习**: XGBoost (预测趋势建模)

## 📂 项目结构概览
- `/integrated_system/frontend/`: 前端 Vue 应用目录
    - `src/views/AdminDashboard.vue`: 管理后台集成总览（包含了调度面板、监控卡片、趋势图表等）
    - `src/views/Dashboard.vue`: **用户端数据大屏（三栏布局：月票Top10 | 中国地图+趋势 | 平台/雷达/词云）**
    - `src/components/charts/GeoMap.vue`: **ECharts 中国地图组件（读者地理分布）**
- `/integrated_system/backend/`: Flask 后端应用目录
    - `api.py`: 暴露所有管理接口与大屏数据查询（含 12 个 `/charts/*` 端点）。
    - `scheduler.py`: 处理爬虫脚本的独立进程调度。
    - `data_manager.py`: 配置源并提供 DB 和底层接口连通性（含 `get_geo_region_distribution`, `get_monthly_ticket_top` 等方法）。
- `/scrapy/`: 独立的数据抓取模块
    - `qidian_advance.py`: 起点高级爬取核心基类（包含 Playwright 无头逃逸机制）。
    - `qidian_realtime_spider.py`: 处理起点实时月票等增量追更抓取（将爬取的新数据 Upsert 入库 `novel_realtime_tracking` 表）。
- `/contexts/devlog.md`: **开发日志（详细记录每次改动、数据库结构、API 清单）**

## 🚨 最近攻坚难点 & 解决方案（记忆库）

### 1. 爬虫抗封锁工程 (起点反爬策略击破)
*   **黑洞代理拦截**：系统之前有陈旧废弃的代理配置导致 requests 被底层代理池吞没而静默超时卡死。现已通过 `session.trust_env = False` 和关闭死池 `use_proxy=False` 解除所有本地代理黑洞，恢复机器网卡的直连能力。
*   **Playwright / Chromium 降级接管**：起点目前对缺少正常登录态或浏览器特征的 `requests` 会直接秒下 403 盾拦或验证码空页。代码现已实装当 requests 收不到有效书目 DOM 时，自动双擎切换调起 `playwright.sync_api`，通过去指纹（`navigator.webdriver=undefined`）、随机 User-Agent 以及过滤清洗失效 `domain` 的全局 Cookie，无缝拿到正确 HTML 源。
*   **DOM 排版双态兼容**：起点的反爬/A-B 测试会在部分端口**随机下放不同排版**——同时存在现代图文流 (`.book-img-text ul li`) 与老式经典表格布局 (`.rank-table-list tbody tr`) 两种视图。`QidianSpider.fetch_rank_page_smart` 现已重写了 BeautifulSoup 选择器，做到两套环境容错抽取，并在遇见表格格式时能精确反切算到月票列，随后精准破解内部嵌入的一阶段 WOFF 字体加密。
*   **实时入库不炸库**：为了让月度/每小时更新脚本稳定叠加，所有写表操作换用 `INSERT INTO ... ON DUPLICATE KEY UPDATE`。

### 2. 后端 Scheduler 调度引擎闪退
*   在 Flask 后端触发 `/api/admin/spider_scheduler/toggle` 时，必须使用环境内的 `sys.executable` 唤起带包路径的 Python 解释器。同时配合 `cwd=os.path.dirname(script_path)` 锚定子进程当前工作目录，解决了前代因为直接调取大系统全局 `"python"` 找不到相对导入 `modules` 导致立刻退出报 `partial` 故障。此外，现在前端卡片已增设 `title` 属性，可以直接悬停看到任何原汁原味的后台抛错报错堆栈 Traceback。

### 3. 前端图表渲染与可视化修复
*   **SVG 原点 Tooltip 严重偏移**：前端之前通过像素硬算在缩放视窗内发生雪崩。通过原生调用 `(e.target as SVGCircleElement).ownerSVGElement.getBoundingClientRect()` 同步计算外部父级容器的宽高系数矩阵，使原点的 Tooltip 窗口百分百吸附坐标、平滑相对 `left / top` 定位。
*   **极少数据点直接不渲染断线**：当一本书刚入库仅有一条历史月票时，由于 SVG 拒绝渲染单点的 `<path>`，图表会进入空中悬一个圆点的空窗期。现已在前端绘制前主动强行复制延长出第二点（并加上“至今”标签），重新平滑拉出蓝色区域带及预测基准带护航效果。

## 📌 开发规范重点（接任者注意事项）
1.  遵循《中文原生协议 v5.0》，**除了代码术语及文件指令，所有的意图沟通、文档描述、系统注释全部采用直接而精确的中文**。不要说 "Let me do..."。
2.  后续如果进一步更新核心驱动，不要轻易把爬网的主逻辑换成脆弱的 `requests`。现在依赖的 Playwright 非常稳定，且已经全额封装防封机制。
3.  大屏 Dashboard (VUE3 + Tailwind) 为确保响应速度严禁嵌入巨量数据，在更新 API 后端时一定要带上 `LIMIT` 并利用分页降低长稳监控耗时。 
