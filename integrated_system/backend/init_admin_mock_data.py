import pymysql
import datetime
import random

AUTH_DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'ip_lumina_auth',
    'charset': 'utf8mb4'
}

def init_db():
    conn = pymysql.connect(**AUTH_DB_CONFIG)
    cursor = conn.cursor()
    
    # 1. 确保 users 表有 last_active_at 和 ai_tokens_used
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    except Exception as e:
        print(f"Column last_active_at likely exists: {e}")
        
    try:
        # 新增记录大模型 token 消耗的字段
        cursor.execute("ALTER TABLE users ADD COLUMN ai_tokens_used INT DEFAULT 0")
    except Exception as e:
        print(f"Column ai_tokens_used likely exists: {e}")

    # 2. 创建或更新 hourly_metrics 时序表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hourly_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        record_time DATETIME NOT NULL UNIQUE,
        pv_count INT DEFAULT 0,
        uv_count INT DEFAULT 0,
        api_calls INT DEFAULT 0,
        ai_tokens_consumed INT DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    
    # 确保 hourly_metrics 有设备来源列
    for col in ['mobile_pv', 'desktop_pv', 'api_pv']:
        try:
            cursor.execute(f"ALTER TABLE hourly_metrics ADD COLUMN {col} INT DEFAULT 0")
        except:
            pass
    
    # 2.5 创建 UV 去重追踪表 — 用于按小时+IP去重统计真实独立访客
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uv_tracking (
        id INT AUTO_INCREMENT PRIMARY KEY,
        record_time DATETIME NOT NULL,
        client_ip VARCHAR(45) NOT NULL,
        user_id INT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_hour_ip (record_time, client_ip)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    
    # 3. 生成 10 个测试用户（包含在线人员）
    now = datetime.datetime.now()
    for i in range(1, 11):
        username = f"test_user_{i}"
        # 让一半的用户在线（last_active_at < 5分钟内），一半不在线
        is_online = i % 2 == 0
        active_time = now - datetime.timedelta(minutes=random.randint(1, 10)) if is_online else now - datetime.timedelta(hours=random.randint(1, 24))
        tokens = random.randint(1000, 50000)
        
        try:
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role, last_active_at, ai_tokens_used)
                VALUES (%s, %s, 'hash', 'user', %s, %s)
                ON DUPLICATE KEY UPDATE 
                    last_active_at = VALUES(last_active_at),
                    ai_tokens_used = VALUES(ai_tokens_used)
            """, (username, f"{username}@test.com", active_time, tokens))
        except Exception as e:
            print(f"Update user error: {e}")
            pass

    # 4. 生成过去 7 天的趋势 Mock 数据，将模型消耗与 API 调用深度挂钩 (支持 30天/7天/24小时 切换)
    # 取 30天 = 720 个小时
    for i in range(720):
        h_time = now.replace(minute=0, second=0, microsecond=0) - datetime.timedelta(hours=i)
        pv = random.randint(50, 500)
        uv = int(pv * random.uniform(0.3, 0.6))
        
        # 建立大模型消耗量逻辑，如果有很多用户那 tokens 就会暴涨
        # 基础调用 + 随 PV 的 AI 算力开销波动
        api_calls = pv * random.randint(2, 5)
        ai_tokens = api_calls * random.randint(500, 2000)  # 例如生成 SWOT 则耗费大量 Token
        
        # 将 PV 分配给设备 (模拟: 移动端 60%, 桌面 30%, API 10%)
        mobile_pv = int(pv * random.uniform(0.5, 0.7))
        desktop_pv = int(pv * random.uniform(0.2, 0.4))
        api_pv = pv - mobile_pv - desktop_pv
        
        try:
            cursor.execute("""
                INSERT INTO hourly_metrics (record_time, pv_count, uv_count, api_calls, ai_tokens_consumed, mobile_pv, desktop_pv, api_pv)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    pv_count = VALUES(pv_count),
                    uv_count = VALUES(uv_count),
                    api_calls = VALUES(api_calls),
                    ai_tokens_consumed = VALUES(ai_tokens_consumed),
                    mobile_pv = VALUES(mobile_pv),
                    desktop_pv = VALUES(desktop_pv),
                    api_pv = VALUES(api_pv)
            """, (h_time, pv, uv, api_calls, ai_tokens, mobile_pv, desktop_pv, api_pv))
        except Exception as e:
            print(f"Insert metrics error: {e}")
            pass

    conn.commit()
    conn.close()
    print("Test data and DB schema successfully applied!")

if __name__ == "__main__":
    init_db()
