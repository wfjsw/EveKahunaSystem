<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import settingSidebar from '../components/sideBar/mainSidebar.vue'

const router = useRouter()

const menuItems = ref([
  { index: 1, label: '角色设置', route: '/setting/characterSetting'},
  { index: 2, label: '工业配置', route: '/setting/industrySetting'},
  { index: 3, label: '账号配置', route: '/setting/accountSetting'}
])

</script>

<template>
  <div class="setting-view">
    <el-aside width="220px" class="setting-aside">
      <settingSidebar :menuItems="menuItems" />
    </el-aside>

    <div class="setting-content">
      <div class="content-panel">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 方法1: 通过CSS变量设置菜单项高度 */
.custom-menu {
  --el-menu-item-height: 50px; /* 设置菜单项高度为60px */
}

.setting-view {
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: #f5f7fa;
  display: flex;
  flex-direction: row;
}

.setting-aside {
  width: 220px;
  min-height: calc(96vh - 60px - 64px);
  height: 100%;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  padding: 16px 0;
  overflow-y: auto;
  overflow-x: hidden;
  flex-shrink: 0;
}

.setting-content {
  flex: 1;
  height: 100%;
  min-height: calc(96vh - 60px - 64px);
  padding: 12px;
  overflow: hidden;
  /* display: flex; */
  /* flex-direction: column; */
  min-width: 0;
}

.content-panel {
  width: 100%;
  min-height: calc(96vh - 60px - 64px - 12px);
  height: 100%;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  padding: 12px;
  overflow-y: auto;
  overflow-x: hidden;
  box-sizing: border-box;
  /* display: flex; */
}

/* 优化滚动条样式 */
.content-panel::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.content-panel::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.content-panel::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.content-panel::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.setting-aside::-webkit-scrollbar {
  width: 6px;
}

.setting-aside::-webkit-scrollbar-track {
  background: #f9fafb;
}

.setting-aside::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.setting-aside::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

</style>