<template>
  <div class="add-watchlist z-101 min-w-100 w-200 h-fit bg-nature-800 border-nature-500 border-[10px] rounded-lg text-white font-sans flex flex-col gap-6">
    <!-- Title -->
    <div class="text-06 text-nature-200 font-05">新增自選股</div>

    <!-- Filter Inputs Row -->
    <div class="flex gap-6 w-full">
      <!-- 股票代號/名稱 -->
      <div class="flex-1 flex flex-col gap-2">
        <label class="text-nature-200 font-06 text-03">股票代號</label>
        <input 
          type="text"
          :value="searchQuery"
          @input="emit('update:searchQuery', $event.target.value)"
          placeholder="請輸入代碼或名稱"
          class="w-full bg-nature-900 border border-nature-200 focus:border-yellow-400 text-nature-100 rounded-[10px] px-5 py-3 focus:outline-none transition-colors duration-200 font-sans"
        />
      </div>

      <!-- 依產業別篩選 -->
      <div class="flex-1 flex flex-col gap-2">
        <label class="text-nature-200 font-06 text-03">依產業別篩選</label>
        <select 
          :value="selectedSector"
          @change="emit('update:selectedSector', $event.target.value)"
          class="w-full bg-nature-900 border border-nature-200 focus:border-yellow-400 text-nature-100 rounded-[10px] px-5 py-3 focus:outline-none transition-colors duration-200 cursor-pointer font-sans"
        >
          <option value="">全部產業</option>
          <option v-for="sector in sectors" :key="sector" :value="sector">
            {{ sector }}
          </option>
        </select>
      </div>
    </div>

    <!-- Stock Table List -->
    <div class="w-full bg-nature-900 border border-nature-600 rounded-lg overflow-hidden flex flex-col">
      <div 
        class="max-h-[300px] overflow-y-auto pr-1"
        @scroll="handleScroll"
      >
        <table class="w-full text-center border-collapse">
          <thead class="sticky top-0 z-10 bg-nature-200 text-nature-900 font-bold text-base">
            <tr>
              <th class="py-3 px-2 w-[80px]">選擇</th>
              <th class="py-3 px-2">代碼</th>
              <th class="py-3 px-2">名稱</th>
              <th class="py-3 px-2">產業別</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="stock in stocks" 
              :key="stock.stock_id"
              class="border-b border-nature-800 last:border-b-0 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-150 cursor-pointer"
              @click="toggleSelect(stock.stock_id)"
            >
              <!-- Checkbox Cell -->
              <td class="py-3 px-2 flex justify-center items-center">
                <div 
                  class="w-5 h-5 rounded flex items-center justify-center transition-all duration-150"
                  :class="isSelected(stock.stock_id) 
                    ? 'bg-yellow-500 border border-yellow-500' 
                    : 'bg-nature-900 border border-nature-200'"
                >
                  <svg 
                    v-if="isSelected(stock.stock_id)" 
                    xmlns="http://www.w3.org/2000/svg" 
                    width="12" 
                    height="12" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="#4E3F00" 
                    stroke-width="4" 
                    stroke-linecap="round" 
                    stroke-linejoin="round"
                  >
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </div>
              </td>
              <td class="py-3 px-2 font-mono text-sm">{{ stock.stock_id }}</td>
              <td class="py-3 px-2 font-bold">{{ stock.stock_name_zh }}</td>
              <td class="py-3 px-2 text-nature-400">{{ stock.sector_name || '-' }}</td>
            </tr>
            <tr v-if="stocks.length === 0">
              <td colspan="4" class="py-8 text-center text-nature-400">
                🔍 查無符合條件的股票
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Actions Buttons (Frame 79) -->
    <div class="flex w-full h-fit gap-5">
      <!-- 取消 -->
      <button 
        @click="emit('close')" 
        class="cursor-pointer w-full text-nature-800 bg-nature-200 text-04 font-07 rounded-[10px] py-3 text-center border-none hover:bg-nature-300 transition-colors duration-200"
      >
        取消
      </button>
      <!-- 確認 -->
      <button 
        @click="emit('confirm')" 
        class="cursor-pointer w-full text-yellow-900 bg-yellow-500 text-04 font-07 rounded-[10px] py-3 text-center border-none hover:bg-yellow-600 transition-colors duration-200"
      >
        確認
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  searchQuery: {
    type: String,
    default: ''
  },
  selectedSector: {
    type: String,
    default: ''
  },
  sectors: {
    type: Array,
    default: () => []
  },
  stocks: {
    type: Array,
    default: () => []
  },
  selectedStockIds: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'update:searchQuery',
  'update:selectedSector',
  'update:selectedStockIds',
  'close',
  'confirm',
  'load-more'
])

const handleScroll = (e) => {
  const { scrollTop, scrollHeight, clientHeight } = e.target
  if (scrollHeight - scrollTop - clientHeight < 50) {
    emit('load-more')
  }
}

const toggleSelect = (stockId) => {
  const selected = [...props.selectedStockIds]
  const index = selected.indexOf(stockId)
  if (index === -1) {
    selected.push(stockId)
  } else {
    selected.splice(index, 1)
  }
  emit('update:selectedStockIds', selected)
}

const isSelected = (stockId) => {
  return props.selectedStockIds.includes(stockId)
}
</script>

<style scoped>
.add-watchlist {
  padding: 30px;
}
/* Scrollbar customization for clean styling */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: color-mix(in srgb, var(--color-nature-900) 50%, transparent);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-nature-500) 40%, transparent);
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--color-nature-500) 60%, transparent);
}
</style>
