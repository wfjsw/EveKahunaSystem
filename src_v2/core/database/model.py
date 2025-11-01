from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    BigInteger,
    UUID,
    ARRAY
)
from sqlalchemy.ext.declarative import declarative_base

from .connect_manager import PostgreModel

all_model = []

class User(PostgreModel):
    __tablename__ = 'user'
    user_name = Column(Text, primary_key=True)
    create_date = Column(DateTime)
    password_hash = Column(Text)
    user_role = Column(Text)
    user_permission = Column(ARRAY(Text))
all_model.append(User)

class UserData(PostgreModel):
    __tablename__ = 'user_data'
    user_name = Column(Text, ForeignKey("user.user_name"), primary_key=True)
    user_qq = Column(Integer, index=True)
    main_character_id = Column(Integer, index=True)
all_model.append(UserData)

class InvitCode(PostgreModel):
    __tablename__ = 'invite_code'
    invite_code = Column(Text, primary_key=True)
    user_name = Column(Text, ForeignKey("user.user_name"))
    create_date = Column(DateTime)
    used_date = Column(DateTime)
all_model.append(InvitCode)

class EveAuthedCharacter(PostgreModel):
    __tablename__ = 'eve_authed_character'
    character_id = Column(Integer, primary_key=True)
    owner_user_name = Column(Text, ForeignKey("user.user_name"))
    character_name = Column(Text, index=True)
    birthday = Column(DateTime)
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_time = Column(DateTime)
    corporation_id = Column(Integer)
    director = Column(Boolean)
all_model.append(EveAuthedCharacter)

class EveAliasCharacter(PostgreModel):
    __tablename__ = 'eve_alias_character'
    alias_character_id = Column(Integer, primary_key=True)
    main_character_id = Column(Integer, nullable=False, index=True)
    character_name = Column(Text)
    enabled = Column(Boolean)
all_model.append(EveAliasCharacter)

class EvePublicCharacterInfo(PostgreModel):
    __tablename__ = 'eve_public_character_info'
    character_id = Column(Integer, primary_key=True)
    alliance_id = Column(Integer)
    birthday = Column(DateTime)
    bloodline_id = Column(Integer)
    corporation_id = Column(Integer)
    description = Column(Text)
    faction_id = Column(Integer)
    gender = Column(Text)
    name = Column(Text)
    race_id = Column(Integer)
    security_status = Column(Float)
    title = Column(Text)
all_model.append(EvePublicCharacterInfo)

class EveCorporation(PostgreModel):
    __tablename__ = 'eve_corporation'
    corporation_id = Column(Integer, primary_key=True)
    alliance_id = Column(Integer)
    ceo_id = Column(Integer)
    creator_id = Column(Integer)
    date_founded = Column(DateTime)
    description = Column(Text)
    faction_id = Column(Integer)
    home_station_id = Column(Integer)
    member_count = Column(Integer)
    name = Column(Text)
    shares = Column(Integer)
    tax_rate = Column(Float)
    ticker = Column(Text)
    url = Column(Text)
    war_eligible = Column(Boolean)

    corporation_icon = Column(Text)
all_model.append(EveCorporation)

class IndustryPlan(PostgreModel):
    __tablename__ = 'industry_plan'
    id = Column(Integer, primary_key=True)
all_model.append(IndustryPlan)

class IndustryPlanProdution(PostgreModel):
    __tablename__ = 'industry_plan_item'
    id = Column(Integer, primary_key=True)
all_model.append(IndustryPlanProdution)

class IndustryPlanMatcher(PostgreModel):
    __tablename__ = 'industry_plan_matcher'
    id = Column(Integer, primary_key=True)
all_model.append(IndustryPlanMatcher)