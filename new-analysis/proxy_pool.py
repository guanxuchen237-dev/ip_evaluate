# -*- coding: utf-8 -*-
"""
IP代理池管理模块
支持从天启代理API获取IP并进行轮换
"""
import requests
import time
import random
from typing import List, Dict, Optional
from retrying import retry
import json

class ProxyPool:
    """IP代理池管理类"""
    
    def __init__(self, api_url: str = None):
        """
        初始化代理池
        
        Args:
            api_url: 天启代理API地址
        """
        self.api_url = api_url or (
            "http://api.tianqiip.com/getip"
            "?secret=2rl0bxsd5sftel1k"
            "&num=10"
            "&type=json"
            "&port=1"
            "&time=3"
            "&mr=1"
            "&sign=cc1cf97695ca37a8da0a5779fef4b954"
        )
        
        self.proxy_list: List[Dict] = []
        self.current_index = 0
        self.failed_proxies = set()
        self.last_fetch_time = 0
        self.fetch_interval = 180  # 3分钟重新获取一次
        
    def fetch_proxies(self, num: int = 10) -> bool:
        """
        从API获取代理IP
        
        Args:
            num: 获取数量
            
        Returns:
            是否成功获取
        """
        try:
            # 构建请求URL
            url = self.api_url.replace('num=10', f'num={num}')
            
            print(f"正在获取{num}个代理IP...")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 1000:
                    proxy_data = data.get('data', [])
                    
                    # 清空旧的代理列表
                    self.proxy_list.clear()
                    self.failed_proxies.clear()
                    
                    # 添加新代理
                    for item in proxy_data:
                        proxy = {
                            'ip': item['ip'],
                            'port': item['port'],
                            'expire': item.get('expire', ''),
                            'city': item.get('city', ''),
                            'isp': item.get('isp', ''),
                            'proxy_url': f"http://{item['ip']}:{item['port']}"
                        }
                        self.proxy_list.append(proxy)
                    
                    self.current_index = 0
                    self.last_fetch_time = time.time()
                    
                    print(f"✅ 成功获取{len(self.proxy_list)}个代理IP")
                    return True
                else:
                    print(f"❌ API返回错误: {data.get('msg', 'Unknown error')}")
                    return False
            else:
                print(f"❌ 请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 获取代理IP异常: {e}")
            return False
    
    def get_proxy(self) -> Optional[Dict]:
        """
        获取一个可用的代理
        
        Returns:
            代理字典，包含http和https配置
        """
        # 检查是否需要重新获取代理
        if not self.proxy_list or (time.time() - self.last_fetch_time > self.fetch_interval):
            self.fetch_proxies()
        
        if not self.proxy_list:
            return None
        
        # 轮换获取代理
        max_attempts = len(self.proxy_list)
        for _ in range(max_attempts):
            proxy_info = self.proxy_list[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxy_list)
            
            # 跳过失败的代理
            proxy_key = f"{proxy_info['ip']}:{proxy_info['port']}"
            if proxy_key in self.failed_proxies:
                continue
            
            return {
                'http': proxy_info['proxy_url'],
                'https': proxy_info['proxy_url'],
                '_info': proxy_info
            }
        
        # 如果所有代理都失败了，重新获取
        print("所有代理都已失效，重新获取...")
        self.fetch_proxies()
        
        if self.proxy_list:
            proxy_info = self.proxy_list[0]
            return {
                'http': proxy_info['proxy_url'],
                'https': proxy_info['proxy_url'],
                '_info': proxy_info
            }
        
        return None
    
    def mark_failed(self, proxy: Dict):
        """
        标记代理为失败
        
        Args:
            proxy: 代理字典
        """
        if proxy and '_info' in proxy:
            info = proxy['_info']
            proxy_key = f"{info['ip']}:{info['port']}"
            self.failed_proxies.add(proxy_key)
            print(f"⚠️ 标记代理失败: {proxy_key}")
    
    def get_random_proxy(self) -> Optional[Dict]:
        """随机获取一个代理"""
        if not self.proxy_list:
            self.fetch_proxies()
        
        if not self.proxy_list:
            return None
        
        # 过滤掉失败的代理
        available = [p for p in self.proxy_list 
                    if f"{p['ip']}:{p['port']}" not in self.failed_proxies]
        
        if not available:
            # 重置失败列表
            self.failed_proxies.clear()
            available = self.proxy_list
        
        proxy_info = random.choice(available)
        return {
            'http': proxy_info['proxy_url'],
            'https': proxy_info['proxy_url'],
            '_info': proxy_info
        }
    
    @retry(stop_max_attempt_number=3, wait_fixed=1000)
    def test_proxy(self, proxy: Dict, test_url: str = "http://myip.ipip.net/") -> bool:
        """
        测试代理是否可用
        
        Args:
            proxy: 代理字典
            test_url: 测试URL
            
        Returns:
            是否可用
        """
        try:
            response = requests.get(
                test_url,
                proxies=proxy,
                timeout=5,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            if response.status_code == 200:
                print(f"✅ 代理可用: {proxy['_info']['ip']}:{proxy['_info']['port']}")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ 代理测试失败: {e}")
            return False


# 全局代理池实例
_proxy_pool = None

def get_proxy_pool() -> ProxyPool:
    """获取全局代理池实例"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool()
    return _proxy_pool


if __name__ == '__main__':
    # 测试代理池
    pool = ProxyPool()
    
    # 获取代理
    if pool.fetch_proxies(num=5):
        print(f"\n当前代理池大小: {len(pool.proxy_list)}")
        
        # 测试几个代理
        for i in range(3):
            proxy = pool.get_proxy()
            if proxy:
                print(f"\n测试代理 {i+1}:")
                print(f"  IP: {proxy['_info']['ip']}")
                print(f"  端口: {proxy['_info']['port']}")
                print(f"  城市: {proxy['_info']['city']}")
                
                # 尝试使用代理
                if pool.test_proxy(proxy):
                    print("  状态: ✅ 可用")
                else:
                    print("  状态: ❌ 不可用")
                    pool.mark_failed(proxy)
