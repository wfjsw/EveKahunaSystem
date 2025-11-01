from quart import Quart, request, jsonify, g, Blueprint, redirect
from src_v2.backend.auth import auth_required
from src.service.log_server import logger
import traceback

from src_v2.core.user.user_manager import UserManager
from src_v2.model.EVE.character.character_manager import CharacterManager
from src_v2.core.database.kahuna_database_utils_v2 import EvePublicCharacterInfoDBUtils
from src_v2.core.utils import KahunaException

api_user_bp = Blueprint('api_user', __name__, url_prefix='/api/user')


@api_user_bp.route("/list", methods=["GET"])
@auth_required
async def get_character_list():
    try:
        character_list = await CharacterManager().get_user_all_characters(g.current_user["user_id"])

        character_list_dict = []
        for character in character_list:
            corp_data = await CharacterManager().get_corporation_data_by_corporation_id(character.corporation_id)
            if not corp_data:
                continue
            character_list_dict.append({
                "name": character.character_name,
                "expiresDate": character.expires_time,
                "corpId": character.corporation_id,
                "corpName": corp_data.name
            })
        return jsonify({"data": character_list_dict})
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@api_user_bp.route("/deleteCharacter", methods=["POST"])
@auth_required
async def delete_character():
    try:
        data = await request.get_json()
        character_name = data.get("characterName")
        await CharacterManager().delete_character_by_character_name(character_name, g.current_user["user_id"])
        return jsonify({"message": "角色删除成功"})
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@api_user_bp.route("/getMainCharacter", methods=["GET"])
@auth_required
async def get_main_character():
    try:
        user_id = g.current_user["user_id"]
        main_character_id = await UserManager().get_main_character_id(user_id)
        if main_character_id in CharacterManager().character_dict:
            main_character = CharacterManager().character_dict[main_character_id]
            return jsonify({"mainCharacter": main_character.character_name})
        else:
            raise KahunaException("发生异常，请联系管理员")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_user_bp.route("/setMainCharacter", methods=["POST"])
@auth_required
async def set_main_character():
    user_id = g.current_user["user_id"]
    data = await request.get_json()
    character_name = data.get("characterName")
    try:
        await UserManager().set_main_character(user_id, character_name)

        return jsonify({"message": "主角色设置成功"})
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@api_user_bp.route('/isAliasCharacterSettingAvaliable', methods=['GET'])
@auth_required
async def is_alias_character_setting_avaliable():
    user_id = g.current_user["user_id"]
    try:
        # 获取用户主账号
        main_character_id = await UserManager().get_main_character_id(user_id)
        main_character = await CharacterManager().get_character_by_character_id(main_character_id)

        # 判断用户所在公司是否有绑定总监权限账号
        director_character_id = await CharacterManager().get_director_character_id_of_corporation(main_character.corporation_id)
        if not director_character_id:
            return jsonify({"isAliasCharacterSettingAvaliable": False})
        
        # 否则返回false
        # 有则返回true

        return jsonify({"isAliasCharacterSettingAvaliable": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_user_bp.route('/getSameTitleAliasCharacterList', methods=['POST'])
@auth_required
async def get_same_title_alias_character_list():
    user_id = g.current_user["user_id"]
    try:
        main_character_id = await UserManager().get_main_character_id(user_id)
        main_character = await CharacterManager().get_character_by_character_id(main_character_id)
        await CharacterManager().refresh_all_public_characters_info_of_corporation(CharacterManager().character_dict[main_character_id].ac_token, main_character.corporation_id)

        same_title_character_list = []
        async for character in await EvePublicCharacterInfoDBUtils.select_character_info_by_characterid_with_same_title(main_character_id):
            same_title_character_list.append(character)
        await UserManager().update_same_title_alias_characters(same_title_character_list, main_character_id)
        alias_character_list = await UserManager().get_alias_character_list(main_character_id)
            
        return jsonify([{
            "CharacterId": alias_character.alias_character_id,
            "CharacterName": alias_character.character_name,
            "Enabled": alias_character.enabled
        } for alias_character in alias_character_list])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_user_bp.route('/getAliasCharacterList', methods=['GET'])
@auth_required
async def get_alias_character_list():
    user_id = g.current_user["user_id"]
    main_character_id = await UserManager().get_main_character_id(user_id)
    try:
        alias_character_list = await UserManager().get_alias_character_list(main_character_id)
        return jsonify([{
            "CharacterId": alias_character.alias_character_id,
            "CharacterName": alias_character.character_name,
            "Enabled": alias_character.enabled
        } for alias_character in alias_character_list])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
