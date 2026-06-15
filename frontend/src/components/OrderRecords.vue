<template>
  <div class="rounded-[10px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col">
    
    <div class="flex w-full h-full">
      <div class="text-06 text-nature-100 w-full"> 交易紀錄 </div>
      <div class="w-full flex flex-row-reverse"> <RecordSelect /> </div>
    </div>

    <div class="flex flex-col w-full h-full text-03 text-nature-100">
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

    <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px]">
      <table class="w-full text-center relative">
        <thead class="sticky top-0 bg-nature-200 border-b-3 text-nature-900 font-05 text-03 z-10">
          <tr>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('stock_id')">
              名稱
              <SortIcon :active="sortKey === 'stock_id'" :order="sortOrder"/>
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('realized_pnl')">
              損益
              <SortIcon :active="sortKey === 'realized_pnl'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('return_rate')">
              報酬率
              <SortIcon :active="sortKey === 'return_rate'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('side')">
              交易類別
              <SortIcon :active="sortKey === 'side'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('quantity')">
              成交股數
              <SortIcon :active="sortKey === 'quantity'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('price')">
              成交價格
              <SortIcon :active="sortKey === 'price'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('computed_net_amount')">
              出帳金額
              <SortIcon :active="sortKey === 'computed_net_amount'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('avg_cost')">
              投資成本
              <SortIcon :active="sortKey === 'avg_cost'" :order="sortOrder" />
            </th>
          </tr>
        </thead>

        <tbody class="text-03 text-nature-800">
          <tr 
            v-for="record in sortedRecords" 
            :key="record.transaction_id || record.order_id" 
            class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors"
          >
            <td class="py-3 px-2 font-mono">
              <div class="font-bold">{{ record.stock_id }}</div>
              <div class="text-xs opacity-60 group-hover:opacity-100 transition-opacity">{{ record.stock_name_zh }}</div>
            </td>
            
            <td class="py-3 px-2">
              <span :class="record.realized_pnl > 0 ? 'text-red-600 group-hover:text-red-300' : (record.realized_pnl < 0 ? 'text-green-500 group-hover:text-green-300' : 'text-yellow-600 group-hover:text-yellow-300')">
                {{ record.realized_pnl !== null ? formatNumber(record.realized_pnl) : '-' }}
              </span>
            </td>
            
            <td class="py-3 px-2">
              <span :class="record.return_rate > 0 ? 'text-red-600 group-hover:text-red-300' : (record.return_rate < 0 ? 'text-green-500 group-hover:text-green-300' : 'text-yellow-600 group-hover:text-yellow-300')">
                {{ record.return_rate !== null ? record.return_rate + '%' : '-' }}
              </span>
            </td>
            
            <td class="py-3 px-2">
              <span :class="record.side === 'BUY' ? 'text-red-600 group-hover:text-red-300' : 'text-green-500 group-hover:text-green-300 '">
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
          class: `inline-block ml-1 align-middle text-01 font-bold transition-colors ${colorClass}` 
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