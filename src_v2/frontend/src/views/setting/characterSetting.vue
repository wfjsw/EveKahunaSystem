<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/http'

interface Character {
  name: string
  expiresDate?: string
  corpName?: string
}

const addCharacterConfirm = ref(false)

let pollInterval: ReturnType<typeof setInterval> | null = null
let listenersMounted = false // 标记监听器是否已挂载

// 开始轮询认证状态
const startAuthStatusPolling = () => {
  if (listenersMounted) {
    console.log('轮询已在进行中，跳过')
    return
  }

  console.log('开始轮询认证状态')
  listenersMounted = true
  
  let pollCount = 0
  const checkAuthStatus = async () => {
    pollCount++
    if (pollCount % 5 === 0) {
      console.log(`认证状态轮询中... (第 ${pollCount} 次检查)`)
    }
    
    try {
      const response = await http.get('/EVE/oauth/authStatus')
      if (response.ok) {
        const data = await response.json()
        const authStatus = data?.authStatus
        const characterName = data?.characterName
        
        if (authStatus === 'success') {
          console.log('检测到认证成功')
          handleAuthComplete(characterName)
        }
      }
    } catch (error) {
      // 静默失败，继续轮询
      console.warn('检查认证状态失败:', error)
    }
  }
  
  // 每 2 秒检查一次，持续 5 分钟（与后端 Redis 过期时间一致）
  pollInterval = setInterval(checkAuthStatus, 2000)
  console.log('✅ 开始轮询认证状态 (每 2 秒检查一次)')
  
  // 5 分钟后停止轮询
  setTimeout(() => {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
      listenersMounted = false
      console.log('停止轮询认证状态')
    }
  }, 300000) // 5 分钟
}

// 停止轮询认证状态
const stopAuthStatusPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
    listenersMounted = false
    console.log('✅ 轮询已停止')
  }
}

const wrapEsiAuth = async () => {
  // 在打开认证窗口之前先开始轮询
  startAuthStatusPolling()
  
  try {
    const response = await http.get('/EVE/oauth/authorize')
    let href = ''
    try {
      const data = await response.clone().json()
      href = data?.authUrl || data?.url || data?.href || ''
    } catch {
      href = await response.text()
    }

    if (typeof href === 'string' && /^https?:\/\//i.test(href)) {
      window.open(href, '_blank', 'noopener,noreferrer')
    } else {
      ElMessage.error('获取认证链接失败')
      stopAuthStatusPolling()
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '请求认证链接失败')
    stopAuthStatusPolling()
  }
}

const characterList = ref<Character[]>([])
const mainCharacter = ref<number | string>('')

const getCharacterList = async () => {
  try {
    const response = await http.get('/user/list')
    const data = await response.json()
    // 后端返回的数据结构是 {data: [...]}，需要取 data 字段
    const list = Array.isArray(data?.data) ? data.data : (data || [])
    // 在列表开头添加一个空选项
    characterList.value = [{ name: '', expiresDate: '', corpName: '' }, ...list]
  } catch (error: any) {
    ElMessage.error(error?.message || '获取角色列表失败')
    characterList.value = [{ name: '', expiresDate: '', corpName: '' }]
  }
}

// 处理认证完成的函数
const handleAuthComplete = (characterName: string) => {
  console.log('认证完成')
  
  // 停止轮询
  stopAuthStatusPolling()
  
  // 更新 UI
  addCharacterConfirm.value = false
  ElMessage.success(`绑定完成，角色名称: ${characterName}`)
  getCharacterList()
}

const handleDelete = async (character: Character) => {
  try {
    const response = await http.post(`/user/deleteCharacter`, {
      characterName: character.name
    })
    ElMessage.success('删除成功')
    if (response.ok) {
      getCharacterList()
    } else {
      ElMessage.error('删除失败')
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '删除失败')
  }
}

const handleSetMainCharacter = async () => {
  try {
    console.log("设置主角色", mainCharacter.value)
    const characterName = mainCharacter.value
    if (characterName === '') {
      ElMessage.error('请选择角色')
      return
    }
    const response = await http.post(`/user/setMainCharacter`, {
      characterName: characterName
    })
    if (response.ok) {
      ElMessage.success('主角色设置成功')
      getCharacterList()
      getIsAliasCharacterSettingAvaliable()
    } else {
      ElMessage.error('主角色设置失败')
      mainCharacter.value = ''
    }
    getCharacterList()
  } catch (error: any) {
    ElMessage.error(error?.message || '主角色设置失败')
  }
}

const getMainCharacter = async () => {
  const response = await http.get('/user/getMainCharacter')
  const data = await response.json()
  mainCharacter.value = data?.mainCharacter || ''
}

const aliasCharacterSettingAvaliable = ref(false)
const getIsAliasCharacterSettingAvaliable = async () => {
  const response = await http.get('/user/isAliasCharacterSettingAvaliable')
  const data = await response.json()
  aliasCharacterSettingAvaliable.value = data?.isAliasCharacterSettingAvaliable || false
}

const aliasCharacterList = ref<{ CharacterId: number, CharacterName: string, Enabled: boolean }[]>([])
let aliasCharacterListEnabled = ref<number[]>([])
const getAliasCharacterList = async () => {
  const response = await http.get('/user/getAliasCharacterList')
  const data = await response.json()
  for (const item of data) {
    if (item.Enabled) {
      aliasCharacterListEnabled.value.push(item.CharacterId)
    }
  }
  aliasCharacterList.value = data || []
}

const getSameTitleAliasCharacterList = async () => {
  const response = await http.post('/user/getSameTitleAliasCharacterList')
  const data = await response.json()
  aliasCharacterList.value = data || []
}

const addNewCharacterProcess = ref(false)

const addSingleNewCharacterForm = reactive({
  inputType: 'characterId' as 'characterId' | 'characterName',
  inputValue: ''
})

onMounted(() => {
  // 页面加载时只获取角色列表，不挂载认证监听器
  // 监听器将在用户点击"开始绑定"按钮时挂载
  console.log('characterSetting mounted')
  getCharacterList()
  getMainCharacter()
  getIsAliasCharacterSettingAvaliable()
  getAliasCharacterList()
})

onBeforeUnmount(() => {
  // 组件卸载时停止轮询
  stopAuthStatusPolling()
})

const searchResults = ref<{ CharacterId: number, CharacterName: string }[]>([])
const selectedCharacterIds = ref<number[]>([])
const searchLoading = ref(false)
const addLoading = ref(false)

const searchCharacters = async () => {
  if (!addSingleNewCharacterForm.inputValue.trim()) {
    ElMessage.warning('请输入搜索值')
    return
  }
  
  searchLoading.value = true
  try {
    const response = await http.post('/user/searchCharacter', {
      inputType: addSingleNewCharacterForm.inputType,
      inputValue: addSingleNewCharacterForm.inputValue.trim()
    })
    
    if (response.ok) {
      const data = await response.json()
      if (Array.isArray(data)) {
        searchResults.value = data
        selectedCharacterIds.value = [] // 清空之前的选择
        if (data.length === 0) {
          ElMessage.info('未找到匹配的角色')
        }
      } else if (data.error) {
        ElMessage.error(data.error)
        searchResults.value = []
      }
    } else {
      const errorData = await response.json().catch(() => ({ error: '搜索失败' }))
      ElMessage.error(errorData.error || '搜索失败')
      searchResults.value = []
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '搜索失败')
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

const addSelectedCharacters = async () => {
  if (selectedCharacterIds.value.length === 0) {
    ElMessage.warning('请至少选择一个角色')
    return
  }
  
  addLoading.value = true
  try {
    const response = await http.post('/user/addAliasCharacters', {
      characterIds: selectedCharacterIds.value
    })
    
    if (response.ok) {
      const data = await response.json()
      ElMessage.success(data.message || '添加成功')
      if (data.aliasCharacterList) {
        aliasCharacterList.value = data.aliasCharacterList
      }
      // 关闭对话框并重置
      addNewCharacterProcess.value = false
      searchResults.value = []
      selectedCharacterIds.value = []
      addSingleNewCharacterForm.inputValue = ''
      // 刷新别名角色列表
      await getAliasCharacterList()
    } else {
      const errorData = await response.json().catch(() => ({ error: '添加失败' }))
      ElMessage.error(errorData.error || '添加失败')
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '添加失败')
  } finally {
    addLoading.value = false
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedCharacterIds.value = selection.map(item => item.CharacterId)
}

const handleSaveAliasCharacters = async () => {
  // TODO: 实现保存别名角色启用状态的功能
  for (const item of aliasCharacterList.value) {
    item.Enabled = aliasCharacterListEnabled.value.includes(item.CharacterId)
  }
  try {
    const response = await http.post('/user/saveAliasCharacters', {
      aliasCharacterList: aliasCharacterList.value
    })
    if (response.ok) {
      ElMessage.success('保存成功')
    } else {
      ElMessage.error('保存失败')
    }
  } catch (error: any) {
    ElMessage.error(error?.message || '保存失败')
  }
}
</script>

<template>
  <el-tabs class="character-setting-tabs">
    <el-tab-pane label="绑定角色设置">
      <div>
        <el-row :gutter="20" align="middle">
          <el-col :span="12" align="middle">
            <el-button @click="addCharacterConfirm = true">添加角色</el-button>
          </el-col>
          <el-col :span="12">
            <span>主角色：</span>
            <el-select v-model="mainCharacter" placeholder="选择角色" style="width: 100%" @change="handleSetMainCharacter">
              <el-option v-for="item in characterList" :key="item.name || 'empty'" :label="item.name || '请选择'" :value="item.name" />
            </el-select>
          </el-col>
        </el-row>
      </div>
      <div>
        <el-table :data="characterList.filter(item => item.name)" style="width: 100%">
          <el-table-column prop="name" label="角色名称" />
          <el-table-column prop="expiresDate" label="过期时间" />
          <el-table-column prop="corpName" label="公司名称" />
          <el-table-column prop="action" label="操作">
            <template #default="scope">
              <el-button type="primary" @click="handleDelete(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <el-dialog v-model="addCharacterConfirm" title="绑定ESI" width="30%" center>
        <span>请知悉</span><br>
        <span>1. 绑定esi会授予网站对应角色的刷新token和访问token，网站将有权限获取token权限内的信息</span><br>
        <span>   绑定即等于同意网站使用你的角色信息</span><br>
        <span>2. 请确认绑定界面的权限是否正确，若对权限有疑问，请不要绑定。</span><br>
        <template #footer>
          <el-button type="primary" @click="wrapEsiAuth">开始绑定</el-button>
        </template>
      </el-dialog>

    </el-tab-pane>

    <el-tab-pane label="小号角色设置(免绑定)">
      <div>
        <span>点击左侧窗口下的获取按钮可获取同主角色title的所有角色</span>
      </div>
      <el-transfer
        v-model="aliasCharacterListEnabled"
        :button-texts="['移出', '添加']"
        :titles="['备选角色', '启用角色']"
        :data="aliasCharacterList"
        :props="{
          key: 'CharacterId',
          label: 'CharacterName'
        }"
        >
        <template #left-footer>
          <el-tooltip content="获取同title角色" placement="top">
            <el-button class="transfer-footer" size="medium" @click="getSameTitleAliasCharacterList"><el-icon><RefreshRight /></el-icon></el-button>
          </el-tooltip>
          <el-tooltip content="添加新角色" placement="top">
            <el-button class="transfer-footer" size="medium" @click="addNewCharacterProcess = true"><el-icon><Plus /></el-icon></el-button>
          </el-tooltip>

          <el-dialog 
            v-model="addNewCharacterProcess"
            style="max-width: 60%;"
          >
            <el-row>
              <el-col :span="24">
                <el-form :model="addSingleNewCharacterForm" label-width="auto">
                  <el-form-item label="搜索方式">
                    <el-radio-group v-model="addSingleNewCharacterForm.inputType">
                      <el-radio-button value="characterId">角色ID</el-radio-button>
                      <el-radio-button value="characterName">角色名称</el-radio-button>
                    </el-radio-group>
                  </el-form-item>

                  <el-form-item label="搜索值">
                    <el-input v-model="addSingleNewCharacterForm.inputValue" placeholder="请输入角色ID或角色名称" />
                  </el-form-item>
                </el-form>
              </el-col>
            </el-row>

            <el-row>
              <el-col :span="6" :offset="9">
                <el-button style="width: 100%;" type="primary" @click="searchCharacters" :loading="searchLoading">搜索</el-button>
              </el-col>
            </el-row>
            
            <!-- 搜索结果表格 -->
            <el-row v-if="searchResults.length > 0">
              <el-col :span="24">
                <el-table 
                  :data="searchResults" 
                  style="width: 100%"
                  @selection-change="handleSelectionChange"
                >
                  <el-table-column type="selection" width="55" />
                  <el-table-column prop="CharacterId" label="角色ID" />
                  <el-table-column prop="CharacterName" label="角色名称" />
                </el-table>
              </el-col>
            </el-row>

            <el-row v-if="searchResults.length > 0">
              <el-col :span="6" :offset="9">
                <el-button 
                  style="width: 100%;" 
                  type="primary" 
                  @click="addSelectedCharacters"
                  :loading="addLoading"
                  :disabled="selectedCharacterIds.length === 0"
                >
                  添加选中角色 ({{ selectedCharacterIds.length }})
                </el-button>
              </el-col>
            </el-row>

          </el-dialog>
        </template>
        <template #right-footer>
          <el-button 
            class="transfer-footer" 
            size="medium"
            @click="handleSaveAliasCharacters"
          >
            保存
          </el-button>
        </template>
      </el-transfer>
    </el-tab-pane>
  </el-tabs>
</template>

<style scoped>
.character-setting-tabs {
  height: 100%;
  width: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.transfer-footer {
  padding: 6px 5px;
  margin: 3px;
}

.el-row {
  margin-bottom: 10px;
}
</style>