import type { Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export function setupAuthGuards(router: Router): void {
  router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore()
    
    // 检查是否需要认证
    if (to.meta.requiresAuth) {
      // 无条件向服务端校验，防止本地状态被篡改
      const isAuthValid = await authStore.checkAuth()
      if (!isAuthValid) {
        next('/login')
        return
      }
      
      // 检查角色权限
      const roles = to.meta.roles as unknown
      if (Array.isArray(roles) && !roles.includes(authStore.userRole as string)) {
        next('/forbidden')
        return
      }
    }
    
    next()
  })
}