#!/usr/bin/env python3
"""
使用大模型对所有书籍进行专业六维度独立评分
更新 ip_ai_evaluation 表的六维分数
"""

import sys
import os
import pymysql
import pandas as pd
import time

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'integrated_system', 'backend'))

from data_manager import ZONGHENG_CONFIG
from ai_service import ai_service

# 数据库配置
DB_CONFIG = ZONGHENG_CONFIG

def get_all_books():
    """获取所有需要评分的书籍"""
    print("\n[1/3] 获取书库数据...")
    try:
        # 使用DataManager获取数据
        from data_manager import data_manager
        
        if data_manager.df.empty:
            print("  ✗ DataManager没有数据")
            return []
        
        # 筛选有简介的书籍
        df = data_manager.df.copy()
        df = df[df['abstract'].notna() & (df['abstract'] != '')]
        
        # 转换为字典列表
        books = df[['title', 'author', 'platform', 'abstract', 'word_count']].to_dict('records')
        
        print(f"  ✓ 获取 {len(books)} 本有简介的作品")
        return books
    except Exception as e:
        print(f"  ✗ 获取数据失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def update_six_dimensions(title, platform, scores):
    """更新数据库中的六维分数"""
    try:
        conn = pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE ip_ai_evaluation 
                SET story_score = %s,
                    character_score = %s,
                    world_score = %s,
                    commercial_score = %s,
                    adaptation_score = %s,
                    safety_score = %s,
                    eval_method = 'ai_llm_v1'
                WHERE title = %s AND platform = %s
            """, (
                scores['story_score'],
                scores['character_score'],
                scores['world_score'],
                scores['commercial_score'],
                scores['adaptation_score'],
                scores['safety_score'],
                title, platform
            ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ 更新数据库失败: {e}")
        return False

def main():
    print("=" * 60)
    print("AI大模型六维度评分系统")
    print("=" * 60)
    
    # 1. 获取所有书籍
    books = get_all_books()
    if not books:
        print("[ERROR] 没有获取到数据")
        return
    
    # 2. 逐个评分
    print(f"\n[2/3] 开始大模型评分（共 {len(books)} 本）...")
    print("注意：每本书需要调用一次大模型，预计耗时较长\n")
    
    success_count = 0
    fail_count = 0
    
    for idx, book in enumerate(books, 1):
        title = book['title']
        author = book.get('author', '')
        platform = book['platform']
        abstract = book['abstract']
        word_count = book.get('word_count', 0) or 0
        
        # 从DataManager获取category
        category = '其他'
        try:
            from data_manager import data_manager
            if not data_manager.df.empty:
                df_match = data_manager.df[
                    (data_manager.df['title'] == title) & 
                    (data_manager.df['platform'] == platform)
                ]
                if not df_match.empty:
                    category = df_match.iloc[0].get('category', '其他')
        except:
            pass
        
        print(f"[{idx}/{len(books)}] {title} ({category})")
        
        try:
            # 调用大模型评分
            scores = ai_service.analyze_six_dimensions(
                title=title,
                abstract=abstract,
                category=category,
                word_count=word_count,
                author=author
            )
            
            # 更新数据库
            if update_six_dimensions(title, platform, scores):
                success_count += 1
                print(f"  ✓ 故事{scores['story_score']:.0f}/角色{scores['character_score']:.0f}/世界观{scores['world_score']:.0f}/商业{scores['commercial_score']:.0f}/改编{scores['adaptation_score']:.0f}/安全{scores['safety_score']:.0f}")
            else:
                fail_count += 1
                
        except Exception as e:
            print(f"  ✗ 评分失败: {e}")
            fail_count += 1
        
        # 每10本休息1秒，避免API限流
        if idx % 10 == 0:
            print(f"\n  --- 进度: {idx}/{len(books)} | 成功:{success_count} | 失败:{fail_count} ---\n")
            time.sleep(1)
    
    # 3. 完成报告
    print("\n" + "=" * 60)
    print("评分完成！")
    print("=" * 60)
    print(f"总计: {len(books)} 本")
    print(f"成功: {success_count} 本")
    print(f"失败: {fail_count} 本")
    print("\n六维分数已更新到 ip_ai_evaluation 表")
    print("eval_method 标记为 'ai_llm_v1'")

if __name__ == "__main__":
    main()
