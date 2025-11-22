import os
from datetime import datetime, timedelta, timezone
import httpx

from src_v2.core.database.kahuna_database_utils_v2 import UserDBUtils
from src_v2.core.utils import KahunaException
from src_v2.core.log import logger
from src_v2.core.config.config import config


async def ensure_user_access_token(user_name: str) -> str:
    """Ensure the user's access token is valid and return it.

    If the token is expired (within a 5-minute buffer) this will attempt to
    refresh it using the OIDC provider's token endpoint and the stored
    refresh_token. On success the DB is updated and the new access token is
    returned. Raises KahunaException on failure or when no refresh token is
    available.
    """
    user_obj = await UserDBUtils.select_user_by_user_name(user_name)
    if not user_obj:
        raise KahunaException("用户不存在")

    now = datetime.now(timezone.utc)
    buffer = timedelta(minutes=5)

    if user_obj.access_token and user_obj.token_expires_at:
        try:
            if user_obj.token_expires_at > (now + buffer):
                return user_obj.access_token
        except Exception:
            # if stored value is malformed, proceed to refresh
            logger.debug("用户 token_expires_at 无效，尝试刷新")

    # need to refresh
    if not user_obj.refresh_token:
        raise KahunaException("Refresh token 不可用，请重新授权")

    provider = os.getenv('OIDC_PROVIDER') or config.get('OIDC', 'PROVIDER', fallback=None) or 'https://seat.winterco.org'
    client_id = os.getenv('OIDC_CLIENT_ID') or config.get('OIDC', 'CLIENT_ID', fallback=None)
    client_secret = os.getenv('OIDC_CLIENT_SECRET') or config.get('OIDC', 'CLIENT_SECRET', fallback=None)

    config_url = f"{provider.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=15.0) as client:
        cfg_resp = await client.get(config_url)
        if cfg_resp.status_code != 200:
            raise KahunaException("无法获取 OIDC 配置")
        cfg = cfg_resp.json()
        token_endpoint = cfg.get('token_endpoint')

        if not token_endpoint:
            raise KahunaException("OIDC 提供者未提供 token_endpoint")

        token_resp = await client.post(
            token_endpoint,
            data={
                'grant_type': 'refresh_token',
                'refresh_token': user_obj.refresh_token,
            },
            auth=(client_id, client_secret) if client_id and client_secret else None,
            headers={'Accept': 'application/json'},
            timeout=20.0,
        )

    if token_resp.status_code != 200:
        logger.error(f"刷新 token 失败: status={token_resp.status_code} body={token_resp.text}")
        raise KahunaException("刷新 token 失败，请重新授权")

    token_json = token_resp.json()
    access_token = token_json.get('access_token') or token_json.get('id_token')
    refresh_token = token_json.get('refresh_token') or user_obj.refresh_token
    expires_in = token_json.get('expires_in')

    expires_at = None
    try:
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
    except Exception:
        expires_at = None

    # persist changes
    try:
        user_obj.access_token = access_token
        user_obj.refresh_token = refresh_token
        user_obj.token_expires_at = expires_at
        await UserDBUtils.merge(user_obj)
    except Exception as e:
        logger.error(f"保存刷新后的 token 失败: {e}")
        raise KahunaException("无法保存刷新后的 token")

    if not access_token:
        raise KahunaException("OIDC 提供者未返回 access_token")

    return access_token
