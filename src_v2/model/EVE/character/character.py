import os
from typing import Any

import aiohttp
from jwt import PyJWKClient, PyJWKClientError
import jwt
from quart import current_app as app, jsonify
from oauthlib.oauth2 import InvalidClientIdError, InvalidScopeError
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from asyncio import Lock

import traceback

from src_v2.core.database.kahuna_database_utils_v2 import EveAuthedCharacterDBUtils, UserDBUtils
from src_v2.core.database.model import EveAuthedCharacter as M_EveAuthedCharacter
from src_v2.core.database.connect_manager import redis_manager
from ..eveesi.oauth import refresh_token
from ..eveesi import eveesi
from ..eveesi.eveutils import parse_iso_datetime
from src_v2.core.log import logger
from src_v2.core.utils import KahunaException


class Character():
    def __init__(self, character_id: int, character_name: str, owner_user_name: str, birthday: datetime, access_token: str, expires_time: datetime, corporation_id: int, director: bool):
        """
        character_id = Column(Integer, primary_key=True)
            owner_user_name = Column(Text, ForeignKey("user.user_name"))
            character_name = Column(Text, index=True)
            birthday = Column(DateTime)
            access_token = Column(Text)
            refresh_token = Column(Text)
            expires_time = Column(DateTime)
            corporation_id = Column(Integer)
            director = Column(Boolean)
        """

        self.character_id = character_id
        self.character_name = character_name
        self.owner_user_name = owner_user_name
        self.birthday = birthday
        self.access_token = access_token
        # self.refresh_token = refresh_token
        self.corporation_id = corporation_id
        self.director = director
        self.token_expires_date = expires_time
        self._refresh_token_lock = Lock()

    async def refresh_character_token(self):
        token_state = await EveAuthedCharacterDBUtils.select_character_by_character_id(self.character_id)
        try:
            # refresh_res_dict = refresh_token(token_state.refresh_token)
            refresh_res_dict = await self.fetch_passthrough_token()
            logger.info(f"{self.character_name} token refreshed.")
        except (InvalidClientIdError, InvalidScopeError) as e:
            logger.error(f"Caught an exception: {type(e).__name__}, message: {str(e)}")
            raise KahunaException(f"{self.character_name} 角色token获取失败，请重新授权")
        if refresh_res_dict:
            token_state.access_token = refresh_res_dict['access_token']
            # token_state.refresh_token = refresh_res_dict['refresh_token']
            expires_in = refresh_res_dict["expires_in"]
            # token_state.expires_time = datetime.fromtimestamp(refresh_res_dict["expires_at"]).astimezone(timezone.utc)
            token_state.expires_time = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            
            character_roles = await eveesi.characters_character_roles(token_state.access_token, self.character_id)
            director_status = "Director" in character_roles['roles'] if 'roles' in character_roles else None
            if director_status != token_state.director:
                token_state.director = director_status
            await EveAuthedCharacterDBUtils.merge(token_state)

            self.access_token = token_state.access_token
            # self.refresh_token = token_state.refresh_token
            self.token_expires_date = token_state.expires_time
            self.director = token_state.director

    async def fetch_passthrough_token(self):
        user_access_token = await self.obtain_user_access_token()
        provider = os.getenv('OIDC_PROVIDER') or app.config.get('OIDC_PROVIDER') or 'https://seat.winterco.org'
        passthrough_url = f"{provider.rstrip('/')}/oauth/passthrough/{self.character_id}"

        headers = {
            "Authorization": f"Bearer {user_access_token}",
            "Accept": "application/json"
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as client:
            async with client.post(passthrough_url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(f"Passthrough token fetch failed: status={resp.status} body={await resp.text()}")
                    raise KahunaException("Passthrough token 获取失败，请重新授权")
                return await resp.json()
        
    async def obtain_user_access_token(self):
        user_obj = await UserDBUtils.select_user_by_user_name(self.owner_user_name)
        if not user_obj:
            raise KahunaException("用户不存在")
        if not user_obj.refresh_token:
            raise KahunaException("用户 Refresh token 不可用，请重新授权")

        expires_at = user_obj.token_expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at and expires_at > datetime.now(timezone.utc) + timedelta(minutes=5) and user_obj.access_token:
            return user_obj.access_token

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
                    'grant_type': 'refresh_token',
                    'refresh_token': user_obj.refresh_token,
                    'redirect_uri': redirect_uri
                },
                auth=auth,
                headers={'Accept': 'application/json'}
            ) as token_resp:
                if token_resp.status != 200:
                    logger.error(f"刷新 token 失败: status={token_resp.status} body={await token_resp.text()}")
                    user_obj.access_token = None
                    user_obj.token_expires_at = None
                    user_obj.refresh_token = None
                    await UserDBUtils.merge(user_obj)
                    raise KahunaException("刷新 token 失败，请重新授权")
                token_json = await token_resp.json()

        access_token = token_json.get('access_token')

        # verify signature & claims
        try:
            if not jwks_uri:
                return jsonify({"status": 500, "message": "jwks_uri not provided by issuer configuration"}), 500
            jwks_client = PyJWKClient(jwks_uri)
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(access_token)
            except PyJWKClientError:
                key_set = jwks_client.get_jwk_set()
                signing_key = key_set.keys[0]
            # audience and issuer validation
            decoded = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=[signing_key.algorithm_name if hasattr(signing_key, 'algorithm_name') else 'RS256'],
                audience=client_id,
                issuer=issuer,
            )
        except Exception as ex:
            logger.error(f"access_token validation failed: {traceback.format_exc()}")
            raise KahunaException("Access Token 验证失败，请重新授权")
        
        token_refresh_token = token_json.get('refresh_token') or user_obj.refresh_token
        if token_refresh_token != user_obj.refresh_token:
            logger.info("Refresh token has been rotated.")
            user_obj.refresh_token = token_refresh_token
        
        expires_in = token_json.get('expires_in')
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
        user_obj.access_token = access_token
        user_obj.token_expires_at = expires_at
        await UserDBUtils.merge(user_obj)

        return access_token


    @classmethod
    def from_db_obj(cls, db_obj: M_EveAuthedCharacter):
        return cls(
            character_id=db_obj.character_id,
            character_name=db_obj.character_name,
            owner_user_name=db_obj.owner_user_name,
            birthday=db_obj.birthday,
            access_token=db_obj.access_token,
            # refresh_token=db_obj.refresh_token,
            expires_time=db_obj.expires_time,
            corporation_id=db_obj.corporation_id,
            director=db_obj.director)

    @property
    async def ac_token(self):
        async with self._refresh_token_lock:
            if not self.token_avaliable:
                await self.refresh_character_token()
        token_statues = await EveAuthedCharacterDBUtils.select_character_by_character_id(self.character_id)
        return token_statues.access_token

    # @property
    # async def wallet_balance(self):
    #     if self._wallet_balance == 0.0:
    #         await self.refresh_wallet_balance()
    #     return self._wallet_balance

    # @wallet_balance.setter
    # def wallet_balance(self, value):
    #     self._wallet_balance = value

    @property
    def token_avaliable(self):
        if self.token_expires_date is None:
            return False

        # 获取当前时间（确保为timezone-aware）
        current = datetime.now(timezone.utc)

        # 添加5分钟缓冲
        now = current + timedelta(minutes=5)

        # 确保 token_expires_date 也是 timezone-aware
        expires_date = self.token_expires_date
        if expires_date.tzinfo is None:
            expires_date = expires_date.replace(tzinfo=timezone.utc)

        logger.debug(f"check if {expires_date} > {now} = {expires_date > now}")
        return expires_date > now

    async def refresh_wallet_balance(self):
        wallet_balance = await eveesi.character_character_id_wallet(self.ac_token, self.character_id)
        if wallet_balance is not None:
            self.wallet_balance = wallet_balance
        else:
            logger.error("刷新钱包余额失败")

    # @property
    # async def info(self):
    #     return f"角色:{self.character_name}\n"\
    #             f"所属用户:{self.QQ}\n"\
    #             f"角色id:{self.character_id}\n"\
    #             f"钱包:{await self.wallet_balance:,.2f\n}" \
    #             f"token过期时间:{self.token_expires_date}\n"

