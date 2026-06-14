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
        @close="showStockInfoModal = false"
        @go-to-trade="handleGoToTrade"
        @view-company-info="handleViewCompanyInfo"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import InventoryCard from '../components/InventoryCard.vue'
import StockInfo from '../components/StockInfo.vue'

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
const selectedStockDetail = ref(null)
const selectedStockHoldings = ref(0)

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
  } catch (error) {
    console.error('撈取持股庫存異常:', error)
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
      alert('轉帳完成！')
    } else {
      const errorData = await response.json()
      alert(`轉帳失敗：${errorData.detail || '帳戶餘額不足'}`)
    }
  } catch (error) {
    console.error('呼叫轉帳 API 連線異常:', error)
    alert('伺服器連線異常，請稍後再試。')
  }
}

// --- 4. 點選庫存持股列，打開詳細彈窗 ---
const handleSelectStock = (stockId) => {
  const holding = mappedHoldings.value.find(h => h.stock_id === stockId)
  if (!holding) return

  // 取得最新日線資訊，以補全彈窗需要的高/開/低/量
  fetch(`/api/stocks/${stockId}/prices?save_id=${props.saveId}&limit=5`, {
    headers: {
      'x-session-id': localStorage.getItem('session_id') || ''
    }
  })
    .then(res => res.json())
    .then(history => {
      const latest = history && history.length > 0 ? history[history.length - 1] : {}
      
      let change = 0
      let changePercent = 0
      if (props.currentPhase !== 'PRE_MARKET' && latest && latest.close_price) {
        change = holding.current_price - latest.close_price
        changePercent = (change / latest.close_price) * 100
      }

      selectedStockDetail.value = {
        stock_id: stockId,
        stock_name_zh: holding.stock_name,
        price: holding.current_price,
        change: parseFloat(change.toFixed(2)),
        changePercent: parseFloat(changePercent.toFixed(2)),
        sector_name: latest.sector_name || '未知產業',
        is_attention: latest.is_attention || false,
        is_disposition: latest.is_disposition || false,
        is_full_delivery: latest.is_full_delivery || false,
        
        open_price: latest.open_price || null,
        high_price: latest.high_price || null,
        low_price: latest.low_price || null,
        volume: latest.volume || 0
      }

      selectedStockHoldings.value = holding.quantity
      showStockInfoModal.value = true
    })
    .catch(err => {
      console.error('載入股票詳細失敗:', err)
    })
}

// 響應前往下單
const handleGoToTrade = (stockId) => {
  showStockInfoModal.value = false
  router.push({
    path: '/transact',
    query: { 
      saveId: props.saveId,
      stockId: stockId
    }
  })
}

const handleViewCompanyInfo = (stockId) => {
  alert(`股票代碼 ${stockId}：此為模擬看盤系統，詳細基本面資訊請參考公開資訊觀測站。`)
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