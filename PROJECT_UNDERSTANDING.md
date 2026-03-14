## IP-Lumina 项目架构与理解

### 项目概述
这是一个网络文学IP价值评估与流行趋势分析平台，用于分析起点中文网、纵横中文网等平台的网络小说数据，计算IP价值评分，进行趋势分析。

### 数据流架构
1. **数据采集层**: 
   - `new-analysis/`: Selenium爬虫，从纵横中文网采集小说数据 (MongoDB存储)
   - 数据字段: 标题、作者、点击量、收藏量、月票、推荐票、字数、状态等

2. **数据处理层**:
   - `data_analysis_v3/`: 高级分析版本
     - 数据提取 (extract_data.py): 从MySQL数据库提取数据
     - 特征工程 (feature_engineering.py): 熵权法计算IP评分，情感分析
     - 模型训练 (model_training.py): XGBoost双引擎模型 (成熟期/引入期)
     - 可视化 (visualize_results.py): 象限图、情感分析图表
   - `data_analysis/`: 基础分析版本
     - NLP分析 (nlp_analysis.py): LDA主题建模 + 情感分析
     - IP价值计算 (ip_value_model.py): 5维度权重评分
     - 趋势分析 (trend_analysis.py): 月票走势

3. **分析算法**:
   - **IP价值评估**: 熵权法 + XGBoost回归
   - **情感分析**: SnowNLP
   - **主题建模**: LDA (5-10个主题)
   - **可视化**: Matplotlib, Seaborn

### 现有界面现状
- ❌ 无Web界面，目前只有Python脚本生成静态图表
- ❌ 无用户交互，只能命令行运行
- ❌ 数据展示不直观，只能查看CSV文件

### 界面改进需求
1. **Web平台搭建**: 构建前后端分离的Web应用
2. **数据可视化**: 交互式图表展示IP价值、趋势分析
3. **用户功能**: 搜索小说、查看详情、对比分析
4. **管理后台**: 数据更新、模型重训练

### 技术栈建议
- **后端**: Flask + SQLAlchemy (轻量，易部署)
- **前端**: React/Vue.js + ECharts/D3.js (交互式图表)
- **数据库**: SQLite/PostgreSQL (替代MySQL/MongoDB)
- **部署**: Docker + Nginx

### 实施计划
1. 创建Flask API后端
2. 构建React前端界面
3. 集成数据可视化
4. 添加用户交互功能
5. 部署测试