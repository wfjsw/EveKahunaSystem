import datetime
import jwt
from functools import wraps
from quart import request, jsonify, g, session
from quart import current_app as app
from src_v2.core.permission.permission_manager import permission_manager

def verify_token(token: str):
    """验证JWT token"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def auth_required(f):
    """认证装饰器"""

    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Use server-side session for authentication
        user_name = session.get('user_name')
        if not user_name:
            return jsonify({'error': '未登录'}), 401
        roles = session.get('roles', [])

        # expose a consistent current_user dict on `g`
        g.current_user = {
            'user_name': user_name,
            'roles': roles or []
        }
        return await f(*args, **kwargs)

    return decorated_function
