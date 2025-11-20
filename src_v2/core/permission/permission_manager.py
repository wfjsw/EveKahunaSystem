from ..database.kahuna_database_utils_v2 import (
    RolesDBUtils,
    PermissionsDBUtils,
    UserRolesDBUtils,
    RolePermissionsDBUtils,
    RoleHierarchyDBUtils,
    UserPermissionsDBUtils,
    UserDBUtils
)
from ..database.connect_manager import postgres_manager as dbm, redis_manager as rdm
from ..log import logger
from ..database.model import (
    Roles as M_Roles,
    Permissions as M_Permissions,
    UserRoles as M_UserRoles,
    RolePermissions as M_RolePermissions,
    RoleHierarchy as M_RoleHierarchy,
    UserPermissions as M_UserPermissions
)

class PermissionManager():
    async def create_role(self, role_name, parent_role_id: int = None, role_description: str = None):
        role_obj = await RolesDBUtils.select_role_by_role_name(role_name)
        if role_obj:
            logger.warning(f"Role {role_name} already exists")
        role_obj = M_Roles(
            role_name=role_name,
            role_description=role_description
        )
        await RolesDBUtils.merge(role_obj)
        role_obj = await RolesDBUtils.select_role_by_role_name(role_name)

        return role_obj

    async def delete_role(self, role_name: str, include_children: bool = False):
        """删除角色，支持级联删除子角色树
        
        方案2：递归搜索后集中删除
        1. 递归收集所有需要删除的角色（包括子角色）
        2. 在一个事务中批量删除所有相关数据
        
        Args:
            role_name: 要删除的角色名称
            include_children: 是否级联删除子角色，如果为False且角色有子角色则抛出异常
        """
        # 检查角色是否存在
        role_obj = await RolesDBUtils.select_role_by_role_name(role_name)
        if not role_obj:
            raise ValueError(f"Role {role_name} does not exist")
        
        # 递归收集所有需要删除的角色
        async def collect_all_children(role_name: str, collected: set) -> None:
            """递归收集所有子角色"""
            if role_name in collected:
                return  # 避免循环引用
            
            collected.add(role_name)
            
            # 收集所有子角色
            async for relationship in await RoleHierarchyDBUtils.select_all_by_parent_role_name(role_name):
                child_name = relationship.child_role_name
                if child_name not in collected:
                    await collect_all_children(child_name, collected)
        
        # 收集需要删除的所有角色
        roles_to_delete = set()
        if include_children:
            await collect_all_children(role_name, roles_to_delete)
        else:
            # 检查是否有子角色
            has_children = False
            async for relationship in await RoleHierarchyDBUtils.select_all_by_parent_role_name(role_name):
                has_children = True
                break
            if has_children:
                raise ValueError(f"Role {role_name} has children, cannot delete. Set include_children=True to delete the entire tree.")
            roles_to_delete.add(role_name)
        
        # 在一个事务中批量删除所有相关数据
        roles_list = list(roles_to_delete)
        if not roles_list:
            return
        
        # 收集所有需要删除的关系对
        # 包括：这些角色作为父角色的所有关系 + 这些角色作为子角色的所有关系
        hierarchy_pairs_to_delete = []
        pairs_set = set()  # 使用集合避免重复
        
        for role in roles_list:
            # 收集作为父角色的关系
            async for relationship in await RoleHierarchyDBUtils.select_all_by_parent_role_name(role):
                pair = (relationship.parent_role_name, relationship.child_role_name)
                if pair not in pairs_set:
                    pairs_set.add(pair)
                    hierarchy_pairs_to_delete.append([relationship.parent_role_name, relationship.child_role_name])
            
            # 收集作为子角色的关系
            async for relationship in await RoleHierarchyDBUtils.select_all_by_child_role_name(role):
                pair = (relationship.parent_role_name, relationship.child_role_name)
                if pair not in pairs_set:
                    pairs_set.add(pair)
                    hierarchy_pairs_to_delete.append([relationship.parent_role_name, relationship.child_role_name])
        
        async with dbm.get_session() as session:
            try:
                # 1. 先删除所有相关的 RoleHierarchy 记录（特定的关系对）
                if hierarchy_pairs_to_delete:
                    await RoleHierarchyDBUtils.delete_hierarchy_by_role_names(hierarchy_pairs_to_delete, session=session)
                
                # 2. 删除相关的 RolePermissions
                await RolePermissionsDBUtils.delete_role_permissions_by_role_names(roles_list, session=session)
                
                # 3. 删除相关的 UserRoles
                # 删除redis中的用户角色
                async for user_role_obj in await UserRolesDBUtils.select_user_roles_by_role_name(role_name):
                    await rdm.redis.delete(f"l:user:roles:{user_role_obj.user_name}")
                await UserRolesDBUtils.delete_user_roles_by_role_names(roles_list, session=session)
                
                # 4. 最后删除所有角色
                await RolesDBUtils.delete_roles_by_role_names(roles_list, session=session)
                
                # 事务会自动在上下文管理器退出时提交
            except Exception as e:
                # 事务会自动在异常时回滚
                raise ValueError(f"Failed to delete role {role_name}: {str(e)}") from e

    async def create_permission(self, permission_name: str, permission_description: str):
        permission_obj = await PermissionsDBUtils.select_permission_by_permission_name(permission_name)
        if permission_obj:
            raise ValueError(f"Permission {permission_name} already exists")
        permission_obj = M_Permissions(
            permission_name=permission_name,
            permission_description=permission_description
        )
        await PermissionsDBUtils.save_obj(permission_obj)
        permission_obj = await PermissionsDBUtils.select_permission_by_permission_name(permission_name)
        return permission_obj
    
    async def delete_permission(self, permission_name: str, force: bool = False):
        # 檢查user_pemrmission
        user_permission_obj = await UserPermissionsDBUtils.select_user_permissions_by_permission_name(permission_name)
        if user_permission_obj:
            if not force:
                raise ValueError(f"Permission {permission_name} is assigned to user, cannot delete")
            await UserPermissionsDBUtils.delete_user_permissions_by_permission_name(permission_name)
        # 檢查role_permission
        role_permission_obj = await RolePermissionsDBUtils.select_role_permissions_by_permission_name(permission_name)
        if role_permission_obj:
            if not force:
                raise ValueError(f"Permission {permission_name} is assigned to role, cannot delete")
            await RolePermissionsDBUtils.delete_role_permissions_by_permission_name(permission_name)
        # 檢查permission
        permission_obj = await PermissionsDBUtils.select_permission_by_permission_name(permission_name)
        if permission_obj:
            await PermissionsDBUtils.delete_obj(permission_obj)
        else:
            raise ValueError(f"Permission {permission_name} does not exist")

    async def add_permissions_to_role(self, role_name: str, permission_name: str):
        role_obj = await RolesDBUtils.select_role_by_role_name(role_name)
        if not role_obj:
            raise ValueError(f"Role {role_name} does not exist")
        permission_obj = await PermissionsDBUtils.select_permission_by_permission_name(permission_name)
        if not permission_obj:
            raise ValueError(f"Permission {permission_name} does not exist")
        role_permission = await RolePermissionsDBUtils.select_role_permission_by_role_name_and_permission_name(role_name, permission_name)
        if role_permission:
            raise ValueError(f"Role {role_name} already has permission {permission_name}")
        await RolePermissionsDBUtils.save_obj(M_RolePermissions(
            role_name=role_name,
            permission_name=permission_name))

    async def remove_permissions_from_role(self, role_name: str, permission_name: str):
        role_permission_obj = await RolePermissionsDBUtils.select_role_permission_by_role_name_and_permission_name(role_name, permission_name)
        if not role_permission_obj:
            raise ValueError(f"Role {role_name} does not have permission {permission_name}")
        await RolePermissionsDBUtils.delete_obj(role_permission_obj)

    async def add_role_to_user(self, user_name: str, role_name: str):
        user_obj = await UserDBUtils.select_user_by_user_name(user_name)
        if not user_obj:
            raise ValueError(f"User {user_name} does not exist")
        role_obj = await RolesDBUtils.select_role_by_role_name(role_name)
        if not role_obj:
            raise ValueError(f"Role {role_name} does not exist")
        user_role = await UserRolesDBUtils.select_user_role_by_user_name_and_role_name(user_name, role_name)
        if user_role:
            raise ValueError(f"User {user_name} already has role {role_name}")
        await UserRolesDBUtils.save_obj(M_UserRoles(
            user_name=user_name,
            role_name=role_name))

    async def remove_role_from_user(self, user_name: str, role_name: str):
        user_role_obj = await UserRolesDBUtils.select_user_role_by_user_name_and_role_name(user_name, role_name)
        if not user_role_obj:
            raise ValueError(f"User {user_name} does not have role {role_name}")
        await UserRolesDBUtils.delete_obj(user_role_obj)

    async def get_role_permissions(self, role_name: str):
        role_permission_obj = await RolePermissionsDBUtils.select_role_permissions_by_role_name(role_name)
        permissions = []
        async for permission_obj in role_permission_obj:
            permissions.append(permission_obj.permission_name)
        return permissions

    async def get_user_roles(self, user_name: str):
        user_role_obj = await UserRolesDBUtils.select_user_roles_by_user_name(user_name)
        roles = []
        async for role_obj in user_role_obj:
            roles.append(role_obj.role_name)
        return roles

    async def get_user_permissions(self, user_name: str):
        user_permission_obj = await UserPermissionsDBUtils.select_user_permissions_by_user_name(user_name)
        permissions = []
        async for permission_obj in user_permission_obj:
            permissions.append(permission_obj.permission_name)
        return permissions

    async def get_permission_usage(self, permission_name: str):
        """获取权限的使用情况（被哪些用户和角色使用）
        
        Args:
            permission_name: 权限名称
            
        Returns:
            dict: 包含 users 和 roles 列表的字典
        """
        users = []
        roles = []
        
        # 查询所有使用该权限的用户
        async for user_permission in await UserPermissionsDBUtils.select_all():
            if user_permission.permission_name == permission_name:
                users.append(user_permission.user_name)
        
        # 查询所有使用该权限的角色
        async for role_permission in await RolePermissionsDBUtils.select_all():
            if role_permission.permission_name == permission_name:
                roles.append(role_permission.role_name)
        
        return {
            "users": list(set(users)) if users else [],
            "roles": list(set(roles)) if roles else [],
            "hasUsage": len(users) > 0 or len(roles) > 0
        }

    async def get_parent_roles(self, role_name: str):
        role_hierarchy_obj = await RoleHierarchyDBUtils.select_parent_roles_by_role_name(role_name)
        parent_roles = []
        async for hierarchy_obj in role_hierarchy_obj:
            parent_roles.append(hierarchy_obj.parent_role_name)
        return parent_roles

    async def get_child_roles(self, role_name: str):
        role_hierarchy_obj = await RoleHierarchyDBUtils.select_child_roles_by_role_name(role_name)
        child_roles = []
        async for hierarchy_obj in role_hierarchy_obj:
            child_roles.append(hierarchy_obj.child_role_name)
        return child_roles

    async def get_all_descendant_roles(self, role_name: str):
        """递归获取角色的所有子角色（包括子角色的子角色）
        
        Args:
            role_name: 角色名称
            
        Returns:
            list[str]: 所有后代角色的列表
        """
        collected = set()
        
        async def collect_all_children(role_name: str, collected: set) -> None:
            """递归收集所有子角色"""
            if role_name in collected:
                return  # 避免循环引用
            
            collected.add(role_name)
            
            # 收集所有子角色
            async for relationship in await RoleHierarchyDBUtils.select_all_by_parent_role_name(role_name):
                child_name = relationship.child_role_name
                if child_name not in collected:
                    await collect_all_children(child_name, collected)
        
        await collect_all_children(role_name, collected)
        # 移除自身，只返回子角色
        collected.discard(role_name)
        return list(collected)

    async def delete_role_hierarchys(self, hierarchy_pairs: list[list[str]]):
        await RoleHierarchyDBUtils.delete_hierarchy_by_role_names(hierarchy_pairs)

    async def init_base_roles(self):
        await self.create_role('admin', role_description='管理员')
        await self.create_role('user', role_description='用户')
        await self.create_role('guest', role_description='访客')

        # 会员等级
        await self.create_role('vip_alpha', role_description='alpha')
        await self.create_role('vip_omega', role_description='omega')

permission_manager = PermissionManager()