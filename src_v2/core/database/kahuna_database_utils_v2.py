from typing import AnyStr, AsyncGenerator
from sqlalchemy import delete, select, text, func, distinct
from sqlalchemy.dialects.sqlite import insert as insert
from sqlalchemy.orm import aliased
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime, timedelta
import traceback

from .connect_manager import postgres_manager as dbm
from ..log import logger
from . import model


class _AsyncIteratorWrapper:
    """包装异步生成器，自动管理资源"""
    def __init__(self, generator: AsyncGenerator, session):
        self._generator = generator
        self._session = session
        self._closed = False
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self._closed:
            raise StopAsyncIteration
        try:
            return await self._generator.__anext__()
        except StopAsyncIteration:
            await self._cleanup()
            raise
        except GeneratorExit:
            await self._cleanup()
            raise
    
    async def _cleanup(self):
        """清理资源"""
        if not self._closed:
            self._closed = True
            try:
                await self._generator.aclose()
            except Exception:
                pass
            if self._session:
                try:
                    await self._session.close()
                except Exception:
                    pass
    
    async def aclose(self):
        """显式关闭"""
        await self._cleanup()
    
    def __del__(self):
        """析构时确保资源被清理（虽然可能已经关闭）"""
        if not self._closed and self._session:
            # 注意：在 __del__ 中不能使用 await，所以这里只是标记
            # 实际清理由 asyncio 的事件循环处理
            pass


class _CommonUtils:
    cls_model = None

    @staticmethod
    async def _create_result_generator(result, session):
        """创建结果生成器，处理提交和回滚"""
        try:
            for item in result.scalars():
                yield item
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    @classmethod
    async def insert_many(cls, rows_list):
        """异步批量插入多条记录

        :param rows_list: 要插入的数据列表，每项是一个字典
        :return: 结果代理对象"""
        if not cls.cls_model:
            raise Exception("cls_model 未设置，请勿直接使用基类")
        async with dbm.get_session() as session:
            stmt = insert(cls.cls_model).values(rows_list)
            result = await session.execute(stmt)
            return result

    @classmethod
    async def insert_many_or_update_async(cls, rows_list, index_elements):
        """
        异步批量插入或更新记录

        :param rows_list: 要插入的数据列表，每项是一个字典
        :param index_elements: 唯一索引字段列表
        :return: 结果代理对象
        """
        if not cls.cls_model:
            raise Exception("cls_model 未设置，请勿直接使用基类")
        async with dbm.get_session() as session:
            stmt = insert(cls.cls_model).values(rows_list)

            update_dict = {c.name: c for c in stmt.excluded if c.name not in index_elements}

            stmt = stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_=update_dict
            )

            result = await session.execute(stmt)
            return result

    @classmethod
    async def insert_many_ignore_conflict(cls, rows_list, index_elements):
        if not cls.cls_model:
            raise Exception("cls_model 未设置，请勿直接使用基类")
        async with dbm.get_session() as session:
            stmt = insert(cls.cls_model).values(rows_list)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=index_elements
            )
            await session.execute(stmt)

    @classmethod
    async def select_all(cls):
        """返回所有记录的异步迭代器"""
        if not cls.cls_model:
            raise Exception("cls_model is None")
        session = dbm._session_maker()
        stmt = select(cls.cls_model)
        result = await session.execute(stmt)
        async_gen = cls._create_result_generator(result, session)
        return _AsyncIteratorWrapper(async_gen, session)

    @classmethod
    def get_obj(cls):
        if not cls.cls_model:
            raise Exception("cls_model is None")
        return cls.cls_model()

    @classmethod
    async def save_obj(cls, asset_owner_obj, session=None):
        if not session:
            async with dbm.get_session() as session:
                session.add(asset_owner_obj)
        else:
            session.add(asset_owner_obj)

    @classmethod
    async def merge(cls, obj):
        if not cls.cls_model:
            raise Exception("cls_model is None")
        async with dbm.get_session() as session:
            await session.merge(obj)

    @classmethod
    async def delete_all(cls):
        if not cls.cls_model:
            raise Exception("cls_model is None")
        async with dbm.get_session() as session:
            stmt = delete(cls.cls_model)
            await session.execute(stmt)

    @classmethod
    async def delete_obj(cls, obj):
        if not cls.cls_model:
            raise Exception("cls_model is None")
        async with dbm.get_session() as session:
            await session.delete(obj)

class _CommonCacheUtils:
    cls_model = None
    cls_base_model = None

    @classmethod
    async def copy_base_to_cache(cls):
        if cls.cls_model == None or cls.cls_base_model == None:
            raise Exception("cls_model or cls_base_model is None")

        async with dbm.get_session() as session:
            try:
                # 清空cache表
                await session.execute(
                    delete(cls.cls_model)
                )

                # 将元数据表的数据复制到Cache表
                table_name = cls.cls_base_model.__tablename__
                cache_table_name = cls.cls_model.__tablename__
                await session.execute(
                    text(f"INSERT INTO {cache_table_name} SELECT * FROM {table_name}")
                )

                logger.info(f"从 {table_name} 复制到 {cache_table_name} 完成。")
            except Exception as e:
                print(traceback.format_stack())
                logger.error(f"从 {table_name} 复制到 {cache_table_name} 失败。")
                raise

class UserDBUtils(_CommonUtils):
    cls_model = model.User

    @classmethod
    async def select_user_by_user_name(cls, user_name: AnyStr):
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.user_name == user_name)
            result = await session.execute(stmt)
            return result.scalars().first()

    @classmethod
    async def delete_user_by_user_username(cls, user_name: AnyStr, session=None):
        if not session:
            async with dbm.get_session() as session:
                stmt = delete(cls.cls_model).where(cls.cls_model.user_name == user_name)
                await session.execute(stmt)
        else:
            stmt = delete(cls.cls_model).where(cls.cls_model.user_name == user_name)
            await session.execute(stmt)

    @classmethod
    async def select_passwd_hash_by_user_name(cls, user_name: AnyStr):
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model.password_hash).where(cls.cls_model.user_name == user_name)
            result = await session.execute(stmt)
            return result.scalars().first()

class UserDataDBUtils(_CommonUtils):
    cls_model = model.UserData
    @classmethod
    async def select_user_data_by_user_name(cls, user_name: AnyStr):
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.user_name == user_name)
            result = await session.execute(stmt)
            return result.scalars().first()

    @classmethod
    async def delete_user_data_by_user_name(cls, user_name: AnyStr, session=None):
        if not session:
            async with dbm.get_session() as session:
                stmt = delete(cls.cls_model).where(cls.cls_model.user_name == user_name)
                await session.execute(stmt)
        else:
            stmt = delete(cls.cls_model).where(cls.cls_model.user_name == user_name)
            await session.execute(stmt)

class EveAuthedCharacterDBUtils(_CommonUtils):
    cls_model = model.EveAuthedCharacter

    @classmethod
    async def select_all_by_owner_user_name(cls, user_name: AnyStr):
        """根据用户名返回所有角色的异步迭代器"""
        session = dbm._session_maker()
        stmt = select(cls.cls_model).where(cls.cls_model.owner_user_name == user_name)
        result = await session.execute(stmt)
        async_gen = cls._create_result_generator(result, session)
        return _AsyncIteratorWrapper(async_gen, session)

    @classmethod
    async def delete_character_by_character_id(cls, character_id: int):
        async with dbm.get_session() as session:
            stmt = delete(cls.cls_model).where(cls.cls_model.character_id == character_id)
            await session.execute(stmt)

    @classmethod
    async def select_character_by_character_name(cls, character_name: str):
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.character_name == character_name)
            result = await session.execute(stmt)
            return result.scalars().first()

    @classmethod
    async def select_character_by_character_id(cls, character_id: int):
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.character_id == character_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    @classmethod
    async def select_all_characters_by_corporation_id(cls, corporation_id: int):
        """根据公司ID返回所有角色的异步迭代器"""
        session = dbm._session_maker()
        stmt = select(cls.cls_model).where(cls.cls_model.corporation_id == corporation_id)
        result = await session.execute(stmt)
        async_gen = cls._create_result_generator(result, session)
        return _AsyncIteratorWrapper(async_gen, session)

class EvePublicCharacterInfoDBUtils(_CommonUtils):
    cls_model = model.EvePublicCharacterInfo

    @classmethod
    async def select_public_character_info_by_character_id(cls, character_id: int):
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.character_id == character_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    @classmethod
    async def select_public_character_info_by_name(cls, character_name: str):
        """根据角色名称查询角色信息"""
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.name == character_name)
            result = await session.execute(stmt)
            return result.scalars().first()

    @classmethod
    async def select_character_info_by_characterid_with_same_title(cls, character_id: int):
        """根据角色ID返回相同标题的角色信息的异步迭代器"""
        session = dbm._session_maker()
        # 创建别名用于自连接
        alias = aliased(cls.cls_model)
        # 自连接：通过标题匹配，找到与给定character_id具有相同标题的所有角色
        stmt = select(cls.cls_model).join(
            alias, 
            cls.cls_model.title == alias.title
        ).where(alias.character_id == character_id)
        result = await session.execute(stmt)
        async_gen = cls._create_result_generator(result, session)
        return _AsyncIteratorWrapper(async_gen, session)

class EveCorporationDBUtils(_CommonUtils):
    cls_model = model.EveCorporation

    @classmethod
    async def select_corporation_by_corporation_id(cls, corporation_id: int) -> cls_model:
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.corporation_id == corporation_id)
            result = await session.execute(stmt)
            return result.scalars().first()

class EveAliasCharacterDBUtils(_CommonUtils):
    cls_model = model.EveAliasCharacter

    @classmethod
    async def select_alias_character_by_character_id(cls, character_id: int):
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.alias_character_id == character_id)
            result = await session.execute(stmt)
            return result.scalars().first()

    @classmethod
    async def select_all_by_main_character_id(cls, main_character_id: int):
        async with dbm.get_session() as session:
            stmt = select(cls.cls_model).where(cls.cls_model.main_character_id == main_character_id)
            result = await session.execute(stmt)
            async_gen = cls._create_result_generator(result, session)
            return _AsyncIteratorWrapper(async_gen, session)