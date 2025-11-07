
import asyncio
from datetime import datetime, timezone, timedelta

from src_v2.core.utils import SingletonMeta
from src_v2.core.utils import KahunaException, get_beijing_utctime

from src_v2.model.EVE.character.character_manager import CharacterManager
from src_v2.core.user.user_manager import UserManager

from src_v2.core.database.kahuna_database_utils_v2 import EveAssetPullMissionDBUtils
from src_v2.core.database.model import EveAssetPullMission as M_EveAssetPullMission

from src_v2.model.EVE.eveesi import eveesi

# kahuna logger
from src_v2.core.log import logger

class AssetManager(metaclass=SingletonMeta):
    async def change_asset_pull_mission_status(self, asset_owner_type: str, asset_owner_id: int, active: bool):
        mission_obj = await EveAssetPullMissionDBUtils.select_mission_by_owner_id_and_owner_type(asset_owner_id, asset_owner_type)
        if not mission_obj:
            raise KahunaException('任务不存在')
        mission_obj.active = active
        await EveAssetPullMissionDBUtils.save_obj(mission_obj)
        
    async def pull_asset_now(self, asset_owner_type: str, asset_owner_id: int):
        mission_obj = await EveAssetPullMissionDBUtils.select_mission_by_owner_id_and_owner_type(asset_owner_id, asset_owner_type)
        if not mission_obj:
            raise KahunaException('任务不存在')
        mission_obj.last_pull_time = get_beijing_utctime(datetime.now())
        await EveAssetPullMissionDBUtils.save_obj(mission_obj)

    async def get_user_asset_pull_mission_list(self, user_name: str) -> list[dict]:
        missions = []
        async for mission in await EveAssetPullMissionDBUtils.select_all_by_user_name(user_name):
            if mission.asset_owner_type == 'character':
                character = await CharacterManager().get_character_by_character_id(mission.asset_owner_id)
                subject_name = character.character_name
            elif mission.asset_owner_type == 'corp':
                corporation = await CharacterManager().get_corporation_data_by_corporation_id(mission.asset_owner_id)
                subject_name = corporation.name
            missions.append({
                'subject_type': mission.asset_owner_type,
                'subject_name': subject_name,
                'subject_id': mission.asset_owner_id,
                'is_active': mission.active,
                'last_pull_time': mission.last_pull_time.replace(tzinfo=timezone(timedelta(hours=+8), 'Shanghai'))
            })
        return missions

    async def create_asset_pull_mission(self, user_name: str, asset_owner_type: str, asset_owner_id: int, active: bool):
        if asset_owner_type == 'character':
            access_character_id = asset_owner_id
        elif asset_owner_type == 'corp':
            main_character_id = await UserManager().get_main_character_id(user_name)
            access_character_id = main_character_id
        mission_obj = await EveAssetPullMissionDBUtils.select_mission_by_owner_id_and_owner_type(asset_owner_id, asset_owner_type)
        if mission_obj:
            raise KahunaException('任务已存在')
        mission_obj = M_EveAssetPullMission(
            user_name = user_name,
            access_character_id = access_character_id,
            asset_owner_type = asset_owner_type,
            asset_owner_id = asset_owner_id,
            active = active,
            last_pull_time = datetime(1980, 1, 1, 0, 0, 0)
        )
        await EveAssetPullMissionDBUtils.save_obj(mission_obj)

    async def save_assets_to_neo4j(self, assets: list):
        for asset in assets:
            

    async def processing_asset_pull_mission(self, mission_obj: M_EveAssetPullMission):
        if mission_obj.asset_owner_type == 'character':
            pull_function = eveesi.characters_character_assets

        elif mission_obj.asset_owner_type == 'corp':
            pull_function = eveesi.corporations_corporation_assets

        access_character = await CharacterManager().get_character_by_character_id(mission_obj.access_character_id)
        assets = await pull_function(access_character.ac_token, mission_obj.asset_owner_id)

        return assets


            