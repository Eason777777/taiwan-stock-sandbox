<template>
  <div class="rounded-[10px] gap-[10px] p-[15px] sm:p-[30px] bg-nature-800 border-nature-500 border-[3px] sm:border-[6px] md:border-[10px] w-[90%] h-fit flex flex-col">
    
    <div class="flex w-full items-center justify-between mb-4">
      <div class="text-04 lg:text-06 text-nature-100 w-full font-bold font-sans"> 資產趨勢 </div>
      <div class="w-full flex flex-row-reverse"> 
        <RecordSelect :titleType="5" /> 
      </div>
    </div>

    <!-- 內容展示區 -->
    <div v-if="isLoading" class="w-full h-[350px] sm:h-[400px] flex items-center justify-center text-nature-300 font-sans">
      載入分析數據中...
    </div>
    <div v-else-if="chartDates.length === 0" class="w-full h-[350px] sm:h-[400px] flex items-center justify-center text-nature-300 font-sans">
      目前尚無歷史資產變動資料。
    </div>
    <div v-else class="w-full relative">
      <LineChart 
        :dates="chartDates"
        :deposit-data="chartDeposit"
        :settlement-data="chartSettlement"
        :holdings-data="chartHoldings"
        :total-assets-data="chartTotalAssets"
        :daily-transactions="chartTransactions"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import RecordSelect from './RecordSelect.vue'
import LineChart from './LineChart.vue'

const props = defineProps({
  saveId: {
    type: Number,
    required: true
  },
  currentDate: {
    type: String,
    required: true
  },
  currentPhase: {
    type: String,
    required: true
  }
})

const route = useRoute()

// 數據統計狀態
const chartDates = ref([])
const chartDeposit = ref([])
const chartSettlement = ref([])
const chartHoldings = ref([])
const chartTotalAssets = ref([])
const chartTransactions = ref({})
const isLoading = ref(true)

const fetchChartData = async () => {
  const saveId = props.saveId || Number(route.query.saveId)
  if (!saveId) return
  
  isLoading.value = true
  try {
    // 1. 獲取資金變動歷史
    const historyRes = await fetch(`/api/saves/${saveId}/accounts/history?limit=500`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    const history = historyRes.ok ? await historyRes.json() : []

    // 2. 獲取所有歷史訂單
    const ordersRes = await fetch(`/api/saves/${saveId}/orders?limit=500`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    const orders = ordersRes.ok ? await ordersRes.json() : []

    // 篩選有成交股數的股票 ID，用以拉取歷史收盤價
    const filledOrders = orders.filter(o => o.status === 'FILLED' || o.exec_price !== null)
    const uniqueStockIds = [...new Set(filledOrders.map(o => o.stock_id))]

    // 3. 拉取收盤價歷史
    const pricePromises = uniqueStockIds.map(stockId =>
      fetch(`/api/stocks/${stockId}/prices?save_id=${saveId}&limit=500`, {
        headers: {
          'x-session-id': localStorage.getItem('session_id') || ''
        }
      }).then(res => res.ok ? res.json() : [])
    )
    const pricesList = await Promise.all(pricePromises)
    
    const stockPricesMap = {}
    uniqueStockIds.forEach((stockId, index) => {
      stockPricesMap[stockId] = pricesList[index]
    })

    // 獲取存檔基本資料以取得開戶日 (start_date)
    const saveRes = await fetch(`/api/saves/${saveId}`, {
      headers: {
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })
    const save = saveRes.ok ? await saveRes.json() : null
    const startDate = save && save.start_date ? save.start_date.slice(0, 10) : ''

    // 取得資金變動的最早日期作為備用
    const historyDates = history
      .map(h => h.sim_date ? h.sim_date.slice(0, 10) : '')
      .filter(Boolean)
    const fallbackStartDate = historyDates.length > 0 
      ? historyDates.reduce((min, d) => d < min ? d : min, historyDates[0]) 
      : ''
    const finalStartDate = startDate || fallbackStartDate

    // 4. 重整所有歷史交易日 (X 軸時間線)
    const allDatesSet = new Set()
    
    // 加上轉帳資金紀錄中的日期（過濾開戶前日期）
    history.forEach(h => {
      if (h.sim_date) {
        const dateStr = h.sim_date.slice(0, 10)
        if (!finalStartDate || dateStr >= finalStartDate) {
          allDatesSet.add(dateStr)
        }
      }
    })
    
    // 加上股票價格歷史中的日期（過濾開戶前日期）
    pricesList.forEach(prices => {
      prices.forEach(p => {
        if (p.trade_date) {
          const dateStr = p.trade_date.slice(0, 10)
          if (!finalStartDate || dateStr >= finalStartDate) {
            allDatesSet.add(dateStr)
          }
        }
      })
    })

    // 如果收市了 (currentPhase === 'CLOSED')，將當前日期也加入時間線中，以呈現當天的最新收盤資產資料
    if (props.currentDate && (props.currentPhase === 'CLOSED' || allDatesSet.size === 0)) {
      allDatesSet.add(props.currentDate.slice(0, 10))
    }

    const sortedDates = [...allDatesSet].sort()

    // 5. 依據時間線，計算每日存款、交割、持股市值與資產總和
    const tempDeposit = []
    const tempSettlement = []
    const tempHoldings = []
    const tempTotalAssets = []
    const tempTransactions = {}

    sortedDates.forEach(date => {
      tempTransactions[date] = { orders: [], deals: [], transfers: [] }
    })

    orders.forEach(o => {
      const orderDate = o.sim_date ? o.sim_date.slice(0, 10) : ''
      if (tempTransactions[orderDate]) {
        tempTransactions[orderDate].orders.push(o)
        if (o.exec_price !== null) {
          tempTransactions[orderDate].deals.push(o)
        }
      }
    })

    // 提取轉帳與存取款紀錄 (變動類型為 INITIAL_DEPOSIT, TRANSFER_IN, TRANSFER_OUT)
    history.forEach(h => {
      const txDate = h.sim_date ? h.sim_date.slice(0, 10) : ''
      if (tempTransactions[txDate]) {
        if (['TRANSFER_IN', 'TRANSFER_OUT', 'INITIAL_DEPOSIT'].includes(h.change_type)) {
          tempTransactions[txDate].transfers.push(h)
        }
      }
    })

    sortedDates.forEach(date => {
      // 尋找最後存款結餘
      const savingsTx = [...history]
        .reverse()
        .find(h => h.account_type === 'SAVINGS' && h.sim_date.slice(0, 10) <= date)
      const depositVal = savingsTx ? parseFloat(savingsTx.balance_after) : 0

      // 尋找最後交割結餘
      const tradingTx = [...history]
        .reverse()
        .find(h => h.account_type === 'TRADING' && h.sim_date.slice(0, 10) <= date)
      const settlementVal = tradingTx ? parseFloat(tradingTx.balance_after) : 0

      // 計算持股市值
      let holdingsVal = 0
      uniqueStockIds.forEach(stockId => {
        let qtyHeld = 0
        orders.forEach(o => {
          const orderDate = o.sim_date ? o.sim_date.slice(0, 10) : ''
          if (o.stock_id === stockId && orderDate <= date && (o.status === 'FILLED' || o.exec_price !== null)) {
            if (o.side === 'BUY') {
              qtyHeld += o.quantity
            } else if (o.side === 'SELL') {
              qtyHeld -= o.quantity
            }
          }
        })

        if (qtyHeld > 0) {
          const prices = stockPricesMap[stockId] || []
          const priceObj = prices.find(p => p.trade_date.slice(0, 10) === date)
          let closePrice = 0
          if (priceObj) {
            closePrice = parseFloat(priceObj.close_price)
          } else {
            const pastPrices = prices.filter(p => p.trade_date.slice(0, 10) <= date)
            if (pastPrices.length > 0) {
              closePrice = parseFloat(pastPrices[pastPrices.length - 1].close_price)
            }
          }
          holdingsVal += qtyHeld * 1000 * closePrice
        }
      })

      const totalVal = depositVal + settlementVal + holdingsVal

      tempDeposit.push(depositVal)
      tempSettlement.push(settlementVal)
      tempHoldings.push(holdingsVal)
      tempTotalAssets.push(totalVal)
    })

    chartDates.value = sortedDates
    chartDeposit.value = tempDeposit
    chartSettlement.value = tempSettlement
    chartHoldings.value = tempHoldings
    chartTotalAssets.value = tempTotalAssets
    chartTransactions.value = tempTransactions
  } catch (err) {
    console.error('Failed to parse asset history data:', err)
  } finally {
    isLoading.value = false
  }
}

watch(
  () => [props.saveId, props.currentDate, props.currentPhase],
  () => {
    fetchChartData()
  },
  { immediate: true }
)

onMounted(() => {
  fetchChartData()
})
</script>
