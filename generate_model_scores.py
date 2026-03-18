#!/usr/bin/env python3
"""
使用IP评分模型v8.1为书库所有作品生成IP评分
创建新表 ip_model_scores 存储预测结果
"""

import pandas as pd
import numpy as np
import pymysql
import os
import sys

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'integrated_system', 'backend'))

from data_manager import QIDIAN_CONFIG, ZONGHENG_CONFIG
from ip_scoring_model_v81 import evaluate_ip

# 数据库配置用于存储新表
TARGET_DB = ZONGHENG_CONFIG

def get_qidian_data():
    """获取起点数据"""
    print("\n[1/4] 获取起点数据...")
    try:
        conn = pymysql.connect(**QIDIAN_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    title, author, category, status,
                    word_count,
                    monthly_ticket_count,
                    recommendation_count,
                    collection_count,
                    ROW_NUMBER() OVER (ORDER BY monthly_ticket_count DESC) as `rank`
                FROM novel_monthly_stats
                WHERE word_count > 0
            """)
            data = cur.fetchall()
        conn.close()
        
        df = pd.DataFrame(data)
        df['platform'] = 'Qidian'
        print(f"  ✓ 获取 {len(df)} 本起点作品")
        return df
    except Exception as e:
        print(f"  ✗ 获取起点数据失败: {e}")
        return pd.DataFrame()

def get_zongheng_data():
    """获取纵横数据"""
    print("\n[2/4] 获取纵横数据...")
    try:
        conn = pymysql.connect(**ZONGHENG_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    title, author, category, status,
                    word_count,
                    monthly_ticket,
                    total_rec,
                    total_click,
                    ROW_NUMBER() OVER (ORDER BY monthly_ticket DESC) as `rank`
                FROM zongheng_book_ranks
                WHERE word_count > 0
            """)
            data = cur.fetchall()
        conn.close()
        
        df = pd.DataFrame(data)
        df['platform'] = 'Zongheng'
        print(f"  ✓ 获取 {len(df)} 本纵横作品")
        return df
    except Exception as e:
        print(f"  ✗ 获取纵横数据失败: {e}")
        return pd.DataFrame()

def predict_scores(df):
    """使用evaluate_ip函数预测评分"""
    print("\n[3/4] 预测IP评分...")
    
    # 先按月票排序生成排名（区分平台）
    print("  根据月票数生成平台内排名...")
    df['rank'] = 999  # 默认值
    
    for platform in ['Qidian', 'Zongheng']:
        mask = df['platform'] == platform
        platform_df = df[mask].copy()
        if not platform_df.empty:
            # 按月票降序排列，生成排名
            platform_df = platform_df.sort_values('finance', ascending=False)
            platform_df['rank'] = range(1, len(platform_df) + 1)
            df.loc[mask, 'rank'] = platform_df['rank'].values
    
    scores = []
    grades = []
    
    # DataManager字段映射: finance=月票, popularity=点击/收藏, interaction=推荐
    total = len(df)
    for idx, row in df.iterrows():
        # 构建evaluate_ip需要的参数 - 使用DataManager字段名
        monthly_val = row.get('finance')  # 月票
        rec_val = row.get('interaction')  # 推荐
        click_val = row.get('popularity')  # 点击/收藏
        word_val = row.get('word_count')
        rank_val = row.get('rank', 999)
        
        book_data = {
            'rank': int(rank_val) if pd.notna(rank_val) else 999,
            'monthly_tickets': int(monthly_val) if pd.notna(monthly_val) else 0,
            'total_recommend': int(rec_val) if pd.notna(rec_val) else 0,
            'word_count': int(word_val) if pd.notna(word_val) else 0,
            'total_click': int(click_val) if pd.notna(click_val) else 0,
            'platform': row.get('platform', 'Qidian')
        }
        
        result = evaluate_ip(book_data)
        scores.append(result['ip_score'])
        grades.append(result['ip_grade'])
        
        if (idx + 1) % 500 == 0:
            print(f"  处理进度: {idx + 1}/{total}")
    
    df['predicted_score'] = scores
    df['predicted_grade'] = grades
    
    # 将E级映射为D级（书库最低等级是D）
    df.loc[df['predicted_grade'] == 'E', 'predicted_grade'] = 'D'
    
    print(f"  ✓ 完成 {len(df)} 本作品评分预测")
    print(f"\n  评分分布:")
    print(f"    S级: {len(df[df.predicted_grade=='S'])} 本")
    print(f"    A级: {len(df[df.predicted_grade=='A'])} 本")
    print(f"    B级: {len(df[df.predicted_grade=='B'])} 本")
    print(f"    C级: {len(df[df.predicted_grade=='C'])} 本")
    print(f"    D级: {len(df[df.predicted_grade=='D'])} 本")
    
    return df

def create_scores_table(df):
    """创建新表存储预测结果"""
    print("\n[4/4] 创建评分表...")
    try:
        conn = pymysql.connect(**TARGET_DB, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            # 删除旧表（如果存在）
            cur.execute("DROP TABLE IF EXISTS ip_model_scores")
            
            # 创建新表
            cur.execute("""
                CREATE TABLE ip_model_scores (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    author VARCHAR(255),
                    platform VARCHAR(50),
                    category VARCHAR(100),
                    status VARCHAR(50),
                    word_count INT,
                    monthly_tickets INT,
                    total_recommend INT,
                    total_click INT,
                    rank_in_platform INT,
                    predicted_score FLOAT,
                    predicted_grade VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_title (title),
                    INDEX idx_score (predicted_score),
                    INDEX idx_grade (predicted_grade)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 插入数据
            insert_sql = """
                INSERT INTO ip_model_scores 
                (title, author, platform, category, status, word_count, 
                 monthly_tickets, total_recommend, total_click, rank_in_platform,
                 predicted_score, predicted_grade)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = []
            for _, row in df.iterrows():
                # 使用DataManager字段名: finance=月票, popularity=点击/收藏, interaction=推荐
                monthly_val = row.get('finance')
                rec_val = row.get('interaction')
                click_val = row.get('popularity')
                word_val = row.get('word_count')
                rank_val = row.get('rank', 999)
                
                values.append((
                    row['title'], row['author'], row['platform'], 
                    row.get('category', '') or '', row.get('status', '') or '',
                    int(word_val) if pd.notna(word_val) else 0,
                    int(monthly_val) if pd.notna(monthly_val) else 0,
                    int(rec_val) if pd.notna(rec_val) else 0,
                    int(click_val) if pd.notna(click_val) else 0,
                    int(rank_val) if pd.notna(rank_val) else 999,
                    float(row['predicted_score']), row['predicted_grade']
                ))
            
            # 批量插入
            batch_size = 500
            for i in range(0, len(values), batch_size):
                batch = values[i:i+batch_size]
                cur.executemany(insert_sql, batch)
                conn.commit()
                print(f"  ✓ 已插入 {min(i+batch_size, len(values))}/{len(values)} 条记录")
            
        conn.close()
        print(f"\n[OK] 成功创建 ip_model_scores 表，共 {len(df)} 条记录")
        return True
        
    except Exception as e:
        print(f"  ✗ 创建表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("IP评分预测系统 - 使用模型v8.1")
    print("=" * 60)
    
    # 使用DataManager已加载的去重数据
    from data_manager import DataManager
    dm = DataManager()
    
    if dm.df.empty:
        print("[ERROR] DataManager没有数据，退出")
        return
    
    # 复制DataFrame避免修改原数据
    all_df = dm.df.copy()
    print(f"\n[OK] 使用DataManager去重后数据: {len(all_df)} 本作品")
    
    # 2. 预测评分
    scored_df = predict_scores(all_df)
    
    # 3. 创建表
    if create_scores_table(scored_df):
        print("\n" + "=" * 60)
        print("完成！新表 ip_model_scores 已创建")
        print("=" * 60)
    else:
        print("\n[ERROR] 创建表失败")

if __name__ == "__main__":
    main()
