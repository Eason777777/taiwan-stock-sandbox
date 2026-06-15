<template>
  <div class="stock-info bg-nature-800 border-[3px] sm:border-[6px] md:border-[10px] border-nature-500 rounded-lg text-white font-sans flex flex-col gap-3 sm:gap-6 shadow-2xl">
    <!-- 1. 最上方標頭 -->
    <div class="flex justify-between items-center w-full border-b border-nature-600 pb-3">
      <div class="flex items-center gap-2.5">
        <span class="text-02 sm:text-03 md:text-04 font-bold text-nature-100 font-mono">{{ stock.stock_id }}</span>
        <span class="text-02 sm:text-03 md:text-04 font-bold text-nature-100">{{ stock.stock_name_zh }}</span>
      </div>
      <!-- Right close button -->
      <button
        @click="emit('close')"
        class="text-nature-400 hover:text-white bg-transparent border-none text-xl sm:text-2xl cursor-pointer leading-none p-1 transition-colors"
      >
        &times;
      </button>
    </div>

    <!-- 2. 中間第 1 排 -->
    <div class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center w-full gap-2 sm:gap-0 p-1 sm:p-3 rounded-lg ">
      <!-- 左側價格與幅度 -->
      <div class="flex flex-col">
        <span class="text-03 sm:text-04 md:text-05 font-bold font-mono" :class="getPriceColorClass(stock.change)">
          {{ formatPrice(stock.price) }}
        </span>
        <span class="text-01 sm:text-02 font-bold mt-1" :class="getPriceColorClass(stock.change)">
          {{ formatChangeText(stock.change, stock.changePercent) }}
        </span>
      </div>

      <!-- 中間警告資訊 -->
      <div class="flex justify-start sm:justify-center items-center flex-1">
        <span
          v-if="hasWarning"
          class="text-red-500 font-bold text-01 sm:text-02 border border-red-500/30 px-2 sm:px-3.5 py-1 bg-red-500/10 rounded animate-pulse"
        >
          {{ getWarningText() }}
        </span>
      </div>

      <!-- 右側查看公司資訊按鈕 -->
      <div class="flex justify-end">
        <button
          @click="emit('view-company-info', stock.stock_id)"
          class="bg-nature-700 hover:bg-nature-600 text-white rounded-[10px] px-3 sm:px-5 py-1.5 sm:py-2 text-01 sm:text-02 border border-nature-600 font-medium cursor-pointer transition-colors duration-200 w-full sm:w-auto"
        >
          查看公司資訊
        </button>
      </div>
    </div>

    <!-- 3. 中間第 2 排 -->
    <div class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center w-full gap-2 sm:gap-0 px-1">
      <!-- 左側量價資訊 (兩行排版，支援 NULL) -->
      <div class="flex flex-col gap-1 font-sans text-01 sm:text-sm">
        <div class="text-nature-200">
          開 <span class="font-mono font-semibold">{{ formatDetailValue(stock.open_price) }}</span> |
          高 <span class="font-mono font-semibold">{{ formatDetailValue(stock.high_price) }}</span> |
          低 <span class="font-mono font-semibold">{{ formatDetailValue(stock.low_price) }}</span>
        </div>
        <div class="text-nature-300">
          成交量 <span class="font-mono font-semibold text-white">{{ formatVolume(stock.volume) }}</span> 張
        </div>
      </div>

      <!-- 中間持股狀況 -->
      <div class="text-nature-200 font-semibold text-02 sm:text-lg text-left sm:text-center flex-1">
        目前持股：<span class="text-yellow-500 font-mono text-03 sm:text-xl">{{ holdingsCount }}</span> 張
      </div>

      <!-- 右側前往下單按鈕 -->
      <div class="flex justify-end">
        <button
          @click="emit('go-to-trade', stock.stock_id)"
          class="bg-yellow-500 hover:bg-yellow-600 active:scale-95 text-nature-900 font-bold rounded-[10px] px-4 sm:px-6 py-1.5 sm:py-2 text-01 sm:text-02 transition-all duration-200 cursor-pointer border-none font-sans w-full sm:w-auto"
        >
          前往下單
        </button>
      </div>
    </div>

    <!-- 4. 下方圖表區域 -->
    <div class="w-full flex flex-col gap-3">
      <hr class="w-full border-t-[3px] border-nature-500 my-2" />
      
      <!-- K線圖區塊 -->
      <CandlestickChart 
        :prices="prices"
        :timeframe="timeframe"
        :theme="'dark'"
        :stockId="stock.stock_id"
        :stockName="stock.stock_name_zh"
        @update:timeframe="(tf) => emit('update:timeframe', tf)"
      />
    </div>

    <!-- 5. 底部返回按鈕 -->
    <div class="w-full flex justify-center mt-2">
      <button
        @click="emit('close')"
        class="bg-nature-200 hover:bg-nature-300 text-nature-900 font-bold rounded-[10px] px-8 sm:px-16 py-2 sm:py-3 transition-colors duration-200 cursor-pointer border-none text-01 sm:text-02 w-full sm:w-auto"
      >
        返回
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import CandlestickChart from './CandlestickChart.vue'

const props = defineProps({
  stock: {
    type: Object,
    required: true,
    default: () => ({
      stock_id: '',
      stock_name_zh: '',
      price: null,
      change: 0,
      changePercent: 0,
      is_attention: false,
      is_disposition: false,
      is_full_delivery: false,
      open_price: null,
      high_price: null,
      low_price: null,
      volume: null
    })
  },
  holdingsCount: {
    type: Number,
    default: 0
  },
  prices: {
    type: Array,
    default: () => []
  },
  timeframe: {
    type: String,
    default: 'daily'
  }
})

const emit = defineEmits(['close', 'view-company-info', 'go-to-trade', 'update:timeframe'])

// Warning flag computed property
const hasWarning = computed(() => {
  return props.stock.is_attention || props.stock.is_disposition || props.stock.is_full_delivery
})

// Generate warning label text
const getWarningText = () => {
  const parts = []
  if (props.stock.is_attention) parts.push('注意')
  if (props.stock.is_disposition) parts.push('處置')
  if (props.stock.is_full_delivery) parts.push('全額交割')
  return parts.join(' | ')
}

// Rise/fall/flat visual classes
const getPriceColorClass = (change) => {
  if (change > 0) return 'text-red-600'
  if (change < 0) return 'text-green-700'
  return 'text-yellow-700'
}

// Formatting functions supporting null values
const formatPrice = (p) => {
  return p !== null && p !== undefined ? Number(p).toFixed(2) : '--'
}

const formatDetailValue = (val) => {
  return val !== null && val !== undefined ? Number(val).toFixed(2) : '--'
}

const formatVolume = (v) => {
  return v !== null && v !== undefined ? Number(v).toLocaleString() : '--'
}

const formatChangeText = (change, percent) => {
  if (change === null || change === undefined) return '--'
  
  const formattedChange = change > 0 ? `+${change.toFixed(2)}` : change.toFixed(2)
  const formattedPercent = percent > 0 ? `+${percent.toFixed(2)}%` : `${percent.toFixed(2)}%`
  
  if (change === 0) {
    return '0.00 (0.00%)'
  }
  
  return `${formattedChange} (${formattedPercent})`
}
</script>

<style scoped>
.stock-info {
  padding: 12px;
  width: 900px;
  max-width: 95vw;
  height: fit-content;
  max-height: 90vh;
  overflow-y: auto;
}

@media (min-width: 640px) {
  .stock-info {
    padding: 20px;
  }
}

@media (min-width: 768px) {
  .stock-info {
    padding: 30px;
  }
}
</style>
