from flask import Flask, send_from_directory
from flask_cors import CORS
from api import api_bp
from auth import auth_bp, init_auth_database, SECRET_KEY
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

# 允许跨域请求（Vite 开发服务器）
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/uploads/*": {"origins": "*"}})

# 注册蓝图
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')

from flask import request
import traceback
import jwt
from datetime import datetime

# 全局流量与在线状态中间件
@app.before_request
def track_metrics():
    # 忽略 OPTIONS 预检请求和静态文件
    if request.method == 'OPTIONS' or request.path.startswith('/uploads/'):
        return

    try:
        import pymysql
        from auth import AUTH_DB_CONFIG
        
        # 记录当前小时的 Metrics
        now = datetime.now()
        hour_time = now.replace(minute=0, second=0, microsecond=0)
        
        is_api = request.path.startswith('/api/')
        client_ip = request.remote_addr

        conn = pymysql.connect(**AUTH_DB_CONFIG)
        with conn.cursor() as cursor:
            # 尝试插入当前小时记录，若已存在则更新
            user_agent = request.headers.get('User-Agent', '').lower()
            if 'mobi' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
                device_col = 'mobile_pv'
            elif 'postman' in user_agent or 'curl' in user_agent or 'python' in user_agent or 'insomnia' in user_agent:
                device_col = 'api_pv'
            else:
                device_col = 'desktop_pv'
            
            # 真实 UV 去重：尝试向 uv_tracking 表插入 (小时, IP)
            # 如果是本小时内首次出现的 IP，则 INSERT 成功 → is_new_uv = True
            # 如果该 IP 本小时已记录过，则触发 DUPLICATE KEY → is_new_uv = False
            is_new_uv = False
            try:
                cursor.execute("""
                    INSERT INTO uv_tracking (record_time, client_ip)
                    VALUES (%s, %s)
                """, (hour_time, client_ip))
                is_new_uv = True  # 插入成功，这是新独立访客
            except pymysql.err.IntegrityError:
                is_new_uv = False  # 已存在，重复访客
            
            uv_inc = 1 if is_new_uv else 0
            
            sql_insert = f"""
            INSERT INTO hourly_metrics (record_time, pv_count, uv_count, api_calls, ai_tokens_consumed, {device_col})
            VALUES (%s, 1, %s, %s, 0, 1)
            ON DUPLICATE KEY UPDATE 
                pv_count = pv_count + 1,
                uv_count = uv_count + %s,
                api_calls = api_calls + %s,
                {device_col} = {device_col} + 1
            """
            api_inc = 1 if is_api else 0
            cursor.execute(sql_insert, (hour_time, uv_inc, api_inc, uv_inc, api_inc))
            
            # 更新在线时间如果包含 Token
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                from auth import SECRET_KEY, get_auth_db
                try:
                    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
                    user_id = payload.get('user_id')
                    if user_id:
                        auth_conn = get_auth_db()
                        with auth_conn.cursor() as auth_cursor:
                            # 检查 Token 限额
                            auth_cursor.execute("SELECT ai_tokens_used, IFNULL(token_limit, 0) as token_limit FROM users WHERE id = %s", (user_id,))
                            user_row = auth_cursor.fetchone()
                            if user_row:
                                limit = int(user_row.get('token_limit', 0) or 0)
                                used = int(user_row.get('ai_tokens_used', 0) or 0)
                                # token_limit = 0 表示无限制；否则检查是否超限
                                if limit == 0 or used < limit:
                                    auth_cursor.execute("UPDATE users SET last_active_at = %s, ai_tokens_used = ai_tokens_used + %s WHERE id = %s", (now, api_inc * 12, user_id))
                                else:
                                    # 超限只更新活跃时间，不再累加 Token
                                    auth_cursor.execute("UPDATE users SET last_active_at = %s WHERE id = %s", (now, user_id))
                        auth_conn.commit()
                        auth_conn.close()
                except Exception as e:
                    pass # 不阻断正常请求
            
            conn.commit()
        conn.close()
    except Exception as e:
        print("[Metrics Error]", e)
        traceback.print_exc()


# 初始化认证数据库
init_auth_database()

# 静态文件：头像上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route('/')
def index():
    return "Novel Visualization API is running. Access endpoints at /api/*"

from scheduler import scheduler_instance
scheduler_instance.start()

if __name__ == '__main__':
    print("[INFO] Starting Flask Server with Auto-Scheduler...")
    print(app.url_map) # DEBUG: Print all routes
    app.run(host='0.0.0.0', port=5000, debug=False)
