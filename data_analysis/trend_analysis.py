import pandas as pd
import pymongo
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Config
MONGO_URI = "mongodb://127.0.0.1:27017"
DB_NAME = "novel_analysis"
COLLECTION_NAME = "qidian_history"
OUTPUT_DIR = "d:/analysis-novel/data_analysis/charts"

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

def plot_trends():
    client = pymongo.MongoClient(MONGO_URI)
    col = client[DB_NAME][COLLECTION_NAME]
    
    data = list(col.find())
    if not data:
        print("No history data found.")
        return
        
    df = pd.DataFrame(data)
    
    # Sort
    df = df.sort_values('data_month')
    
    # 1. Total Market Trend (Avg Rank - Lower is better, but Avg of top 20 is always ~10.5 so this chart is less useful for rank)
    # Skip market trend or change to "Stability"? 
    # Let's keep Top 5 Books Trend only, as it's the main request.
    
    # 2. Top 5 Books Trend
    # Find books that appear in at least 3 months
    book_counts = df['title'].value_counts()
    valid_books = book_counts[book_counts >= 3].index
    
    df_valid = df[df['title'].isin(valid_books)]
    
    # Pick Top 5 by TOTAL Tickets (Max Tickets in any month)
    top_books = df_valid.groupby('title')['history_tickets'].max().sort_values(ascending=False).head(5).index
    df_top = df_valid[df_valid['title'].isin(top_books)]
    
    plt.figure(figsize=(12, 6))
    sns.lineplot(x='data_month', y='history_tickets', hue='title', data=df_top, marker='o', linewidth=2.5)
    # plt.gca().invert_yaxis() # Not for tickets
    plt.title('头部 IP 月票走势分析 (Historical Monthly Tickets)', fontsize=16)
    plt.xlabel('月份')
    plt.ylabel('月票数量')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/top5_trend.png")
    
    print("Trend charts saved.")

if __name__ == "__main__":
    plot_trends()
