"""
角色缓存模块 - 缓存从书籍中提取的角色信息
"""
import os
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any

CACHE_DIR = os.path.join(os.path.dirname(__file__), 'characters')

def _ensure_cache_dir():
    """确保缓存目录存在"""
    os.makedirs(CACHE_DIR, exist_ok=True)

def _get_cache_key(title: str, author: str, platform: str = '') -> str:
    """生成缓存文件名"""
    raw_key = f"{platform}|{title}|{author}"
    hash_key = hashlib.md5(raw_key.encode('utf-8')).hexdigest()[:16]
    return hash_key

def _get_cache_path(cache_key: str) -> str:
    """获取缓存文件路径"""
    return os.path.join(CACHE_DIR, f"{cache_key}.json")

def get_cached_characters(title: str, author: str, platform: str = '') -> Optional[List[Dict[str, Any]]]:
    """
    获取缓存的角色列表
    
    Returns:
        角色列表，如果没有缓存则返回 None
    """
    _ensure_cache_dir()
    cache_key = _get_cache_key(title, author, platform)
    cache_path = _get_cache_path(cache_key)
    
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('characters')
    except Exception as e:
        print(f"[WARN] Failed to read character cache: {e}")
        return None

def save_characters_cache(title: str, author: str, platform: str, characters: List[Dict[str, Any]]) -> bool:
    """
    保存角色到缓存
    
    Args:
        title: 书籍标题
        author: 作者
        platform: 平台（zongheng/qidian）
        characters: 角色列表
    
    Returns:
        是否保存成功
    """
    _ensure_cache_dir()
    cache_key = _get_cache_key(title, author, platform)
    cache_path = _get_cache_path(cache_key)
    
    data = {
        "book_key": f"{platform}|{title}|{author}",
        "title": title,
        "author": author,
        "platform": platform,
        "characters": characters,
        "extracted_at": datetime.now().isoformat()
    }
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] Characters cached for '{title}'")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save character cache: {e}")
        return False

def clear_character_cache(title: str, author: str, platform: str = '') -> bool:
    """清除指定书籍的角色缓存"""
    cache_key = _get_cache_key(title, author, platform)
    cache_path = _get_cache_path(cache_key)
    
    if os.path.exists(cache_path):
        try:
            os.remove(cache_path)
            return True
        except:
            return False
    return True
