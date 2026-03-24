"""
黑名单管理模块
提供加入黑名单、移出黑名单（白名单）、查询黑名单状态等功能
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import pymysql
from auth import AUTH_DB_CONFIG, admin_required

blacklist_bp = Blueprint('blacklist', __name__, url_prefix='/api')

# ============================================================
#  数据库表结构初始化
# ============================================================

def init_blacklist_table():
    """初始化黑名单数据表"""
    conn = pymysql.connect(**AUTH_DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ip_blacklist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    novel_id VARCHAR(255) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    author VARCHAR(255) DEFAULT '',
                    platform VARCHAR(50) DEFAULT '',
                    reason TEXT,
                    admin_id INT DEFAULT NULL,
                    admin_name VARCHAR(100) DEFAULT '',
                    status ENUM('active', 'removed') DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    removed_at DATETIME DEFAULT NULL,
                    removed_reason TEXT,
                    UNIQUE KEY uk_novel (novel_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            conn.commit()
    finally:
        conn.close()

# ============================================================
#  API 路由
# ============================================================

@blacklist_bp.route('/admin/blacklist', methods=['POST'])
def admin_add_blacklist():
    """管理端接口：加入下架管控黑名单"""
    data = request.json or {}
    novel_id = data.get('novel_id', '')
    title = data.get('title', '')
    reason = data.get('reason', 'Admin manual enforcement')
    author = data.get('author', '')
    platform = data.get('platform', '')
    
    if not novel_id or not title:
        return jsonify({'success': False, 'error': '缺少必要参数: novel_id 和 title'}), 400
    
    # 获取当前登录管理员信息
    admin_info = getattr(g, 'user', None) or {}
    admin_id = admin_info.get('id')
    admin_name = admin_info.get('username', 'Unknown')
    
    conn = pymysql.connect(**AUTH_DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 检查是否已在黑名单中
            cursor.execute(
                "SELECT id, status FROM ip_blacklist WHERE novel_id = %s",
                (novel_id,)
            )
            existing = cursor.fetchone()
            
            if existing:
                if existing[1] == 'active':
                    return jsonify({
                        'success': False,
                        'error': f'《{title}》已在黑名单中'
                    }), 409
                else:
                    # 之前被移除过，现在重新加入
                    cursor.execute("""
                        UPDATE ip_blacklist 
                        SET status = 'active', reason = %s, admin_id = %s, admin_name = %s,
                            author = %s, platform = %s, updated_at = NOW(), removed_at = NULL
                        WHERE novel_id = %s
                    """, (reason, admin_id, admin_name, author, platform, novel_id))
            else:
                # 新加入黑名单
                cursor.execute("""
                    INSERT INTO ip_blacklist (novel_id, title, author, platform, reason, admin_id, admin_name)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (novel_id, title, author, platform, reason, admin_id, admin_name))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'《{title}》已被成功加入管控黑名单',
                'novel_id': novel_id,
                'status': 'blacklisted'
            })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': f'数据库错误: {str(e)}'}), 500
    finally:
        conn.close()


@blacklist_bp.route('/admin/whitelist', methods=['POST'])
def admin_remove_blacklist():
    """管理端接口：将书籍移出黑名单（加入白名单）"""
    data = request.json or {}
    novel_id = data.get('novel_id', '')
    title = data.get('title', '')
    reason = data.get('reason', 'Admin manual removal')
    
    if not novel_id:
        return jsonify({'success': False, 'error': '缺少必要参数: novel_id'}), 400
    
    # 获取当前登录管理员信息
    admin_info = getattr(g, 'user', None) or {}
    admin_id = admin_info.get('id')
    admin_name = admin_info.get('username', 'Unknown')
    
    conn = pymysql.connect(**AUTH_DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # 检查是否在黑名单中
            cursor.execute(
                "SELECT id, status, title FROM ip_blacklist WHERE novel_id = %s",
                (novel_id,)
            )
            existing = cursor.fetchone()
            
            if not existing:
                return jsonify({
                    'success': False,
                    'error': '该书籍不在黑名单中'
                }), 404
            
            if existing[1] == 'removed':
                return jsonify({
                    'success': False,
                    'error': f'《{existing[2]}》已从黑名单中移除'
                }), 409
            
            # 移出黑名单
            cursor.execute("""
                UPDATE ip_blacklist 
                SET status = 'removed', removed_reason = %s, removed_at = NOW(), updated_at = NOW()
                WHERE novel_id = %s
            """, (f"Removed by {admin_name}: {reason}", novel_id))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'《{existing[2]}》已移出黑名单',
                'novel_id': novel_id,
                'status': 'whitelisted'
            })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': f'数据库错误: {str(e)}'}), 500
    finally:
        conn.close()


@blacklist_bp.route('/admin/blacklist/status/<novel_id>', methods=['GET'])
def get_blacklist_status(novel_id):
    """查询书籍的黑名单状态"""
    if not novel_id:
        return jsonify({'success': False, 'error': '缺少 novel_id 参数'}), 400
    
    conn = pymysql.connect(**AUTH_DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT novel_id, title, status, reason, created_at, removed_at
                FROM ip_blacklist WHERE novel_id = %s
            """, (novel_id,))
            
            result = cursor.fetchone()
            
            if not result:
                return jsonify({
                    'success': True,
                    'novel_id': novel_id,
                    'is_blacklisted': False,
                    'status': 'not_found',
                    'message': '该书籍不在黑名单中'
                })
            
            return jsonify({
                'success': True,
                'novel_id': result[0],
                'title': result[1],
                'is_blacklisted': result[2] == 'active',
                'status': 'blacklisted' if result[2] == 'active' else 'removed',
                'reason': result[3],
                'created_at': result[4].isoformat() if result[4] else None,
                'removed_at': result[5].isoformat() if result[5] else None
            })
    except Exception as e:
        return jsonify({'success': False, 'error': f'数据库错误: {str(e)}'}), 500
    finally:
        conn.close()


@blacklist_bp.route('/admin/blacklist/list', methods=['GET'])
def get_blacklist():
    """获取黑名单列表"""
    status = request.args.get('status', 'active')  # active, removed, all
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    conn = pymysql.connect(**AUTH_DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            where_clause = ""
            params = []
            
            if status == 'active':
                where_clause = "WHERE status = 'active'"
            elif status == 'removed':
                where_clause = "WHERE status = 'removed'"
            
            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM ip_blacklist {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
            
            # 获取列表
            offset = (page - 1) * per_page
            data_sql = f"""
                SELECT novel_id, title, author, platform, reason, admin_name, 
                       status, created_at, removed_at
                FROM ip_blacklist {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_sql, params + [per_page, offset])
            
            results = cursor.fetchall()
            items = []
            for row in results:
                items.append({
                    'novel_id': row[0],
                    'title': row[1],
                    'author': row[2],
                    'platform': row[3],
                    'reason': row[4],
                    'admin_name': row[5],
                    'status': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                    'removed_at': row[8].isoformat() if row[8] else None
                })
            
            return jsonify({
                'success': True,
                'items': items,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            })
    except Exception as e:
        return jsonify({'success': False, 'error': f'数据库错误: {str(e)}'}), 500
    finally:
        conn.close()
