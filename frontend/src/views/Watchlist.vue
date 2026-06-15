<template>
  <div class="w-full flex flex-col items-center justify-center">
    <!-- 1. 自選股主列表卡片 -->
    <WatchlistCard 
      :stocks="watchlistStocks"
      @select-stock="handleSelectStock"
      @add-stock="openAddWatchlist"
      @next-phase="handleNextPhase"
    />

    <!-- 2. 新增自選股彈窗 -->
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
        :stocks="stocksDb"
        @close="closeAddWatchlist"
        @confirm="confirmAddWatchlist"
        @load-more="loadMoreAddStocks"
      />
    </div>

    <!-- 3. 股票詳細資訊彈窗 -->
    <div 
      v-if="showStockInfoModal && selectedStockDetail" 
      class="fixed inset-0 z-[100] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
      @click.self="showStockInfoModal = false"
    >
      <StockInfo 
        :stock="selectedStockDetail"
        :holdings-count="selectedStockHoldings"
        :prices="klinePrices"
        v-model:timeframe="currentTimeframe"
        @close="showStockInfoModal = false"
        @go-to-trade="handleGoToTrade"
        @view-company-info="handleViewCompanyInfo"
      />
    </div>

    <!-- 4. 公司基本面資訊彈窗 -->
    <CompanyInfo
      v-if="showCompanyInfoModal && companyInfoDetail"
      :stock="companyInfoDetail"
      :suspensions="companyInfoSuspensions"
      @close="showCompanyInfoModal = false; showStockInfoModal = true"
    />

    <!-- 5. 交易成交/失效委託總覽彈窗 -->
    <TradeSettlementModal
      v-if="showSettlementModal"
      :settled-orders="settledOrdersList"
      :previous-phase="previousPhase"
      @close="showSettlementModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import WatchlistCard from '../components/WatchlistCard.vue'
import AddWatchlist from '../components/AddWatchlist.vue'
import StockInfo from '../components/StockInfo.vue'
import CompanyInfo from '../components/CompanyInfo.vue'
import TradeSettlementModal from '../components/TradeSettlementModal.vue'
import { companyProfileCache } from '../api/cache.js'

const props = defineProps({
  saveId: {
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
  }
})

const emit = defineEmits(['refresh-save'])
const router = useRouter()

// --- 狀態定義 ---
const watchlistStocks = ref([])
const showAddWatchlistModal = ref(false)
const showStockInfoModal = ref(false)
const showCompanyInfoModal = ref(false)
const companyInfoDetail = ref(null)
const companyInfoSuspensions = ref([])

const showSettlementModal = ref(false)
const settledOrdersList = ref([])
const previousPhase = ref('')

// K線圖歷史資料與當前選中週期
const klinePrices = ref([])
const currentTimeframe = ref('daily')

// 股票詳細與持股
const selectedStockDetail = ref(null)
const selectedStockHoldings = ref(0)

// 新增自選股彈窗用變數與分頁控制
const addQuery = ref('')
const addSector = ref('')
const addSelectedIds = ref([])
const stocksDb = ref([]) // 所有候選股票
const sectorsList = ref([])

const addLimit = 50
const addOffset = ref(0)
const addHasMore = ref(true)
const addIsLoading = ref(false)

// --- 1. 取得自選股與價格資料 ---
const loadWatchlist = async () => {
  if (!props.saveId) return

  try {
    const response = await fetch(`/api/saves/${props.saveId}/watchlist`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })

    if (!response.ok) return
    const watchlistData = await response.json()

    watchlistStocks.value = watchlistData.map((item) => {
      const price = item.current_price !== null ? parseFloat(item.current_price) : 100
      const change = item.price_change !== null ? parseFloat(item.price_change) : 0
      const changePercent = item.price_change_percent !== null ? parseFloat(item.price_change_percent) : 0
      return {
        id: item.stock_id,
        name: item.stock_name_zh,
        price: price,
        change: parseFloat(change.toFixed(2)),
        changePercent: parseFloat(changePercent.toFixed(2)),
        is_attention: !!item.is_attention,
        is_disposition: !!item.is_disposition,
        is_full_delivery: !!item.is_full_delivery,
        sector_name: item.sector_name
      }
    })
  } catch (error) {
    console.error('取得自選清單異常:', error)
  }
}

// --- 2. 推進下個階段 ---
const handleNextPhase = async () => {
  try {
    const response = await fetch(`/api/saves/${props.saveId}/advance`, {
      method: 'POST',
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })

    if (response.ok) {
      const data = await response.json()
      previousPhase.value = props.currentPhase
      emit('refresh-save') // 通知 Game.vue 重新拉取最新的存檔狀態
      loadWatchlist()

      if (data.settled_orders && data.settled_orders.length > 0) {
        settledOrdersList.value = data.settled_orders
        showSettlementModal.value = true
      }
    } else {
      const errorData = await response.json()
      alert(`推進失敗：${errorData.detail || '未知錯誤'}`)
    }
  } catch (error) {
    console.error('推進階段連線異常:', error)
  }
}

// --- 3. 新增自選股動作與分頁查詢 ---
const fetchSectors = async () => {
  try {
    const res = await fetch('/api/stocks/sectors', {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    if (res.ok) {
      sectorsList.value = await res.json()
    }
  } catch (e) {
    console.error('載載產業別失敗:', e)
  }
}

const fetchStocksPage = async (reset = false) => {
  if (reset) {
    addOffset.value = 0
    addHasMore.value = true
    stocksDb.value = []
  }
  if (!addHasMore.value || addIsLoading.value) return

  addIsLoading.value = true
  try {
    const query = addQuery.value.trim()
    const sector = addSector.value
    let url = `/api/stocks?limit=${addLimit}&offset=${addOffset.value}`
    if (query) url += `&q=${encodeURIComponent(query)}`
    if (sector) url += `&sector=${encodeURIComponent(sector)}`

    const res = await fetch(url, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    if (res.ok) {
      const rows = await res.json()
      if (rows.length < addLimit) {
        addHasMore.value = false
      }
      stocksDb.value = reset ? rows : [...stocksDb.value, ...rows]
      addOffset.value += rows.length
    }
  } catch (error) {
    console.error('載入股票分頁失敗:', error)
  } finally {
    addIsLoading.value = false
  }
}

// 監聽關鍵字或篩選變更 (防抖)
let debounceTimer = null
watch([addQuery, addSector], () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchStocksPage(true)
  }, 300)
})

const loadMoreAddStocks = () => {
  fetchStocksPage(false)
}

const openAddWatchlist = async () => {
  await fetchSectors()
  await fetchStocksPage(true)
  addSelectedIds.value = watchlistStocks.value.map(s => s.id)
  showAddWatchlistModal.value = true
}

const closeAddWatchlist = () => {
  showAddWatchlistModal.value = false
  addQuery.value = ''
  addSector.value = ''
}

const confirmAddWatchlist = async () => {
  const currentIds = watchlistStocks.value.map(s => s.id)
  
  // 計算新增與刪除的項目
  const toAdd = addSelectedIds.value.filter(id => !currentIds.includes(id))
  const toRemove = currentIds.filter(id => !addSelectedIds.value.includes(id))

  try {
    // 執行新增
    for (const stockId of toAdd) {
      await fetch(`/api/saves/${props.saveId}/watchlist`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-session-id': localStorage.getItem('session_id') || ''
        },
        body: JSON.stringify({ stock_id: stockId })
      })
    }

    // 執行刪除
    for (const stockId of toRemove) {
      await fetch(`/api/saves/${props.saveId}/watchlist/${stockId}`, {
        method: 'DELETE',
        headers: {
          'x-session-id': localStorage.getItem('session_id') || ''
        }
      })
    }

    closeAddWatchlist()
    loadWatchlist()
  } catch (error) {
    console.error('同步自選股清單失敗:', error)
    alert('自選股更新失敗，請重試。')
  }
}

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
  } catch (err) {
    console.error('載入 K 線價格資料失敗:', err)
  }
}

// 監聽時間週期切換
watch(currentTimeframe, (newTf) => {
  if (selectedStockDetail.value) {
    fetchKlinePrices(selectedStockDetail.value.stock_id, newTf)
  }
})

// --- 4. 點選股票顯示詳細彈窗 ---
const handleSelectStock = async (stockId) => {
  const stock = watchlistStocks.value.find(s => s.id === stockId)
  if (!stock) return

  // 重設週期為日 K
  currentTimeframe.value = 'daily'
  klinePrices.value = []

  try {
    // 用 Promise.all 平行載入 K線歷史、詳細報價與用戶持股資料
    const [klineData, detailRes, holdingsRes] = await Promise.all([
      fetchKlinePrices(stockId, 'daily'),
      fetch(`/api/saves/${props.saveId}/stocks/${stockId}`, {
        headers: {
          'x-session-id': localStorage.getItem('session_id') || ''
        }
      }),
      fetch(`/api/saves/${props.saveId}/holdings`, {
        headers: {
          'x-session-id': localStorage.getItem('session_id') || ''
        }
      })
    ])
    
    if (!detailRes.ok) throw new Error('無法取得股票詳細報價')
    const detail = await detailRes.json()
    
    selectedStockDetail.value = {
      stock_id: stockId,
      stock_name_zh: detail.stock_name_zh,
      price: detail.current_price,
      change: detail.price_change,
      changePercent: detail.price_change_percent,
      sector_name: detail.sector_name || '未知產業',
      is_attention: detail.is_attention,
      is_disposition: detail.is_disposition,
      is_full_delivery: detail.is_full_delivery,
      
      open_price: detail.open_price,
      high_price: detail.high_price,
      low_price: detail.low_price,
      volume: detail.volume
    }

    if (holdingsRes.ok) {
      const holdings = await holdingsRes.json()
      const userHolding = holdings.find(h => h.stock_id === stockId)
      selectedStockHoldings.value = userHolding ? userHolding.quantity : 0
    } else {
      selectedStockHoldings.value = 0
    }
    
    showStockInfoModal.value = true
  } catch (err) {
    console.error('載入股票詳細失敗:', err)
    selectedStockHoldings.value = 0
    showStockInfoModal.value = true
  }
}

// 響應前往下單
const handleGoToTrade = (stockId) => {
  showStockInfoModal.value = false
  // 導向交易分頁，並攜帶參數
  router.push({
    path: '/game/transact',
    query: { 
      saveId: props.saveId,
      stockId: stockId
    }
  })
}

const handleViewCompanyInfo = async (stockId) => {
  try {
    const hasCache = !!companyProfileCache.value[stockId]

    // 建立平行請求 Promise
    const suspensionsPromise = fetch(`/api/stocks/${stockId}/suspensions?save_id=${props.saveId}`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })

    const profilePromise = hasCache 
      ? Promise.resolve(null)
      : fetch(`/api/stocks/${stockId}`, {
          headers: {
            'x-session-id': localStorage.getItem('session_id') || ''
          }
        })

    const [resProfile, resSuspensions] = await Promise.all([
      profilePromise,
      suspensionsPromise
    ])

    // 處理基本資料快取讀寫
    if (hasCache) {
      companyInfoDetail.value = companyProfileCache.value[stockId]
    } else {
      if (!resProfile || !resProfile.ok) throw new Error('無法取得股票基本資料')
      const profileData = await resProfile.json()
      companyProfileCache.value[stockId] = profileData
      companyInfoDetail.value = profileData
    }

    // 處理暫停交易紀錄
    if (resSuspensions.ok) {
      companyInfoSuspensions.value = await resSuspensions.json()
    } else {
      companyInfoSuspensions.value = []
    }

    showStockInfoModal.value = false
    showCompanyInfoModal.value = true
  } catch (err) {
    console.error('載入基本面資料與暫停交易紀錄失敗:', err)
    alert('載入公司資料失敗，請稍後再試。')
  }
}

// 監聽 saveId、階段、日期的變更以即時刷新資料
watch(
  () => [props.saveId, props.currentPhase, props.currentDate],
  () => {
    loadWatchlist()
  },
  { immediate: true }
)
</script>