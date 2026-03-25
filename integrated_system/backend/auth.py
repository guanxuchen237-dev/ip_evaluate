"""
认证与授权模块
提供用户注册、登录、JWT 验证和角色权限管理
"""

from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta, timezone
import pymysql
import jwt

# ============================================================
#  配置
# ============================================================

SECRET_KEY = 'ip-lumina-secret-key-2026'
JWT_EXPIRATION_HOURS = 24

# 独立的用户认证数据库（与爬虫数据库分离）
AUTH_DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'ip_lumina_auth',
    'charset': 'utf8mb4'
}

auth_bp = Blueprint('auth', __name__)


# ============================================================
#  数据库工具
# ============================================================

def get_auth_db():
    """获取认证数据库连接"""
    return pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


def init_auth_database():
    """
    初始化认证数据库和用户表。
    如果数据库或表不存在则自动创建。
    """
    # 先连接 MySQL 服务器（不指定数据库），确保数据库存在
    conn_config = {k: v for k, v in AUTH_DB_CONFIG.items() if k != 'database'}
    try:
        conn = pymysql.connect(**conn_config, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{AUTH_DB_CONFIG['database']}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        conn.close()
        print(f"[AUTH] 数据库 '{AUTH_DB_CONFIG['database']}' 已就绪")
    except Exception as e:
        print(f"[AUTH] 创建数据库失败: {e}")
        return

    # 再连接目标数据库，创建用户表
    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('user', 'admin') NOT NULL DEFAULT 'user',
                    avatar VARCHAR(255) DEFAULT NULL,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_predictions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    title VARCHAR(255) NOT NULL,
                    category VARCHAR(50) DEFAULT NULL,
                    score FLOAT DEFAULT 0,
                    predicted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    details JSON DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    book_title VARCHAR(255) NOT NULL,
                    book_author VARCHAR(100) DEFAULT NULL,
                    platform VARCHAR(50) DEFAULT NULL,
                    risk_level ENUM('High', 'Medium', 'Low', 'Positive') NOT NULL,
                    risk_type ENUM('COMPLIANCE', 'PLOT_TOXIC', 'UPDATE_ENTROPY', 'POTENTIAL_GEM', 'GLOBAL_GEM', 'NORMAL', 'DEEP_AUDIT') NOT NULL,
                    content_snippet TEXT,
                    score FLOAT DEFAULT NULL,
                    trigger_source VARCHAR(50) DEFAULT 'virtual_reader',
                    status ENUM('PENDING', 'REVIEWED', 'RESOLVED', 'Ignored') DEFAULT 'PENDING',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # 修改现有表的risk_type ENUM值（如果表已存在）
            try:
                cursor.execute("""
                    ALTER TABLE ip_audit_logs 
                    MODIFY COLUMN risk_type ENUM('COMPLIANCE', 'PLOT_TOXIC', 'UPDATE_ENTROPY', 'POTENTIAL_GEM', 'GLOBAL_GEM', 'NORMAL', 'DEEP_AUDIT') NOT NULL
                """)
            except Exception as e:
                pass  # 表不存在或已是最新结构，忽略错误
            
            # 修改现有表的status ENUM值，添加'Ignored'（如果表已存在）
            try:
                cursor.execute("""
                    ALTER TABLE ip_audit_logs 
                    MODIFY COLUMN status ENUM('PENDING', 'REVIEWED', 'RESOLVED', 'Ignored') DEFAULT 'PENDING'
                """)
            except Exception as e:
                pass  # 表不存在或已是最新结构，忽略错误
            
            # 添加 markdown_report 字段（存储AI审计报告）
            try:
                cursor.execute("""
                    ALTER TABLE ip_audit_logs 
                    ADD COLUMN markdown_report MEDIUMTEXT DEFAULT NULL
                """)
            except Exception as e:
                pass  # 字段已存在，忽略错误
            
            # 添加 details 字段（存储审计详情JSON）
            try:
                cursor.execute("""
                    ALTER TABLE ip_audit_logs 
                    ADD COLUMN details JSON DEFAULT NULL
                """)
            except Exception as e:
                pass  # 字段已存在，忽略错误

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_chapters (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    chapter_num INT NOT NULL,
                    chapter_title VARCHAR(255) NOT NULL,
                    content MEDIUMTEXT NOT NULL,
                    source VARCHAR(50) DEFAULT 'scraped',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_title_chap (title, chapter_num)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        conn.commit()

        # 动态添加 token_limit 列（兼容已有表）
        with conn.cursor() as cursor:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN token_limit INT DEFAULT 0")
                conn.commit()
                print("[AUTH] 已添加 token_limit 列")
            except Exception:
                pass  # 列已存在

        # 创建默认管理员账户（如果不存在）
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                admin_hash = generate_password_hash('admin123')
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, %s)",
                    ('admin', 'admin@ip-lumina.com', admin_hash, 'admin')
                )
                conn.commit()
                print("[AUTH] 默认管理员账户已创建: admin / admin123")
            else:
                print("[AUTH] 管理员账户已存在，跳过创建")

        conn.close()
        print("[AUTH] 用户表初始化完成")
    except Exception as e:
        print(f"[AUTH] 初始化用户表失败: {e}")


# ============================================================
#  JWT 工具
# ============================================================

def generate_token(user_id: int, role: str) -> str:
    """生成 JWT token"""
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def decode_token(token: str) -> dict:
    """解析 JWT token"""
    return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])


# ============================================================
#  权限装饰器
# ============================================================

def login_required(f):
    """要求登录的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return jsonify({'error': '未提供认证令牌', 'code': 'NO_TOKEN'}), 401

        try:
            payload = decode_token(token)
            g.current_user_id = payload['user_id']
            g.current_user_role = payload['role']
            # 设置 g.user 供其他模块使用
            g.user = {
                'id': payload['user_id'],
                'role': payload['role']
            }
            # 尝试从数据库获取用户名并更新活跃时间
            try:
                conn = get_auth_db()
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT username FROM users WHERE id = %s",
                        (payload['user_id'],)
                    )
                    user = cursor.fetchone()
                    if user:
                        g.user['username'] = user['username']
                    # 更新用户活跃时间（用于在线状态判断）
                    cursor.execute(
                        "UPDATE users SET last_active_at = NOW() WHERE id = %s",
                        (payload['user_id'],)
                    )
                    conn.commit()
                conn.close()
            except Exception as e:
                print(f"[AUTH] 更新用户活跃时间失败: {e}")
        except jwt.ExpiredSignatureError:
            return jsonify({'error': '令牌已过期，请重新登录', 'code': 'TOKEN_EXPIRED'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': '无效的认证令牌', 'code': 'INVALID_TOKEN'}), 401

        return f(*args, **kwargs)
    return decorated


def token_limit_required(f):
    """检查Token限额的装饰器 - 当用户超出限额时禁用AI接口"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        try:
            conn = get_auth_db()
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT ai_tokens_used, IFNULL(token_limit, 0) as token_limit FROM users WHERE id = %s",
                    (g.current_user_id,)
                )
                user = cursor.fetchone()
                if user and user['token_limit'] > 0 and user['ai_tokens_used'] >= user['token_limit']:
                    conn.close()
                    return jsonify({
                        'error': f'Token额度已用完 (已用: {user["ai_tokens_used"]:,} / 限额: {user["token_limit"]:,})', 
                        'code': 'TOKEN_LIMIT_EXCEEDED',
                        'used': user['ai_tokens_used'],
                        'limit': user['token_limit']
                    }), 403
            conn.close()
        except Exception:
            pass  # 如果检查失败，允许继续访问
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """要求管理员权限的装饰器"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if g.current_user_role != 'admin':
            return jsonify({'error': '需要管理员权限', 'code': 'ADMIN_REQUIRED'}), 403
        return f(*args, **kwargs)
    return decorated


# ============================================================
#  认证 API
# ============================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据为空'}), 400

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    # 参数校验
    if not username or len(username) < 2:
        return jsonify({'error': '用户名至少需要2个字符'}), 400
    if not email or '@' not in email:
        return jsonify({'error': '请提供有效的邮箱地址'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': '密码至少需要6个字符'}), 400

    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 检查用户名是否已存在
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': '该用户名已被注册'}), 409

            # 检查邮箱是否已存在
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': '该邮箱已被注册'}), 409

            # 创建用户
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (%s, %s, %s, 'user')",
                (username, email, password_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid

        conn.close()

        # 生成 token
        token = generate_token(user_id, 'user')
        return jsonify({
            'message': '注册成功',
            'token': token,
            'user': {
                'id': user_id,
                'username': username,
                'email': email,
                'role': 'user',
                'avatar': None
            }
        }), 201

    except Exception as e:
        return jsonify({'error': f'注册失败: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据为空'}), 400

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': '请提供用户名和密码'}), 400

    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email, password_hash, role, avatar, is_active FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({'error': '用户名或密码错误'}), 401

        if not user['is_active']:
            return jsonify({'error': '该账户已被禁用，请联系管理员'}), 403

        if not check_password_hash(user['password_hash'], password):
            return jsonify({'error': '用户名或密码错误'}), 401

        # 生成 token
        token = generate_token(user['id'], user['role'])
        return jsonify({
            'message': '登录成功',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role'],
                'avatar': user['avatar']
            }
        })

    except Exception as e:
        return jsonify({'error': f'登录失败: {str(e)}'}), 500


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户信息"""
    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email, role, avatar, is_active, created_at FROM users WHERE id = %s",
                (g.current_user_id,)
            )
            user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({'error': '用户不存在'}), 404

        # 序列化 datetime
        user['created_at'] = user['created_at'].isoformat() if user['created_at'] else None

        return jsonify({'user': user})

    except Exception as e:
        return jsonify({'error': f'获取用户信息失败: {str(e)}'}), 500


# ============================================================
#  个人资料 API
# ============================================================

@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """修改个人资料（用户名、邮箱）"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据为空'}), 400

    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()

    if not username or len(username) < 2:
        return jsonify({'error': '用户名至少需要2个字符'}), 400
    if not email or '@' not in email:
        return jsonify({'error': '请提供有效的邮箱地址'}), 400

    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 检查用户名冲突（排除自己）
            cursor.execute(
                "SELECT id FROM users WHERE username = %s AND id != %s",
                (username, g.current_user_id)
            )
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': '该用户名已被占用'}), 409

            # 检查邮箱冲突（排除自己）
            cursor.execute(
                "SELECT id FROM users WHERE email = %s AND id != %s",
                (email, g.current_user_id)
            )
            if cursor.fetchone():
                conn.close()
                return jsonify({'error': '该邮箱已被占用'}), 409

            cursor.execute(
                "UPDATE users SET username = %s, email = %s WHERE id = %s",
                (username, email, g.current_user_id)
            )
            conn.commit()

            # 返回更新后的用户信息
            cursor.execute(
                "SELECT id, username, email, role, avatar, is_active, created_at FROM users WHERE id = %s",
                (g.current_user_id,)
            )
            user = cursor.fetchone()
        conn.close()

        if user and user.get('created_at'):
            user['created_at'] = user['created_at'].isoformat()

        return jsonify({'message': '资料更新成功', 'user': user})

    except Exception as e:
        return jsonify({'error': f'更新失败: {str(e)}'}), 500


@auth_bp.route('/password', methods=['PUT'])
@login_required
def change_password():
    """修改密码"""
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据为空'}), 400

    old_password = data.get('old_password') or ''
    new_password = data.get('new_password') or ''

    if not old_password:
        return jsonify({'error': '请输入当前密码'}), 400
    if not new_password or len(new_password) < 6:
        return jsonify({'error': '新密码至少需要6个字符'}), 400

    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM users WHERE id = %s",
                (g.current_user_id,)
            )
            user = cursor.fetchone()

            if not user or not check_password_hash(user['password_hash'], old_password):
                conn.close()
                return jsonify({'error': '当前密码不正确'}), 401

            new_hash = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, g.current_user_id)
            )
            conn.commit()
        conn.close()

        return jsonify({'message': '密码修改成功'})

    except Exception as e:
        return jsonify({'error': f'密码修改失败: {str(e)}'}), 500


@auth_bp.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    """上传头像"""
    import os
    import uuid

    if 'avatar' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400

    # 检查文件类型
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        return jsonify({'error': '仅支持 PNG/JPG/GIF/WEBP 格式'}), 400

    # 检查文件大小（限制 2MB）
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > 2 * 1024 * 1024:
        return jsonify({'error': '头像文件不能超过 2MB'}), 400

    try:
        # 保存文件
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{g.current_user_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # 更新数据库
        avatar_url = f"/uploads/avatars/{filename}"
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET avatar = %s WHERE id = %s",
                (avatar_url, g.current_user_id)
            )
            conn.commit()
        conn.close()

        return jsonify({'message': '头像上传成功', 'avatar': avatar_url})

    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


# ============================================================
#  管理员 API
# ============================================================

@auth_bp.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    """获取所有用户列表或新建用户（管理员）"""
    if request.method == 'POST':
        data = request.json or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        role = data.get('role', 'user')
        is_active = data.get('is_active', 1)

        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400

        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(password)

        try:
            conn = get_auth_db()
            with conn.cursor() as cursor:
                # 检查用户名或邮箱是否已存在
                cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email if email else None))
                if cursor.fetchone():
                    return jsonify({'error': '用户名或邮箱已存在'}), 400

                cursor.execute(
                    "INSERT INTO users (username, password_hash, email, role, is_active, last_active_at) VALUES (%s, %s, %s, %s, %s, NULL)",
                    (username, hashed_password, email, role, is_active)
                )
                conn.commit()
                new_id = cursor.lastrowid
            conn.close()
            return jsonify({'message': '用户创建成功', 'id': new_id}), 201
        except Exception as e:
            return jsonify({'error': f'创建用户失败: {str(e)}'}), 500

    # GET 请求逻辑

    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, username, email, role, avatar, is_active, created_at, last_active_at, ai_tokens_used, IFNULL(token_limit, 0) as token_limit FROM users ORDER BY created_at DESC"
            )
            users = cursor.fetchall()
        conn.close()

        # 获取定义的在线判定窗口
        import os, json
        from datetime import datetime, timedelta
        online_window = 15
        cfg_path = os.path.join(os.path.dirname(__file__), 'config', 'system_config.json')
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    online_window = json.load(f).get('online_window_minutes', 15)
            except:
                pass
        
        active_threshold = datetime.now() - timedelta(minutes=online_window)

        # 序列化 datetime
        for u in users:
            u['created_at'] = u['created_at'].isoformat() if u['created_at'] else None
            if u['last_active_at']:
                # 判断是否被算作在线
                u['is_online'] = u['last_active_at'] >= active_threshold
                u['last_active_at'] = u['last_active_at'].strftime('%Y-%m-%d %H:%M')
            else:
                u['is_online'] = False
                u['last_active_at'] = None

        return jsonify({'users': users, 'total': len(users)})

    except Exception as e:
        return jsonify({'error': f'获取用户列表失败: {str(e)}'}), 500


@auth_bp.route('/admin/users/<int:user_id>/toggle', methods=['PUT'])
@admin_required
def toggle_user_status(user_id):
    """启用/禁用用户（管理员）"""
    # 不允许禁用自己
    if user_id == g.current_user_id:
        return jsonify({'error': '不能禁用自己的账户'}), 400

    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, is_active FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()

            if not user:
                conn.close()
                return jsonify({'error': '用户不存在'}), 404

            new_status = 0 if user['is_active'] else 1
            cursor.execute("UPDATE users SET is_active = %s WHERE id = %s", (new_status, user_id))
            conn.commit()
        conn.close()

        status_text = '启用' if new_status else '禁用'
        return jsonify({'message': f'用户已{status_text}', 'is_active': new_status})

    except Exception as e:
        return jsonify({'error': f'操作失败: {str(e)}'}), 500

@auth_bp.route('/admin/users/<int:user_id>', methods=['PUT', 'DELETE'])
@admin_required
def manage_single_user(user_id):
    """管理员编辑或删除用户"""
    if request.method == 'DELETE':
        if user_id == g.current_user_id:
            return jsonify({'error': '不能删除自己的账户'}), 400
            
        try:
            conn = get_auth_db()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
            conn.close()
            return jsonify({'message': '用户已删除'})
        except Exception as e:
            return jsonify({'error': f'删除用户失败: {str(e)}'}), 500

    # PUT 请求逻辑
    data = request.json or {}
    username = data.get('username')
    email = data.get('email')
    role = data.get('role')
    is_active = data.get('is_active')
    token_limit = data.get('token_limit', 0)
    password = data.get('password')  # 新增：获取密码字段

    if not username:
        return jsonify({'error': '用户名不能为空'}), 400

    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': '用户不存在'}), 404
            
            if user_id == g.current_user_id and role != 'admin' and user['role'] == 'admin':
                return jsonify({'error': '不能取消自己的管理员权限'}), 400

            cursor.execute("SELECT id FROM users WHERE (username = %s OR email = %s) AND id != %s", (username, email, user_id))
            if cursor.fetchone():
                return jsonify({'error': '用户名或邮箱已被其他人使用'}), 400

            # 如果有密码，则更新密码
            if password and len(password) >= 6:
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(password)
                cursor.execute(
                    "UPDATE users SET username = %s, email = %s, role = %s, is_active = %s, token_limit = %s, password_hash = %s WHERE id = %s",
                    (username, email, role, is_active, int(token_limit or 0), password_hash, user_id)
                )
            else:
                cursor.execute(
                    "UPDATE users SET username = %s, email = %s, role = %s, is_active = %s, token_limit = %s WHERE id = %s",
                    (username, email, role, is_active, int(token_limit or 0), user_id)
                )
            conn.commit()
        conn.close()
        return jsonify({'message': '用户信息更新成功'})
    except Exception as e:
        return jsonify({'error': f'更新用户失败: {str(e)}'}), 500


@auth_bp.route('/admin/users/<int:user_id>/reset_tokens', methods=['POST'])
@admin_required
def reset_user_tokens(user_id):
    """重置指定用户的 Token 用量"""
    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET ai_tokens_used = 0 WHERE id = %s", (user_id,))
            conn.commit()
            updated = cursor.rowcount > 0
        conn.close()
        if updated:
            return jsonify({'message': 'Token 用量已重置'})
        return jsonify({'error': '用户不存在'}), 404
    except Exception as e:
        return jsonify({'error': f'重置失败: {str(e)}'}), 500


# ============================================================
#  忘记密码功能
# ============================================================

import secrets
import string

# 内存中存储重置token（生产环境应使用Redis或数据库）
reset_tokens = {}

@auth_bp.route('/forgot_password', methods=['POST'])
def forgot_password():
    """
    忘记密码 - 发送重置验证码
    由于是本地项目，返回验证码让用户输入
    """
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'error': '请输入邮箱地址'}), 400
    
    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, email FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
        conn.close()
        
        if not user:
            # 安全考虑：不透露邮箱是否存在
            return jsonify({
                'success': True,
                'message': '如果该邮箱已注册，您将收到重置验证码'
            })
        
        # 生成6位数字验证码
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # 存储验证码（5分钟有效）
        reset_tokens[email] = {
            'code': code,
            'user_id': user['id'],
            'expires': datetime.now(timezone.utc) + timedelta(minutes=5)
        }
        
        print(f"[AUTH] 忘记密码验证码: {email} -> {code}")
        
        # 返回验证码（本地开发环境，实际应发送邮件）
        return jsonify({
            'success': True,
            'message': '验证码已生成',
            'code': code,  # 仅开发环境返回
            'username': user['username']
        })
        
    except Exception as e:
        print(f"[AUTH] 忘记密码错误: {e}")
        return jsonify({'error': '操作失败，请稍后重试'}), 500


@auth_bp.route('/reset_password', methods=['POST'])
def reset_password():
    """
    重置密码 - 验证验证码并设置新密码
    """
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '')
    
    if not email or not code or not new_password:
        return jsonify({'error': '请填写所有字段'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': '密码至少需要6个字符'}), 400
    
    # 验证验证码
    token_data = reset_tokens.get(email)
    if not token_data:
        return jsonify({'error': '验证码无效或已过期'}), 400
    
    if token_data['code'] != code:
        return jsonify({'error': '验证码错误'}), 400
    
    if datetime.now(timezone.utc) > token_data['expires']:
        del reset_tokens[email]
        return jsonify({'error': '验证码已过期，请重新获取'}), 400
    
    try:
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 更新密码
            new_hash = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (new_hash, token_data['user_id'])
            )
            conn.commit()
        conn.close()
        
        # 清除验证码
        del reset_tokens[email]
        
        print(f"[AUTH] 密码重置成功: {email}")
        return jsonify({
            'success': True,
            'message': '密码重置成功，请使用新密码登录'
        })
        
    except Exception as e:
        print(f"[AUTH] 重置密码错误: {e}")
        return jsonify({'error': '重置失败，请稍后重试'}), 500
