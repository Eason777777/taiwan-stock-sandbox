<template>
  <div class="holding-info w-full flex flex-col font-sans">
    <!-- 總損益加總標題區 -->
    <div class="flex items-center gap-3 text-03 font-bold mb-4 text-white">
      <span>原幣未實現損益</span>
      <span :class="getProfitLossColorClass(totalPL)">
        {{ formatProfitLoss(totalPL) }}
      </span>
    </div>

    <!-- 庫存持股表格 -->
    <div class="w-full overflow-y-auto max-h-[348px] rounded-[10px] border border-nature-600 bg-[#F8F9FA] holding-info-container">
      <table class="w-full border-collapse font-sans text-nature-900 table-fixed">
        <thead>
          <tr class="bg-[#E9ECEF] h-[52px]">
            <th @click="handleSort('stock_id')" class="sticky top-0 z-10 bg-[#E9ECEF] border-b-[3px] border-nature-600 py-2 px-2 text-center text-[24px] font-bold cursor-pointer hover:bg-nature-300 transition-colors select-none">
              代碼 <span class="ml-1 text-01 font-mono opacity-70">{{ getSortIndicator('stock_id') }}</span>
            </th>
            <th @click="handleSort('stock_name')" class="sticky top-0 z-10 bg-[#E9ECEF] border-b-[3px] border-nature-600 py-2 px-2 text-center text-[24px] font-bold cursor-pointer hover:bg-nature-300 transition-colors select-none">
              名稱 <span class="ml-1 text-01 font-mono opacity-70">{{ getSortIndicator('stock_name') }}</span>
            </th>
            <th @click="handleSort('quantity')" class="sticky top-0 z-10 bg-[#E9ECEF] border-b-[3px] border-nature-600 py-2 px-2 text-center text-[24px] font-bold cursor-pointer hover:bg-nature-300 transition-colors select-none">
              庫存 <span class="ml-1 text-01 font-mono opacity-70">{{ getSortIndicator('quantity') }}</span>
            </th>
            <th @click="handleSort('profit_loss')" class="sticky top-0 z-10 bg-[#E9ECEF] border-b-[3px] border-nature-600 py-2 px-2 text-center text-[24px] font-bold cursor-pointer hover:bg-nature-300 transition-colors select-none">
              原幣損益 <span class="ml-1 text-01 font-mono opacity-70">{{ getSortIndicator('profit_loss') }}</span>
            </th>
            <th @click="handleSort('profit_rate')" class="sticky top-0 z-10 bg-[#E9ECEF] border-b-[3px] border-nature-600 py-2 px-2 text-center text-[24px] font-bold cursor-pointer hover:bg-nature-300 transition-colors select-none">
              獲利率 <span class="ml-1 text-01 font-mono opacity-70">{{ getSortIndicator('profit_rate') }}</span>
            </th>
            <th @click="handleSort('current_price')" class="sticky top-0 z-10 bg-[#E9ECEF] border-b-[3px] border-nature-600 py-2 px-2 text-center text-[24px] font-bold cursor-pointer hover:bg-nature-300 transition-colors select-none">
              現價 <span class="ml-1 text-01 font-mono opacity-70">{{ getSortIndicator('current_price') }}</span>
            </th>
            <th @click="handleSort('avg_cost')" class="sticky top-0 z-10 bg-[#E9ECEF] border-b-[3px] border-nature-600 py-2 px-2 text-center text-[24px] font-bold cursor-pointer hover:bg-nature-300 transition-colors select-none">
              平均成本 <span class="ml-1 text-01 font-mono opacity-70">{{ getSortIndicator('avg_cost') }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="holding in sortedHoldings" 
            :key="holding.stock_id"
            @click="emit('select-stock', holding.stock_id)"
            class="bg-[#F8F9FA] hover:bg-[#E2E6EA] border-b border-nature-300 cursor-pointer transition-colors duration-200 ease-out h-[46px]"
          >
            <td class="py-2 text-[20px] font-medium text-nature-900 font-mono text-center">{{ holding.stock_id }}</td>
            <td class="py-2 text-[20px] font-medium text-nature-900 text-center">{{ holding.stock_name }}</td>
            <td class="py-2 text-[20px] font-medium text-nature-900 font-mono text-center">{{ holding.quantity }}</td>
            <td class="py-2 text-[20px] font-medium font-mono text-center" :class="getProfitLossColorClass(holding.profit_loss)">
              {{ formatProfitLoss(holding.profit_loss) }}
            </td>
            <td class="py-2 text-[20px] font-medium font-mono text-center" :class="getProfitLossColorClass(holding.profit_rate)">
              {{ formatProfitRate(holding.profit_rate) }}
            </td>
            <td class="py-2 text-[20px] font-medium text-nature-900 font-mono text-center">{{ holding.current_price }}</td>
            <td class="py-2 text-[20px] font-medium text-nature-900 font-mono text-center">{{ holding.avg_cost }}</td>
          </tr>
          
          <!-- 表格底層淡灰色橫條列緩衝 -->
          <tr class="bg-[#E9ECEF]/30 h-[20px]">
            <td colspan="7" class="py-1"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  holdings: {
    type: Array,
    required: true,
    default: () => []
  },
  totalProfitLoss: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['select-stock'])

// 排序狀態管理
const sortKey = ref(null)
const sortOrder = ref('none') // 'none' | 'asc' | 'desc'

// 計算總損益 (若外部未傳入則由 holdings 內之損益加總)
const totalPL = computed(() => {
  if (props.totalProfitLoss !== null && props.totalProfitLoss !== undefined) {
    return props.totalProfitLoss
  }
  return props.holdings.reduce((sum, h) => sum + (h.profit_loss || 0), 0)
})

// 根據點擊欄位輪替排序狀態：none -> asc -> desc -> none
const handleSort = (key) => {
  if (sortKey.value === key) {
    if (sortOrder.value === 'none') {
      sortOrder.value = 'asc'
    } else if (sortOrder.value === 'asc') {
      sortOrder.value = 'desc'
    } else {
      sortOrder.value = 'none'
      sortKey.value = null
    }
  } else {
    sortKey.value = key
    sortOrder.value = 'asc'
  }
}

// 獲取排序指示器符號
const getSortIndicator = (key) => {
  if (sortKey.value !== key || sortOrder.value === 'none') return '⇅'
  return sortOrder.value === 'asc' ? '▲' : '▼'
}

// 動態過濾並排序清單
const sortedHoldings = computed(() => {
  if (!props.holdings) return []
  if (!sortKey.value || sortOrder.value === 'none') {
    return [...props.holdings]
  }

  return [...props.holdings].sort((a, b) => {
    let valA = a[sortKey.value]
    let valB = b[sortKey.value]

    // 字串欄位處理 (如代碼、名稱)
    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortOrder.value === 'asc'
        ? valA.localeCompare(valB)
        : valB.localeCompare(valA)
    }

    // 數值欄位處理
    valA = valA !== undefined && valA !== null ? Number(valA) : 0
    valB = valB !== undefined && valB !== null ? Number(valB) : 0

    return sortOrder.value === 'asc' ? valA - valB : valB - valA
  })
})

// 顏色判斷 (正數紅、負數綠、平盤黑)
const getProfitLossColorClass = (val) => {
  if (val > 0) return 'text-red-600 font-bold'
  if (val < 0) return 'text-green-600 font-bold'
  return 'text-nature-900'
}

// 原幣損益格式化 (+ / -)
const formatProfitLoss = (val) => {
  if (val === null || val === undefined) return '--'
  if (val > 0) return `+${val}`
  return `${val}`
}

// 獲利率格式化 (+ / - / %)
const formatProfitRate = (val) => {
  if (val === null || val === undefined) return '--'
  const formattedVal = Math.abs(val).toFixed(1)
  if (val > 0) return `+${formattedVal}%`
  if (val < 0) return `-${formattedVal}%`
  return `${formattedVal}%`
}
</script>

<style scoped>
/* Scrollbar customization for clean styling */
.holding-info-container::-webkit-scrollbar {
  width: 6px;
}
.holding-info-container::-webkit-scrollbar-track {
  background: #E9ECEF;
  border-radius: 4px;
}
.holding-info-container::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-nature-500) 40%, transparent);
  border-radius: 4px;
}
.holding-info-container::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--color-nature-500) 60%, transparent);
}
</style>
