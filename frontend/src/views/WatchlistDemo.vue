<!-- 展示頁面，之後應拆成四個檔案 + Game.vue 接上後端 -->
<template>
  <div class="min-h-screen flex flex-col bg-nature-900 text-white">
    <!-- 1. 頂部狀態與導覽組合元件 -->
    <TopBar 
      v-model:activeTab="currentTab"
      date="2026/04/31"
      status="09:00"
      savings="888"
      delivery="999"
    />

    <!-- 2. 主內容區域 (居中排版) -->
    <div class="flex-1 flex flex-col items-center justify-center gap-8 p-6">
      <!-- 自選股列表 -->
      <WatchlistCard 
        v-if="currentTab === '自選'"
        :stocks="mockStocks"
        @select-stock="handleSelectStock"
        @add-stock="handleAddStock"
        @next-phase="handleNextPhase"
      />

      <!-- 下單交易面板 (重構後的分層 UI 元件) -->
      <OrderCard 
        v-if="currentTab === '交易'"
        :stocks="demoStocksDb"
        v-model:stock-id="orderStockId"
        v-model:price="orderPrice"
        v-model:quantity="orderQuantity"
        v-model:side="orderSide"
        v-model:order-type="orderOrderType"
        :is-after-hours="orderIsAfterHours"
        :disabled-market="orderDisabledMarket"
        :stock-error="orderStockError"
        :price-error="orderPriceError"
        :quantity-error="orderQuantityError"
        @select-stock="handleOrderSelectStock"
        @submit="handleOrderSubmit"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import TopBar from '../components/TopBar.vue'
import WatchlistCard from '../components/WatchlistCard.vue'
import BuySellSlider from '../components/BuySellSlider.vue'
import OrderTypeSlider from '../components/OrderTypeSlider.vue'
import StockInput from '../components/StockInput.vue'
import OrderCard from '../components/OrderCard.vue'

// 1. 互動滑塊測試狀態
const sliderState = ref('default')
const orderType = ref('default')
const isAfterHours = ref(false)
const disabledMarket = ref(false)

const resetOrderType = () => {
  orderType.value = isAfterHours.value ? 'after_hours' : 'default'
}

watch(isAfterHours, () => {
  orderType.value = 'default'
})

// 2. 股票搜尋測試狀態
const selectedStockId = ref('')
const showMockError = ref(false)
const lastSelectedStock = ref(null)

const onStockSelect = (stock) => {
  lastSelectedStock.value = stock
}

// 3. 下單交易面板 (分層業務狀態)
const orderStockId = ref('')
const orderPrice = ref('')
const orderQuantity = ref(1)
const orderSide = ref('default')
const orderOrderType = ref('default')
const orderIsAfterHours = ref(false)
const orderDisabledMarket = ref(false)

const orderStockError = ref('')
const orderPriceError = ref('')
const orderQuantityError = ref('')

// 模擬後端股票資料庫
const demoStocksDb = [
  { stock_id: '2330', stock_name_zh: '台積電', market_type: '上市' },
  { stock_id: '2317', stock_name_zh: '鴻海', market_type: '上市' },
  { stock_id: '2454', stock_name_zh: '聯發科', market_type: '上市' },
  { stock_id: '2337', stock_name_zh: '旺宏', market_type: '上市' },
  { stock_id: '2338', stock_name_zh: '光罩', market_type: '上市' },
  { stock_id: '2331', stock_name_zh: '精英', market_type: '上市' },
  { stock_id: '2332', stock_name_zh: '友訊', market_type: '上市' },
  { stock_id: '0050', stock_name_zh: '元大台灣50', market_type: '上市' },
  { stock_id: '00919', stock_name_zh: '群益台灣精選高息', market_type: '上市' },
  { stock_id: '2308', stock_name_zh: '台達電', market_type: '上市' },
  { stock_id: '23303.HK', stock_name_zh: '23303', market_type: '港股' },
  { stock_id: '2330345.HK', stock_name_zh: '海亮國際', market_type: '港股' },
  { stock_id: '2887', stock_name_zh: '台新金', market_type: '上市' }
]

// 模擬股票搜尋
const demoSuggestions = computed(() => {
  const query = selectedStockId.value.trim().toLowerCase()
  if (!query) return []
  return demoStocksDb.filter(stock => 
    stock.stock_id.toLowerCase().includes(query) || 
    stock.stock_name_zh.toLowerCase().includes(query)
  )
})

// 模擬股票參考價 (業務規則)
const getRefPrice = (id) => {
  if (!id) return 0
  if (id === '2330') return 2450
  if (id === '48763') return 16
  if (id === '0050') return 150
  if (id === '2317') return 180
  if (id === '2454') return 1200
  if (id === '2603') return 190
  if (id === '3008') return 2200
  if (id === '2308') return 340
  const num = parseInt(id.replace(/\D/g, '')) || 100
  return (num % 500) + 10
}

// 監聽委託類型切換，自動填入價格 (業務與輸入框連動)
watch(orderOrderType, (newVal) => {
  orderPriceError.value = ''
  if (newVal === 'market') {
    orderPrice.value = '市價'
  } else if (newVal === 'after_hours') {
    orderPrice.value = '定價'
  } else {
    orderPrice.value = getRefPrice(orderStockId.value) || ''
  }
})

// 監聽股號更換，自動更新為參考價 (業務與輸入框連動)
watch(orderStockId, (newId) => {
  orderStockError.value = ''
  if (orderOrderType.value === 'limit' || orderOrderType.value === 'default') {
    orderPrice.value = getRefPrice(newId) || ''
  }
})

// 點選 WatchlistCard 股票，連動更新下單面板並切換至交易分頁
const handleSelectStock = (stockId) => {
  console.log('自選股點選股票代碼:', stockId)
  orderStockId.value = stockId
  orderPrice.value = getRefPrice(stockId) || ''
  currentTab.value = '交易'
}

// OrderCard 內部選中股票
const handleOrderSelectStock = (stock) => {
  orderStockId.value = stock.stock_id
  orderPrice.value = getRefPrice(stock.stock_id) || ''
}

// 點擊確認下單，執行業務校驗與防錯
const handleOrderSubmit = () => {
  orderStockError.value = ''
  orderPriceError.value = ''
  orderQuantityError.value = ''

  let isValid = true

  // 1. 校驗股票編號
  if (!orderStockId.value) {
    orderStockError.value = '請輸入並選取股票代碼'
    isValid = false
  } else {
    const exists = demoStocksDb.some(s => s.stock_id === orderStockId.value)
    if (!exists) {
      orderStockError.value = '請選擇清單中的有效股票'
      isValid = false
    }
  }

  // 2. 校驗買賣設定
  if (orderSide.value === 'default') {
    orderStockError.value = orderStockError.value 
      ? orderStockError.value + ' | 請設定買進或賣出' 
      : '請點選設定買進或賣出'
    isValid = false
  }

  // 3. 校驗委託類型
  if (orderOrderType.value === 'default') {
    orderPriceError.value = '請選擇委託類型'
    isValid = false
  }

  // 4. 校驗委託價格 (僅限價單)
  if (orderOrderType.value === 'limit') {
    const pVal = parseFloat(orderPrice.value)
    if (isNaN(pVal) || pVal <= 0) {
      orderPriceError.value = '請輸入有效價格'
      isValid = false
    }
  }

  // 5. 校驗委託張數
  if (orderQuantity.value < 1) {
    orderQuantityError.value = '委託張數至少需要 1 張'
    isValid = false
  }

  if (!isValid) return

  alert(`🎉 模擬下單委託成功！
股票代碼：${orderStockId.value}
買賣方向：${orderSide.value === 'buy' ? '買進' : '賣出'}
委託類型：${orderOrderType.value === 'limit' ? '限價' : orderOrderType.value === 'market' ? '市價' : '盤後定價'}
委託價格：${orderPrice.value}
委託張數：${orderQuantity.value} 張`)
}

// 其他全局狀態與 Mock 資料
const currentTab = ref('自選')
const mockStocks = ref([
  { id: '2330', name: '台積電', price: 2450, change: 45, changePercent: 1.87 },
  { id: '48763', name: '我的桐人', price: 16, change: -2, changePercent: -11.11 },
  { id: '0050', name: '元大台灣50', price: 150, change: 0, changePercent: 0.00 },
  { id: '2317', name: '鴻海', price: 180, change: 3, changePercent: 1.69 },
  { id: '2454', name: '聯發科', price: 1200, change: -15, changePercent: -1.23 },
  { id: '2603', name: '長榮', price: 190, change: 0, changePercent: 0.00 },
  { id: '3008', name: '大立光', price: 2200, change: 50, changePercent: 2.33 },
  { id: '2308', name: '台達電', price: 340, change: -5, changePercent: -1.45 },
  { id: '2881', name: '富邦金', price: 75, change: 0.5, changePercent: 0.67 },
  { id: '2882', name: '國泰金', price: 58, change: -0.2, changePercent: -0.34 },
  { id: '2883', name: '開發金', price: 12, change: 0, changePercent: 0.00 },
  { id: '2884', name: '玉山金', price: 25, change: 0.1, changePercent: 0.40 },
  { id: '2885', name: '兆豐金', price: 30, change: -0.3, changePercent: -1.00 },
  { id: '2886', name: '台新金', price: 20, change: 0, changePercent: 0.00 },
  { id: '2887', name: '永豐金', price: 15, change: 0.2, changePercent: 1.35 }
])

const handleAddStock = () => {
  alert('點擊了「新增自選股」按鈕，準備開啟搜尋股票視窗！')
}

const handleNextPhase = () => {
  alert('點擊了「進入下一階段」按鈕，準備進行委託單撮合與時空推進！')
}
</script>

<style scoped>
/* Additional page-scoped styles if needed */
</style>
