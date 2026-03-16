
import os
import sys
import pandas as pd
import numpy as np
import traceback

# 模拟 jieba 环境
class MockJieba:
    class MockAnalyse:
        def extract_tags(self, *args, **kwargs): return []
    analyse = MockAnalyse()
    def cut(self, text): return [text]

sys.modules['jieba'] = MockJieba()
sys.modules['jieba.analyse'] = MockJieba.MockAnalyse()

# 模拟 gensim
sys.modules['gensim'] = type('Mock', (), {'corpora': None, 'models': None})

# 添加后端路径
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'integrated_system', 'backend')))

from data_manager import DataManager

def test_reality_check():
    try:
        dm = DataManager()
        
        # 模拟《无敌天命》的真实高热度数据
        input_data = {
            'title': '无敌天命',
            'category': '玄幻奇幻',
            'word_count': 1200000,
            'finance': 43337,
            'interaction': 712030,
            'popularity': 712030 * 0.2
        }
        
        print("\n--- 正在进行真实模型预测 (无任何人工干预补丁) ---")
        res = dm.predict_ip(input_data)
        print(f"VAL_SCORE:{res['score']}")
        print(f"VAL_MSG:{res['details'].get('data_source')}")
        
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    test_reality_check()
