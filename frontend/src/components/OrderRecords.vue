<template>
  <div class="sm:w-[90%] sm:p-[20px] md:p-[30px] sm:border-[6px] md:border-[10px] rounded-[10px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col">
    
    <div class="flex w-full h-full">
      <div class="sm:text-04 md:text-06 text-04 text-nature-100 w-full"> 交易紀錄 </div>
      <div class="w-full flex flex-row-reverse"> <RecordSelect /> </div>
    </div>
    <div class="sm:text-02 md:text-03 text-02">
      <div class="flex flex-col w-full h-full text-nature-100">
          <div> 
              已出帳投資總額 
              <span class="text-nature-200">{{ formatNumber(spendingAmount) }}</span> 
          </div>
          
          <div> 
              原幣已實現損益 
              <span :class="profitLoss > 0 ? 'text-red-400' : (profitLoss < 0 ? 'text-green-300' : 'text-yellow-200')">
                  {{ profitLoss > 0 ? '+' : '' }}{{ formatNumber(profitLoss) }}
              </span> 
          </div>

          <div> 
              投資報酬率 
              <span :class="returnRate > 0 ? 'text-red-400' : (returnRate < 0 ? 'text-green-300' : 'text-yellow-200')">
                  {{ returnRate > 0 ? '+' : '' }}{{ returnRate }}%
              </span> 
          </div>
      </div>
    </div>

    <div class="bg-nature-200 rounded-[10px] overflow-x-auto max-h-[400px]">
       <table class="w-full min-w-[900px] md:min-w-[1200px] text-center relative">
        <thead class="sticky top-0 bg-nature-200 border-b-3 text-nature-900 font-05 text-[12px] lg:text-02 z-10">
          <tr>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('stock_id')">
              股票
              <SortIcon :active="sortKey === 'stock_id'" :order="sortOrder"/>
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('sim_date')">
              交易日
              <SortIcon :active="sortKey === 'sim_date'" :order="sortOrder" />
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('side')">
              交易類別
              <SortIcon :active="sortKey === 'side'" :order="sortOrder" />
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('quantity')">
              成交張數
              <SortIcon :active="sortKey === 'quantity'" :order="sortOrder" />
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('price')">
              成交價格
              <SortIcon :active="sortKey === 'price'" :order="sortOrder" />
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('fee')">
              手續費
              <SortIcon :active="sortKey === 'fee'" :order="sortOrder" />
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('tax')">
              交易稅
              <SortIcon :active="sortKey === 'tax'" :order="sortOrder" />
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('net_amount')">
              淨收付金額
              <SortIcon :active="sortKey === 'net_amount'" :order="sortOrder" />
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('realized_pnl')">
              損益
              <SortIcon :active="sortKey === 'realized_pnl'" :order="sortOrder" />
            </th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2cursor-pointer hover:bg-nature-300 transition-colors" @click="sortBy('return_rate')">
              報酬率
              <SortIcon :active="sortKey === 'return_rate'" :order="sortOrder" />
            </th>
          </tr>
        </thead>

        <tbody class="text-[10px] sm:text-01 md:text-02 lg:text-03  text-nature-800">
          <tr 
            v-for="record in sortedRecords" 
            :key="record.transaction_id || record.order_id" 
            class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors"
          >
            <!-- 1. 股票 -->
            <td class="">
              <div class="font-bold">{{ record.stock_id }}</div>
              <div class="text-[9px] sm:text-[11px] md:text-01 opacity-60 group-hover:opacity-100 transition-opacity">{{ record.stock_name_zh }}</div>
            </td>
            
            <!-- 2. 交易日 -->
            <td class="">
              {{ record.sim_date ? record.sim_date.slice(0, 10).replace(/-/g, '/') : '-' }}
            </td>
            
            <!-- 3. 交易類別 -->
            <td class="">
              <span :class="record.side === 'BUY' ? 'text-red-600 group-hover:text-red-300' : 'text-green-500 group-hover:text-green-300 '">
                {{ record.side === 'BUY' ? '買進' : '賣出' }}
              </span>
            </td>
            
            <!-- 4. 成交張數 -->
            <td class="">{{ formatNumber(record.quantity) }}</td>
            
            <!-- 5. 成交價格 -->
            <td class="">{{ record.price }}</td>

            <!-- 6. 手續費 -->
            <td class="">
              {{ record.fee !== null && record.fee !== undefined ? formatNumber(record.fee) : '-' }}
            </td>

            <!-- 7. 交易稅 -->
            <td class="">
              {{ record.tax && record.side === 'SELL' ? formatNumber(record.tax) : '-' }}
            </td>
            
            <!-- 8. 淨收付金額 -->
            <td class="">
              <span :class="record.side === 'BUY' ? 'text-green-600 group-hover:text-green-300' : 'text-red-600 group-hover:text-red-300'">
                {{ record.side === 'BUY' ? '-' : '' }}{{ formatNumber(record.net_amount !== null ? record.net_amount : Math.round(record.price * record.quantity * 1000)) }}
              </span>
            </td>

            <!-- 9. 損益 -->
            <td class="">
              <span :class="record.realized_pnl > 0 ? 'text-red-600 group-hover:text-red-300' : (record.realized_pnl < 0 ? 'text-green-500 group-hover:text-green-300' : 'text-yellow-600 group-hover:text-yellow-300')">
                {{ record.realized_pnl !== null ? (record.realized_pnl > 0 ? '+' : '') + formatNumber(record.realized_pnl) : '-' }}
              </span>
            </td>
            
            <!-- 10. 報酬率 -->
            <td class="">
              <span :class="record.return_rate > 0 ? 'text-red-600 group-hover:text-red-300' : (record.return_rate < 0 ? 'text-green-500 group-hover:text-green-300' : 'text-yellow-600 group-hover:text-yellow-300')">
                {{ record.return_rate !== null ? (record.return_rate > 0 ? '+' : '') + record.return_rate + '%' : '-' }}
              </span>
            </td>
          </tr>
          
          <tr class="h-[20px] lg:h-[25px] bg-nature-200">
            <td colspan="10"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
  import { ref, computed, onMounted, defineComponent, h } from 'vue'
  import { useRoute } from 'vue-router'
  import RecordSelect from './RecordSelect.vue'

  // 🚀 新增：內聯渲染排序箭頭的微型元件，保持模板乾淨
  const SortIcon = defineComponent({
    props: ['active', 'order'],
    setup(props) {
      return () => {
        let iconText = '⇅'
        let colorClass = 'text-nature-900' // 未排序時的淺色

        if (props.active) {
          if (props.order === 'asc') {
            iconText = '▲'
            colorClass = 'text-nature-900' // 排序啟用時的深色
          } else if (props.order === 'desc') {
            iconText = '▼'
            colorClass = 'text-nature-900'
          }
        }

        return h('span', { 
          class: `inline-block ml-1 align-middle text-[8px] md:text-01  font-bold transition-colors ${colorClass}` 
        }, iconText)
      }
    }
  })

  const saveRecords = ref([])
  const isLoading = ref(true)
  
  // 🚀 新增：排序狀態
  const sortKey = ref('')
  const sortOrder = ref('') // 'asc' 或 'desc' 或 ''

  const spendingAmount = ref(0)
  const profitLoss = ref(0)
  const returnRate = ref(0)

  // 🚀 新增：點擊表頭的排序切換邏輯
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

  // 🚀 新增：依據排序狀態動態計算的陣列
  const sortedRecords = computed(() => {
    if (!sortKey.value || !sortOrder.value) return saveRecords.value

    return [...saveRecords.value].sort((a, b) => {
      let valA = a[sortKey.value]
      let valB = b[sortKey.value]

      // 針對「出帳金額」的特殊判斷，因為它是前端算出來的
      if (sortKey.value === 'computed_net_amount') {
        valA = a.net_amount !== null ? Number(a.net_amount) : (Number(a.price) * Number(a.quantity))
        valB = b.net_amount !== null ? Number(b.net_amount) : (Number(b.price) * Number(b.quantity))
      } else {
        // 確保數字欄位轉型正確，以便正確比對大小
        if (!isNaN(valA) && valA !== null) valA = Number(valA)
        if (!isNaN(valB) && valB !== null) valB = Number(valB)
      }

      // 將 null 值往後排
      if (valA === null || valA === undefined) return 1
      if (valB === null || valB === undefined) return -1

      if (valA < valB) return sortOrder.value === 'asc' ? -1 : 1
      if (valA > valB) return sortOrder.value === 'asc' ? 1 : -1
      return 0
    })
  })

  const calculateSummary = (records) => {
    let totalSpent = 0
    let totalPnL = 0
    let totalSoldCost = 0

    records.forEach(record => {
      if (record.side === 'BUY') {
        totalSpent += Number(record.net_amount || (record.price * record.quantity))
      } else if (record.side === 'SELL') {
        if (record.realized_pnl !== null) {
          totalPnL += Number(record.realized_pnl)
        }
        if (record.net_amount !== null && record.realized_pnl !== null) {
          totalSoldCost += (Number(record.net_amount) - Number(record.realized_pnl))
        }
      }
    })

    spendingAmount.value = Math.round(totalSpent)
    profitLoss.value = Math.round(totalPnL)

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
      isLoading.value = false
      return
    }

    try {
      // 💡 取得已成交的股票交易紀錄 (Transactions)
        const response = await fetch(`/api/saves/${saveId}/holdings/transactions`, {headers: {
          'Content-Type': 'application/json',
          'x-session-id': localStorage.getItem('session_id') || ''
        }
      })

      if (response.ok) {
        const data = await response.json()
        saveRecords.value = data

        calculateSummary(data)

      }
    } catch {
    } finally {
      isLoading.value = false
    }
  }

  onMounted(() => {
    fetchSaves()
  })

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-'
    return Number(num).toLocaleString()
  }

  const formatSide = (side) => {
    if (side === 'BUY') return '買進'
    if (side === 'SELL') return '賣出'
    return side 
  }

  const getSideColorClass = (side) => {
    return side === 'BUY' ? 'text-red-500' : 'text-green-500'
  }

  const calculateAmount = (price, quantity) => {
    if (!price || !quantity) return '-'
    const total = Number(price) * Number(quantity)
    return formatNumber(Math.round(total))
  }

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