<template>
  <div class="min-w-[1280px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col">
    
    <div class="flex w-full h-full">
      <div class="text-07 text-nature-100 w-full"> 交易紀錄 </div>
      <div class="w-full flex flex-row-reverse"> <RecordSelect /> </div>
    </div>

    <div class="flex flex-col w-full h-full">
        <div class="text-04 text-nature-100 "> 
            已出帳投資總額 
            <span class="text-nature-200">{{ formatNumber(spendingAmount) }}</span> 
        </div>
        
        <div class="text-04 text-nature-100"> 
            原幣已實現損益 
            <span :class="profitLoss > 0 ? 'text-red-400' : (profitLoss < 0 ? 'text-green-300' : 'text-yellow-200')">
                {{ profitLoss > 0 ? '+' : '' }}{{ formatNumber(profitLoss) }}
            </span> 
        </div>

        <div class="text-04 text-nature-100"> 
            投資報酬率 
            <span :class="returnRate > 0 ? 'text-red-400' : (returnRate < 0 ? 'text-green-300' : 'text-yellow-200')">
                {{ returnRate > 0 ? '+' : '' }}{{ returnRate }}%
            </span> 
        </div>
    </div>

    <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px]">
      <table class="w-full text-center relative">
        <thead class="sticky top-0 bg-nature-200 border-b-3 text-nature-900 font-05 text-04">
          <tr>
            <th class="py-3 px-2">名稱</th>
            <th class="py-3 px-2">損益</th>
            <th class="py-3 px-2">報酬率</th>
            <th class="py-3 px-2">交易類別</th>
            <th class="py-3 px-2">成交股數</th>
            <th class="py-3 px-2">成交價格</th>
            <th class="py-3 px-2">出帳金額</th>
            <th class="py-3 px-2">投資成本</th>
          </tr>
        </thead>

        <tbody class="text-04 text-nature-800">
          <tr 
            v-for="record in saveRecords" 
            :key="record.order_id" 
            class="border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors"
          >
            <td class="py-3 px-2">{{ record.stock_id }}</td>
            
            <td class="py-3 px-2">
              <span :class="record.realized_pnl > 0 ? 'text-red-600' : (record.realized_pnl < 0 ? 'text-green-500' : '')">
                {{ record.realized_pnl !== null ? formatNumber(record.realized_pnl) : '-' }}
              </span>
            </td>
            
            <td class="py-3 px-2">
              <span :class="record.return_rate > 0 ? 'text-red-600' : (record.return_rate < 0 ? 'text-green-500' : '')">
                {{ record.return_rate !== null ? record.return_rate + '%' : '-' }}
              </span>
            </td>
            
            <td class="py-3 px-2">
              <span :class="record.side === 'BUY' ? 'text-red-600' : 'text-green-500'">
                {{ record.side === 'BUY' ? '買進' : '賣出' }}
              </span>
            </td>
            
            <td class="py-3 px-2">{{ formatNumber(record.quantity) }}</td>
            
            <td class="py-3 px-2">{{ record.price }}</td>
            
            <td class="py-3 px-2">
              {{ record.net_amount !== null 
                ? formatNumber(record.net_amount) 
                : formatNumber(Math.round(record.price * record.quantity)) 
              }}
            </td>
            
            <td class="py-3 px-2">
              {{ record.avg_cost !== null ? formatNumber(record.avg_cost) : '-' }}
            </td>
          </tr>
          
          <tr class="h-[50px] bg-nature-200">
            <td colspan="8"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
  import { ref, onMounted } from 'vue'
  import { useRoute } from 'vue-router'
  import RecordSelect from './RecordSelect.vue'

  const saveRecords = ref([])
  const isLoading = ref(true)
  
  // 上方的總計數字 (若後端沒有直接給，這部分未來可能需要靠前端遍歷 saveRecords 來計算)
  const spendingAmount = ref(0)
  const profitLoss = ref(0)
  const returnRate = ref(0)

  // 🚀 新增：計算總計數據的函式
  const calculateSummary = (records) => {
    let totalSpent = 0
    let totalPnL = 0
    let totalSoldCost = 0

    records.forEach(record => {
      if (record.side === 'BUY') {
        // 買進：加總所有買進的出帳金額
        totalSpent += Number(record.net_amount || (record.price * record.quantity))
      } else if (record.side === 'SELL') {
        // 賣出：加總所有賣出的已實現損益
        if (record.realized_pnl !== null) {
          totalPnL += Number(record.realized_pnl)
        }
        
        // 🚀 修正這裡！利用「入帳金額 - 損益」精準反推總成本
        if (record.net_amount !== null && record.realized_pnl !== null) {
          totalSoldCost += (Number(record.net_amount) - Number(record.realized_pnl))
        }
      }
    })

    // 更新 ref 變數
    spendingAmount.value = Math.round(totalSpent)
    profitLoss.value = Math.round(totalPnL)

    // 計算總投資報酬率
    if (totalSoldCost > 0) {
      returnRate.value = ((totalPnL / totalSoldCost) * 100).toFixed(2)
    } else {
      returnRate.value = 0
    }
  }

  const route = useRoute()

  const fetchSaves = async () => {
    const saveId = route.query.saveId

    if (!saveId) {
      console.error('缺少存檔 ID，無法載入資料')
      isLoading.value = false
      return
    }

    try {
      // 💡 注意：依據你上一回合提供的資料結構，這裡的 API 可能是抓取委託單 (Orders)
      // 若後端路由不同，請將 /api/holding/transactions 替換為實際的端點
      const response = await fetch(`/api/saves/${saveId}/orders`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'x-session-id': localStorage.getItem('session_id')
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('成功拿到股票交易資料:', data)
        saveRecords.value = data
        
        // 🚀 在這裡呼叫計算函式，把剛拿到的資料傳進去
        calculateSummary(data)
        
      } else {
        console.error('無法取得交易紀錄...')
      }
    } catch (error) {
      console.error('API 連線失敗:', error)
    } finally {
      isLoading.value = false
    }
  }

  onMounted(() => {
    fetchSaves()
  })

  // ==========================================
  // --- 股票交易專用：顯示轉換邏輯 (Formatters) ---
  // ==========================================

  /**
   * 1. 數字千分位格式化
   * 用途：將數字轉為帶有逗號的金融格式，如 10000 -> 10,000
   */
  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-'
    return Number(num).toLocaleString()
  }

  /**
   * 2. 轉換交易類別
   * 用途：將資料庫的 BUY / SELL 轉換為中文顯示
   */
  const formatSide = (side) => {
    if (side === 'BUY') return '買進'
    if (side === 'SELL') return '賣出'
    return side 
  }

  /**
   * 3. 判斷文字顏色
   * 用途：買進顯示紅色，賣出顯示綠色 (可直接綁定於 HTML 的 :class)
   */
  const getSideColorClass = (side) => {
    return side === 'BUY' ? 'text-red-500' : 'text-green-500'
  }

  /**
   * 4. 計算出帳金額 (粗估)
   * 用途：由於目前委託單資料無手續費與交易稅，此處單純以 價格 * 數量 計算
   */
  const calculateAmount = (price, quantity) => {
    if (!price || !quantity) return '-'
    const total = Number(price) * Number(quantity)
    return formatNumber(Math.round(total))
  }

  /**
   * 5. 轉換訂單狀態 (選用)
   * 用途：若未來你的表格需要顯示該筆交易是「已成交」還是「委託中」，可套用此函式
   */
  const formatStatus = (status) => {
    const statusMap = {
      'FILLED': '已成交',
      'PRE_MARKET': '盤前委託',
      'PENDING': '委託中',
      'CANCELLED': '已取消'
    }
    return statusMap[status] || status
  }
</script>