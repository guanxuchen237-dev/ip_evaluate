# 网络文学IP价值评估与流行趋势分析系统
## View-Analysis Project

---

## 📁 项目结构

```
view-analysis/
├── data/                    # 数据文件
│   └── cleaned_data.csv     # 清洗后的数据
├── models/                  # 保存的模型
├── outputs/                 # 输出图表
├── utils/                   # 工具函数
│   ├── __init__.py
│   └── stopwords.py         # 停用词表
├── step1_data_alignment.py  # 数据对齐与清洗
├── step2_label_construction.py # 熵权法构建IP_Score
├── step3_feature_engineering.py # 特征工程
├── step4_model_training.py  # XGBoost模型训练
├── step5_trend_analysis.py  # LDA主题与趋势分析
├── step6_visualization.py   # 可视化生成
├── run_all.py               # 一键运行所有步骤
└── README.md                # 项目说明
```

---

## 🚀 快速开始

```bash
# 安装依赖
pip install pandas numpy scikit-learn matplotlib seaborn jieba gensim wordcloud

# 一键运行所有分析
python run_all.py
```

---

## 📊 分析流程

### Step 1: 数据对齐 (Data Alignment)
- 统一纵横和起点的字段名
- 处理缺失值和异常值
- 字段映射：title, author, category, word_count, status等

### Step 2: 标签构建 (Label Construction)
- 使用**熵权法**计算IP_Score
- 公式：$IP\_Score = w_1 \cdot N(热度) + w_2 \cdot N(互动) + w_3 \cdot N(付费)$
- 权重由数据自动计算，客观性强

### Step 3: 特征工程 (Feature Engineering)
- 数值特征：标准化、对数变换
- 衍生特征：互动率、含金量
- 类别特征：One-Hot编码
- 文本特征：TF-IDF、LDA主题概率

### Step 4: 模型训练 (Model Training)
- 算法：XGBoost / GradientBoosting
- 评估：MSE, RMSE, R² Score
- 输出：特征重要性排名

### Step 5: 趋势分析 (Trend Analysis)
- LDA主题模型（8个主题）
- 主题随时间变化趋势
- 高频关键词统计

### Step 6: 可视化 (Visualization)
- 特征重要性条形图
- 平台对比分析
- 词云、热力图等

---

## 📈 核心发现

| 特征 | 重要性 | 含义 |
|------|--------|------|
| click_or_collect | 38.2% | 热度是IP核心 |
| monthly_ticket | 8.6% | 付费意愿 |
| week_recommend | 5.9% | 近期活跃度 |

**结论**：用户基数(75%) >> 付费意愿(16%)

---

## 📚 技术栈

- Python 3.8+
- Pandas, NumPy
- Scikit-learn, XGBoost
- Matplotlib, Seaborn
- Jieba, Gensim, WordCloud
