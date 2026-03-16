from pymongo import MongoClient
import json

client = MongoClient('mongodb://localhost:27017/')
collection = client['novel_analysis']['novels']

print("\n" + "="*70)
print("完整数据展示（优化版）")
print("="*70)

for doc in collection.find().limit(5):
    print(f"\n📚 [{doc.get('rank', 'N/A')}] 【{doc.get('title')}】")
    print(f"👤 作者: {doc.get('author_name')}")
    print(f"🏷️  分类: {doc.get('category_name')}")
    print(f"📝 状态: {doc.get('status')} | 签约: {doc.get('contract_status', '未知')}")
    print(f"📖 字数: {doc.get('total_words', 0):,}")
    
    print(f"\n📊 市场数据:")
    print(f"  🎫 月票: {doc.get('monthly_ticket_count', 0):,}")
    print(f"  👍 总推荐: {doc.get('total_recommendation_count', 0):,}")
    print(f"  📅 周推荐: {doc.get('week_recommendation_count', 0):,}")
    print(f"  👁️  点击: {doc.get('click_count', 0):,}")
    print(f"  💰 捧场/打赏: {doc.get('reward_count', 0):,} 人")
    print(f"  👥 书粉: {doc.get('fans_count', 0):,}")
    
    # 榜单排名信息（优化显示）
    rankings = doc.get('ranking_lists', [])
    if rankings:
        print(f"\n🏆 榜单排名:")
        for rank in rankings:
            rank_name = rank.get('rank_name', '未知榜')
            position = rank.get('position', 'N/A')
            number = rank.get('rank_number', 0)
            print(f"  • {rank_name}: 第 {position} 名 ({number:,} 票)")
    
    print("=" * 70)

# 删除所有文档的collection_count字段
print("\n删除无用的collection_count字段...")
result = collection.update_many(
    {},
    {'$unset': {'collection_count': ""}}
)
print(f"✅ 已删除 {result.modified_count} 个文档的collection_count字段")

client.close()
