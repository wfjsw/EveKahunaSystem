"""
Neo4j 模型管理器 - 负责创建索引、约束和管理模型
"""
from typing import List, Type
from .neo4j_models import NodeModel
from .connect_manager import neo4j_manager
from ..log import logger


class Neo4jModelManager:
    """Neo4j 模型管理器"""
    
    def __init__(self):
        self.registered_models: List[Type[NodeModel]] = []
    
    def register_model(self, model_class: Type[NodeModel]):
        """注册模型类"""
        if model_class not in self.registered_models:
            self.registered_models.append(model_class)
            logger.info(f"注册 Neo4j 模型: {model_class.__name__}")
    
    def register_models(self, *model_classes: Type[NodeModel]):
        """批量注册模型"""
        for model_class in model_classes:
            self.register_model(model_class)
    
    async def create_indexes(self, constraint_properties_map: dict = None):
        """创建所有模型的索引
        
        Args:
            constraint_properties_map: 字典，key 为模型类名，value 为已有约束的属性集合
        """
        if constraint_properties_map is None:
            constraint_properties_map = {}
        
        async with neo4j_manager.get_transaction() as tx:
            for model_class in self.registered_models:
                constraint_properties = constraint_properties_map.get(model_class.__name__, set())
                await self._create_model_indexes(tx, model_class, constraint_properties)
    
    async def _create_model_indexes(self, tx, model_class: Type[NodeModel], constraint_properties: set = None):
        """创建单个模型的索引
        
        Args:
            tx: 事务对象
            model_class: 模型类
            constraint_properties: 已有约束的属性集合（这些属性不需要创建索引，因为约束会自动创建）
        """
        if constraint_properties is None:
            constraint_properties = set()
        
        labels_list = model_class.get_labels()
        # Neo4j 索引语法不支持多标签，使用第一个标签（主标签）
        primary_label = labels_list[0] if labels_list else model_class.__name__
        indexes = model_class.get_indexes()
        
        for index_def in indexes:
            property_name = index_def["property"]
            
            # 如果该属性已有约束，跳过创建索引（约束会自动创建索引）
            if property_name in constraint_properties:
                logger.info(f"跳过创建索引 {primary_label}.{property_name}（已有约束）")
                continue
            
            index_type = index_def.get("type", "RANGE")
            
            # 创建索引名称（使用主标签）
            index_name = f"{primary_label.lower()}_{property_name}_index"
            
            # 创建索引（只使用主标签）
            query = f"""
            CREATE INDEX {index_name} IF NOT EXISTS
            FOR (n:{primary_label})
            ON (n.{property_name})
            """
            
            try:
                await tx.run(query)
                logger.info(f"创建索引: {index_name} 在 {primary_label}.{property_name}")
            except Exception as e:
                logger.warning(f"创建索引失败 {index_name}: {e}")
    
    async def create_constraints(self):
        """创建所有模型的约束
        
        Returns:
            dict: 字典，key 为模型类名，value 为已创建约束的属性集合
        """
        constraint_properties_map = {}
        async with neo4j_manager.get_transaction() as tx:
            for model_class in self.registered_models:
                constraint_properties = await self._create_model_constraints(tx, model_class)
                constraint_properties_map[model_class.__name__] = constraint_properties
        return constraint_properties_map
    
    async def _create_model_constraints(self, tx, model_class: Type[NodeModel]):
        """创建单个模型的约束
        
        Returns:
            set: 已创建约束的属性集合
        """
        labels_list = model_class.get_labels()
        # Neo4j 约束语法不支持多标签，使用第一个标签（主标签）
        primary_label = labels_list[0] if labels_list else model_class.__name__
        constraints = model_class.get_constraints()
        constraint_properties = set()
        
        for constraint_def in constraints:
            property_name = constraint_def["property"]
            constraint_type = constraint_def.get("type", "UNIQUE")
            
            if constraint_type == "UNIQUE":
                constraint_name = f"{primary_label.lower()}_{property_name}_unique"
                
                # 先尝试删除可能存在的同名索引（如果存在）
                # 因为唯一约束会自动创建索引，如果已存在索引会冲突
                # 使用 IF EXISTS 避免错误
                possible_index_name = f"{primary_label.lower()}_{property_name}_index"
                try:
                    drop_index_query = f"DROP INDEX {possible_index_name} IF EXISTS"
                    await tx.run(drop_index_query)
                    logger.debug(f"尝试删除可能冲突的索引: {possible_index_name}")
                except Exception as e:
                    logger.debug(f"删除索引时出错（可忽略）: {e}")
                
                query = f"""
                CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                FOR (n:{primary_label})
                REQUIRE n.{property_name} IS UNIQUE
                """
                
                try:
                    await tx.run(query)
                    constraint_properties.add(property_name)
                    logger.info(f"创建唯一约束: {constraint_name} 在 {primary_label}.{property_name}")
                except Exception as e:
                    # 如果创建约束失败，可能是因为索引冲突，尝试更彻底的清理
                    error_msg = str(e)
                    if "index" in error_msg.lower() or "IndexAlreadyExists" in error_msg:
                        logger.warning(f"创建约束失败，尝试清理冲突的索引: {error_msg}")
                        # 尝试查找并删除所有相关索引
                        try:
                            show_indexes_query = "SHOW INDEXES"
                            index_result = await tx.run(show_indexes_query)
                            async for record in index_result:
                                index_name = record.get("name")
                                index_properties = record.get("properties", [])
                                # 检查索引是否针对相同的属性和标签
                                if index_name and index_properties:
                                    if property_name in index_properties:
                                        await tx.run(f"DROP INDEX {index_name} IF EXISTS")
                                        logger.info(f"删除冲突的索引: {index_name}")
                            # 重试创建约束
                            await tx.run(query)
                            constraint_properties.add(property_name)
                            logger.info(f"创建唯一约束成功（重试）: {constraint_name}")
                        except Exception as retry_error:
                            logger.warning(f"创建约束失败（重试后）: {retry_error}")
                    else:
                        logger.warning(f"创建约束失败 {constraint_name}: {e}")
        
        return constraint_properties
    
    async def drop_all_indexes(self):
        """删除所有索引（谨慎使用）"""
        async with neo4j_manager.get_session() as session:
            query = "SHOW INDEXES"
            result = await session.run(query)
            
            indexes = []
            async for record in result:
                indexes.append(record["name"])
            
            async with neo4j_manager.get_transaction() as tx:
                for index_name in indexes:
                    try:
                        await tx.run(f"DROP INDEX {index_name} IF EXISTS")
                        logger.info(f"删除索引: {index_name}")
                    except Exception as e:
                        logger.warning(f"删除索引失败 {index_name}: {e}")
    
    async def drop_all_constraints(self):
        """删除所有约束（谨慎使用）"""
        async with neo4j_manager.get_session() as session:
            query = "SHOW CONSTRAINTS"
            result = await session.run(query)
            
            constraints = []
            async for record in result:
                constraints.append(record["name"])
            
            async with neo4j_manager.get_transaction() as tx:
                for constraint_name in constraints:
                    try:
                        await tx.run(f"DROP CONSTRAINT {constraint_name} IF EXISTS")
                        logger.info(f"删除约束: {constraint_name}")
                    except Exception as e:
                        logger.warning(f"删除约束失败 {constraint_name}: {e}")
    
    async def init_schema(self):
        """初始化数据库模式（创建所有索引和约束）
        
        注意：先创建约束（约束会自动创建索引），然后只为没有约束的属性创建索引
        """
        logger.info("开始初始化 Neo4j 数据库模式...")
        
        # 先创建约束（约束会自动创建索引）
        constraint_properties_map = await self.create_constraints()
        
        # 然后只为没有约束的属性创建索引
        await self.create_indexes(constraint_properties_map)
        
        logger.info("Neo4j 数据库模式初始化完成")


# 全局模型管理器实例
neo4j_model_manager = Neo4jModelManager()

# 注册所有模型
from .neo4j_models import (
    Asset, Location, Character, Corporation, ItemType, SolarSystem,
    Blueprint, Material, Product, Activity
)

neo4j_model_manager.register_models(
    Asset, Location, Character, Corporation, ItemType, SolarSystem,
    Blueprint, Material, Product, Activity
)


