import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Configs
input_file = "d:/analysis-novel/data_analysis/qidian_final_model.csv"
output_dir = "d:/analysis-novel/data_analysis/charts"
os.makedirs(output_dir, exist_ok=True)

# Set Chinese font
plt.rcParams['font.sans-serif'] = ['SimHei'] # Windows default Chinese font
plt.rcParams['axes.unicode_minus'] = False

def visualize():
    print("Loading data for Visualization...")
    df = pd.read_csv(input_file)
    top10 = df.head(10)
    
    # 1. IP Value Bar Chart
    plt.figure(figsize=(10, 6))
    sns.barplot(x='IP_Value', y='title', data=top10, palette='viridis')
    plt.title('网络文学 IP 价值榜单 TOP10', fontsize=16)
    plt.xlabel('IP 价值总分 (0-100)', fontsize=12)
    plt.ylabel('小说名称', fontsize=12)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/top10_ip_value.png")
    print("Saved bar chart.")

    # 2. Radar Chart for Top 1 Data
    # Dimensions
    categories = ['market_score', 'content_score', 'reputation_score', 'engagement_score', 'potential_score']
    labels_cn = ['市场表现', '内容质量', '用户口碑', '互动深度', '增长潜力']
    
    # Top 1 book
    book = top10.iloc[0]
    values = book[categories].values.flatten().tolist()
    values += values[:1] # Close the circle
    
    angles = [n / float(len(categories)) * 2 * np.pi for n in range(len(categories))]
    angles += angles[:1]
    
    plt.figure(figsize=(6, 6))
    ax = plt.subplot(111, polar=True)
    plt.xticks(angles[:-1], labels_cn, size=12)
    ax.plot(angles, values, linewidth=1, linestyle='solid', label=book['title'])
    ax.fill(angles, values, 'b', alpha=0.1)
    plt.title(f"IP 五维价值分析: {book['title']}", fontsize=16, y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(1.1, 1.1))
    plt.savefig(f"{output_dir}/radar_chart_top1.png")
    print("Saved radar chart.")
    
    # 3. Correlation Heatmap
    plt.figure(figsize=(9, 7))
    corr_cols = categories + ['IP_Value']
    df_rename = df[corr_cols].rename(columns={
        'market_score': '市场表现',
        'content_score': '内容质量',
        'reputation_score': '用户口碑',
        'engagement_score': '互动深度',
        'potential_score': '增长潜力',
        'IP_Value': 'IP总价值'
    })
    
    corr = df_rename.corr()
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", annot_kws={"size": 10})
    plt.title('IP 评估维度相关性矩阵', fontsize=16)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/correlation_matrix.png")
    print("Saved correlation map.")

if __name__ == "__main__":
    visualize()
