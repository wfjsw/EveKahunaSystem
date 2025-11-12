<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { http } from '@/http'
import { ElMessage } from 'element-plus'
import type { InputNumberInstance } from 'element-plus/lib/components/index.js'
import { Loading } from '@element-plus/icons-vue'

interface HandleSearchItemCountForm {
    item_name: string
    item_id: InputNumberInstance | null
    item_location: string
    container_id: string
    data: any[]
}

const handleSearchItemCountdialogVisible = ref(false)
const handleSearchContainerdialogVisible = ref(false)
const handleSearchItemCountdialogLoading = ref(false)
const handleSearchItemCountForm = ref<HandleSearchItemCountForm>({
    item_name: '',
    item_id: null,
    item_location: '',
    container_id: '',
    data: []
})
const handleSearchItemCountdialog = () => {
    handleSearchItemCountdialogVisible.value = true
    console.log("handleSearchItemCount")
}

const handleSearchItemCount = async () => {
    const res = await http.post('/EVE/asset/searchContainerByItemNameAndQuantity', {
        item_name: handleSearchItemCountForm.value.item_name
    })
    const data = await res.json()
    console.log("handleSearchItemCount", data)
    if (data.status !== 200) {
        ElMessage.error(data.message)
        return
    }
    handleSearchItemCountForm.value.data = data.data
    // handleSearchItemCountForm.value.item_location = data.data.item_location
    // handleSearchItemCountForm.value.container_id = data.data.container_id
}

const handleSearchContainerdialog = () => {
    console.log("handleSearchContainer")
}

const handleAddIndustrypermision = async (row: any) => {
    handleSearchItemCountdialogLoading.value = true
    console.log("handleSearchItemCountdialogLoading", handleSearchItemCountdialogLoading.value)
    const res = await http.post('/EVE/industry/addIndustrypermision', {
        container: row.container,
        asset: row.asset,
        structure: row.structure,
        system: row.system,
        tag: row.container.tag
    })
    const data = await res.json()
    if (data.status !== 200) {
        ElMessage.error(data.message)
        return
    }
    ElMessage.success(data.message)
    handleSearchItemCountdialogLoading.value = false
    handleSearchItemCountdialogVisible.value = false
    getUserAllContainerPermission()
}

const userContainerPermission = ref([])
const userContainerPermissionLoading = ref(false)
const getUserAllContainerPermission = async () => {
    userContainerPermissionLoading.value = true
    const res = await http.get('/EVE/industry/getUserAllContainerPermission')
    const data = await res.json()
    if (data.status !== 200) {
        userContainerPermissionLoading.value = false
        ElMessage.error(data.message)
        return
    }
    userContainerPermission.value = data.data
    userContainerPermissionLoading.value = false
}

const handleDeleteIndustrypermision = async (row: any) => {
    const res = await http.post('/EVE/industry/deleteIndustrypermision', {
        asset_owner_id: row.asset_owner_id,
        asset_container_id: row.asset_container_id
    })
    const data = await res.json()
    if (data.status !== 200) {
        ElMessage.error(data.message)
        return
    }
    ElMessage.success(data.message)
    getUserAllContainerPermission()
    console.log("handleDeleteIndustrypermision", row)
}

const handleViewContent = (row: any) => {
    console.log("handleViewContent", row)
}

const TypeSuggestionsCreateFilter = (queryString: string) => {
  return (restaurant: TypeItem) => {
    return (
      restaurant.value.toLowerCase().indexOf(queryString.toLowerCase()) === 0
    )
  }
}

interface TypeItem {
    value: string
}
const TypeSuggestions = ref<TypeItem[]>([])
const fetchTypeSuggestions = async (queryString: string, cb: (suggestions: TypeItem[]) => void) => {
    const res = await http.get('/EVE/industry/getTypeList')
    const data = await res.json()

    TypeSuggestions.value = data.data
    const results = queryString
    ? TypeSuggestions.value.filter(TypeSuggestionsCreateFilter(queryString))
    : []

    cb(results)
}

onMounted(async () => {
    await getUserAllContainerPermission()
})
</script>
<template>
    <div style="display: flex; flex-direction: horizontal; gap: 10px;">
        <div style="min-width: 300px;">
            <el-button type="primary" @click="handleSearchItemCountdialog">搜索物品数目新增许可</el-button>
            <el-button type="primary" @click="handleSearchContainerdialog">检索容器新增许可</el-button>
            <el-table
                :data="userContainerPermission"
                border
                v-loading="userContainerPermissionLoading"
                show-overflow-tooltip
            >
                <el-table-column label="资产类型" prop="owner_type" />
                <el-table-column label="所有者" prop="owner_name" width="200"/>
                <el-table-column label="容器ID" prop="asset_container_id" />
                <el-table-column label="建筑" prop="structure_name" width="200"/>
                <el-table-column label="星系" prop="system_name" />
                <el-table-column label="标签" prop="tag" />
                <el-table-column label="操作" width="200">
                    <template #default="scope">
                        <el-button type="primary" @click="handleDeleteIndustrypermision(scope.row)">删除</el-button>
                        <el-button type="primary" @click="handleViewContent(scope.row)">查看内容</el-button>
                    </template>
                </el-table-column>
            </el-table>
        </div>
        <div>
            <h1>
                1
            </h1>
        </div>
    </div>

    <el-dialog
        v-model="handleSearchItemCountdialogVisible"
        title="搜索物品新增许可"
        width="70%"
    >
        <el-form :model="handleSearchItemCountForm" label-width="120px">
            <el-form-item label="物品名">
                <el-autocomplete
                    v-model="handleSearchItemCountForm.item_name"
                    :fetch-suggestions="fetchTypeSuggestions"
                    value-key="value"
                />
            </el-form-item>
            <el-button type="primary" @click="handleSearchItemCount">
                搜索
            </el-button>
            <el-form-item label="搜索结果">
                <el-table
                    :data="handleSearchItemCountForm.data"
                    border
                    v-loading="handleSearchItemCountdialogLoading"
                    max-height="700px"
                >
                    <el-table-column label="名称" prop="asset.type_name" />
                    <el-table-column label="数量" prop="asset.quantity" />
                    <el-table-column label="建筑" prop="structure.structure_name" />
                    <el-table-column label="容器ID" prop="container.item_id" />
                    <el-table-column label="容器位置" prop="container.location_flag" />
                    <el-table-column label="标签" prop="container.tag">
                        <template #default="scope">
                            <el-input v-model="scope.row.container.tag" placeholder="请输入标签" />
                        </template>
                    </el-table-column>
                    <el-table-column label="操作" width="100">
                        <template #default="scope">
                            <el-button type="primary" @click="handleAddIndustrypermision(scope.row)">新增</el-button>
                        </template>
                    </el-table-column>
                </el-table>
            </el-form-item>
        </el-form>
    </el-dialog>
</template>