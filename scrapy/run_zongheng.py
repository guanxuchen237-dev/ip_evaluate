import sys
import os
from unittest.mock import patch

sys.path.append(r'd:\ip-lumina-main\scrapy')
import zongheng_spider_v4

# 强制禁用代理，直接使用本地网络直连避免劣质代理阻塞
zongheng_spider_v4.ProxyManager.get_valid_proxy = lambda self: None

# 抓取 2026年02月（当前月）数据用于前端展示
inputs = ['2026-02', '2026-02', '20', '1', '3']

with patch('builtins.input', side_effect=inputs):
    zongheng_spider_v4.main()
