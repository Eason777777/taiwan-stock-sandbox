<template>
  <div class="min-h-screen flex flex-col bg-nature-900 text-white">
    <!-- 1. 頂部狀態與導覽組合元件 -->
    <TopBar 
      v-model:activeTab="currentTab"
      date="2026/04/31"
      status="09:00"
      :savings="savingsAmount.toLocaleString()"
      :delivery="deliveryAmount.toLocaleString()"
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

      <!-- 資產分頁 -->
      <InventoryCard 
        v-if="currentTab === '資產'"
        :delivery-balance="deliveryAmount"
        :savings-balance="savingsAmount"
        :holdings="demoHoldings"
        @update-balances="handleUpdateBalances"
        @select-stock="handleSelectStock"
      />
    </div>

    <!-- 新增自選股彈窗遮罩與主體 -->
    <div 
      v-if="showAddWatchlistModal" 
      class="fixed inset-0 z-[100] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
      @click.self="closeAddWatchlist"
    >
      <AddWatchlist 
        v-model:searchQuery="addQuery"
        v-model:selectedSector="addSector"
        v-model:selectedStockIds="addSelectedIds"
        :sectors="sectorsList"
        :stocks="filteredAddStocks"
        @close="closeAddWatchlist"
        @confirm="confirmAddWatchlist"
      />
    </div>

    <!-- 股票詳細資訊彈窗遮罩與主體 -->
    <div 
      v-if="showStockInfoModal && selectedStockDetail" 
      class="fixed inset-0 z-[100] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
      @click.self="showStockInfoModal = false"
    >
      <StockInfo 
        :stock="selectedStockDetail"
        :holdings-count="selectedStockHoldings"
        @close="showStockInfoModal = false"
        @go-to-trade="handleGoToTrade"
        @view-company-info="handleViewCompanyInfo"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import TopBar from '../components/TopBar.vue'
import WatchlistCard from '../components/WatchlistCard.vue'
import OrderCard from '../components/OrderCard.vue'
import AddWatchlist from '../components/AddWatchlist.vue'
import StockInfo from '../components/StockInfo.vue'
import InventoryCard from '../components/InventoryCard.vue'

// 0. 資產與帳戶狀態
const deliveryAmount = ref(2000)
const savingsAmount = ref(1000)

const handleUpdateBalances = (newDelivery, newSavings) => {
  deliveryAmount.value = newDelivery
  savingsAmount.value = newSavings
}

// 0.5 模擬持股狀態
const demoHoldings = ref([
  {
    stock_id: '0120',
    stock_name: '海星星',
    quantity: 34.5,
    profit_loss: 225,
    profit_rate: 29.4,
    current_price: 106,
    avg_cost: 68
  },
  {
    stock_id: '0121',
    stock_name: '超級飽食海星',
    quantity: 80,
    profit_loss: -60,
    profit_rate: -7.8,
    current_price: 207,
    avg_cost: 182
  },
  {
    stock_id: '0122',
    stock_name: '寶石海星',
    quantity: 15,
    profit_loss: 450,
    profit_rate: 15.0,
    current_price: 330,
    avg_cost: 300
  },
  {
    stock_id: '0123',
    stock_name: '可達鴨',
    quantity: 120,
    profit_loss: -1200,
    profit_rate: -12.5,
    current_price: 70,
    avg_cost: 80
  },
  {
    stock_id: '0124',
    stock_name: '哥達鴨',
    quantity: 50,
    profit_loss: 0,
    profit_rate: 0.0,
    current_price: 150,
    avg_cost: 150
  },
  {
    stock_id: '0125',
    stock_name: '蚊香蝌蚪',
    quantity: 200,
    profit_loss: 800,
    profit_rate: 40.0,
    current_price: 14,
    avg_cost: 10
  },
  {
    stock_id: '0126',
    stock_name: '蚊香君',
    quantity: 60,
    profit_loss: -300,
    profit_rate: -5.0,
    current_price: 95,
    avg_cost: 100
  },
  {
    stock_id: '0127',
    stock_name: '蚊香泳士',
    quantity: 10,
    profit_loss: 2500,
    profit_rate: 125.0,
    current_price: 450,
    avg_cost: 200
  }
])

// 1. 下單交易面板 (分層業務狀態)
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

// 2. 新增自選股彈窗業務狀態
const showAddWatchlistModal = ref(false)
const addQuery = ref('')
const addSector = ref('')
const addSelectedIds = ref([])

// 3. 股票詳細資訊彈窗業務狀態
const showStockInfoModal = ref(false)
const selectedStockDetail = ref(null)
const selectedStockHoldings = ref(0)

// 模擬後端股票資料庫 (豐富了產業別)
const demoStocksDb = [
  { stock_id: '2330', stock_name_zh: '台積電', market_type: '上市', sector_name: '半導體業' },
  { stock_id: '2317', stock_name_zh: '鴻海', market_type: '上市', sector_name: '其他電子業' },
  { stock_id: '2454', stock_name_zh: '聯發科', market_type: '上市', sector_name: '半導體業' },
  { stock_id: '2337', stock_name_zh: '旺宏', market_type: '上市', sector_name: '半導體業' },
  { stock_id: '2338', stock_name_zh: '光罩', market_type: '上市', sector_name: '半導體業' },
  { stock_id: '2331', stock_name_zh: '精英', market_type: '上市', sector_name: '電腦及週邊設備業' },
  { stock_id: '2332', stock_name_zh: '友訊', market_type: '上市', sector_name: '通信網路業' },
  { stock_id: '0050', stock_name_zh: '元大台灣50', market_type: '上市', sector_name: 'ETF' },
  { stock_id: '00919', stock_name_zh: '群益台灣精選高息', market_type: '上市', sector_name: 'ETF' },
  { stock_id: '2308', stock_name_zh: '台達電', market_type: '上市', sector_name: '電子零組件業' },
  { stock_id: '23303.HK', stock_name_zh: '23303', market_type: '港股', sector_name: '港股' },
  { stock_id: '2330345.HK', stock_name_zh: '海亮國際', market_type: '港股', sector_name: '港股' },
  { stock_id: '2887', stock_name_zh: '台新金', market_type: '上市', sector_name: '金融保險業' },
  { stock_id: '0120', stock_name_zh: '海星星', market_type: '上市', sector_name: '神奇寶貝業' },
  { stock_id: '0121', stock_name_zh: '超級飽食海星', market_type: '上市', sector_name: '神奇寶貝業' },
  { stock_id: '0122', stock_name_zh: '寶石海星', market_type: '上市', sector_name: '神奇寶貝業' },
  { stock_id: '0123', stock_name_zh: '可達鴨', market_type: '上市', sector_name: '神奇寶貝業' },
  { stock_id: '0124', stock_name_zh: '哥達鴨', market_type: '上市', sector_name: '神奇寶貝業' },
  { stock_id: '0125', stock_name_zh: '蚊香蝌蚪', market_type: '上市', sector_name: '神奇寶貝業' },
  { stock_id: '0126', stock_name_zh: '蚊香君', market_type: '上市', sector_name: '神奇寶貝業' },
  { stock_id: '0127', stock_name_zh: '蚊香泳士', market_type: '上市', sector_name: '神奇寶貝業' }
]

// 提取獨立的產業別清單供下拉選單使用
const sectorsList = computed(() => {
  const allSectors = demoStocksDb.map(s => s.sector_name)
  return [...new Set(allSectors.filter(Boolean))]
})

// 依據搜尋詞與產業篩選候選清單
const filteredAddStocks = computed(() => {
  return demoStocksDb.filter(stock => {
    const matchesQuery = !addQuery.value.trim() || 
      stock.stock_id.toLowerCase().includes(addQuery.value.trim().toLowerCase()) ||
      stock.stock_name_zh.toLowerCase().includes(addQuery.value.trim().toLowerCase())
    
    const matchesSector = !addSector.value || stock.sector_name === addSector.value

    return matchesQuery && matchesSector
  })
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

// 模擬持股狀態 (業務規則)
const getMockHoldings = (id) => {
  if (id === '2330') return 5
  if (id === '2317') return 10
  if (id === '2887') return 20
  return 0
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

// 點選股票，跳出詳細資訊彈窗 (自選股清單或持股清單點擊觸發)
const handleSelectStock = (stockId) => {
  console.log('點選股票代碼:', stockId)
  
  const watchlistStock = mockStocks.value.find(s => s.id === stockId)
  const dbStock = demoStocksDb.find(s => s.stock_id === stockId)
  const holdingStock = demoHoldings.value.find(h => h.stock_id === stockId)
  
  let name = '未知股票'
  let price = 0
  let change = 0
  let changePercent = 0
  
  if (watchlistStock) {
    name = watchlistStock.name
    price = watchlistStock.price
    change = watchlistStock.change
    changePercent = watchlistStock.changePercent
  } else if (holdingStock) {
    name = holdingStock.stock_name
    price = holdingStock.current_price
    change = holdingStock.profit_loss
    changePercent = holdingStock.profit_rate
  } else if (dbStock) {
    name = dbStock.stock_name_zh
    price = getRefPrice(stockId)
  }
  
  const isETF = stockId === '0050' || stockId === '00919'
  const isHongKong = stockId.endsWith('.HK')
  
  selectedStockDetail.value = {
    stock_id: stockId,
    stock_name_zh: name,
    price: price,
    change: change,
    changePercent: changePercent,
    sector_name: dbStock ? dbStock.sector_name : '未知產業',
    is_attention: stockId === '2330' || stockId === '2454' || stockId === '2317' || stockId === '2887',
    is_disposition: stockId === '2330' || stockId === '2308' || stockId === '2887',
    is_full_delivery: stockId === '48763' || stockId === '2317' || stockId === '2308' || stockId === '2887',
    
    // ETF 或港股模擬 null 值情形
    open_price: isHongKong ? null : price * 0.99,
    high_price: isETF ? null : price * 1.02,
    low_price: isHongKong || isETF ? null : price * 0.97,
    volume: isETF ? null : Math.round(5000 + Math.random() * 45000)
  }
  
  selectedStockHoldings.value = getMockHoldings(stockId) || (holdingStock ? holdingStock.quantity : 0)
  showStockInfoModal.value = true
}

// 響應「前往下單」事件：跳轉交易頁面
const handleGoToTrade = (stockId) => {
  showStockInfoModal.value = false
  orderStockId.value = stockId
  orderPrice.value = getRefPrice(stockId) || ''
  currentTab.value = '交易'
}

// 響應「查看公司資訊」事件
const handleViewCompanyInfo = (stockId) => {
  alert(`🏢 準備為您載入股票代碼 ${stockId} 的公司詳細資訊（此彈窗功能將於後續實作）`)
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

// 點擊新增自選股按鈕開彈窗
const handleAddStock = () => {
  addQuery.value = ''
  addSector.value = ''
  addSelectedIds.value = []
  showAddWatchlistModal.value = true
}

const closeAddWatchlist = () => {
  showAddWatchlistModal.value = false
}

// 確認將勾選股票加入自選
const confirmAddWatchlist = () => {
  addSelectedIds.value.forEach(id => {
    const exists = mockStocks.value.some(s => s.id === id)
    if (!exists) {
      const stockInfo = demoStocksDb.find(s => s.stock_id === id)
      if (stockInfo) {
        mockStocks.value.push({
          id: stockInfo.stock_id,
          name: stockInfo.stock_name_zh,
          price: getRefPrice(stockInfo.stock_id),
          // 產生模擬隨機漲跌
          change: Number(((Math.random() - 0.5) * 10).toFixed(2)),
          changePercent: Number(((Math.random() - 0.5) * 5).toFixed(2))
        })
      }
    }
  })
  showAddWatchlistModal.value = false
}

const handleNextPhase = () => {
  alert('點擊了「進入下一階段」按鈕，準備進行委託單撮合與時空推進！')
}
</script>

<style scoped>
/* Additional page-scoped styles if needed */
</style>
