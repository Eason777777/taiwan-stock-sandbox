<template>
  <div class="w-full flex flex-col items-center justify-center">
    <!-- 1. 資產整合卡片 (包含餘額與庫存持股) -->
    <InventoryCard 
      :delivery-balance="deliveryBalance"
      :savings-balance="savingsBalance"
      :holdings="mappedHoldings"
      @update-balances="handleUpdateBalances"
      @select-stock="handleSelectStock"
    />

    <!-- 2. 股票詳細資訊彈窗 -->
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

    <!-- 3. 公司基本面資訊彈窗 -->
    <CompanyInfo
      v-if="showCompanyInfoModal && companyInfoDetail"
      :stock="companyInfoDetail"
      :suspensions="companyInfoSuspensions"
      @close="showCompanyInfoModal = false; showStockInfoModal = true"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import InventoryCard from '../components/InventoryCard.vue'
import StockInfo from '../components/StockInfo.vue'
import CompanyInfo from '../components/CompanyInfo.vue'
import { companyProfileCache } from '../api/cache.js'
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
  }
})

const emit = defineEmits(['update-balances'])
const router = useRouter()

// --- 狀態定義 ---
const rawHoldings = ref([])
const showStockInfoModal = ref(false)
const showCompanyInfoModal = ref(false)
const companyInfoDetail = ref(null)
const companyInfoSuspensions = ref([])
const selectedStockDetail = ref(null)
const selectedStockHoldings = ref(0)

// K線圖歷史資料與當前選中週期
const klinePrices = ref([])
const currentTimeframe = ref('daily')

// --- 1. 資料轉換 (將後端欄位映射為前端 HoldingInfo 期待的欄位) ---
const mappedHoldings = computed(() => {
  return rawHoldings.value.map(h => ({
    stock_id: h.stock_id,
    stock_name: h.stock_name_zh,
    quantity: h.quantity,
    profit_loss: h.unrealized_pnl,
    profit_rate: h.unrealized_pnl_pct,
    current_price: h.market_price || h.avg_cost, // 當天無現價則回退至成本價
    avg_cost: h.avg_cost
  }))
})

// --- 2. 撈取使用者真實持股 API ---
const fetchHoldings = async () => {
  if (!props.saveId) return

  try {
    const response = await fetch(`/api/saves/${props.saveId}/holdings`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })

    if (response.ok) {
      rawHoldings.value = await response.json()
    }
  } catch {
  }
}

// --- 3. 處理轉帳 API (將前端計算之差值同步給後端資料庫) ---
const handleUpdateBalances = async (newDelivery, newSavings) => {
  const diff = newSavings - props.savingsBalance
  if (diff === 0) return

  const direction = diff > 0 ? 'trading_to_savings' : 'savings_to_trading'
  const amount = Math.abs(diff)

  try {
    const response = await fetch(`/api/saves/${props.saveId}/accounts/transfer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-session-id': localStorage.getItem('session_id') || ''
      },
      body: JSON.stringify({ direction, amount })
    })

    if (response.ok) {
      const data = await response.json()
      // 同步頂部狀態列餘額
      emit('update-balances', data.trading_balance, data.savings_balance)
      showToast('轉帳完成！', { type: 'success' })
    } else {
      const errorData = await response.json()
      showToast(`轉帳失敗：${errorData.detail || '帳戶餘額不足'}`, { type: 'error' })
    }
  } catch {
    showToast('伺服器連線異常，請稍後再試。', { type: 'error' })
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
  } catch {
  }
}

// 監聽時間週期切換
watch(currentTimeframe, (newTf) => {
  if (selectedStockDetail.value) {
    fetchKlinePrices(selectedStockDetail.value.stock_id, newTf)
  }
})

// --- 4. 點選庫存持股列，打開詳細彈窗 ---
const handleSelectStock = async (stockId) => {
  const holding = mappedHoldings.value.find(h => h.stock_id === stockId)
  if (!holding) return

  // 重設週期為日 K
  currentTimeframe.value = 'daily'
  klinePrices.value = []

  try {
    // 用 Promise.all 平行載入 K線歷史與詳細報價
    const [, detailRes] = await Promise.all([
      fetchKlinePrices(stockId, 'daily'),
      fetch(`/api/saves/${props.saveId}/stocks/${stockId}`, {
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

    selectedStockHoldings.value = holding.quantity
    showStockInfoModal.value = true
  } catch {
    selectedStockHoldings.value = holding.quantity
    showStockInfoModal.value = true
  }
}

// 響應前往下單
const handleGoToTrade = (stockId) => {
  showStockInfoModal.value = false
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
  } catch {
    showToast('載入公司資料失敗，請稍後再試。', { type: 'error' })
  }
}

// 監聽 saveId、階段、日期的變更以即時更新持股與資產
watch(
  () => [props.saveId, props.currentPhase, props.currentDate],
  () => {
    fetchHoldings()
  },
  { immediate: true }
)
</script>