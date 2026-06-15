<template>
  <div class="w-full flex flex-col items-center justify-center">
    <!-- 1. 下單交易面版 -->
    <OrderCard
      :stocks="stocksDb"
      v-model:stock-id="orderStockId"
      v-model:price="orderPrice"
      v-model:quantity="orderQuantity"
      v-model:side="orderSide"
      v-model:order-type="orderOrderType"
      :is-after-hours="orderIsAfterHours"
      :disabled-market="orderDisabledMarket"
      :disabled="saveStatus !== 'ACTIVE'"
      :stock-error="orderStockError"
      :price-error="orderPriceError"
      :quantity-error="orderQuantityError"
      :prices="klinePrices"
      v-model:timeframe="currentTimeframe"
      :stock-name="orderStockName"
      :orders="ordersList"
      :current-date="currentDate"
      :current-phase="currentPhase"
      @select-stock="handleOrderSelectStock"
      @search-stock="handleSearchStock"
      @load-more-stocks="handleLoadMoreStocks"
      @submit="handleOrderSubmit"
      @cancel-order="handleCancelOrder"
    />

    <!-- 2. 撤單確認彈窗 -->
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
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import OrderCard from '../components/OrderCard.vue'
import ConfirmModal from '../components/ConfirmModal.vue'
import { showToast } from '../components/Toast.vue'

const props = defineProps({
  saveId: {
    type: Number,
    required: true
  },
  savingsBalance: {
    type: Number,
    required: true
  },
  deliveryBalance: {
    type: Number,
    required: true
  },
  currentPhase: {
    type: String,
    required: true
  },
  currentDate: {
    type: String,
    required: true
  },
  saveStatus: {
    type: String,
    default: 'ACTIVE'
  }
})

const emit = defineEmits(['refresh-save'])
const route = useRoute()

// --- 狀態與分頁定義 ---
const stocksDb = ref([]) // 所有候選股票列表
const searchLimit = 50
const searchOffset = ref(0)
const searchHasMore = ref(true)
const searchIsLoading = ref(false)
const searchQuery = ref('')

const orderStockId = ref('')
const orderStockName = ref('')
const klinePrices = ref([])
const currentTimeframe = ref('daily')
const orderPrice = ref('')
const orderQuantity = ref(1)
const orderSide = ref('default')
const orderOrderType = ref('default')
const orderIsAfterHours = ref(false)
const orderDisabledMarket = ref(false)

const orderStockError = ref('')
const orderPriceError = ref('')
const orderQuantityError = ref('')

// --- 1. 載入可用股票資料庫 (分頁加載) ---
const fetchStocksPage = async (reset = false) => {
  if (reset) {
    searchOffset.value = 0
    searchHasMore.value = true
  }
  if (!searchHasMore.value || searchIsLoading.value) return

  searchIsLoading.value = true
  try {
    const q = searchQuery.value.trim()
    let url = `/api/stocks?limit=${searchLimit}&offset=${searchOffset.value}`
    if (q) {
      url += `&q=${encodeURIComponent(q)}`
    }
    const response = await fetch(url, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    if (response.ok) {
      const rows = await response.json()
      if (rows.length < searchLimit) {
        searchHasMore.value = false
      }
      stocksDb.value = reset ? rows : [...stocksDb.value, ...rows]
      searchOffset.value += rows.length
    }
  } catch {
  } finally {
    searchIsLoading.value = false
  }
}

let searchDebounceTimer = null
const handleSearchStock = (query) => {
  searchQuery.value = query
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    fetchStocksPage(true)
  }, 300)
}

const handleLoadMoreStocks = () => {
  fetchStocksPage(false)
}

// 根據目前遊戲階段，設定交易面板的預設可用性
const applyPhaseRestrictions = () => {
  // 盤前：僅限限價單
  if (props.currentPhase === 'PRE_MARKET') {
    orderDisabledMarket.value = true
    orderIsAfterHours.value = false
    if (orderOrderType.value === 'market') {
      orderOrderType.value = 'limit'
    }
  } 
  // 盤後：僅限定價單 (在前端映射為 after_hours 頁，送出時會轉為 MARKET 給後端)
  else if (props.currentPhase === 'POST_MARKET') {
    orderDisabledMarket.value = false
    orderIsAfterHours.value = true
    orderOrderType.value = 'after_hours'
    orderPrice.value = '定價'
  } 
  // 盤中：不限制
  else {
    orderDisabledMarket.value = false
    orderIsAfterHours.value = false
    if (orderOrderType.value === 'after_hours') {
      orderOrderType.value = 'default'
      orderPrice.value = ''
    }
  }
}

// 取得股票參考價
const getRefPrice = async (stockId) => {
  if (!stockId) return 0
  try {
    const res = await fetch(`/api/stocks/${stockId}/prices?save_id=${props.saveId}&limit=1`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    if (res.ok) {
      const history = await res.json()
      if (history && history.length > 0) {
        const latest = history[history.length - 1]
        return latest.close_price || latest.ref_price || 100
      }
    }
  } catch {
  }
  return 100
}

// --- 2. 監聽委託類型切換，自動填入價格 ---
watch(orderOrderType, async (newVal) => {
  orderPriceError.value = ''
  if (newVal === 'market') {
    orderPrice.value = '市價'
  } else if (newVal === 'after_hours') {
    orderPrice.value = '定價'
  } else {
    const refP = await getRefPrice(orderStockId.value)
    orderPrice.value = refP ? refP.toString() : ''
  }
})

// 載入 K 線價格資料的獨立函式
const fetchKlinePrices = async (stockId, tf) => {
  if (!props.saveId || !stockId) return
  const intervalMap = { daily: 'day', weekly: 'week', monthly: 'month' }
  const interval = intervalMap[tf] || 'day'
  
  try {
    const res = await fetch(`/api/stocks/${stockId}/prices?save_id=${props.saveId}&interval=${interval}`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    if (res.ok) {
      klinePrices.value = await res.json()
    }
  } catch {
  }
}

// 監聽時間週期切換
watch(currentTimeframe, (newTf) => {
  if (orderStockId.value) {
    fetchKlinePrices(orderStockId.value, newTf)
  }
})

// --- 3. 監聽股號更換，自動更新為參考價與 K 線資料 ---
watch(orderStockId, async (newId) => {
  orderStockError.value = ''
  
  klinePrices.value = []
  orderStockName.value = ''
  
  if (!newId) return

  // 取得參考價
  if (orderOrderType.value === 'limit' || orderOrderType.value === 'default') {
    const refP = await getRefPrice(newId)
    orderPrice.value = refP ? refP.toString() : ''
  }

  // 載入 K 線歷史價格
  if (currentTimeframe.value === 'daily') {
    await fetchKlinePrices(newId, 'daily')
  } else {
    currentTimeframe.value = 'daily'
  }

  // 載入股票名稱
  try {
    const res = await fetch(`/api/saves/${props.saveId}/stocks/${newId}`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    if (res.ok) {
      const detail = await res.json()
      orderStockName.value = detail.stock_name_zh || ''
    }
  } catch {
  }
})

// 點選推薦股號
const handleOrderSelectStock = async (stock) => {
  const stockId = typeof stock === 'object' && stock !== null ? stock.stock_id : stock
  orderStockId.value = stockId
}

// --- 4. 送出下單委託 API ---
const handleOrderSubmit = async () => {
  orderStockError.value = ''
  orderPriceError.value = ''
  orderQuantityError.value = ''

  // 基礎驗證
  if (!orderStockId.value) {
    orderStockError.value = '請輸入股號'
    return
  }
  if (orderSide.value === 'default') {
    showToast('請選擇買入或賣出！', { type: 'warning' })
    return
  }
  if (orderOrderType.value === 'default') {
    showToast('請選擇委託類型！', { type: 'warning' })
    return
  }
  if (!orderQuantity.value || orderQuantity.value < 1) {
    orderQuantityError.value = '張數必須大於等於 1'
    return
  }

  // 轉換為後端規格
  const uppercaseSide = orderSide.value === 'buy' ? 'BUY' : 'SELL'
  
  // 盤後定價單(after_hours)與市價單(market)在後端皆為 MARKET 類型，且皆不需傳 price 欄位
  const isMarket = orderOrderType.value === 'market' || orderOrderType.value === 'after_hours'
  const backendOrderType = isMarket ? 'MARKET' : 'LIMIT'
  const backendPrice = isMarket ? null : parseFloat(orderPrice.value)

  if (backendOrderType === 'LIMIT' && (isNaN(backendPrice) || backendPrice <= 0)) {
    orderPriceError.value = '請輸入有效的限價金額'
    return
  }

  const payload = {
    stock_id: orderStockId.value,
    order_type: backendOrderType,
    side: uppercaseSide,
    price: backendPrice,
    quantity: parseInt(orderQuantity.value)
  }

  try {
    const response = await fetch(`/api/saves/${props.saveId}/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-session-id': localStorage.getItem('session_id') || ''
      },
      body: JSON.stringify(payload)
    })

    if (response.ok) {
      showToast('委託下單成功！', { type: 'success' })
      emit('refresh-save') // 刷新 Game.vue 之帳戶資金
      fetchOrders()
      
      // 清空表單
      orderStockId.value = ''
      orderPrice.value = ''
      orderQuantity.value = 1
      orderSide.value = 'default'
      orderOrderType.value = 'default'
    } else {
      const errorData = await response.json()
      showToast(`下單失敗：${errorData.detail || '餘額不足或非交易時段'}`, { type: 'error' })
    }
  } catch {
    showToast('伺服器連線異常，請稍後再試。', { type: 'error' })
  }
}

// 監聽來自自選股點選「前往下單」的路由參數，相容 keep-alive 快取
watch(() => route.query.stockId, (newStockId) => {
  if (newStockId) {
    orderStockId.value = newStockId.toString()
  }
}, { immediate: true })

// --- 5. 委託單列表資料讀取與撤單 ---
const ordersList = ref([])
const showConfirmModal = ref(false)
const orderIdToCancel = ref(null)

const fetchOrders = async () => {
  if (!props.saveId) return
  try {
    const response = await fetch(`/api/saves/${props.saveId}/orders?limit=100`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    if (response.ok) {
      ordersList.value = await response.json()
    }
  } catch {
  }
}

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

  try {
    const response = await fetch(`/api/saves/${props.saveId}/orders/${orderId}`, {
      method: 'DELETE',
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })

    if (response.ok) {
      showToast('已成功撤銷委託！', { type: 'success' })
      emit('refresh-save') // 刷新交割戶與持股狀態
      fetchOrders() // 重新載入列表
    } else {
      const errorData = await response.json()
      showToast(`撤單失敗：${errorData.detail || '已成交或已過期'}`, { type: 'error' })
    }
  } catch {
    showToast('伺服器連線異常，請稍後再試。', { type: 'error' })
  }
}

// 監聽存檔變更
watch(() => props.saveId, () => {
  fetchOrders()
}, { immediate: true })

onMounted(() => {
  fetchStocksPage(true)
  applyPhaseRestrictions()
  fetchOrders()
})

watch(() => props.currentPhase, () => {
  applyPhaseRestrictions()
  fetchOrders()
})
</script>