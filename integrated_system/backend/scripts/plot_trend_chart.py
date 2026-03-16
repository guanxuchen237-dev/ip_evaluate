#!/usr/bin/env python3
"""
热门作品月票趋势图绘制脚本
从数据库获取起点和纵横各前5名热度最高且周期长的作品，绘制趋势图
缺失月份使用线性插值算法补全（不修改数据库）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import numpy as np

# 数据库配置
try:
    from data_manager import QIDIAN_CONFIG as QD_CONFIG, ZONGHENG_CONFIG as ZH_CONFIG
except ImportError:
    from backend.data_manager import QIDIAN_CONFIG as QD_CONFIG, ZONGHENG_CONFIG as ZH_CONFIG


def interpolate_missing_months(dates: List[str], values: List[int]) -> Tuple[List[str], List[Optional[int]]]:
    """
    对缺失月份进行线性插值
    不修改原始数据，返回补全后的新数据
    """
    if not dates or len(dates) == 0:
        return [], []
    
    if len(dates) == 1:
        return dates, values
    
    def parse_date(date_str: str) -> Optional[Tuple[int, int]]:
        match = date_str.match(r'(\d{4})-(\d{2})')
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None
    
    def generate_months(start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        result = []
        year, month = start
        while year < end[0] or (year == end[0] and month <= end[1]):
            result.append((year, month))
            month += 1
            if month > 12:
                month = 1
                year += 1
        return result
    
    start = parse_date(dates[0])
    end = parse_date(dates[-1])
    if not start or not end:
        return dates, values
    
    all_months = generate_months(start, end)
    original_data = {date: val for date, val in zip(dates, values)}
    
    new_dates = []
    new_values = []
    
    for year, month in all_months:
        date_key = f"{year}-{month:02d}"
        new_dates.append(date_key)
        if date_key in original_data:
            new_values.append(original_data[date_key])
        else:
            new_values.append(None)
    
    # 线性插值
    for i in range(len(new_values)):
        if new_values[i] is None:
            prev_idx = next((j for j in range(i-1, -1, -1) if new_values[j] is not None), -1)
            next_idx = next((j for j in range(i+1, len(new_values)) if new_values[j] is not None), -1)
            
            if prev_idx >= 0 and next_idx >= 0:
                prev_val = new_values[prev_idx]
                next_val = new_values[next_idx]
                gap = next_idx - prev_idx
                pos = i - prev_idx
                interpolated = prev_val + (next_val - prev_val) * (pos / gap)
                new_values[i] = round(interpolated)
            elif prev_idx >= 0:
                new_values[i] = new_values[prev_idx]
            elif next_idx >= 0:
                new_values[i] = new_values[next_idx]
            else:
                new_values[i] = 0
    
    return new_dates, new_values


def get_top_books_qidian(limit: int = 5) -> List[Dict]:
    """获取起点前N名热度最高且周期长的作品"""
    books = []
    try:
        conn = pymysql.connect(**QD_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            # 查询热度最高且周期长的作品
            cur.execute("""
                SELECT 
                    title,
                    MAX(monthly_tickets_on_list) as max_tickets,
                    COUNT(DISTINCT CONCAT(year, '-', month)) as month_count
                FROM novel_monthly_stats
                GROUP BY title
                HAVING month_count >= 3
                ORDER BY max_tickets DESC, month_count DESC
                LIMIT %s
            """, (limit,))
            
            top_books = cur.fetchall()
            
            # 获取每本书的月度趋势数据
            for book in top_books:
                title = book['title']
                cur.execute("""
                    SELECT 
                        CONCAT(year, '-', LPAD(month, 2, '0')) as period,
                        MAX(monthly_tickets_on_list) as monthly_tickets
                    FROM novel_monthly_stats
                    WHERE title = %s
                    GROUP BY year, month
                    ORDER BY year, month
                """, (title,))
                
                trend_data = cur.fetchall()
                if trend_data:
                    dates = [d['period'] for d in trend_data]
                    tickets = [int(d['monthly_tickets'] or 0) for d in trend_data]
                    
                    # 插值补全缺失月份
                    interpolated_dates, interpolated_tickets = interpolate_missing_months(dates, tickets)
                    
                    books.append({
                        'title': title,
                        'platform': '起点',
                        'original_dates': dates,
                        'original_tickets': tickets,
                        'dates': interpolated_dates,
                        'tickets': interpolated_tickets
                    })
        
        conn.close()
    except Exception as e:
        print(f"[ERROR] 获取起点数据失败: {e}")
    
    return books


def get_top_books_zongheng(limit: int = 5) -> List[Dict]:
    """获取纵横前N名热度最高且周期长的作品"""
    books = []
    try:
        conn = pymysql.connect(**ZH_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            # 查询热度最高且周期长的作品
            cur.execute("""
                SELECT 
                    title,
                    MAX(monthly_ticket) as max_tickets,
                    COUNT(DISTINCT CONCAT(year, '-', month)) as month_count
                FROM zongheng_book_ranks
                GROUP BY title
                HAVING month_count >= 3
                ORDER BY max_tickets DESC, month_count DESC
                LIMIT %s
            """, (limit,))
            
            top_books = cur.fetchall()
            
            # 获取每本书的月度趋势数据
            for book in top_books:
                title = book['title']
                cur.execute("""
                    SELECT 
                        CONCAT(year, '-', LPAD(month, 2, '0')) as period,
                        MAX(monthly_ticket) as monthly_tickets
                    FROM zongheng_book_ranks
                    WHERE title = %s
                    GROUP BY year, month
                    ORDER BY year, month
                """, (title,))
                
                trend_data = cur.fetchall()
                if trend_data:
                    dates = [d['period'] for d in trend_data]
                    tickets = [int(d['monthly_tickets'] or 0) for d in trend_data]
                    
                    # 插值补全缺失月份
                    interpolated_dates, interpolated_tickets = interpolate_missing_months(dates, tickets)
                    
                    books.append({
                        'title': title,
                        'platform': '纵横',
                        'original_dates': dates,
                        'original_tickets': tickets,
                        'dates': interpolated_dates,
                        'tickets': interpolated_tickets
                    })
        
        conn.close()
    except Exception as e:
        print(f"[ERROR] 获取纵横数据失败: {e}")
    
    return books


def plot_trend_chart(books: List[Dict], output_file: str = 'trend_chart.png'):
    """绘制趋势图"""
    if not books:
        print("没有数据可绘制")
        return
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(16, 9))
    
    # 起点和纵横的颜色配置
    qidian_colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
    zongheng_colors = ['#3ba272', '#fc8452', '#9a60b4', '#ea7ccc', '#ff9f7f']
    
    qidian_idx = 0
    zongheng_idx = 0
    
    for book in books:
        dates = book['dates']
        tickets = book['tickets']
        title = book['title']
        platform = book['platform']
        
        # 转换日期格式
        x_dates = [datetime.strptime(d, '%Y-%m') for d in dates]
        
        # 选择颜色
        if platform == '起点':
            color = qidian_colors[qidian_idx % len(qidian_colors)]
            qidian_idx += 1
        else:
            color = zongheng_colors[zongheng_idx % len(zongheng_colors)]
            zongheng_idx += 1
        
        # 绘制线条
        ax.plot(x_dates, tickets, label=f"[{platform}] {title}", 
                color=color, linewidth=2, marker='o', markersize=3)
    
    # 设置图表属性
    ax.set_xlabel('月份', fontsize=12)
    ax.set_ylabel('月票数量', fontsize=12)
    ax.set_title('起点与纵横热门作品月票趋势对比\n（各平台热度最高且周期长的前5名作品）', 
                 fontsize=14, fontweight='bold')
    
    # 设置X轴格式
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45, ha='right')
    
    # 添加网格
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # 添加图例
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=9)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"图表已保存到: {output_file}")
    
    # 显示图表
    plt.show()


def main():
    """主函数"""
    print("=" * 60)
    print("热门作品月票趋势图绘制")
    print("=" * 60)
    
    # 获取起点数据
    print("\n[1/3] 正在获取起点前5名热门作品...")
    qidian_books = get_top_books_qidian(5)
    print(f"      获取到 {len(qidian_books)} 本起点作品")
    for book in qidian_books:
        print(f"      - {book['title']}: {len(book['original_dates'])}个月数据")
    
    # 获取纵横数据
    print("\n[2/3] 正在获取纵横前5名热门作品...")
    zongheng_books = get_top_books_zongheng(5)
    print(f"      获取到 {len(zongheng_books)} 本纵横作品")
    for book in zongheng_books:
        print(f"      - {book['title']}: {len(book['original_dates'])}个月数据")
    
    # 合并数据
    all_books = qidian_books + zongheng_books
    
    if not all_books:
        print("\n[ERROR] 没有获取到任何数据，请检查数据库连接")
        return
    
    # 绘制图表
    print("\n[3/3] 正在绘制趋势图...")
    plot_trend_chart(all_books, 'top_books_trend.png')
    
    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
