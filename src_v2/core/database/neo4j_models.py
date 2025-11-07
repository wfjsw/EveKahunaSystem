"""
Neo4j 数据模型定义
使用 Python 类定义节点和关系的结构，类似于 SQLAlchemy 的模型定义方式
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# ==================== 节点模型基类 ====================

class NodeModel:
    """节点模型基类"""
    
    @classmethod
    def get_labels(cls) -> List[str]:
        """获取节点标签列表"""
        return [cls.__name__]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        """获取索引定义"""
        return []
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        """获取约束定义"""
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 Neo4j 创建）"""
        result = {}
        for k, v in self.__dict__.items():
            if v is not None:
                # 处理 datetime 对象
                if isinstance(v, datetime):
                    result[k] = v.isoformat()
                else:
                    result[k] = v
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建实例"""
        return cls(**data)


# ==================== Asset 相关节点模型 ====================

@dataclass
class Asset(NodeModel):
    """资产节点"""
    item_id: int  # 唯一标识
    type_id: int
    quantity: int
    is_blueprint_copy: bool = False
    is_singleton: bool = False
    location_flag: Optional[str] = None
    owner_id: Optional[int] = None
    owner_type: Optional[str] = None  # "character" | "corporation"
    created_at: Optional[datetime] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["Asset"]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "item_id", "type": "RANGE"},
            {"property": "type_id", "type": "RANGE"},
            {"property": "owner_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "item_id", "type": "UNIQUE"},
        ]


@dataclass
class Location(NodeModel):
    """位置节点"""
    location_id: int  # 唯一标识
    location_type: str  # "station" | "solar_system" | "structure" | "item"
    name: Optional[str] = None
    solar_system_id: Optional[int] = None
    region_id: Optional[int] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["Location"]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "location_id", "type": "RANGE"},
            {"property": "location_type", "type": "RANGE"},
            {"property": "solar_system_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "location_id", "type": "UNIQUE"},
        ]


@dataclass
class Character(NodeModel):
    """角色节点"""
    character_id: int
    character_name: Optional[str] = None
    corporation_id: Optional[int] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["Character"]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "character_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "character_id", "type": "UNIQUE"},
        ]


@dataclass
class Corporation(NodeModel):
    """公司节点"""
    corporation_id: int
    corporation_name: Optional[str] = None
    ticker: Optional[str] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["Corporation"]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "corporation_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "corporation_id", "type": "UNIQUE"},
        ]


@dataclass
class ItemType(NodeModel):
    """物品类型节点"""
    type_id: int
    type_name: Optional[str] = None
    group_id: Optional[int] = None
    category_id: Optional[int] = None
    volume: Optional[float] = None
    mass: Optional[float] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["ItemType"]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "type_id", "type": "RANGE"},
            {"property": "group_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "type_id", "type": "UNIQUE"},
        ]


@dataclass
class SolarSystem(NodeModel):
    """星系节点"""
    solar_system_id: int
    solar_system_name: Optional[str] = None
    security: Optional[float] = None
    region_id: Optional[int] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["SolarSystem"]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "solar_system_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "solar_system_id", "type": "UNIQUE"},
        ]


# ==================== 工业制造相关节点模型 ====================

@dataclass
class Blueprint(NodeModel):
    """蓝图节点"""
    blueprint_type_id: int
    blueprint_name: Optional[str] = None
    max_production_limit: Optional[int] = None
    research_material_efficiency: Optional[float] = None
    research_time_efficiency: Optional[float] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["Blueprint"]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "blueprint_type_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "blueprint_type_id", "type": "UNIQUE"},
        ]


@dataclass
class Material(NodeModel):
    """材料节点（继承自 ItemType）"""
    type_id: int
    type_name: Optional[str] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["Material", "ItemType"]  # 多标签
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "type_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "type_id", "type": "UNIQUE"},
        ]


@dataclass
class Product(NodeModel):
    """产品节点（继承自 ItemType）"""
    type_id: int
    type_name: Optional[str] = None
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["Product", "ItemType"]  # 多标签
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "type_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "type_id", "type": "UNIQUE"},
        ]


@dataclass
class Activity(NodeModel):
    """制造活动节点"""
    activity_id: int
    activity_name: Optional[str] = None  # 1=制造, 3=研究材料效率等
    
    @classmethod
    def get_labels(cls) -> List[str]:
        return ["Activity"]
    
    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "activity_id", "type": "RANGE"},
        ]
    
    @classmethod
    def get_constraints(cls) -> List[Dict[str, Any]]:
        return [
            {"property": "activity_id", "type": "UNIQUE"},
        ]


# ==================== 关系定义 ====================

class RelationshipType(Enum):
    """关系类型枚举"""
    # Asset 关系
    LOCATED_IN = "LOCATED_IN"
    OWNED_BY = "OWNED_BY"
    IS_TYPE = "IS_TYPE"
    CONTAINS = "CONTAINS"
    IN_SYSTEM = "IN_SYSTEM"
    
    # 工业制造关系
    REQUIRES_MATERIAL = "REQUIRES_MATERIAL"
    PRODUCES = "PRODUCES"
    HAS_ACTIVITY = "HAS_ACTIVITY"
    CAN_BE_MADE_FROM = "CAN_BE_MADE_FROM"


@dataclass
class Relationship:
    """关系定义"""
    type: RelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "properties": self.properties
        }


