import jwt
import traceback

import urllib.parse
from quart import Quart, request, jsonify, g, Blueprint, current_app as app, redirect, session, Response
from src_v2.backend.auth import auth_required
from werkzeug.security import check_password_hash, generate_password_hash
import os
import aiohttp
from jwt import PyJWKClient, PyJWKClientError

from src_v2.core.config.config import config
from src_v2.core.permission.permission_manager import permission_manager
from src_v2.core.user.user_manager import UserManager
from src_v2.core.log import logger
from src_v2.model.EVE.character.character_manager import CharacterManager
from src_v2.core.utils import KahunaException
from src_v2.core.database.kahuna_database_utils_v2 import EveAuthedCharacterDBUtils, UserDBUtils
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

def _set_session_for_user(user_name: str, roles: list[str] = []):
    session.clear()
    session['user_name'] = user_name
    session['roles'] = roles or []


@api_auth_bp.route('/me', methods=['GET'])
@auth_required
async def get_current_user():
    """获取当前用户信息"""
    try:
        # read current user from session-provided g.current_user
        current = g.current_user
        # prefer user_name for display; many helpers still accept username
        user_lookup = current.get('user_name') or current.get('user_id')
        user = await UserManager().get_user(user_lookup)
        if not user:
            return jsonify({"status": 404, "message": "用户不存在"}), 404

        roles = await permission_manager.get_user_roles(user_lookup)
        vip_state = await permission_manager.get_vip_state(user_lookup)
        if vip_state:
            roles.append(vip_state.vip_level)

        return jsonify({
            "status": 200,
            "id": getattr(user, 'id', user.user_name),
            "username": getattr(user, 'display_name', user.user_name),
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
    # use a random opaque state and store in session
    state = os.urandom(16).hex()
    session['oidc_state'] = state
    provider = os.getenv('OIDC_PROVIDER') or app.config.get('OIDC_PROVIDER') or 'https://seat.winterco.org'
    config_url = f"{provider.rstrip('/')}/.well-known/openid-configuration"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as client:
        async with client.get(config_url) as cfg_resp:
            if cfg_resp.status != 200:
                return jsonify({"status": 500, "message": "Failed to fetch OIDC configuration"}), 500
            cfg = await cfg_resp.json()
    authorization_endpoint = cfg.get('authorization_endpoint')
    issuer = cfg.get('issuer')

    client_id = os.getenv('OIDC_CLIENT_ID') or app.config.get('OIDC_CLIENT_ID')
    redirect_uri = os.getenv('OIDC_REDIRECT_URI') or app.config.get('OIDC_REDIRECT_URI') or (app.config.get('BASE_URL','http://localhost:5000') + '/api/auth/oidc/callback')
    # new opaque state for this auth request
    state = os.urandom(16).hex()
    nonce = os.urandom(8).hex()
    session['oidc_state'] = state
    session['oidc_nonce'] = nonce

    esi_scope=[k for k, v in dict(config['ESI']).items() if v == 'true']

    scopes = ['openid', 'accounts', 'groups', 'passthrough']
    scopes.extend(esi_scope)

    client_id = urllib.parse.quote(str(client_id), safe='')
    redirect_uri = urllib.parse.quote(redirect_uri, safe='')
    state = urllib.parse.quote(state, safe='')
    nonce = urllib.parse.quote(nonce, safe='')
    scope = urllib.parse.quote(' '.join(scopes), safe='')

    authorize_url = (
        f"{authorization_endpoint}?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope={scope}&state={state}&nonce={nonce}"
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
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as client:
            async with client.get(config_url) as cfg_resp:
                if cfg_resp.status != 200:
                    return jsonify({"status": 500, "message": "Failed to fetch OIDC configuration"}), 500
                cfg = await cfg_resp.json()
        token_endpoint = cfg.get('token_endpoint')
        jwks_uri = cfg.get('jwks_uri')
        issuer = cfg.get('issuer')

        client_id = os.getenv('OIDC_CLIENT_ID') or app.config.get('OIDC_CLIENT_ID')
        client_secret = os.getenv('OIDC_CLIENT_SECRET') or app.config.get('OIDC_CLIENT_SECRET')
        redirect_uri = os.getenv('OIDC_REDIRECT_URI') or app.config.get('OIDC_REDIRECT_URI') or (app.config.get('BASE_URL','http://localhost:5000') + '/api/auth/oidc/callback')

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20.0)) as client:
            auth = aiohttp.BasicAuth(client_id, client_secret) if client_id and client_secret else None
            async with client.post(
                token_endpoint,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri
                },
                auth=auth,
                headers={'Accept': 'application/json'}
            ) as token_resp:
                if token_resp.status != 200:
                    return jsonify({"status": 500, "message": "Failed to obtain token from OIDC provider"}), 500
                token_json = await token_resp.json()
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
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            except PyJWKClientError:
                key_set = jwks_client.get_jwk_set()
                signing_key = key_set.keys[0]

            # audience and issuer validation
            decoded = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=[signing_key.algorithm_name if hasattr(signing_key, 'algorithm_name') else 'RS256'],
                audience=client_id,
                issuer=issuer,
            )
        except Exception as ex:
            logger.error(f"id_token validation failed: {traceback.format_exc()}")
            return jsonify({"status": 500, "message": "id_token validation failed"}), 500

        user_name = decoded.get('sub')
        display_name = decoded.get('nam')

        # verify nonce
        saved_nonce = session.get('oidc_nonce')
        if saved_nonce and decoded.get('nonce') != saved_nonce:
            return jsonify({"status": 400, "message": "Invalid nonce in id_token"}), 400

        # Create or update local user: store access_token, refresh_token, expires_at
        user_obj = await UserDBUtils.select_user_by_user_name(user_name)
        expires_at = datetime.fromtimestamp(decoded.get('exp'), tz=timezone.utc)
        roles = decoded.get('groups', [])


        if user_obj:
            user_obj.access_token = access_token or id_token or None
            user_obj.refresh_token = token_json.get('refresh_token')
            user_obj.token_expires_at = expires_at
            await UserDBUtils.merge(user_obj)
        else:
            # create via UserManager
            await UserManager().create_user(
                user_name=user_name,
                display_name=display_name,
                access_token=(access_token or id_token),
                refresh_token=token_json.get('refresh_token'),
                token_expires_at=expires_at
            )
            # assign default role
            # await permission_manager.add_role_to_user(user_name, 'user')

        user_characters = decoded.get('acct', [])

        for char in user_characters:
            try:
                # 使用从state解析出的user_id，而不是g.current_user
                character = await CharacterManager().insert_new_character(
                    char['id'],
                    user_name  # 使用从state解析出的user_id
                )
            except KahunaException as e:
                logger.error(f"角色信息入库失败: {str(e)}")
                return jsonify({"status": 500, "message": str(e)}), 500
            except Exception as e:
                logger.error(f"角色信息入库失败: {traceback.format_exc()}")
                return jsonify({"status": 500, "message": "角色信息入库失败"}), 500

        # 删除不在 user_characters 列表中的角色
        existing_characters = await CharacterManager().get_user_all_characters(user_name)
        user_character_ids = {char['id'] for char in user_characters}
        for character in existing_characters:
            if character['id'] not in user_character_ids:
                try:
                    await EveAuthedCharacterDBUtils.delete_character_by_character_id(character['id'])
                except Exception as e:
                    logger.error(f"删除角色失败: {traceback.format_exc()}")

        _set_session_for_user(user_name, roles=roles)

        # redirect to frontend; session cookie holds auth state
        frontend_redirect = os.getenv('FRONTEND_URL') or 'http://localhost:5173'
        return redirect(frontend_redirect)
    except Exception as e:
        logger.error(f"OIDC callback error: {traceback.format_exc()}")
        return jsonify({"status": 500, "message": "OIDC callback failed"}), 500
 

@api_auth_bp.route('/logout', methods=['POST'])
@auth_required
async def logout():
    """用户登出"""
    try:
        # Clear server-side session to log out
        session.clear()
        return jsonify({"status": 200, "message": "登出成功"})
    except KahunaException as e:
        return jsonify({"status": 500, "message": str(e)}), 500
    except Exception as e:
        logger.error(f"登出失败: {traceback.format_exc()}")
        return jsonify({"status": 500, "message": "登出失败"}), 500


# @api_auth_bp.route('/deleteAccount', methods=['POST'])
# @auth_required
# async def delete_account():
#     """注销账号"""
#     try:
#         user_id = g.current_user["user_id"]
#         main_character_id = await UserManager().get_main_character_id(user_id)
#         # 删除用户所有角色相关数据
        
#         # 删除用户角色数据
#         await CharacterManager().delete_all_alias_characters_of_main_character(main_character_id)
#         await CharacterManager().delete_all_character_of_user(user_id)

#         # 删除用户数据
#         await UserManager().delete_user(user_id)

#         return jsonify({"status": 200, "message": "注销成功"})
#     except KahunaException as e:
#         return jsonify({"status": 500, "message": str(e)}), 500
#     except Exception as e:
#         logger.error(f"注销账号失败: {traceback.format_exc()}")
#         return jsonify({"status": 500, "message": "注销账号失败"}), 500
