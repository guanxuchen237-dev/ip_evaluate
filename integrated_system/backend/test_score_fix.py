import sys
import os

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_manager import DataManager

if __name__ == '__main__':
    dm = DataManager()
    
    # Test cases mapping
    cases = [
        ("0票无推荐垫底旧书", {'title': 'Test1', 'category': '玄幻', 'word_count': 100000, 'interaction': 0, 'finance': 0, 'popularity': 0}),
        ("100票微互动小书", {'title': 'Test2', 'category': '玄幻', 'word_count': 500000, 'interaction': 5000, 'finance': 100, 'popularity': 2000}),
        ("1万票中等热度书", {'title': 'Test3', 'category': '玄幻', 'word_count': 2000000, 'interaction': 500000, 'finance': 10000, 'popularity': 100000}),
        ("15万票爆款头部书", {'title': 'Test4', 'category': '玄幻', 'word_count': 5000000, 'interaction': 3000000, 'finance': 150000, 'popularity': 800000})
    ]
    
    print("-" * 50)
    for name, data in cases:
        try:
            res = dm.predict_ip(data)
            score = res.get('score', 0)
            level = res.get('details', {}).get('predicted_level', '未知')
            print(f"[{name}]")
            print(f"  Inputs: 月票={data['finance']} | 互动={data['interaction']} | 字数={data['word_count']}")
            print(f"  Score:  {score} (Level: {level})")
            print("-" * 50)
        except Exception as e:
            print(f"[{name}] Errored: {e}")
