<template>
  <div class="table-container">
    <table class="card-table">
      <thead>
        <tr class="table-header">
          <th>配置类型</th>
          <th>配置描述</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody class="industry-plan-config-flow-table">
        <tr v-for="item in list" :key="item.config_id" class="card-row cursor-move">
          <td class="config-type-name">{{ configTypeMap[item.config_type] }}</td>
          <td class="config-description">
            <el-tooltip
              :content="formatConfigValue(item.config_type, item.config_value)"
              placement="top"
            >
              <div class="config-description-text">
                {{ formatConfigValue(item.config_type, item.config_value) }}
              </div>
            </el-tooltip>
          </td>
          <td class="action-cell">
            <el-button type="primary" plain @click="handleModifyConfigFlow(item)">
              修改
            </el-button>
            <el-button type="primary" plain @click="handleDeleteConfigFlowConfig(item)">
              删除
            </el-button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { http } from '@/http'
import { ElMessage } from 'element-plus'

interface PlanConfigObject {
    "config_id": number,
    "config_index_id": number,
    "config_type": string,
    "config_value": object
}
interface Props {
  list: PlanConfigObject[]
}
const props = defineProps<Props>()

const handleModifyConfigFlow = (item: PlanConfigObject) => {
  console.log(item)
}

const configTypeMap = ref<{ [key: string]: string }>({
  "StructureRigConfig": "建筑插件",
  "StructureAssignConf": "建筑分配",
  "MaterialTagConf": "原材料标记",
  "DefaultBlueprintConf": "缺省蓝图参数",
  "LoadAssetConf": "载入库存"
})

const handleDeleteConfigFlowConfig = async (item: PlanConfigObject) => {
  const index = props.list.findIndex(config => config.config_id === item.config_id)
  if (index !== -1) {
    // 直接修改 props.list 来删除元素
    props.list.splice(index, 1)
  }
}

const formatConfigValue = (type: string, value: any) => {
  // 如果 value 是字符串，先解析为对象
  let parsedValue = value
  if (typeof value === 'string') {
    try {
      parsedValue = JSON.parse(value)
    } catch (e) {
      console.error("解析 config_value 失败:", e)
      return String(value)
    }
  }
  
  // 使用 parsedValue 而不是 value
  if (type === 'StructureRigConfig') {
    return `建筑: ${parsedValue.structure_name || 'N/A'}, 时间效率等级: ${parsedValue.time_eff_level ?? 0}, 材料效率等级: ${parsedValue.mater_eff_level ?? 0}`
  } else if (type === 'StructureAssignConf') {
    return `建筑: ${parsedValue.structure_name || 'N/A'}, 分配类型: ${parsedValue.assign_type || 'N/A'}, 关键词: ${parsedValue.keyword || 'N/A'}`
  } else if (type === 'MaterialTagConf') {
    return `原材料标记: ${parsedValue.tag_item_value || 'N/A'}, 原材料类型: ${parsedValue.tag_item_type || 'N/A'}`
  } else if (type === 'DefaultBlueprintConf') {
    return `蓝图: ${parsedValue.blueprint_name || 'N/A'}, 时间效率: ${parsedValue.time_eff ?? 0}, 材料效率: ${parsedValue.mater_eff ?? 0}`
  } else if (type === 'LoadAssetConf') {
    return `库存许可: ${parsedValue.tag || parsedValue.container_tag || 'N/A'}`
  }
  
  return JSON.stringify(parsedValue)
}


</script>

<style scoped>
.table-container {
  width: 100%;
  padding: 8px 0;
}

.card-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 12px;
  background: transparent;
}

.table-header {
  background: transparent;
}

.table-header th {
  padding: 12px 16px;
  text-align: left;
  font-weight: 600;
  font-size: 14px;
  color: #606266;
  border: none;
  background: transparent;
}

.industry-plan-config-flow-table {
  display: table-row-group;
}

.card-row {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  margin-bottom: 12px;
  display: table-row;
  border: none;
}

.card-row:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
  background: #ffffff;
}

.card-row td {
  padding: 16px;
  border: none;
  background: transparent;
  vertical-align: middle;
}

.card-row:first-child td:first-child {
  border-top-left-radius: 12px;
}

.card-row:first-child td:last-child {
  border-top-right-radius: 12px;
}

.card-row:last-child td:first-child {
  border-bottom-left-radius: 12px;
}

.card-row:last-child td:last-child {
  border-bottom-right-radius: 12px;
}

.config-type-name {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
  min-width: 150px;
  width: 20%;
}

.config-description {
  font-size: 14px;
  color: #606266;
  position: relative;
}

.config-description-text {
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  width: 100%;
  cursor: help;
}

.action-cell {
  width: 200px;
  text-align: right;
  white-space: nowrap;
}

.action-cell .el-button {
  margin-left: 8px;
  transition: all 0.2s;
}

.action-cell .el-button:first-child {
  margin-left: 0;
}

.action-cell .el-button:hover {
  transform: scale(1.05);
}

/* 拖拽时的视觉反馈 */
.card-row.sortable-ghost {
  opacity: 0.5;
  background: #f5f7fa;
}

.card-row.sortable-drag {
  opacity: 0.8;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .table-container {
    padding: 4px 0;
  }

  .card-table {
    border-spacing: 0 8px;
  }

  .card-row td {
    padding: 12px;
  }

  .config-type-name {
    min-width: 120px;
    font-size: 14px;
    width: 25%;
  }

  .config-description {
    font-size: 13px;
  }

  .action-cell {
    width: 150px;
  }

  .action-cell .el-button {
    padding: 8px 12px;
    font-size: 12px;
  }

  .table-header th {
    padding: 10px 12px;
    font-size: 13px;
  }
}

/* 空状态优化 */
.industry-plan-config-flow-table:empty::after {
  content: '暂无配置';
  display: block;
  text-align: center;
  padding: 40px;
  color: #909399;
  font-size: 14px;
}
</style>