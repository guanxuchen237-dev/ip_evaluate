import pymysql
from datetime import datetime
import statistics

# 连接数据库查询捞尸人的历史数据
conn = pymysql.connect(host='localhost', user='root', password='root', database='qidian_data', cursorclass=pymysql.cursors.DictCursor)

with conn.cursor() as cur:
    cur.execute("""
        SELECT year, month, monthly_tickets_on_list 
        FROM novel_monthly_stats 
        WHERE title = '捞尸人' 
        ORDER BY year, month
    """)
    all_data = cur.fetchall()
    
    print("=== 捞尸人完整历史数据 ===")
    for row in all_data:
        print(f"{row['year']}/{row['month']} - 月票: {row['monthly_tickets_on_list']:,}")

conn.close()

print("\n" + "="*60)
print("优化预测算法验证")
print("="*60)

# 过滤掉12月数据（不完整）
filtered_data = [d for d in all_data if d['month'] != 12]

def predict_next_months_optimized(data, start_idx, months=3):
    """优化预测算法"""
    if start_idx < 3:
        return None, 0, {}
    
    train_data = data[:start_idx]
    tickets = [d['monthly_tickets_on_list'] for d in train_data]
    
    # 1. 计算多月平均增长率（最近3-6个月）
    growth_rates = []
    for i in range(1, min(6, len(tickets))):
        if tickets[-(i+1)] > 0:
            rate = (tickets[-i] - tickets[-(i+1)]) / tickets[-(i+1)]
            growth_rates.append(rate)
    
    # 加权平均：近期权重更高
    if growth_rates:
        weights = [0.4, 0.3, 0.2, 0.1, 0.0, 0.0][:len(growth_rates)]
        avg_growth = sum(g * w for g, w in zip(growth_rates, weights)) / sum(weights[:len(growth_rates)])
    else:
        avg_growth = 0
    
    # 2. 计算趋势稳定性（标准差）
    if len(tickets) >= 3:
        stability = 1 - min(1, statistics.stdev(tickets[-6:]) / statistics.mean(tickets[-6:])) if statistics.mean(tickets[-6:]) > 0 else 0
    else:
        stability = 0.5
    
    # 3. 判断趋势方向
    recent_avg = statistics.mean(tickets[-3:]) if len(tickets) >= 3 else tickets[-1]
    earlier_avg = statistics.mean(tickets[-6:-3]) if len(tickets) >= 6 else tickets[0]
    
    if recent_avg > earlier_avg * 1.2:
        trend = "上升"
        trend_factor = 1.1
    elif recent_avg < earlier_avg * 0.8:
        trend = "下降"
        trend_factor = 0.9
    else:
        trend = "平稳"
        trend_factor = 1.0
    
    # 4. 基准值使用最近3个月平均（更稳定）
    base_value = statistics.mean(tickets[-3:]) if len(tickets) >= 3 else tickets[-1]
    
    # 5. 预测
    predictions = []
    for i in range(1, months + 1):
        # 衰减因子 + 趋势调整
        decay = 0.90 ** i  # 更平缓的衰减
        stability_factor = 0.5 + 0.5 * stability  # 稳定性越高，预测越自信
        
        pred = int(base_value * (1 + avg_growth * decay * trend_factor * stability_factor))
        predictions.append(max(pred, int(base_value * 0.5)))  # 不低于基准的50%
    
    info = {
        'avg_growth': avg_growth,
        'stability': stability,
        'trend': trend,
        'base_value': base_value,
        'growth_rates': growth_rates
    }
    
    return predictions, avg_growth, info

# 回测验证
print("\n【优化回测1】基于2025年8月前数据预测")
idx1 = 8
pred1, growth1, info1 = predict_next_months_optimized(filtered_data, idx1, 3)
print(f"基准值(3月平均): {info1['base_value']:,.0f}票")
print(f"平均增长率: {growth1*100:.1f}%")
print(f"趋势: {info1['trend']}, 稳定性: {info1['stability']:.2f}")
print(f"增长率序列: {[f'{r*100:.1f}%' for r in info1['growth_rates'][:3]]}")

months_to_check = [(2025, 9), (2025, 10), (2025, 11)]
errors1 = []
for i, (year, month) in enumerate(months_to_check):
    pred = pred1[i]
    actual = next((d['monthly_tickets_on_list'] for d in filtered_data if d['year'] == year and d['month'] == month), None)
    if actual:
        error = abs(pred - actual) / actual * 100
        errors1.append(error)
        status = "✓" if error < 30 else "✗"
        print(f"  {year}/{month}月: 预测 {pred:,} vs 实际 {actual:,} - 误差 {error:.1f}% {status}")

print(f"  平均误差: {statistics.mean(errors1):.1f}%")

print("\n【优化回测2】基于2025年6月前数据预测")
idx2 = 6
pred2, growth2, info2 = predict_next_months_optimized(filtered_data, idx2, 3)
print(f"基准值(3月平均): {info2['base_value']:,.0f}票")
print(f"平均增长率: {growth2*100:.1f}%")
print(f"趋势: {info2['trend']}, 稳定性: {info2['stability']:.2f}")

months_to_check2 = [(2025, 7), (2025, 8), (2025, 9)]
errors2 = []
for i, (year, month) in enumerate(months_to_check2):
    pred = pred2[i]
    actual = next((d['monthly_tickets_on_list'] for d in filtered_data if d['year'] == year and d['month'] == month), None)
    if actual:
        error = abs(pred - actual) / actual * 100
        errors2.append(error)
        status = "✓" if error < 30 else "✗"
        print(f"  {year}/{month}月: 预测 {pred:,} vs 实际 {actual:,} - 误差 {error:.1f}% {status}")

print(f"  平均误差: {statistics.mean(errors2):.1f}%")

print("\n【优化回测3】基于2025年4月前数据预测")
idx3 = 4
pred3, growth3, info3 = predict_next_months_optimized(filtered_data, idx3, 3)
print(f"基准值(3月平均): {info3['base_value']:,.0f}票")
print(f"平均增长率: {growth3*100:.1f}%")
print(f"趋势: {info3['trend']}, 稳定性: {info3['stability']:.2f}")

months_to_check3 = [(2025, 5), (2025, 6), (2025, 7)]
errors3 = []
for i, (year, month) in enumerate(months_to_check3):
    pred = pred3[i]
    actual = next((d['monthly_tickets_on_list'] for d in filtered_data if d['year'] == year and d['month'] == month), None)
    if actual:
        error = abs(pred - actual) / actual * 100
        errors3.append(error)
        status = "✓" if error < 30 else "✗"
        print(f"  {year}/{month}月: 预测 {pred:,} vs 实际 {actual:,} - 误差 {error:.1f}% {status}")

print(f"  平均误差: {statistics.mean(errors3):.1f}%")

# 当前预测
print("\n" + "="*60)
print("当前预测：基于2025年11月数据预测2026年1-3月")
print("="*60)
last_idx = len(filtered_data)
pred_now, growth_now, info_now = predict_next_months_optimized(filtered_data, last_idx, 3)
print(f"基准值(3月平均): {info_now['base_value']:,.0f}票")
print(f"平均增长率: {growth_now*100:.1f}%")
print(f"趋势: {info_now['trend']}, 稳定性: {info_now['stability']:.2f}")
print(f"\n预测结果:")
print(f"  2026/1月: {pred_now[0]:,}票")
print(f"  2026/2月: {pred_now[1]:,}票")
print(f"  2026/3月: {pred_now[2]:,}票")
