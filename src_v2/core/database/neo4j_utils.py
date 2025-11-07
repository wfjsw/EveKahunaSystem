"""
Neo4j CRUD 操作工具类
"""
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from .neo4j_models import NodeModel, RelationshipType
from .connect_manager import neo4j_manager
from ..log import logger

if TYPE_CHECKING:
    from .neo4j_models import Asset


class Neo4jAssetUtils:
    """Asset 相关的 CRUD 操作"""
    
    @staticmethod
    async def create_asset(asset: 'Asset') -> bool:
        """创建资产节点"""
        async with neo4j_manager.get_transaction() as tx:
            query = """
            CREATE (a:Asset {
                item_id: $item_id,
                type_id: $type_id,
                quantity: $quantity,
                is_blueprint_copy: $is_blueprint_copy,
                is_singleton: $is_singleton,
                location_flag: $location_flag,
                owner_id: $owner_id,
                owner_type: $owner_type,
                created_at: datetime()
            })
            RETURN a
            """
            
            result = await tx.run(query, asset.to_dict())
            record = await result.single()
            return record is not None
    
    @staticmethod
    async def create_asset_with_relationships(
        asset: 'Asset',
        location_id: int,
        owner_id: int,
        owner_type: str
    ) -> bool:
        """创建资产节点并建立关系"""
        async with neo4j_manager.get_transaction() as tx:
            # 创建或获取 Location
            location_query = """
            MERGE (loc:Location {location_id: $location_id})
            RETURN loc
            """
            
            # 创建或获取 Owner
            owner_label = "Character" if owner_type == "character" else "Corporation"
            owner_prop = "character_id" if owner_type == "character" else "corporation_id"
            
            # 创建 Asset 并建立关系
            asset_query = f"""
            MERGE (a:Asset {{item_id: $item_id}})
            SET a.type_id = $type_id,
                a.quantity = $quantity,
                a.is_blueprint_copy = $is_blueprint_copy,
                a.is_singleton = $is_singleton,
                a.location_flag = $location_flag,
                a.owner_id = $owner_id,
                a.owner_type = $owner_type,
                a.created_at = datetime()
            
            WITH a
            MERGE (loc:Location {{location_id: $location_id}})
            MERGE (a)-[:LOCATED_IN {{location_flag: $location_flag}}]->(loc)
            
            WITH a
            MERGE (owner:{owner_label} {{{owner_prop}: $owner_id}})
            MERGE (a)-[:OWNED_BY {{owner_type: $owner_type}}]->(owner)
            
            WITH a
            MERGE (it:ItemType {{type_id: $type_id}})
            MERGE (a)-[:IS_TYPE]->(it)
            
            RETURN a
            """
            
            params = asset.to_dict()
            params["location_id"] = location_id
            params["owner_id"] = owner_id
            params["owner_type"] = owner_type
            
            result = await tx.run(asset_query, params)
            record = await result.single()
            return record is not None
    
    @staticmethod
    async def get_asset_hierarchy(owner_id: int, owner_type: str, max_depth: int = 5) -> List[Dict]:
        """获取资产层级结构"""
        async with neo4j_manager.get_session() as session:
            owner_label = "Character" if owner_type == "character" else "Corporation"
            owner_prop = "character_id" if owner_type == "character" else "corporation_id"
            
            query = f"""
            MATCH path = (owner:{owner_label} {{{owner_prop}: $owner_id}})
                  <-[:OWNED_BY]-(asset:Asset)
                  -[:LOCATED_IN*0..{max_depth}]->(loc:Location)
            RETURN path
            ORDER BY length(path) DESC
            LIMIT 100
            """
            
            result = await session.run(query, {"owner_id": owner_id})
            paths = []
            async for record in result:
                paths.append(record["path"])
            return paths
    
    @staticmethod
    async def batch_create_assets(assets: List['Asset'], location_ids: List[int], 
                                  owner_ids: List[int], owner_types: List[str]):
        """批量创建资产"""
        async with neo4j_manager.get_transaction() as tx:
            query = """
            UNWIND $assets AS asset_data
            MERGE (a:Asset {item_id: asset_data.item_id})
            SET a.type_id = asset_data.type_id,
                a.quantity = asset_data.quantity,
                a.is_blueprint_copy = asset_data.is_blueprint_copy,
                a.is_singleton = asset_data.is_singleton,
                a.location_flag = asset_data.location_flag,
                a.owner_id = asset_data.owner_id,
                a.owner_type = asset_data.owner_type,
                a.created_at = datetime()
            
            WITH a, asset_data
            MERGE (loc:Location {location_id: asset_data.location_id})
            MERGE (a)-[:LOCATED_IN]->(loc)
            
            WITH a, asset_data
            MERGE (it:ItemType {type_id: asset_data.type_id})
            MERGE (a)-[:IS_TYPE]->(it)
            """
            
            assets_data = [
                {**asset.to_dict(), "location_id": loc_id, "owner_id": owner_id, "owner_type": owner_type}
                for asset, loc_id, owner_id, owner_type in zip(assets, location_ids, owner_ids, owner_types)
            ]
            
            await tx.run(query, {"assets": assets_data})


class Neo4jIndustryUtils:
    """工业制造相关的 CRUD 操作"""
    
    @staticmethod
    async def create_blueprint_material_relationship(
        blueprint_type_id: int,
        material_type_id: int,
        quantity: int,
        activity_id: int = 1
    ) -> bool:
        """创建蓝图-材料关系"""
        async with neo4j_manager.get_transaction() as tx:
            query = """
            MERGE (bp:Blueprint {blueprint_type_id: $blueprint_type_id})
            MERGE (mat:Material:ItemType {type_id: $material_type_id})
            MERGE (bp)-[r:REQUIRES_MATERIAL {
                activity_id: $activity_id,
                quantity: $quantity
            }]->(mat)
            RETURN r
            """
            
            result = await tx.run(query, {
                "blueprint_type_id": blueprint_type_id,
                "material_type_id": material_type_id,
                "quantity": quantity,
                "activity_id": activity_id
            })
            record = await result.single()
            return record is not None
    
    @staticmethod
    async def create_blueprint_product_relationship(
        blueprint_type_id: int,
        product_type_id: int,
        quantity: int,
        activity_id: int = 1,
        probability: float = 1.0
    ) -> bool:
        """创建蓝图-产品关系"""
        async with neo4j_manager.get_transaction() as tx:
            query = """
            MERGE (bp:Blueprint {blueprint_type_id: $blueprint_type_id})
            MERGE (prod:Product:ItemType {type_id: $product_type_id})
            MERGE (bp)-[r:PRODUCES {
                activity_id: $activity_id,
                quantity: $quantity,
                probability: $probability
            }]->(prod)
            RETURN r
            """
            
            result = await tx.run(query, {
                "blueprint_type_id": blueprint_type_id,
                "product_type_id": product_type_id,
                "quantity": quantity,
                "activity_id": activity_id,
                "probability": probability
            })
            record = await result.single()
            return record is not None
    
    @staticmethod
    async def get_manufacturing_chain(product_type_id: int, max_depth: int = 10) -> List[Dict]:
        """获取制造链（从产品追溯到所有原材料）"""
        async with neo4j_manager.get_session() as session:
            query = f"""
            MATCH path = (prod:Product:ItemType {{type_id: $product_type_id}})
                  <-[:PRODUCES]-(bp:Blueprint)
                  -[:REQUIRES_MATERIAL*0..{max_depth}]->(mat:Material:ItemType)
            RETURN path
            ORDER BY length(path)
            LIMIT 100
            """
            
            result = await session.run(query, {"product_type_id": product_type_id})
            paths = []
            async for record in result:
                paths.append(record["path"])
            return paths
    
    @staticmethod
    async def get_blueprint_tree(blueprint_type_id: int, max_depth: int = 10) -> Dict[str, Any]:
        """获取蓝图依赖树（返回 ECharts 格式）"""
        async with neo4j_manager.get_session() as session:
            query = f"""
            MATCH path = (bp:Blueprint {{blueprint_type_id: $blueprint_type_id}})
                  -[:REQUIRES_MATERIAL*0..{max_depth}]->(mat:Material:ItemType)
            RETURN path
            LIMIT 100
            """
            
            result = await session.run(query, {"blueprint_type_id": blueprint_type_id})
            
            nodes = []
            links = []
            node_ids = set()
            
            async for record in result:
                path = record["path"]
                # 处理路径中的节点和关系
                for i, node in enumerate(path.nodes):
                    node_id = str(node.get("blueprint_type_id") or node.get("type_id"))
                    if node_id not in node_ids:
                        labels = list(node.labels)
                        if "Blueprint" in labels:
                            nodes.append({
                                "id": node_id,
                                "name": node.get("blueprint_name") or f"Blueprint_{node_id}",
                                "category": "blueprint"
                            })
                        elif "Material" in labels or "ItemType" in labels:
                            nodes.append({
                                "id": node_id,
                                "name": node.get("type_name") or f"Material_{node_id}",
                                "category": "material"
                            })
                        node_ids.add(node_id)
                
                # 处理关系
                for relationship in path.relationships:
                    start_node = relationship.start_node
                    end_node = relationship.end_node
                    start_id = str(start_node.get("blueprint_type_id") or start_node.get("type_id"))
                    end_id = str(end_node.get("blueprint_type_id") or end_node.get("type_id"))
                    
                    links.append({
                        "source": start_id,
                        "target": end_id,
                        "value": relationship.get("quantity", 1)
                    })
            
            return {
                "nodes": nodes,
                "links": links,
                "categories": [
                    {"name": "blueprint"},
                    {"name": "material"},
                    {"name": "product"}
                ]
            }

