<script setup lang="ts">
import { ref, computed } from 'vue'
import { useHelpStore } from '@/stores/help'

const helpStore = useHelpStore()

// 目录数据结构
interface HelpSection {
  id: string
  title: string
  children?: HelpSection[]
  content?: string
}

// 示例目录结构（等待用户填充内容）
const helpSections = ref<HelpSection[]>([
  {
    id: 'intro',
    title: '系统介绍',
    children: [
      { id: 'intro-overview', title: '系统概述', content: '系统概述内容待填充...' },
      { id: 'intro-features', title: '核心功能', content: '核心功能内容待填充...' }
    ]
  },
  {
    id: 'getting-started',
    title: '快速开始',
    children: [
      { id: 'getting-started-install', title: '安装配置', content: '安装配置内容待填充...' },
      { id: 'getting-started-first-use', title: '首次使用', content: '首次使用内容待填充...' }
    ]
  },
  {
    id: 'features',
    title: '功能说明',
    children: [
      { id: 'features-industry', title: '工业规划', content: '工业规划功能说明待填充...' },
      { id: 'features-market', title: '市场分析', content: '市场分析功能说明待填充...' }
    ]
  }
])

// 当前选中的目录项
const activeSectionId = ref<string>(helpSections.value[0]?.id || '')
const activeSubSectionId = ref<string>(helpSections.value[0]?.children?.[0]?.id || '')

// 当前显示的内容
const currentContent = computed(() => {
  if (activeSubSectionId.value) {
    // 查找二级目录的内容
    for (const section of helpSections.value) {
      if (section.children) {
        const subSection = section.children.find(child => child.id === activeSubSectionId.value)
        if (subSection) {
          return subSection.content || '内容待填充...'
        }
      }
    }
  }
  // 如果没有二级目录，查找一级目录的内容
  const section = helpSections.value.find(s => s.id === activeSectionId.value)
  return section?.content || '内容待填充...'
})

// 处理一级目录点击
const handleSectionClick = (sectionId: string) => {
  activeSectionId.value = sectionId
  const section = helpSections.value.find(s => s.id === sectionId)
  if (section?.children && section.children.length > 0) {
    activeSubSectionId.value = section.children[0].id
  } else {
    activeSubSectionId.value = ''
  }
}

// 处理二级目录点击
const handleSubSectionClick = (subSectionId: string) => {
  activeSubSectionId.value = subSectionId
}
</script>

<template>
  <el-drawer
    v-model="helpStore.isOpen"
    title="使用说明"
    :size="800"
    direction="rtl"
    :before-close="helpStore.closeHelp"
  >
    <div class="help-drawer-container">
      <!-- 左侧目录导航 -->
      <div class="help-sidebar">
        <el-scrollbar>
          <el-menu
            :default-active="activeSubSectionId || activeSectionId"
            class="help-menu"
            @select="handleSubSectionClick"
            :default-openeds="[activeSectionId]"
          >
            <template v-for="section in helpSections" :key="section.id">
              <!-- 一级目录 -->
              <el-sub-menu :index="section.id" @click="handleSectionClick(section.id)">
                <template #title>
                  <span>{{ section.title }}</span>
                </template>
                <!-- 二级目录 -->
                <el-menu-item
                  v-for="child in section.children"
                  :key="child.id"
                  :index="child.id"
                >
                  {{ child.title }}
                </el-menu-item>
              </el-sub-menu>
            </template>
          </el-menu>
        </el-scrollbar>
      </div>

      <!-- 右侧内容区域 -->
      <div class="help-content">
        <el-scrollbar>
          <div class="help-content-inner">
            <div class="help-content-text" v-html="currentContent"></div>
          </div>
        </el-scrollbar>
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.help-drawer-container {
  display: flex;
  height: calc(100vh - 60px);
  overflow: hidden;
  background-color: #f5f7fa;
}

.help-sidebar {
  width: 240px;
  border-right: 1px solid #e1e8ed;
  flex-shrink: 0;
  height: 100%;
  background-color: white;
}

.help-menu {
  border-right: none;
  height: 100%;
  background-color: white;
}

.help-content {
  flex: 1;
  height: 100%;
  overflow: hidden;
  background-color: white;
}

.help-content-inner {
  padding: 24px;
  min-height: 100%;
  background-color: white;
}

.help-content-text {
  line-height: 1.8;
  color: #2c3e50;
  font-size: 14px;
  background-color: white;
}

.help-content-text :deep(h1) {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: #2c3e50;
  border-bottom: 2px solid #e1e8ed;
  padding-bottom: 8px;
}

.help-content-text :deep(h2) {
  font-size: 20px;
  font-weight: 600;
  margin: 24px 0 12px 0;
  color: #2c3e50;
}

.help-content-text :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 16px 0 8px 0;
  color: #2c3e50;
}

.help-content-text :deep(p) {
  margin: 0 0 12px 0;
  color: #64748b;
}

.help-content-text :deep(ul),
.help-content-text :deep(ol) {
  margin: 0 0 12px 0;
  padding-left: 24px;
  color: #64748b;
}

.help-content-text :deep(li) {
  margin: 4px 0;
}

.help-content-text :deep(code) {
  background-color: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  color: #e11d48;
}

.help-content-text :deep(pre) {
  background-color: #f8fafc;
  border: 1px solid #e1e8ed;
  border-radius: 6px;
  padding: 16px;
  overflow-x: auto;
  margin: 12px 0;
}

.help-content-text :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: #2c3e50;
}

/* 菜单项样式优化 */
:deep(.el-menu-item) {
  color: #64748b;
  transition: all 0.2s;
}

:deep(.el-menu-item:hover) {
  background-color: #f1f5f9;
  color: #2c3e50;
}

:deep(.el-menu-item.is-active) {
  background-color: #e0f2fe;
  color: #0284c7;
  font-weight: 500;
}

:deep(.el-sub-menu__title) {
  color: #2c3e50;
  font-weight: 500;
  transition: all 0.2s;
}

:deep(.el-sub-menu__title:hover) {
  background-color: #f1f5f9;
  color: #2c3e50;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .help-drawer-container {
    flex-direction: column;
  }

  .help-sidebar {
    width: 100%;
    height: 200px;
    border-right: none;
    border-bottom: 1px solid #e1e8ed;
  }

  .help-content {
    height: calc(100% - 200px);
  }
}
</style>

