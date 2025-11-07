import datetime
import jwt
from functools import wraps
from quart import request, jsonify, g
from quart import current_app as app
from src_v2.core.permission.permission_manager import permission_manager

from src_v2.core.log import logger

def permission_required(req_permissions: list[str]):
    """权限装饰器（带参数）"""
    def decorator(f):
        @wraps(f)
        async def decorated_function(*args, **kwargs):
            # 在请求执行时检查权限
            user_id = g.current_user['user_id']
            for permission in req_permissions:
                per_name = permission.split(":")[0]
                per_action = permission.split(":")[1]

            roles = await permission_manager.get_user_roles(user_id)
            permissions = []
            for role in roles:
                role_permissions = await permission_manager.get_role_permissions(role)
                permissions.extend(role_permissions)
            user_permissions = await permission_manager.get_user_permissions(user_id)
            permissions.extend(user_permissions)

            permission_access = all(perm in permissions for perm in req_permissions)

            # 检查权限
            if not permission_access:
                logger.error(f"{f.__name__}: 用户 {user_id} 权限不足，缺少权限 {req_permissions}")
                return jsonify({'error': '权限不足'}), 403
            
            return await f(*args, **kwargs)
        return decorated_function
    return decorator