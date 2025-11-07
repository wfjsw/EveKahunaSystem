<script setup lang="ts">
import { ref } from 'vue'
import SidebarLayout from '../components/SidebarLayout.vue'
import settingSidebar from '../components/sideBar/mainSidebar.vue'

const menuItems = ref([
  { index: 1, label: '用户管理', route: '/admin/userManagement'},
  { index: 2, label: '权限管理', route: '/admin/permissionManagement'}
])

</script>

<template>
  <SidebarLayout 
    :aside-width="220" 
    :menu-items="menuItems"
    :sidebar-component="settingSidebar"
  >
    <router-view />
  </SidebarLayout>
</template>