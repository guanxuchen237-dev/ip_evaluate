import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import matplotlib.font_manager as fm

# Set Chinese font (SimHei usually works on Windows)
plt.rcParams['font.sans-serif'] = ['SimHei'] 
plt.rcParams['axes.unicode_minus'] = False

DATA_DIR = r"d:\analysis-novel\data_analysis_v3"
IN_FILE = os.path.join(DATA_DIR, "final_featured_data.csv")
PLOT_DIR = os.path.join(DATA_DIR, "plots")

if not os.path.exists(PLOT_DIR):
    os.makedirs(PLOT_DIR)

def main():
    if not os.path.exists(IN_FILE):
        print("Data file not found.")
        return
        
    df = pd.read_csv(IN_FILE)
    
    # 1. Finance-Popularity Quadrant
    plt.figure(figsize=(10, 8))
    sns.scatterplot(data=df, x='popularity', y='finance', hue='lifecycle_stage', alpha=0.6)
    
    # Add quadrant lines (median)
    x_med = df['popularity'].median()
    y_med = df['finance'].median()
    plt.axvline(x_med, color='r', linestyle='--', alpha=0.5)
    plt.axhline(y_med, color='r', linestyle='--', alpha=0.5)
    
    plt.xscale('log') # Log scale because popularity varies wildly
    plt.yscale('log')
    plt.title('付费-热度 象限图 (Log Scale)')
    plt.xlabel('热度 (Popularity)')
    plt.ylabel('付费 (Finance)')
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "quadrant_chart.png"))
    print("Generated quadrant_chart.png")
    
    # 2. Lifecycle Feature Boxplot (Growth Potential)
    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df, x='lifecycle_stage', y='growth_potential', showfliers=False)
    plt.title('生命周期特征差异: 增长潜力')
    plt.savefig(os.path.join(PLOT_DIR, "lifecycle_boxplot.png"))
    print("Generated lifecycle_boxplot.png")
    
    # 3. Sentiment vs IP Score
    plt.figure(figsize=(10, 6))
    # Filter out 0 sentiment (empty abstracts) for clearer view if Zongheng has many
    df_sent = df[df['abstract'].notna() & (df['abstract'] != '')]
    sns.regplot(data=df_sent, x='sentiment_intensity', y='IP_Score', scatter_kws={'alpha':0.3}, line_kws={'color':'red'})
    plt.title('情感强度与 IP 得分关系')
    plt.xlabel('情感强度 (abs(score-0.5)*2)')
    plt.ylabel('IP Score')
    plt.savefig(os.path.join(PLOT_DIR, "sentiment_plot.png"))
    print("Generated sentiment_plot.png")

    # 4. Grade Distribution
    plt.figure(figsize=(8, 6))
    order = ['S', 'A', 'B', 'C']
    sns.countplot(data=df, x='Grade', order=order, palette='viridis')
    plt.title('作品评级分布 (Grade Distribution)')
    plt.savefig(os.path.join(PLOT_DIR, "grade_distribution.png"))
    print("Generated grade_distribution.png")

if __name__ == "__main__":
    main()
