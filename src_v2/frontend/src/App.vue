<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import smallSideBar from './components/sideBar/smallSideBar.vue'
import { computed } from 'vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

// 定义公开页面列表（不需要认证和主布局）
const publicPages = ['login', 'forbidden', 'characterAuthClose']
const isPublicPage = computed(() => publicPages.includes(route.name as string))

// 主菜单配置 - 使用 computed 响应式地生成菜单项
const menuItems = computed(() => {
  const items: { id: number; icon: string; label: string; active: boolean; route: string }[] = []
  let id_index = 1
  
  // 首页始终显示
  items.push({ id: id_index++, icon: 'House', label: '首页', active: router.currentRoute.value.path === '/home' || router.currentRoute.value.path === '/', route: '/home' })

  // 根据用户角色动态添加菜单项
  const userRoles = authStore.user?.roles || []
  if (userRoles.includes('user')) {
    items.push({ id: id_index++, icon: 'Cpu', label: '工业', active: router.currentRoute.value.path.startsWith('/industry'), route: '/industry' })
    // items.push({ id: id_index++, icon: 'ShoppingBag', label: '公司商城', active: router.currentRoute.value.path === '/corpShop', route: '/corpShop' })
    items.push({ id: id_index++, icon: 'Opportunity', label: '实用工具', active: router.currentRoute.value.path === '/utils', route: '/utils' })
    items.push({ id: id_index++, icon: 'Setting', label: '设置', active: router.currentRoute.value.path.startsWith('/setting'), route: '/setting' })
  }
  if (userRoles.includes('admin')) {
    items.push({ id: id_index++, icon: 'Cpu', label: '管理员', active: router.currentRoute.value.path.startsWith('/admin'), route: '/admin' })
  }
  
  return items
})

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="kahuna-container">
    <!-- 公开页面（登录页、403页面等）不显示主布局 -->
    <router-view v-if="isPublicPage" />
    
    <!-- 主应用布局 - 确保用户信息已加载 -->
    <el-container v-else-if="authStore.isAuthenticated">
      <!-- 左侧窄侧边菜单 -->
      <smallSideBar :menu-items="menuItems" />

      <!-- 主内容区域 -->
      <el-container class="main-container">
        <el-header class="main-header">
          <div class="header-content">
            <h2>Kahuna-System</h2>
            <div class="header-actions">
              
              <!-- 用户信息和退出按钮 -->
              <div class="user-info">
                <el-dropdown @command="handleLogout">
                  <span class="user-dropdown">
                    <el-avatar :size="32">
                      {{ authStore.user?.username?.charAt(0)?.toUpperCase() }}
                    </el-avatar>
                    <span class="username">{{ authStore.user?.username }}</span>
                    <el-icon><ArrowDown /></el-icon>
                  </span>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>
        </el-header>
        
        <el-main class="main-content">
          <div class="main-content-inner">
            <router-view />
          </div>
        </el-main>
        
        <el-footer class="main-footer">
          <span>© 2024 Kahuna Bot. All rights reserved.</span>
        </el-footer>
      </el-container>
    </el-container>
  </div>
</template>

<style scoped>
.main-container {
  margin-left: 60px;
  transition: margin-left 0.3s ease;
  min-height: 98vh;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.kahuna-container {
  height: 100%;
  background-color: #f5f7fa;
  overflow: hidden;
}

/* 主内容区域样式 */
.main-header {
  background: white;
  border-bottom: 1px solid #e1e8ed;
  padding: 0 24px;
  display: flex;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
  flex-shrink: 0;
  height: 64px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-content h2 {
  margin: 0;
  color: #2c3e50;
  font-weight: 600;
  font-size: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.main-content {
  flex: 1;
  padding: 24px;
  background: #f5f7fa;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.main-content-inner {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.content-wrapper {
  background: white;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  height: 100%;
  overflow: auto;
}

.content-wrapper h3 {
  margin: 0 0 16px 0;
  color: #2c3e50;
  font-weight: 600;
}

.content-wrapper p {
  margin: 0;
  color: #64748b;
  line-height: 1.6;
}

.main-footer {
  background: white;
  border-top: 1px solid #e1e8ed;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 14px;
  height: 60px;
  flex-shrink: 0;
}

/* 优化 el-main 的默认样式 */
:deep(.el-main) {
  padding: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 60px !important;
  }
  
  .menu-item {
    width: 50px;
    height: 50px;
  }
  
  .main-header {
    padding: 0 16px;
    height: 56px;
  }
  
  .header-content h2 {
    font-size: 18px;
  }
  
  .main-content {
    padding: 16px;
  }
  
  .main-footer {
    height: 48px;
    font-size: 12px;
  }
}

.user-info {
  margin-left: 16px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-dropdown:hover {
  background-color: #f1f5f9;
}

.username {
  color: #64748b;
  font-size: 14px;
}

/* 优化主内容区域的滚动条样式 */
.main-content-inner {
  scrollbar-width: thin;
  scrollbar-color: #c1c1c1 #f1f1f1;
}

.main-content-inner::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.main-content-inner::-webkit-scrollbar-track {
  background: #f5f7fa;
  border-radius: 4px;
}

.main-content-inner::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.main-content-inner::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
