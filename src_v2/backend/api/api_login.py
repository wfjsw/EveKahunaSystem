import datetime, jwt
import traceback

from quart import Quart, request, jsonify, g, Blueprint, current_app as app, redirect, session, Response
from src_v2.backend.auth import auth_required
from werkzeug.security import check_password_hash, generate_password_hash
import os
import httpx
from jwt import PyJWKClient

from src_v2.core.permission.permission_manager import permission_manager
from src_v2.core.user.user_manager import UserManager
from src_v2.core.log import logger
from src_v2.model.EVE.character.character_manager import CharacterManager
from src_v2.core.utils import KahunaException
from src_v2.core.database.kahuna_database_utils_v2 import UserDBUtils
from datetime import datetime, timedelta, timezone

# app = Quart(__name__)
# app.config['SECRET_KEY'] = 'your-secret-key-here'
# QuartSchema(app)

api_auth_bp = Blueprint('api_auth', __name__, url_prefix='/api/auth')

# 用户数据库模拟（实际应用中应使用真实数据库）
# users_db = {
#     'admin': {
#         'password_hash': generate_password_hash('admin123'),
#         'role': 'admin',
#         'email': 'admin@example.com'
#     }
# }

def create_token(user_id: str, role: str):
    """创建JWT token"""
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


@api_auth_bp.route('/me', methods=['GET'])
@auth_required
async def get_current_user():
    """获取当前用户信息"""
    try:
        user_id = g.current_user['user_id']
        user = await UserManager().get_user(user_id)
        if not user:
            return jsonify({"status": 404, "message": "用户不存在"}), 404

        roles = await permission_manager.get_user_roles(user_id)
        vip_state = await permission_manager.get_vip_state(user_id)
        if vip_state:
            roles.append(vip_state.vip_level)

        return jsonify({
            "status": 200,
            "id": user.user_name,
            "username": user.user_name,
            "roles": list(set(roles)),
        })
    except KahunaException as e:
        return jsonify({"status": 500, "message": str(e)}), 500
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {traceback.format_exc()}")
        return jsonify({"status": 500, "message": "获取当前用户信息失败"}), 500


@api_auth_bp.route('/oidc/login')
async def oidc_login():
    """Start OpenID Connect authorization by redirecting to provider."""
    client_id = os.getenv('OIDC_CLIENT_ID') or app.config.get('OIDC_CLIENT_ID')
    redirect_uri = os.getenv('OIDC_REDIRECT_URI') or app.config.get('OIDC_REDIRECT_URI') or 'http://localhost:5000/api/auth/oidc/callback'
    state = jwt.encode({'rnd': os.urandom(8).hex(), 'ts': datetime.datetime.now(datetime.timezone.utc).isoformat()}, app.config.get('SECRET_KEY','secret'), algorithm='HS256')
    session['oidc_state'] = state
    provider = os.getenv('OIDC_PROVIDER') or app.config.get('OIDC_PROVIDER') or 'https://seat.winterco.org'
    config_url = f"{provider.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0) as client:
        cfg_resp = await client.get(config_url)
    if cfg_resp.status_code != 200:
        return jsonify({"status": 500, "message": "Failed to fetch OIDC configuration"}), 500
    cfg = cfg_resp.json()
    authorization_endpoint = cfg.get('authorization_endpoint')
    issuer = cfg.get('issuer')

    client_id = os.getenv('OIDC_CLIENT_ID') or app.config.get('OIDC_CLIENT_ID')
    redirect_uri = os.getenv('OIDC_REDIRECT_URI') or app.config.get('OIDC_REDIRECT_URI') or (app.config.get('BASE_URL','http://localhost:5000') + '/api/auth/oidc/callback')
    state = jwt.encode({'rnd': os.urandom(8).hex(), 'ts': datetime.datetime.now(datetime.timezone.utc).isoformat()}, app.config.get('SECRET_KEY','secret'), algorithm='HS256')
    nonce = os.urandom(8).hex()
    session['oidc_state'] = state
    session['oidc_nonce'] = nonce
    authorize_url = (
        f"{authorization_endpoint}?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope=openid&state={state}&nonce={nonce}"
    )
    return redirect(authorize_url)

@api_auth_bp.route('/oidc/callback')
async def oidc_callback():
    """Handle OIDC callback: exchange code for tokens, create/update user, return JWT via a small HTML that stores it in localStorage."""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        saved_state = session.get('oidc_state')
        if not code or not state or state != saved_state:
            return jsonify({"status": 400, "message": "Invalid OIDC callback (missing code or invalid state)"}), 400

        provider = os.getenv('OIDC_PROVIDER') or app.config.get('OIDC_PROVIDER') or 'https://seat.winterco.org'
        config_url = f"{provider.rstrip('/')}/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=10.0) as client:
            cfg_resp = await client.get(config_url)
        if cfg_resp.status_code != 200:
            return jsonify({"status": 500, "message": "Failed to fetch OIDC configuration"}), 500
        cfg = cfg_resp.json()
        token_endpoint = cfg.get('token_endpoint')
        jwks_uri = cfg.get('jwks_uri')
        issuer = cfg.get('issuer')

        client_id = os.getenv('OIDC_CLIENT_ID') or app.config.get('OIDC_CLIENT_ID')
        client_secret = os.getenv('OIDC_CLIENT_SECRET') or app.config.get('OIDC_CLIENT_SECRET')
        redirect_uri = os.getenv('OIDC_REDIRECT_URI') or app.config.get('OIDC_REDIRECT_URI') or (app.config.get('BASE_URL','http://localhost:5000') + '/api/auth/oidc/callback')

        async with httpx.AsyncClient(timeout=20.0) as client:
            token_resp = await client.post(
                token_endpoint,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri
                },
                auth=(client_id, client_secret),
                headers={'Accept': 'application/json'}
            )

        if token_resp.status_code != 200:
            return jsonify({"status": 500, "message": "Failed to obtain token from OIDC provider"}), 500
        token_json = token_resp.json()
        access_token = token_json.get('access_token')
        id_token = token_json.get('id_token')

        # Derive and verify user identity from `id_token` using provider JWKS
        if not id_token:
            return jsonify({"status": 500, "message": "id_token missing from token response"}), 500

        # verify signature & claims
        try:
            if not jwks_uri:
                return jsonify({"status": 500, "message": "jwks_uri not provided by issuer configuration"}), 500
            jwks_client = PyJWKClient(jwks_uri)
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            # audience and issuer validation
            decoded = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=[signing_key.algorithm if hasattr(signing_key, 'algorithm') else 'RS256'],
                audience=client_id,
                issuer=issuer,
            )
        except Exception as ex:
            logger.error(f"id_token validation failed: {traceback.format_exc()}")
            return jsonify({"status": 500, "message": "id_token validation failed"}), 500

        username = decoded.get('preferred_username') or decoded.get('email') or decoded.get('sub')

        # verify nonce
        saved_nonce = session.get('oidc_nonce')
        if saved_nonce and decoded.get('nonce') != saved_nonce:
            return jsonify({"status": 400, "message": "Invalid nonce in id_token"}), 400

        # Create or update local user: store access_token, refresh_token, expires_at
        user_obj = await UserDBUtils.select_user_by_user_name(username)
        expires_at = None
        try:
            expires_in = token_json.get('expires_in')
            if expires_in:
                expires_at = datetime.now(datetime.timezone.utc) + timedelta(seconds=int(expires_in))
        except Exception:
            expires_at = None

        if user_obj:
            user_obj.access_token = access_token or id_token or None
            user_obj.refresh_token = token_json.get('refresh_token')
            user_obj.token_expires_at = expires_at
            await UserDBUtils.merge(user_obj)
        else:
            # create via UserManager
            await UserManager().create_user(
                user_name=username,
                access_token=(access_token or id_token),
                refresh_token=token_json.get('refresh_token'),
                token_expires_at=expires_at
            )
            # assign default role
            await permission_manager.add_role_to_user(username, 'user')

        # create local JWT for app session
        roles = await permission_manager.get_user_roles(username)
        token = create_token(username, ",".join(roles))

        # return a small HTML that stores token and redirects to SPA
        frontend_redirect = os.getenv('FRONTEND_URL') or 'http://localhost:5173'
        html = f"""
        <html><head><meta charset='utf-8'></head><body>
        <script>
          try {{
            localStorage.setItem('token', '{token}');
          }} catch(e) {{}}
          window.location = '{frontend_redirect}';
        </script>
        </body></html>
        """
        return Response(html, content_type='text/html')
    except Exception as e:
        logger.error(f"OIDC callback error: {traceback.format_exc()}")
        return jsonify({"status": 500, "message": "OIDC callback failed"}), 500
 

@api_auth_bp.route('/logout', methods=['POST'])
@auth_required
async def logout():
    """用户登出"""
    try:
        # 在实际应用中，可以将token加入黑名单
        return jsonify({"status": 200, "message": "登出成功"})
    except KahunaException as e:
        return jsonify({"status": 500, "message": str(e)}), 500
    except Exception as e:
        logger.error(f"登出失败: {traceback.format_exc()}")
        return jsonify({"status": 500, "message": "登出失败"}), 500


@api_auth_bp.route('/deleteAccount', methods=['POST'])
@auth_required
async def delete_account():
    """注销账号"""
    try:
        user_id = g.current_user["user_id"]
        main_character_id = await UserManager().get_main_character_id(user_id)
        # 删除用户所有角色相关数据
        
        # 删除用户角色数据
        await CharacterManager().delete_all_alias_characters_of_main_character(main_character_id)
        await CharacterManager().delete_all_character_of_user(user_id)

        # 删除用户数据
        await UserManager().delete_user(user_id)

        return jsonify({"status": 200, "message": "注销成功"})
    except KahunaException as e:
        return jsonify({"status": 500, "message": str(e)}), 500
    except Exception as e:
        logger.error(f"注销账号失败: {traceback.format_exc()}")
        return jsonify({"status": 500, "message": "注销账号失败"}), 500
