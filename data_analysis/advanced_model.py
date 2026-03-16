import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Configs
input_file = "d:/analysis-novel/data_analysis/combined_features.csv"
output_file = "d:/analysis-novel/data_analysis/advanced_analysis_results.csv"
output_dir = "d:/analysis-novel/data_analysis/charts"
os.makedirs(output_dir, exist_ok=True)

# Font
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def advanced_analysis():
    print("Loading Combined Data...")
    df = pd.read_csv(input_file)
    
    # 1. K-Means Clustering (S/A/B/C)
    # Features for clustering
    features = ['word_count', 'month_tickets', 'total_recommendation_count', 'engagement_score']
    X = df[features].fillna(0)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=4, random_state=42)
    df['cluster'] = kmeans.fit_predict(X_scaled)
    
    # Analyze Clusters to assign Tiers (S > A > B > C)
    # We rank clusters by average 'month_tickets'
    cluster_ranks = df.groupby('cluster')['month_tickets'].mean().sort_values(ascending=False).index
    tier_map = {cluster_ranks[0]: 'S级神作', cluster_ranks[1]: 'A级潜力', cluster_ranks[2]: 'B级腰部', cluster_ranks[3]: 'C级普通'}
    df['tier'] = df['cluster'].map(tier_map)
    
    print("Clustering Complete. Tiers assigned.")
    print(df['tier'].value_counts())
    
    # 2. Cross-Platform Analysis
    print("\n--- Platform Comparison ---")
    print(df.groupby('platform')[['month_tickets', 'engagement_score']].mean())
    
    # 3. Visualizations
    
    # A. Tier Distribution Scatter
    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='word_count', y='month_tickets', hue='tier', style='platform', data=df, palette='deep')
    plt.title('小说分级聚类分析 (字数 vs 月票)', fontsize=16)
    plt.xlabel('总字数', fontsize=12)
    plt.ylabel('月票数', fontsize=12)
    plt.savefig(f"{output_dir}/cluster_scatter.png")
    
    # B. Platform Contrast Boxplot
    plt.figure(figsize=(8, 6))
    sns.boxplot(x='platform', y='engagement_score', data=df)
    plt.title('起点 vs 纵横：互动深度对比', fontsize=16)
    plt.ylabel('互动深度 score', fontsize=12)
    plt.savefig(f"{output_dir}/platform_contrast.png")

    # C. Category Distribution (New)
    plt.figure(figsize=(10, 6))
    # Filter only Qidian for category analysis (Zongheng might have diff cat names)
    df_q = df[df['platform'] == 'Qidian']
    sns.boxplot(x='category_name', y='month_tickets', data=df_q, palette='Set3') 
    plt.title('起点各频道月票热度分布', fontsize=16)
    plt.ylabel('月票数', fontsize=12)
    plt.xlabel('频道', fontsize=12)
    plt.xticks(rotation=45)
    plt.savefig(f"{output_dir}/category_month_tickets.png")
    
    # Save Results
    df.to_csv(output_file, index=False, encoding='utf-8_sig')
    print(f"Saved Advanced Analysis to {output_file}")

if __name__ == "__main__":
    advanced_analysis()
