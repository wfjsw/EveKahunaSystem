<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { http } from '@/http'
import IndustryPlanConfigFlowTable from './industryPlanConfigFlowTable.vue'
import { ElMessage } from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'

interface Props {
    selectedPlan: string
}

const configTypeMap = ref<{ [key: string]: string }>({
  "StructureRigConfig": "建筑插件",
  "StructureAssignConf": "建筑分配",
  "MaterialTagConf": "原材料标记",
  "DefaultBlueprintConf": "缺省蓝图参数",
  "LoadAssetConf": "载入库存"
})

const props = defineProps<Props>()


interface ConfigObject {
    "config_id": number,
    "config_type": string,
    "config_value": object
}
const configFlowConfigList = ref<ConfigObject[]>([])
const getConfigFlowConfigList = async () => {
    const res = await http.get('/EVE/industry/getConfigFlowConfigList')
    const data = await res.json()
    if (data.status !== 200) {
        ElMessage.error(data.message)
        return
    }
    configFlowConfigList.value = data.data
    ElMessage.success("获取配置库配置列表")
}

interface PlanConfigObject {
    "config_id": number,
    "config_index_id": number,
    "config_type": string,
    "config_value": object
}
const configFlowList = ref<PlanConfigObject[]>([])
const getConfigFlowList = async () => {
    const res = await http.post('/EVE/industry/getConfigFlowList', {
        plan_name: props.selectedPlan
    })
    const data = await res.json()
    configFlowList.value = data.data
}

const addConfigToPlan = async (config: PlanConfigObject) => {
    const res = await http.post('/EVE/industry/addConfigToPlan', {
        plan_name: props.selectedPlan,
        config_id: config.config_id
    })
    const data = await res.json()
    if (data.status !== 200) {
        ElMessage.error(data.message)
        return
    }
    ElMessage.success(data.message)
    getConfigFlowList()
    configFlowManagementVisible.value = false
}

const saveConfigFlowToPlan = async () => {
    const res = await http.post('/EVE/industry/saveConfigFlowToPlan', {
        plan_name: props.selectedPlan,
        config_list: configFlowList.value
    })
    const data = await res.json()
    if (data.status !== 200) {
        ElMessage.error(data.message)
        return
    }
    ElMessage.success(data.message)
    getConfigFlowList()
}

// ============== 配置库管理 ==============

const configFlowManagementVisible = ref(false)
const openConfigFlowManagement = () => {
    configFlowManagementVisible.value = true
}

const createConfigDrawerVisible = ref(false)
const openCreateConfigDrawer = () => {
    createConfigDrawerVisible.value = true
}


interface StructureRigConfig {
    structure_id: number,
    time_eff_level: number,
    mater_eff_level: number
}
interface StructureAssignConf {
    structure_id: number,
    assign_type: string,
    keyword: string
}
interface MaterialTagConf {
    tag_item_value: string,
    tag_item_type: string
}
interface DefaultBlueprintConf {
    blueprint_id: number,
    time_eff: number,
    mater_eff: number
}
interface LoadAssetConf {
    owner_id: number,
    container_id: number
}
const configForm = ref({
    StructureRigConfig: {
        structure_name: '',
        time_eff_level: 0,
        mater_eff_level: 0
    },
    StructureAssignConf: {
        structure_name: '',
        assign_type: '',
        keyword: ''
    },
    MaterialTagConf: {
        tag_item_value: '',
        tag_item_type: ''
    },
    DefaultBlueprintConf: {
        select_type: 'blueprint',
        blueprint_name: "",
        time_eff: 0,
        mater_eff: 0
    },
    LoadAssetConf: {
        container_tag: ""
    }
})

const createConfigType = ref('建筑插件')
const createConfig = async () => {
    let config_value = null
    console.log("createConfigType.value", createConfigType.value)
    if (createConfigType.value === 'StructureRigConfig') {
        const structure_item = structureSuggestions.value.find(item => item.structure_name === configForm.value.StructureRigConfig.structure_name)
        if (structure_item) {
            config_value = {
                structure_id: structure_item.structure_id,
                time_eff_level: configForm.value.StructureRigConfig.time_eff_level,
                mater_eff_level: configForm.value.StructureRigConfig.mater_eff_level
            }
        }
    } else if (createConfigType.value === 'StructureAssignConf') {
        config_value = configForm.value.StructureAssignConf
    } else if (createConfigType.value === 'MaterialTagConf') {
        config_value = configForm.value.MaterialTagConf
    } else if (createConfigType.value === 'DefaultBlueprintConf') {
        config_value = configForm.value.DefaultBlueprintConf
    } else if (createConfigType.value === 'LoadAssetConf') {
        const container_permission_item = ContainerPermissionSuggestions.value.find(item => item.tag === configForm.value.LoadAssetConf.container_tag)
        if (container_permission_item) {
            config_value = container_permission_item
        }
        else {
            ElMessage.error("未找到对应的库存许可")
            return
        }
    }
    console.log("config_value", config_value)
    const res = await http.post('/EVE/industry/createConfigFlowConfig', {
        config_type: createConfigType.value,
        config_value: config_value
    })
    const data = await res.json()
    if (data.status !== 200) {
        ElMessage.error(data.message)
        return
    }
    ElMessage.success(data.message)
    createConfigDrawerVisible.value = false
    getConfigFlowConfigList()
}

const structureSuggestionsCreateFilter = (queryString: string) => {
  return (restaurant: StructureItem) => {
    return (
      restaurant.structure_name.toLowerCase().indexOf(queryString.toLowerCase()) === 0
    )
  }
}

interface StructureItem {
    structure_id: number,
    structure_name: string
}
const structureSuggestions = ref<StructureItem[]>([])
const fetchStructureSuggestions = async (queryString: string, cb: (suggestions: StructureItem[]) => void) => {
    const res = await http.get('/EVE/industry/getStructureList')
    const data = await res.json()

    console.log("data", data)
    structureSuggestions.value = data.data
    const results = queryString
    ? structureSuggestions.value.filter(structureSuggestionsCreateFilter(queryString))
    : []

    console.log("results", results)
    cb(results)
}

const assignTypeOptions = ref([
    { value: 'group', label: 'group' },
    { value: 'meta', label: 'meta' },
    { value: 'blueprint', label: 'blueprint' },
    { value: 'marketGroup', label: 'marketGroup' },
    { value: 'category', label: 'category'}
])
interface AssignKeywordItem {
    value: string
}
const StructureAssignKeywordSuggestions = ref<AssignKeywordItem[]>([])
const StructureAssignKeywordCreateFilter = (queryString: string) => {
  return (restaurant: AssignKeywordItem) => {
    return (
      restaurant.value.toLowerCase().indexOf(queryString.toLowerCase()) === 0
    )
  }
}
const fetchSuggestions = async (assign_type: string) => {
    console.log("fetchSuggestions assign_type", assign_type)
    const res = await http.post('/EVE/industry/getStructureAssignKeywordSuggestions', {
        assign_type: assign_type
    })
    const data = await res.json()
    console.log("fetchSuggestions data", data)
    return data
}
const fetchStructureAssignKeywordSuggestions = async (queryString: string, cb: (suggestions: AssignKeywordItem[]) => void) => {
    const assign_type = configForm.value.StructureAssignConf.assign_type
    console.log("fetchStructureAssignKeywordSuggestions assign_type", assign_type)
    const data = await fetchSuggestions(assign_type)
    StructureAssignKeywordSuggestions.value = data.data
    
    const results = queryString
    ? StructureAssignKeywordSuggestions.value.filter(StructureAssignKeywordCreateFilter(queryString))
    : []
    console.log("results", results)

    cb(results)
}

const MaterialSuggestions = ref<AssignKeywordItem[]>([])
const fetchMaterialSuggestions = async (queryString: string, cb: (suggestions: AssignKeywordItem[]) => void) => {
    let assign_type = configForm.value.MaterialTagConf.tag_item_type
    const data = await fetchSuggestions(assign_type)
    BlueprintSuggestions.value = data.data
    
    const results = queryString
    ? BlueprintSuggestions.value.filter(StructureAssignKeywordCreateFilter(queryString))
    : []

    cb(results)
}

const BlueprintSuggestions = ref<AssignKeywordItem[]>([])
const fetchBlueprintSuggestions = async (queryString: string, cb: (suggestions: AssignKeywordItem[]) => void) => {
    let assign_type = configForm.value.DefaultBlueprintConf.select_type
    const data = await fetchSuggestions(assign_type)
    BlueprintSuggestions.value = data.data
    
    const results = queryString
    ? BlueprintSuggestions.value.filter(StructureAssignKeywordCreateFilter(queryString))
    : []

    cb(results)
}

interface ContainerPermissionItem {
    tag: string
}
const ContainerPermissionSuggestions = ref<ContainerPermissionItem[]>([])
const StructureContainerPermissionCreateFilter = (queryString: string) => {
  return (restaurant: ContainerPermissionItem) => {
    return (
      restaurant.tag.toLowerCase().indexOf(queryString.toLowerCase()) === 0
    )
  }
}
const fetchContainerPermissionSuggestions = async (queryString: string, cb: (suggestions: ContainerPermissionItem[]) => void) => {
    const res = await http.get('/EVE/industry/getUserAllContainerPermission')
    const data = await res.json()
    console.log("fetchContainerPermissionSuggestions data", data)
    ContainerPermissionSuggestions.value = data.data
    
    const results = queryString
    ? ContainerPermissionSuggestions.value.filter(StructureContainerPermissionCreateFilter(queryString))
    : ContainerPermissionSuggestions.value
    cb(results)
}

// 格式化 JSON 用于 tooltip 显示（带缩进）
const formatJsonTooltip = (value: any): string => {
    try {
        if (typeof value === 'string') {
            // 如果是字符串，尝试解析为 JSON
            const parsed = JSON.parse(value)
            return JSON.stringify(parsed, null, 2)
        } else if (typeof value === 'object' && value !== null) {
            // 如果是对象，直接格式化
            return JSON.stringify(value, null, 2)
        }
        return String(value)
    } catch (e) {
        // 如果不是有效的 JSON，返回原值
        return String(value)
    }
}

// 格式化 JSON 用于单元格显示（单行，截断）
const formatJsonDisplay = (value: any): string => {
    try {
        if (typeof value === 'string') {
            const parsed = JSON.parse(value)
            return JSON.stringify(parsed)
        } else if (typeof value === 'object' && value !== null) {
            return JSON.stringify(value)
        }
        return String(value)
    } catch (e) {
        return String(value)
    }
}

// =========================================

onMounted(() => {
    getConfigFlowList()
})

// 监听 selectedPlan 的变化，当变化时重新获取数据
watch(
    () => props.selectedPlan,
    (newPlan) => {
        if (newPlan) {
            getConfigFlowList()
        }
    },
    { immediate: false } // immediate: false 表示不在初始化时执行，因为 onMounted 已经处理了
)
</script>

<template>
<div class="industry-plan-config-flow-container" style="flex-direction: column; height: 100%;" >
<div style="display: flex; flex-direction: row; justify-content: flex-start; flex-wrap: wrap; gap: 8px;">
    <el-button @click="openConfigFlowManagement">
        配置库管理
    </el-button>
    <el-button @click="saveConfigFlowToPlan">
        保存当前配置
    </el-button>
    <el-button @click="getConfigFlowList">
        重置修改
    </el-button>
    <el-button>
        保存为预设
    </el-button>
    <el-button>
        从预设加载
    </el-button>
</div>
<VueDraggable
              v-model="configFlowList"
              target="tbody"
              :animation="150"
            >
<industry-plan-config-flow-table :list="configFlowList" />
</VueDraggable>
</div>

<el-drawer 
    v-model="configFlowManagementVisible"
    resizable
    size="600"
    @opened="getConfigFlowConfigList"
>
    <div style="display: flex; flex-direction: column; height: 100%;">
        <div>
            <el-button @click="openCreateConfigDrawer">
                创建配置
            </el-button>
        </div>
        <div>
            <el-table
            :data="configFlowConfigList"
            >
                <el-table-column label="配置类型" prop="config_type">
                    <template #default="{ row }">
                        {{ configTypeMap[row.config_type] }}
                    </template>
                </el-table-column>
                <el-table-column label="配置" prop="config_value">
                    <template #default="{ row }">
                        <el-tooltip
                            placement="top"
                            effect="dark"
                            :raw-content="true"
                        >
                            <template #content>
                                <pre class="json-tooltip-content">{{ formatJsonTooltip(row.config_value) }}</pre>
                            </template>
                            <div class="config-value-cell">
                                {{ formatJsonDisplay(row.config_value) }}
                            </div>
                        </el-tooltip>
                    </template>
                </el-table-column>
                <el-table-column label="操作" prop="action">
                    <template #default="{ row }">
                        <el-button type="primary" plain @click="addConfigToPlan(row)">
                            添加到计划{{ props.selectedPlan }}
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
        </div>
    </div>

    <el-drawer
    v-model="createConfigDrawerVisible"
    resizable
    width="500px"
    >
        <el-radio-group v-model="createConfigType" size="large" fill="#6cf">
            <el-radio-button label="建筑插件" value="StructureRigConfig" />
            <el-radio-button label="建筑分配" value="StructureAssignConf" />
            <el-radio-button label="原材料标记" value="MaterialTagConf" />
            <el-radio-button label="缺省蓝图参数" value="DefaultBlueprintConf" />
            <el-radio-button label="载入库存" value="LoadAssetConf" />
        </el-radio-group>

        <!-- 建筑插件配置 -->
        <el-form :model="configForm.StructureRigConfig" label-width="120px" v-if="createConfigType === 'StructureRigConfig'">
            <el-form-item label="选择建筑">
                <el-autocomplete
                    v-model="configForm.StructureRigConfig.structure_name"
                    :fetch-suggestions="fetchStructureSuggestions"
                    value-key="structure_name"
                />
            </el-form-item>
            <span>0=无插件，1=T1插件，2=T2插件</span>
            <el-form-item label="时间效率等级">
                <el-input-number v-model="configForm.StructureRigConfig.time_eff_level" :min="0" :max="2" placeholder="请输入时间效率等级" />
            </el-form-item>
            <el-form-item label="材料效率等级">
                <el-input-number v-model="configForm.StructureRigConfig.mater_eff_level" :min="0" :max="2" placeholder="请输入材料效率等级" />
            </el-form-item>
        </el-form>

        <!-- 建筑分配配置 -->
        <el-form :model="configForm.StructureAssignConf" label-width="120px" v-else-if="createConfigType === 'StructureAssignConf'">
            <el-form-item label="选择建筑">
                <el-autocomplete
                    v-model="configForm.StructureAssignConf.structure_name"
                    :fetch-suggestions="fetchStructureSuggestions"
                    value-key="structure_name"
                />
            </el-form-item>
            <el-form-item label="分配类型">
                <el-select v-model="configForm.StructureAssignConf.assign_type" placeholder="Select" style="width: 240px">
                    <el-option
                    v-for="item in assignTypeOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"/>
                </el-select>
            </el-form-item>
            <el-form-item label="标记关键字">
                <el-autocomplete
                    v-model="configForm.StructureAssignConf.keyword"
                    :fetch-suggestions="fetchStructureAssignKeywordSuggestions"
                    value-key="value"
                />
            </el-form-item>
        </el-form>

        <!-- 原材料标记配置 -->
        <el-form :model="configForm.MaterialTagConf" label-width="120px" v-else-if="createConfigType === 'MaterialTagConf'">
            <el-form-item label="原材料类型">
                <el-select v-model="configForm.MaterialTagConf.tag_item_type" placeholder="Select" style="width: 240px">
                    <el-option
                    v-for="item in assignTypeOptions"
                    :key="item.value"
                    :label="item.label"
                    :value="item.value"/>
                </el-select>
            </el-form-item>
            <el-form-item label="标记关键字">
                <el-autocomplete
                    v-model="configForm.MaterialTagConf.tag_item_value"
                    :fetch-suggestions="fetchMaterialSuggestions"
                    value-key="value"
                />
            </el-form-item>
        </el-form>
        
        <!-- 缺省蓝图参数配置 -->
        <el-form :model="configForm.DefaultBlueprintConf" label-width="120px" v-else-if="createConfigType === 'DefaultBlueprintConf'">

            <el-form-item label="选择蓝图">
                <el-autocomplete
                    v-model="configForm.DefaultBlueprintConf.blueprint_name"
                    :fetch-suggestions="fetchBlueprintSuggestions"
                    value-key="value"
                />
            </el-form-item>
            <el-form-item label="时间效率">
                <el-input-number v-model="configForm.DefaultBlueprintConf.time_eff" placeholder="请输入时间效率" :min="0" :max="20" />
            </el-form-item>
            <el-form-item label="材料效率">
                <el-input-number v-model="configForm.DefaultBlueprintConf.mater_eff" placeholder="请输入材料效率" :min="0" :max="10" />
            </el-form-item>
        </el-form>
        
        <!-- 载入库存配置 -->
        <el-form :model="configForm.LoadAssetConf" label-width="120px" v-else-if="createConfigType === 'LoadAssetConf'">
            <el-form-item label="选择库存许可">
                <el-autocomplete
                    v-model="configForm.LoadAssetConf.container_tag"
                    :fetch-suggestions="fetchContainerPermissionSuggestions"
                    value-key="tag"
                />
            </el-form-item>
            </el-form>

        <template #footer>
            <el-button @click="createConfig" type="primary" plain size="large">创建</el-button>
        </template>
        </el-drawer>
    </el-drawer>
</template>

<style scoped>
.config-value-cell {
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.json-tooltip-content {
    margin: 0;
    padding: 8px;
    background: #1f1f1f;
    color: #fff;
    border-radius: 4px;
    max-width: 500px;
    max-height: 400px;
    overflow: auto;
    font-size: 12px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
}
</style>