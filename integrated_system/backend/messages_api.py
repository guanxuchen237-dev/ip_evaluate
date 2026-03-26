"""
留言板API模块
提供用户与管理员之间的留言功能
"""
from flask import Blueprint, request, jsonify, g
import pymysql
from datetime import datetime
from auth import login_required, get_auth_db, AUTH_DB_CONFIG

messages_bp = Blueprint('messages', __name__, url_prefix='/messages')

def init_messages_table():
    """创建留言板相关表"""
    try:
        conn = pymysql.connect(**AUTH_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cursor:
            # 创建留言表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    username VARCHAR(100) NOT NULL,
                    content TEXT NOT NULL,
                    is_admin_reply BOOLEAN DEFAULT FALSE,
                    admin_id INT NULL,
                    admin_name VARCHAR(100) NULL,
                    parent_id INT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_created_at (created_at),
                    INDEX idx_is_read (is_read),
                    FOREIGN KEY (parent_id) REFERENCES messages(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            conn.commit()
            print("[OK] messages 表创建成功或已存在")
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] 创建 messages 表失败: {e}")
        return False

# ============================================================
#  用户端API
# ============================================================

@messages_bp.route('/list', methods=['GET'])
@login_required
def get_user_messages():
    """获取当前用户的留言列表（包含管理员回复）"""
    try:
        user_id = g.user_id
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 获取总数量
            cursor.execute("""
                SELECT COUNT(*) as total FROM messages 
                WHERE user_id = %s AND parent_id IS NULL
            """, (user_id,))
            total = cursor.fetchone()['total']
            
            # 获取留言列表（包含回复）
            cursor.execute("""
                SELECT m.*, 
                       (SELECT COUNT(*) FROM messages replies 
                        WHERE replies.parent_id = m.id AND replies.is_admin_reply = TRUE) as reply_count
                FROM messages m
                WHERE m.user_id = %s AND m.parent_id IS NULL
                ORDER BY m.created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, page_size, (page - 1) * page_size))
            messages = cursor.fetchall()
            
            # 为每条留言获取回复
            for msg in messages:
                cursor.execute("""
                    SELECT id, content, is_admin_reply, admin_name, created_at
                    FROM messages
                    WHERE parent_id = %s
                    ORDER BY created_at ASC
                """, (msg['id'],))
                msg['replies'] = cursor.fetchall()
                
        conn.close()
        
        return jsonify({
            'messages': messages,
            'total': total,
            'page': page,
            'total_pages': (total + page_size - 1) // page_size
        })
        
    except Exception as e:
        print(f"[Messages Error] Get user messages: {e}")
        return jsonify({'error': str(e)}), 500


@messages_bp.route('/send', methods=['POST'])
@login_required
def send_message():
    """用户发送留言"""
    try:
        data = request.json
        content = data.get('content', '').strip()
        parent_id = data.get('parent_id')  # 如果是回复，指定父留言ID
        
        if not content:
            return jsonify({'error': '留言内容不能为空'}), 400
            
        if len(content) > 1000:
            return jsonify({'error': '留言内容不能超过1000字'}), 400
        
        user_id = g.user_id
        username = g.user.get('username', 'Unknown')
        
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO messages (user_id, username, content, parent_id, is_admin_reply)
                VALUES (%s, %s, %s, %s, FALSE)
            """, (user_id, username, content, parent_id))
            conn.commit()
            message_id = cursor.lastrowid
            
        conn.close()
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'message': '留言发送成功'
        })
        
    except Exception as e:
        print(f"[Messages Error] Send message: {e}")
        return jsonify({'error': str(e)}), 500


@messages_bp.route('/unread_count', methods=['GET'])
@login_required
def get_unread_count():
    """获取用户未读的管理员回复数量"""
    try:
        user_id = g.user_id
        
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 获取用户所有留言ID
            cursor.execute("""
                SELECT id FROM messages WHERE user_id = %s AND parent_id IS NULL
            """, (user_id,))
            user_message_ids = [row['id'] for row in cursor.fetchall()]
            
            if not user_message_ids:
                return jsonify({'unread_count': 0})
            
            # 统计这些留言下的未读管理员回复
            format_strings = ','.join(['%s'] * len(user_message_ids))
            cursor.execute(f"""
                SELECT COUNT(*) as unread_count 
                FROM messages 
                WHERE parent_id IN ({format_strings}) 
                AND is_admin_reply = TRUE 
                AND is_read = FALSE
            """, tuple(user_message_ids))
            
            result = cursor.fetchone()
            unread_count = result['unread_count'] if result else 0
            
        conn.close()
        
        return jsonify({'unread_count': unread_count})
        
    except Exception as e:
        print(f"[Messages Error] Get unread count: {e}")
        return jsonify({'error': str(e)}), 500


@messages_bp.route('/mark_read/<int:message_id>', methods=['POST'])
@login_required
def mark_as_read(message_id):
    """将管理员回复标记为已读"""
    try:
        user_id = g.user_id
        
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 验证这条回复是否属于该用户的留言
            cursor.execute("""
                UPDATE messages m1
                JOIN messages m2 ON m1.parent_id = m2.id
                SET m1.is_read = TRUE
                WHERE m1.id = %s AND m2.user_id = %s AND m1.is_admin_reply = TRUE
            """, (message_id, user_id))
            conn.commit()
            
        conn.close()
        
        return jsonify({'success': True, 'message': '已标记为已读'})
        
    except Exception as e:
        print(f"[Messages Error] Mark read: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================
#  管理员端API
# ============================================================

@messages_bp.route('/admin/list', methods=['GET'])
@login_required
def get_all_messages():
    """管理员获取所有留言列表"""
    try:
        # 检查是否是管理员
        if g.user.get('role') != 'admin':
            return jsonify({'error': '权限不足'}), 403
            
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        status = request.args.get('status', 'all')  # all, unread, replied, unreplied
        
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 构建查询条件
            where_clause = "WHERE m.parent_id IS NULL"
            params = []
            
            if status == 'unread':
                where_clause += """ AND EXISTS (
                    SELECT 1 FROM messages replies 
                    WHERE replies.parent_id = m.id 
                    AND replies.is_admin_reply = TRUE 
                    AND replies.is_read = FALSE
                )"""
            elif status == 'replied':
                where_clause += """ AND EXISTS (
                    SELECT 1 FROM messages replies 
                    WHERE replies.parent_id = m.id 
                    AND replies.is_admin_reply = TRUE
                )"""
            elif status == 'unreplied':
                where_clause += """ AND NOT EXISTS (
                    SELECT 1 FROM messages replies 
                    WHERE replies.parent_id = m.id 
                    AND replies.is_admin_reply = TRUE
                )"""
            
            # 获取总数量
            cursor.execute(f"""
                SELECT COUNT(*) as total 
                FROM messages m
                {where_clause}
            """)
            total = cursor.fetchone()['total']
            
            # 获取留言列表
            cursor.execute(f"""
                SELECT m.*, u.email as user_email,
                       (SELECT COUNT(*) FROM messages replies 
                        WHERE replies.parent_id = m.id AND replies.is_admin_reply = TRUE) as reply_count,
                       (SELECT COUNT(*) FROM messages replies 
                        WHERE replies.parent_id = m.id AND replies.is_admin_reply = TRUE AND replies.is_read = FALSE) as unread_reply_count
                FROM messages m
                LEFT JOIN users u ON m.user_id = u.id
                {where_clause}
                ORDER BY m.created_at DESC
                LIMIT %s OFFSET %s
            """, params + [page_size, (page - 1) * page_size])
            messages = cursor.fetchall()
            
            # 为每条留言获取回复
            for msg in messages:
                cursor.execute("""
                    SELECT id, content, is_admin_reply, admin_name, created_at, is_read
                    FROM messages
                    WHERE parent_id = %s
                    ORDER BY created_at ASC
                """, (msg['id'],))
                msg['replies'] = cursor.fetchall()
                
        conn.close()
        
        return jsonify({
            'messages': messages,
            'total': total,
            'page': page,
            'total_pages': (total + page_size - 1) // page_size
        })
        
    except Exception as e:
        print(f"[Messages Error] Get all messages: {e}")
        return jsonify({'error': str(e)}), 500


@messages_bp.route('/admin/reply', methods=['POST'])
@login_required
def admin_reply():
    """管理员回复留言"""
    try:
        # 检查是否是管理员
        if g.user.get('role') != 'admin':
            return jsonify({'error': '权限不足'}), 403
            
        data = request.json
        parent_id = data.get('parent_id')
        content = data.get('content', '').strip()
        
        if not parent_id or not content:
            return jsonify({'error': '缺少必要参数'}), 400
            
        if len(content) > 1000:
            return jsonify({'error': '回复内容不能超过1000字'}), 400
        
        admin_id = g.user_id
        admin_name = g.user.get('username', 'Admin')
        
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 获取父留言的用户ID
            cursor.execute("SELECT user_id FROM messages WHERE id = %s", (parent_id,))
            parent = cursor.fetchone()
            if not parent:
                conn.close()
                return jsonify({'error': '留言不存在'}), 404
                
            user_id = parent['user_id']
            
            # 插入管理员回复
            cursor.execute("""
                INSERT INTO messages (user_id, username, content, parent_id, is_admin_reply, admin_id, admin_name, is_read)
                VALUES (%s, %s, %s, %s, TRUE, %s, %s, FALSE)
            """, (user_id, admin_name, content, parent_id, admin_id, admin_name))
            conn.commit()
            reply_id = cursor.lastrowid
            
        conn.close()
        
        return jsonify({
            'success': True,
            'reply_id': reply_id,
            'message': '回复成功'
        })
        
    except Exception as e:
        print(f"[Messages Error] Admin reply: {e}")
        return jsonify({'error': str(e)}), 500


@messages_bp.route('/admin/delete/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    """管理员删除留言（会级联删除所有回复）"""
    try:
        # 检查是否是管理员
        if g.user.get('role') != 'admin':
            return jsonify({'error': '权限不足'}), 403
            
        conn = get_auth_db()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
            conn.commit()
            
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '留言已删除'
        })
        
    except Exception as e:
        print(f"[Messages Error] Delete message: {e}")
        return jsonify({'error': str(e)}), 500


@messages_bp.route('/admin/stats', methods=['GET'])
@login_required
def get_message_stats():
    """管理员获取留言统计信息"""
    try:
        # 检查是否是管理员
        if g.user.get('role') != 'admin':
            return jsonify({'error': '权限不足'}), 403
            
        conn = get_auth_db()
        with conn.cursor() as cursor:
            # 总留言数
            cursor.execute("SELECT COUNT(*) as total FROM messages WHERE parent_id IS NULL")
            total = cursor.fetchone()['total']
            
            # 今日新增
            cursor.execute("""
                SELECT COUNT(*) as today 
                FROM messages 
                WHERE parent_id IS NULL AND DATE(created_at) = CURDATE()
            """)
            today = cursor.fetchone()['today']
            
            # 未回复数
            cursor.execute("""
                SELECT COUNT(*) as unreplied 
                FROM messages m
                WHERE m.parent_id IS NULL 
                AND NOT EXISTS (
                    SELECT 1 FROM messages replies 
                    WHERE replies.parent_id = m.id AND replies.is_admin_reply = TRUE
                )
            """)
            unreplied = cursor.fetchone()['unreplied']
            
            # 未读回复数
            cursor.execute("""
                SELECT COUNT(*) as unread 
                FROM messages 
                WHERE is_admin_reply = TRUE AND is_read = FALSE
            """)
            unread = cursor.fetchone()['unread']
            
        conn.close()
        
        return jsonify({
            'total': total,
            'today': today,
            'unreplied': unreplied,
            'unread': unread
        })
        
    except Exception as e:
        print(f"[Messages Error] Get stats: {e}")
        return jsonify({'error': str(e)}), 500
