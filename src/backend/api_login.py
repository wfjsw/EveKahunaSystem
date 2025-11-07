from quart import Quart, request, jsonify, g, Blueprint
from quart import current_app as app
from quart_schema import QuartSchema
from functools import wraps
import jwt
import datetime
from werkzeug.security import check_password_hash, generate_password_hash

from src.service.log_server import logger

# app = Quart(__name__)
# app.config['SECRET_KEY'] = 'your-secret-key-here'
# QuartSchema(app)

api_auth_bp = Blueprint('api_auth', __name__, url_prefix='/api/auth')

# 用户数据库模拟（实际应用中应使用真实数据库）
users_db = {
    'admin': {
        'password_hash': generate_password_hash('admin123'),
        'role': 'admin',
        'email': 'admin@example.com'
    }
}

INVITE_CODE = '123456'

@api_auth_bp.route('/signup', methods=['POST'])
async def signup():
    data = await request.get_json()
    username = data.get('username')
    logger.debug(f"username: {username}")
    password = data.get('password')
    logger.debug(f"password: {password}")
    invite_code = data.get('inviteCode')
    logger.debug(f"invite_code: {invite_code}")

    if invite_code != INVITE_CODE:
        return jsonify({'error': '邀请码错误'}), 400

    users_db[username] = {
        'password_hash': generate_password_hash(password),
        'role': 'user',
        'email': f'{''}'
    }

    return jsonify({})

def create_token(user_id: str, role: str):
    """创建JWT token"""
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

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
        token = request.headers.get('Authorization')
        
        if not token or not token.startswith('Bearer '):
            return jsonify({'error': '缺少认证token'}), 401
        
        token = token.split(' ')[1]
        payload = verify_token(token)
        
        if not payload:
            return jsonify({'error': '无效的token'}), 401
        
        g.current_user = payload
        return await f(*args, **kwargs)
    
    return decorated_function

@api_auth_bp.route('/login', methods=['POST'])
async def login():
    """用户登录"""
    data = await request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    user = users_db.get(username)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    token = create_token(username, user['role'])
    
    return jsonify({
        'token': token,
        'user': {
            'id': username,
            'username': username,
            'email': user['email'],
            'role': user['role']
        }
    })

@api_auth_bp.route('/me', methods=['GET'])
@auth_required
async def get_current_user():
    """获取当前用户信息"""
    user_id = g.current_user['user_id']
    user = users_db.get(user_id)
    
    return jsonify({
        'id': user_id,
        'username': user_id,
        'email': user['email'],
        'role': user['role']
    })

@api_auth_bp.route('/logout', methods=['POST'])
@auth_required
async def logout():
    """用户登出"""
    # 在实际应用中，可以将token加入黑名单
    return jsonify({'message': '登出成功'})


