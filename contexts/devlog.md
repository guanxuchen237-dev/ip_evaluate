# 📋 IP Lumina 开发日志

## 2026-02-23 (今日)

### 一、管理后台采集监控优化

#### 改动文件
- `integrated_system/backend/api.py` — 修复 `/admin/monitor/pipeline` 端点的 import 路径
- `integrated_system/frontend/src/views/AdminDashboard.vue` — 采集趋势图优化

#### 改动内容
1. **采集趋势图改为双线**：去掉原来的"总量"线，只保留 **起点（蓝色）** 和 **纵横（绿色）** 两条线
2. **新增数据点圆圈**：每个采集时间点都有可见的 SVG 圆点
3. **新增悬浮提示**：鼠标悬停数据点显示暗色 tooltip（时间 + 起点/纵横各自数量）
4. **新增面积填充**：蓝色和绿色半透明渐变底色，数据趋势更直观
5. **新增悬停竖线**：hover 时显示紫色虚线辅助定位

#### 代码要点
- `chartHover` ref 控制悬浮状态
- `chartPoints` computed 预计算所有数据点的 SVG 坐标（viewBox 800×200）
- `getSmoothLine()` 和 `getAreaPath()` 生成 SVG path 数据

---

### 二、用户端数据大屏全面升级

#### 新增后端 API（data_manager.py + api.py）

| API 路由 | 方法 | 数据源 | 说明 |
|---------|------|--------|------|
| `/charts/geo_region` | `get_geo_region_distribution()` | `zongheng_book_comments.ip_region` | 省份级读者评论分布 |
| `/charts/ticket_top` | `get_monthly_ticket_top(limit)` | 两个平台的 `realtime_tracking` 表 | 跨平台月票排行 |

#### 新增前端文件
- `src/components/charts/GeoMap.vue` — ECharts 中国地图组件（注册 `china.json`，蓝色渐变色域）
- `src/assets/china.json` — 中国省份 GeoJSON（来自 DataV.aliyun，582KB）

#### Dashboard.vue 重写为三栏大屏布局

```
┌─────────────┬─────────────────┬──────────────┐
│ 统计卡片 (4个：书库/IP指数/作者/评论)            │
├─────────────┼─────────────────┼──────────────┤
│ 月票 Top10  │  读者地理分布    │  平台分布    │
│ 排行榜      │  (中国地图)      │              │
│             │                 │  IP深度雷达  │
│ 起点/纵横   │                 │              │
│ 跨平台      │                 │  热门词云    │
│             │  全站互动趋势    │              │
│ 题材饼图    │  (折线图)        │  快捷入口    │
│             │                 │  AI/对话     │
└─────────────┴─────────────────┴──────────────┘
```

#### 真实数据接入

| 模块 | 数据来源 | 样例数据 |
|------|---------|---------|
| 月票 Top10 | 起点 `novel_realtime_tracking` + 纵横 `zongheng_realtime_tracking` | 无敌天命 20.1万、捞尸人 13.3万 |
| 地理分布 | 纵横评论 `ip_region`（11万条） | 广东 11508、山东 8174、江苏 6597 |
| 题材饼图 | `/charts/distribution` → 两库 category 汇总 | 玄幻奇幻 33.65%、都市 25.89% |
| 趋势图 | `/charts/trend` → 月票月度统计 | 月度互动曲线 |
| 平台分布 | `/charts/platform` → 各库 record count | 起点 602 vs 纵横 1308 |
| 雷达/词云 | `/charts/radar`、`/charts/wordcloud` | 已接真实 |

#### 数据库表结构参考

**纵横 (`zongheng_analysis_v8`)**
- `zongheng_book_comments`: thread_id, book_id, book_title, user_id, nickname, content, **ip_region**, crawl_time（11万行）
- `zongheng_book_ranks`: title, author, category, monthly_ticket, rank_num, fan_count, word_count...（7787行）
- `zongheng_realtime_tracking`: novel_id, title, monthly_tickets, total_recommend, monthly_ticket_rank（101行）

**起点 (`qidian_data`)**
- `novel_monthly_stats`: title, author, category, monthly_ticket_count, collection_count, recommendation_count...（3469行）
- `novel_realtime_tracking`: novel_id, title, monthly_tickets, collection_count, monthly_ticket_rank（100行）

---

## 历史记忆要点

### 数据库连接配置
```python
ZONGHENG_CONFIG = {'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'zongheng_analysis_v8'}
QIDIAN_CONFIG   = {'host': 'localhost', 'port': 3306, 'user': 'root', 'password': 'root', 'database': 'qidian_data'}
```

### 已有的 Chart API 端点清单
| 路由 | data_manager 方法 | 用途 |
|------|------------------|------|
| `/stats/overview` | `get_overview_stats()` | 总览统计 |
| `/charts/rank` | `get_top_ip_novels(10)` | IP价值排行 |
| `/charts/distribution` | `get_category_distribution()` | 题材分布 |
| `/charts/trend` | `get_interaction_trend()` | 互动趋势 |
| `/charts/platform` | `get_platform_distribution()` | 平台分布 |
| `/charts/wordcloud` | `get_wordcloud_data()` | 作者词云 |
| `/charts/radar` | `get_radar_data()` | IP雷达 |
| `/charts/scatter` | `get_scatter_data()` | 散点图 |
| `/charts/correlation` | `get_correlation_matrix()` | 相关矩阵 |
| `/charts/author_tiers` | `get_author_tiers()` | 作家梯队 |
| `/charts/geo_region` | `get_geo_region_distribution()` | 🆕 地理分布 |
| `/charts/ticket_top` | `get_monthly_ticket_top()` | 🆕 月票排行 |

### 前端图表组件清单 (`src/components/charts/`)
TopRankBar, TrendLineChart, CategoryPie, WordCloud, RadarChart, AuthorPyramid, GeoMap（🆕），AnimatedBarChart, ComparisonChart, FloatingBubbles, FlowingWave, TrendSparkline
