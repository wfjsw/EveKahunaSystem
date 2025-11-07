import asyncio

AAQQ = 461630479



async def test1():
    # await init_server_service()
    from src_v2.core.database.connect_manager import postgres_manager, redis_manager
    from src_v2.backend.app import init_backend
    from src_v2.model.EVE.eveesi.esi_req_manager import init_esi_manager
    from src_v2.model.EVE.character.character_manager import CharacterManager
    from src_v2.core.user.user_manager import UserManager

    await postgres_manager.init()
    await redis_manager.init()
    await UserManager().init()
    await CharacterManager().init()

    await init_esi_manager()
    await init_backend()
    print(111)

async def test2():
    from src_v2.core.database.connect_manager import postgres_manager, redis_manager, neo4j_manager
    from src_v2.backend.app import init_backend
    from src_v2.model.EVE.eveesi.esi_req_manager import init_esi_manager
    from src_v2.model.EVE.character.character_manager import CharacterManager
    from src_v2.core.user.user_manager import UserManager
    from src_v2.model.EVE.asset.asset_manager import AssetManager
    from src_v2.core.database.kahuna_database_utils_v2 import EveAssetPullMissionDBUtils

    await postgres_manager.init()
    await redis_manager.init()
    await neo4j_manager.init()
    
    await init_esi_manager()
    # await init_backend()


    mission_obj = await EveAssetPullMissionDBUtils.select_mission_by_owner_id_and_owner_type(98446928, 'corp')
    assets = await AssetManager().processing_asset_pull_mission(mission_obj)
    print(111)

async def main():
    # init_server()
    await test2()
    pass

if __name__ == '__main__':
    # asyncio.run(main())
    asyncio.run(main())