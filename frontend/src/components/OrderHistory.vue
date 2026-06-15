<template>
  <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px] custom-scrollbar">
    <table class="w-full border-collapse text-nature-800 relative table-fixed">
      <thead class="sticky top-0 bg-nature-200 border-b-[3px] border-nature-800 text-nature-900 font-bold text-02 z-10">
        <tr>
          <!-- 操作 (無須排序) -->
          <th class="py-3 px-2 text-center w-[80px]">操作</th>
          
          <!-- 商品 -->
          <th @click="handleSort('stock_id')" class="py-3 px-2 text-center cursor-pointer select-none w-[100px]">
            股票 <span class="text-xs font-normal font-mono" v-if="sortKey === 'stock_id'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
          </th>
          
          <!-- 買賣 -->
          <th @click="handleSort('side')" class="py-3 px-2 text-center cursor-pointer select-none w-[80px]">
            買賣 <span class="text-xs font-normal font-mono" v-if="sortKey === 'side'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
          </th>

          <!-- 委託類型 -->
          <th  class="py-3 px-2 text-center cursor-pointer select-none w-[100px]">
            委託類型 <span class="text-xs font-normal font-mono" v-if="sortKey === 'order_type'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
          </th>
          
          <!-- 委託單價 -->
          <th @click="handleSort('price')" class="py-3 px-2 text-center cursor-pointer select-none w-[110px]">
            單價 <span class="text-xs font-normal font-mono" v-if="sortKey === 'price'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
          </th>
          
          <!-- 狀態 -->
          <th @click="handleSort('status')" class="py-3 px-2 text-center cursor-pointer select-none w-[100px]">
            狀態 <span class="text-xs font-normal font-mono" v-if="sortKey === 'status'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
          </th>
          
          <!-- 成交價格 -->
          <th @click="handleSort('exec_price')" class="py-3 px-2 text-center cursor-pointer select-none w-[110px]">
            成交價格 <span class="text-xs font-normal font-mono" v-if="sortKey === 'exec_price'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
          </th>
          
          <!-- 下單時間 -->
          <th @click="handleSort('order_id')" class="py-3 px-2 text-center cursor-pointer select-none w-[130px]">
            下單時間 <span class="text-xs font-normal font-mono" v-if="sortKey === 'order_id'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
          </th>
          
          <!-- 成交時間 (以 order_id 輔助排序即可) -->
          <th @click="handleSort('order_id')" class="py-3 px-2 text-center cursor-pointer select-none w-[130px]">
            成交時間 <span class="text-xs font-normal font-mono" v-if="sortKey === 'order_id'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
          </th>
        </tr>
      </thead>
      <tbody class="text-01">
        <tr v-if="sortedOrders.length === 0">
          <td colspan="9" class="py-8 text-center text-nature-500 font-bold bg-nature-200">
            目前無符合條件的委託單紀錄
          </td>
        </tr>
        <tr 
          v-else
          v-for="(order, index) in sortedOrders" 
          :key="order.order_id || index" 
          class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out"
        >
          <!-- 1. 操作 (撤單按鈕) -->
          <td class="py-3 px-2 text-center">
            <button 
              v-if="order.status === 'PENDING'"
              @click="emit('cancel-order', order.order_id)"
              class="px-2 py-1 bg-red-600 hover:bg-red-800 text-white rounded font-bold cursor-pointer transition-colors text-xs border-none outline-none"
            >
              撤單
            </button>
            <span v-else class="text-nature-400 group-hover:text-nature-300">-</span>
          </td>

          <!-- 2. 股票 -->
          <td class="py-3 px-2 text-center font-mono">
            <div class="font-bold text-nature-900 group-hover:text-nature-100">{{ order.stock_id }}</div>
            <div class="text-xs text-nature-500 group-hover:text-nature-300">{{ order.stock_name_zh }}</div>
          </td>

          <!-- 3. 買賣 -->
          <td class="py-3 px-2 text-center">
            <span :class="['font-bold', order.side === 'BUY' ? 'text-red-600 group-hover:text-red-300' : 'text-green-700 group-hover:text-green-300']">
              {{ order.side === 'BUY' ? '買進' : '賣出' }}
            </span>
            <div class="text-xs font-mono">{{ order.quantity }} 張</div>
          </td>

          <!-- 4. 委託類型 -->
          <td class="py-3 px-2 text-center font-bold">
            {{ getOrderTypeName(order) }}
          </td>

          <!-- 5. 單價 -->
          <td class="py-3 px-2 text-center font-mono font-bold">
            {{ getOrderPriceDisplay(order) }}
          </td>

          <!-- 6. 狀態 -->
          <td class="py-3 px-2 text-center font-bold">
            <span v-if="order.status === 'PENDING'" class="text-yellow-600 group-hover:text-yellow-400">待成交</span>
            <span v-else-if="order.status === 'FILLED'" class="text-green-700 group-hover:text-green-300">已成交</span>
            <span v-else-if="order.status === 'CANCELED'" class="text-nature-400 group-hover:text-nature-300">已撤銷</span>
            <span v-else-if="order.status === 'EXPIRED'" class="text-red-600 group-hover:text-red-300">已逾期</span>
            <span v-else class="text-nature-500">{{ order.status }}</span>
          </td>

          <!-- 7. 成交價格 -->
          <td class="py-3 px-2 text-center font-mono font-bold">
            <span v-if="order.status === 'FILLED' && order.exec_price !== null">
              {{ Number(order.exec_price).toFixed(1) }}
            </span>
            <span v-else class="text-nature-400 group-hover:text-nature-300">-</span>
          </td>

          <!-- 8. 下單時間 -->
          <td class="py-3 px-2 text-center font-mono whitespace-pre-line text-xs">
            {{ getOrderTime(order) }}
          </td>

          <!-- 9. 成交時間 -->
          <td class="py-3 px-2 text-center font-mono whitespace-pre-line text-xs">
            {{ getFillTime(order) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  orders: {
    type: Array,
    required: true,
    default: () => []
  }
})

const emit = defineEmits(['cancel-order'])

// 排序狀態
const sortKey = ref('order_id')
const sortOrder = ref('desc') // 'asc' | 'desc'

const handleSort = (key) => {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}

// 根據排序狀態計算結果
const sortedOrders = computed(() => {
  const list = [...props.orders]
  const key = sortKey.value
  const order = sortOrder.value === 'asc' ? 1 : -1

  return list.sort((a, b) => {
    let valA = a[key]
    let valB = b[key]

    // 對數值類型進行處理
    if (key === 'price' || key === 'exec_price') {
      valA = valA !== null && valA !== undefined ? parseFloat(valA) : -1
      valB = valB !== null && valB !== undefined ? parseFloat(valB) : -1
    }

    if (valA < valB) return -1 * order
    if (valA > valB) return 1 * order
    return 0
  })
})

// 判斷委託類型
const getOrderTypeName = (order) => {
  if (order.phase === 'POST_MARKET') return '盤後定價'
  return order.order_type === 'MARKET' ? '市價' : '限價'
}

// 判斷單價顯示
const getOrderPriceDisplay = (order) => {
  if (order.phase === 'POST_MARKET') return '定價'
  if (order.order_type === 'MARKET') return '市價'
  return order.price !== null && order.price !== undefined ? Number(order.price).toFixed(1) : '-'
}

// 格式化下單時間
const getOrderTime = (order) => {
  if (!order.sim_date) return '-'
  const dateStr = order.sim_date.slice(0, 10).replace(/-/g, '/') // "YYYY/MM/DD"
  const phaseMap = {
    'PRE_MARKET': '盤前',
    'INTRADAY': '盤中',
    'POST_MARKET': '盤後',
    'CLOSED': '收市'
  }
  const phaseStr = phaseMap[order.phase] || order.phase
  return `${dateStr}\n${phaseStr}`
}

// 格式化成交時間 (推估)
const getFillTime = (order) => {
  if (order.status !== 'FILLED') return '-'
  if (!order.sim_date) return '-'
  
  const dateStr = order.sim_date.slice(0, 10).replace(/-/g, '/') // "YYYY/MM/DD"
  
  let fillPhase = ''
  if (order.phase === 'PRE_MARKET') {
    fillPhase = '盤中'
  } else if (order.phase === 'INTRADAY') {
    fillPhase = '盤後'
  } else if (order.phase === 'POST_MARKET') {
    fillPhase = '收市'
  } else {
    fillPhase = order.phase
  }
  
  return `${dateStr}\n${fillPhase}`
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.5);
}
</style>
