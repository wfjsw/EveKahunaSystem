from datetime import datetime
from typing import AnyStr

from cachetools import TTLCache
from asyncio import Lock
from uuid import uuid4

from .user import User
from src_v2.core.database.kahuna_database_utils_v2 import (
    UserDBUtils,
    UserDataDBUtils
)
from src_v2.core.database.connect_manager import postgres_manager, redis_manager
from src_v2.core.database.model import User as M_User
from src_v2.core.database.model import UserData as M_UserData
from src_v2.core.database.kahuna_database_utils_v2 import EveAuthedCharacterDBUtils
from src_v2.core.database.kahuna_database_utils_v2 import EveAliasCharacterDBUtils
from src_v2.core.database.model import EveAliasCharacter as M_EveAliasCharacter
from src_v2.core.log import logger

# import Exception
from src_v2.core.utils import KahunaException, SingletonMeta, get_beijing_utctime

ESI_CACHE = TTLCache(maxsize=100, ttl=300)
class UserManager(metaclass=SingletonMeta):
    def __init__(self):
        self.init_status = False
        self.lock = Lock()
        self.user_dict = {} # {qq_id: User()}

    async def init(self):
        await self.init_user_dict()

    async def init_user_dict(self):
        #  postgre 不再全量读取到内存，只保存热点数据
        if not self.init_status:
            async for user in await UserDBUtils.select_all():
                usr_obj = User(
                    user_name=user.user_name,
                    user_role=user.user_role,
                    user_permission=user.user_permission
                )
                self.user_dict[usr_obj.user_name] = usr_obj
                logger.info(f'初始化用户 {user.user_name} 成功。')
        self.init_status = True
        logger.info(f"init user list complete. {id(self)}")

    async def create_user(self, user_name: AnyStr, passwd_hash: AnyStr) -> User:
        # 检查是否已存在
        if await UserDBUtils.select_user_by_user_name(user_name):
            raise KahunaException("用户已存在")

        # 信息入库
        #  创建user
        async with postgres_manager.get_session() as session:
            user_database_obj = M_User(
                user_name=user_name,
                create_date=get_beijing_utctime(datetime.now()),
                password_hash=passwd_hash,
                user_role="user",
                user_permission=["member"]
            )
            await UserDBUtils.save_obj(user_database_obj, session=session)
            #  创建userdata
            userdata_database_obj = M_UserData(
                user_name=user_name
            )
            await UserDataDBUtils.save_obj(userdata_database_obj, session=session)

            # 存入dict
            self.user_dict[user_name] = User(user_name=user_name, user_role="user", user_permission=["member"])

            return self.user_dict[user_name]

    async def get_user(self, user_name: AnyStr) -> User | None:
        if not self.init_status:
            await self.init_user_dict()
        return self.user_dict.get(user_name, None)

    async def get_password_hash(self, user_name: AnyStr):
        return await UserDBUtils.select_passwd_hash_by_user_name(user_name)

    async def get_user_data(self, user_name: AnyStr):
        user_data = await UserDataDBUtils.select_user_data_by_user_name(user_name)
        if not user_data:
            raise KahunaException("userdata 不存在")
        return user_data

    async def get_main_character_id(self, user_name: AnyStr):
        main_character_id = await redis_manager.redis.get(f"user_{user_name}:main_character_id")
        if main_character_id:
            return int(main_character_id)
        user_data = await UserDataDBUtils.select_user_data_by_user_name(user_name)
        if not user_data:
            raise KahunaException("用户数据不存在")
        if not user_data.main_character_id:
            raise KahunaException("用户主角色未设置")
        await redis_manager.redis.set(f"user_{user_name}:main_character_id", user_data.main_character_id, ex=60 * 60)
        return user_data.main_character_id

    async def set_main_character(self, user_name: AnyStr, main_character_name: str):
        character = await EveAuthedCharacterDBUtils.select_character_by_character_name(main_character_name)
        if not character:
            raise KahunaException("角色不存在")
        main_character_id = character.character_id
        user_data = await UserDataDBUtils.select_user_data_by_user_name(user_name)
        if not user_data:
            raise KahunaException("用户数据不存在")
        user_data.main_character_id = main_character_id
        await UserDataDBUtils.merge(user_data)
        await redis_manager.redis.set(f"user_{user_name}:main_character_id", main_character_id, ex=60 * 60)

    async def update_same_title_alias_characters(self, character_list: list, main_character_id):
        for character in character_list:
            alias_character = await EveAliasCharacterDBUtils.select_alias_character_by_character_id(character.character_id)
            if not alias_character:
                await EveAliasCharacterDBUtils.save_obj(M_EveAliasCharacter(
                    alias_character_id=character.character_id,
                    main_character_id=main_character_id,
                    character_name=character.name,
                    enabled=False
                ))

    async def get_alias_character_list(self, main_character_id: int):
        alias_character_list = []
        async for alias_character in await EveAliasCharacterDBUtils.select_all_by_main_character_id(main_character_id):
            alias_character_list.append(alias_character)
        return alias_character_list

    def user_exists(self, user_name: AnyStr) -> bool:
        return user_name in self.user_dict.keys()

    # VIP系统挂起
    # @classmethod
    # def add_member_time(cls, qq: int, days: int):
    #     if (user := cls.user_dict.get(qq, None)) is None:
    #         raise KahunaException("用户不存在。")
    #     return user.add_member_time(days)


    async def delete_user(self, user_name: AnyStr):
        async with postgres_manager.get_session() as session:
            # 删除userdata
            await UserDataDBUtils.delete_user_data_by_user_name(user_name, session=session)
            # 删除user
            await UserDBUtils.delete_user_by_user_username(user_name, session=session)
            # 从内存移除
            if user_name in self.user_dict:
                self.user_dict.pop(user_name)

        
    #
    # async def clean_member_time(cls, qq: int) -> User:
    #     if (user := cls.user_dict.get(qq, None)) is None:
    #         raise KahunaException("用户不存在。")
    #     await user.clean_member_time()
    #
    #     return user

    def get_users_list(self):
        return [user for user in self.user_dict.values()]