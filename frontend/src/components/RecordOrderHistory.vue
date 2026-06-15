<template>
  <div class="w-[98%] sm:w-[90%] max-w-[1280px] gap-[10px] p-[6px] sm:p-[20px] md:p-[30px] bg-nature-800 border-nature-500 border-[3px] sm:border-[6px] md:border-[10px] h-fit flex flex-col">
    
    <div class="flex w-full h-full">
      <div class="text-03 sm:text-04 md:text-06 lg:text-07 text-nature-100 w-full">委託紀錄</div>
      <div class="w-full flex flex-row-reverse">
        <RecordSelect :titleType="4" />
      </div>
    </div>

    <!-- 待成交 / 今日委託 篩選器，置於下方，保持響應式與同學風格一致 -->
    <div class="flex flex-wrap gap-4 text-01 sm:text-02 md:text-03 lg:text-04 text-nature-100 mb-2">
      <button 
        type="button"
        @click="togglePending"
        :class="['px-3 py-1.5 sm:px-5 sm:py-2 rounded-lg font-bold border border-solid transition-all duration-300 cursor-pointer text-xs sm:text-sm outline-none', 
                 showPending ? 'bg-yellow-500 text-nature-900 border-yellow-500 shadow-md' : 'bg-nature-900 text-nature-300 border-nature-600 hover:bg-nature-750']"
      >
        待成交
      </button>
      <button 
        type="button"
        @click="toggleToday"
        :class="['px-3 py-1.5 sm:px-5 sm:py-2 rounded-lg font-bold border border-solid transition-all duration-300 cursor-pointer text-xs sm:text-sm outline-none', 
                 showToday ? 'bg-green-300 text-green-900 border-green-300 shadow-md' : 'bg-nature-900 text-nature-300 border-nature-600 hover:bg-nature-750']"
      >
        今日委託單
      </button>
    </div>

    <!-- 委託紀錄表格 (完全手刻，符合 record 頁面手刻表格風格與響應式規格) -->
    <div class="w-full">
      <div v-if="isLoading" class="py-8 text-center text-nature-300 animate-pulse text-lg">
        載入中...
      </div>
      <div v-else class="bg-nature-200 rounded-[10px] overflow-auto max-h-[400px] custom-scrollbar">
        <table class="w-full text-center relative min-w-[640px]">
          <thead class="sticky top-0 bg-nature-200 border-b-3 text-nature-900 font-05 text-[10px] sm:text-01 md:text-02 lg:text-03 z-10">
            <tr>
              <!-- 操作 (無須排序) -->
              <th class="py-1.5 px-1 sm:py-3 sm:px-2 select-none">操作</th>
              
              <!-- 商品 -->
              <th @click="sortBy('stock_id')" class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors">
                股票 <SortIcon :active="sortKey === 'stock_id'" :order="sortOrder" />
              </th>
              
              <!-- 買賣 -->
              <th @click="sortBy('side')" class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors">
                買賣 <SortIcon :active="sortKey === 'side'" :order="sortOrder" />
              </th>

              <!-- 委託類型 -->
              <th class="py-1.5 px-1 sm:py-3 sm:px-2 select-none">委託類型</th>
              
              <!-- 委託單價 -->
              <th @click="sortBy('price')" class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors">
                單價 <SortIcon :active="sortKey === 'price'" :order="sortOrder" />
              </th>
              
              <!-- 狀態 -->
              <th @click="sortBy('status')" class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors">
                狀態 <SortIcon :active="sortKey === 'status'" :order="sortOrder" />
              </th>
              
              <!-- 成交價格 -->
              <th @click="sortBy('exec_price')" class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors">
                成交價格 <SortIcon :active="sortKey === 'exec_price'" :order="sortOrder" />
              </th>
              
              <!-- 下單時間 -->
              <th @click="sortBy('order_id')" class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors">
                下單時間 <SortIcon :active="sortKey === 'order_id'" :order="sortOrder" />
              </th>
              
              <!-- 成交時間 -->
              <th @click="sortBy('order_id')" class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors">
                成交時間 <SortIcon :active="sortKey === 'order_id'" :order="sortOrder" />
              </th>
            </tr>
          </thead>
          <tbody class="text-[10px] sm:text-01 md:text-02 lg:text-03 text-nature-800">
            <tr v-if="sortedRecords.length === 0">
              <td colspan="9" class="py-8 text-center text-nature-500 font-bold bg-nature-200">
                目前無符合條件的委託單紀錄
              </td>
            </tr>
            <tr 
              v-else
              v-for="(order, index) in sortedRecords" 
              :key="order.order_id || index" 
              class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors"
            >
              <!-- 1. 操作 (撤單按鈕) -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2">
                <button 
                  v-if="order.status === 'PENDING'"
                  @click="handleCancelOrder(order.order_id)"
                  class="px-2 py-1 bg-red-600 hover:bg-red-800 text-white rounded font-bold cursor-pointer transition-colors text-xs border-none outline-none"
                >
                  撤單
                </button>
                <span v-else class="text-nature-400 group-hover:text-nature-300">-</span>
              </td>

              <!-- 2. 股票 -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2 font-mono">
                <div class="font-bold">{{ order.stock_id }}</div>
                <div class="text-[9px] sm:text-[11px] md:text-01 opacity-60 group-hover:opacity-100 transition-opacity">{{ order.stock_name_zh }}</div>
              </td>

              <!-- 3. 買賣 -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2">
                <span :class="['font-bold', order.side === 'BUY' ? 'text-red-600 group-hover:text-red-300' : 'text-green-500 group-hover:text-green-300']">
                  {{ order.side === 'BUY' ? '買進' : '賣出' }}
                </span>
                <div class="text-xs font-mono opacity-60 group-hover:opacity-100 transition-opacity">{{ order.quantity }} 張</div>
              </td>

              <!-- 4. 委託類型 -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2">
                {{ getOrderTypeName(order) }}
              </td>

              <!-- 5. 單價 -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2 font-mono">
                {{ getOrderPriceDisplay(order) }}
              </td>

              <!-- 6. 狀態 -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2 font-bold">
                <span v-if="order.status === 'PENDING'" class="text-yellow-600 group-hover:text-yellow-300">待成交</span>
                <span v-else-if="order.status === 'FILLED'" class="text-green-500 group-hover:text-green-300">已成交</span>
                <span v-else-if="order.status === 'CANCELED'" class="text-nature-400 group-hover:text-nature-300">已撤銷</span>
                <span v-else-if="order.status === 'EXPIRED'" class="text-red-600 group-hover:text-red-300">已逾期</span>
                <span v-else>{{ order.status }}</span>
              </td>

              <!-- 7. 成交價格 -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2 font-mono">
                <span v-if="order.status === 'FILLED' && order.exec_price !== null">
                  {{ Number(order.exec_price).toFixed(1) }}
                </span>
                <span v-else class="text-nature-400 group-hover:text-nature-300">-</span>
              </td>

              <!-- 8. 下單時間 -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2 font-mono whitespace-pre-line">
                {{ getOrderTime(order) }}
              </td>

              <!-- 9. 成交時間 -->
              <td class="py-1.5 px-1 sm:py-3 sm:px-2 font-mono whitespace-pre-line">
                {{ getFillTime(order) }}
              </td>
            </tr>
            
            <tr class="h-[50px] bg-nature-200">
              <td colspan="9"></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 撤單確認彈窗 -->
    <ConfirmModal
      v-model:show="showConfirmModal"
      title="確認撤銷委託"
      message="確定要撤銷此筆委託單嗎？此操作將無法復原。"
      confirm-text="確認撤單"
      cancel-text="取消"
      type="danger"
      @confirm="confirmCancelOrder"
      @cancel="closeConfirmModal"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineComponent, h } from 'vue'
import { useRoute } from 'vue-router'
import RecordSelect from './RecordSelect.vue'
import ConfirmModal from './ConfirmModal.vue'
import { showToast } from './Toast.vue'

const props = defineProps({
  currentDate: {
    type: String,
    default: ''
  },
  currentPhase: {
    type: String,
    default: ''
  }
})

const route = useRoute()
const ordersList = ref([])
const isLoading = ref(true)

const showPending = ref(true)
const showToday = ref(false)

const showConfirmModal = ref(false)
const orderIdToCancel = ref(null)

// 排序狀態
const sortKey = ref('')
const sortOrder = ref('') // 'asc' | 'desc' | ''

// 🚀 內聯渲染排序箭頭元件
const SortIcon = defineComponent({
  props: ['active', 'order'],
  setup(props) {
    return () => {
      let iconText = '⇅'
      let colorClass = 'text-nature-900'

      if (props.active) {
        if (props.order === 'asc') {
          iconText = '▲'
          colorClass = 'text-nature-900'
        } else if (props.order === 'desc') {
          iconText = '▼'
          colorClass = 'text-nature-900'
        }
      }

      return h('span', { 
        class: `inline-block ml-1 align-middle text-01 sm:text-02 lg:text-03 font-bold transition-colors ${colorClass}` 
      }, iconText)
    }
  }
})

const togglePending = () => {
  showPending.value = !showPending.value
  if (showPending.value) {
    showToday.value = false
  }
}

const toggleToday = () => {
  showToday.value = !showToday.value
  if (showToday.value) {
    showPending.value = false
  }
}

const fetchOrders = async () => {
  const saveId = route.query.saveId
  if (!saveId) {
    isLoading.value = false
    return
  }
  
  try {
    const response = await fetch(`/api/saves/${saveId}/orders?limit=100`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    if (response.ok) {
      ordersList.value = await response.json()
    }
  } catch (error) {
    console.error('載入委託紀錄失敗:', error)
  } finally {
    isLoading.value = false
  }
}

const filteredOrders = computed(() => {
  let list = ordersList.value

  if (showPending.value) {
    return list.filter(o => o.status === 'PENDING')
  }

  if (showToday.value) {
    if (!props.currentDate) return list
    const todayStr = props.currentDate.slice(0, 10)
    return list.filter(o => o.sim_date.slice(0, 10) === todayStr)
  }

  return list
})

const sortBy = (key) => {
  if (sortKey.value === key) {
    if (sortOrder.value === 'asc') {
      sortOrder.value = 'desc'
    } else if (sortOrder.value === 'desc') {
      sortOrder.value = ''
      sortKey.value = ''
    }
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}

const sortedRecords = computed(() => {
  if (!sortKey.value || !sortOrder.value) return filteredOrders.value

  const list = [...filteredOrders.value]
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

    if (valA === null || valA === undefined) return 1
    if (valB === null || valB === undefined) return -1

    if (valA < valB) return -1 * order
    if (valA > valB) return 1 * order
    return 0
  })
})

const handleCancelOrder = (orderId) => {
  orderIdToCancel.value = orderId
  showConfirmModal.value = true
}

const closeConfirmModal = () => {
  showConfirmModal.value = false
  orderIdToCancel.value = null
}

const confirmCancelOrder = async () => {
  const orderId = orderIdToCancel.value
  closeConfirmModal()
  if (!orderId) return

  const saveId = route.query.saveId
  try {
    const response = await fetch(`/api/saves/${saveId}/orders/${orderId}`, {
      method: 'DELETE',
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })

    if (response.ok) {
      showToast('已成功撤銷委託！', { type: 'success' })
      fetchOrders()
    } else {
      const errorData = await response.json()
      showToast(`撤單失敗：${errorData.detail || '已成交或已過期'}`, { type: 'error' })
    }
  } catch (error) {
    console.error('撤單 API 連線異常:', error)
    showToast('伺服器連線異常，請稍後再試。', { type: 'error' })
  }
}

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

const formatNumber = (num) => {
  if (num === null || num === undefined) return '-'
  return Number(num).toLocaleString()
}

watch(() => props.currentPhase, () => {
  fetchOrders()
})

watch(() => props.currentDate, () => {
  fetchOrders()
})

onMounted(() => {
  fetchOrders()
})
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
