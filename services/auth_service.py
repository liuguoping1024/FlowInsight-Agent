"""
认证服务
处理用户登录、注册、token 生成和验证
"""
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from database.db_connection import db
from config import DB_CONFIG

logger = logging.getLogger(__name__)

# JWT 密钥（生产环境应该从环境变量读取）
JWT_SECRET_KEY = 'flowinsight-secret-key-change-in-production'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24  # Token 有效期 24 小时


class AuthService:
    """认证服务类"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """加密密码"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False
    
    @staticmethod
    def generate_token(user_id: int, username: str) -> str:
        """生成 JWT token"""
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """验证 JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token 已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token 无效: {e}")
            return None
    
    @staticmethod
    def register(username: str, password: str, email: str = None, phone: str = None) -> Dict[str, Any]:
        """用户注册"""
        try:
            # 检查用户名是否已存在
            sql_check = "SELECT id FROM users WHERE username = %s"
            existing = db.execute_query(sql_check, (username,))
            if existing:
                return {
                    'success': False,
                    'message': '用户名已存在'
                }
            
            # 加密密码
            password_hash = AuthService.hash_password(password)
            
            # 插入新用户（默认分配到普通用户组）
            sql_insert = """
            INSERT INTO users (username, password_hash, email, phone, group_id, is_active)
            VALUES (%s, %s, %s, %s, 2, TRUE)
            """
            db.execute_update(sql_insert, (username, password_hash, email, phone))
            
            # 获取新创建的用户
            sql_user = "SELECT id, username, email, phone, group_id FROM users WHERE username = %s"
            user = db.execute_query(sql_user, (username,))
            
            if user:
                return {
                    'success': True,
                    'message': '注册成功',
                    'user': user[0]
                }
            else:
                return {
                    'success': False,
                    'message': '注册失败，无法获取用户信息'
                }
        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            return {
                'success': False,
                'message': f'注册失败: {str(e)}'
            }
    
    @staticmethod
    def login(username: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        try:
            # 查询用户
            sql = """
            SELECT id, username, password_hash, email, phone, group_id, is_active
            FROM users
            WHERE username = %s
            """
            users = db.execute_query(sql, (username,))
            
            if not users:
                return {
                    'success': False,
                    'message': '用户名或密码错误'
                }
            
            user = users[0]
            
            # 检查用户是否激活
            if not user.get('is_active', False):
                return {
                    'success': False,
                    'message': '用户账号已被禁用'
                }
            
            # 验证密码
            if not AuthService.verify_password(password, user['password_hash']):
                return {
                    'success': False,
                    'message': '用户名或密码错误'
                }
            
            # 生成 token
            token = AuthService.generate_token(user['id'], user['username'])
            
            return {
                'success': True,
                'message': '登录成功',
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user.get('email'),
                    'phone': user.get('phone'),
                    'group_id': user.get('group_id')
                }
            }
        except Exception as e:
            logger.error(f"用户登录失败: {e}")
            return {
                'success': False,
                'message': f'登录失败: {str(e)}'
            }
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """根据用户ID获取用户信息"""
        try:
            sql = """
            SELECT id, username, email, phone, group_id, is_active, created_at
            FROM users
            WHERE id = %s
            """
            users = db.execute_query(sql, (user_id,))
            return users[0] if users else None
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None

