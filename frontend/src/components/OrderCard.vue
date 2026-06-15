<!-- 下單卡片(尚須調整) -->
<template>
  <div class="order-card bg-nature-800 border-3 sm:border-6 md:border-10 border-nature-500 rounded-xl shadow-2xl text-white font-sans">
    <!-- Main Form Area (2-Column Grid Layout) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 sm:gap-x-12 md:gap-x-24 gap-y-4 sm:gap-y-6 w-full items-start" data-tutorial="order-form">
      <!-- Row 1 Left: Stock Code Input -->
      <div>
        <StockInput
          :model-value="stockId"
          @update:model-value="emit('update:stockId', $event)"
          :stocks="stocks"
          label="股票編號"
          placeholder="請輸入代碼或名稱 (如 2330)"
          :error-message="stockError"
          @select="emit('select-stock', $event)"
          @search="emit('search-stock', $event)"
          @load-more="emit('load-more-stocks')"
        />
      </div>
      <!-- Row 1 Right: Buy/Sell Slider -->
      <div class="flex flex-col gap-2">
        <span class="text-nature-200 font-06 text-02 sm:text-03">買賣設定</span>
        <BuySellSlider
          :model-value="side"
          @update:model-value="emit('update:side', $event)"
        />
      </div>

      <!-- Row 2 Left: Price Input -->
      <div class="flex flex-col gap-2">
        <label class="text-nature-200 font-06 text-02 sm:text-03">委託價格</label>
        <div class="flex items-center gap-4">
          <input
            type="text"
            :value="price"
            @input="emit('update:price', $event.target.value)"
            :disabled="isPriceDisabled"
            placeholder="請輸入委託價格"
            class="w-full max-w-[320px] bg-nature-900 border border-nature-200 focus:border-yellow-400 text-nature-100 rounded-[10px] px-5 py-3 focus:outline-none transition-colors duration-200 disabled:bg-nature-950 disabled:border-nature-600 disabled:text-nature-500 disabled:cursor-not-allowed"
          />
          <span v-if="priceError" class="text-red-500 text-sm font-medium">
            {{ priceError }}
          </span>
        </div>
      </div>
      <!-- Row 2 Right: Order Type Slider -->
      <div class="flex flex-col gap-2">
        <span class="text-nature-200 font-06 text-02 sm:text-03">委託類型</span>
        <OrderTypeSlider
          :model-value="orderType"
          @update:model-value="emit('update:orderType', $event)"
          :is-after-hours="isAfterHours"
          :disabled-market="disabledMarket"
        />
      </div>

      <!-- Row 3 Left: Quantity Input -->
      <div class="flex flex-col gap-2">
        <label class="text-nature-200 font-06 text-02 sm:text-03">委託張數</label>
        <div class="flex items-center gap-4">
          <input
            type="number"
            :value="quantity"
            @input="emit('update:quantity', parseInt($event.target.value) || 1)"
            min="1"
            placeholder="請輸入委託張數"
            class="w-full max-w-[320px] bg-nature-900 border border-nature-200 focus:border-yellow-400 text-nature-100 rounded-[10px] px-5 py-3 focus:outline-none transition-colors duration-200"
          />
          <span v-if="quantityError" class="text-red-500 text-sm font-medium">
            {{ quantityError }}
          </span>
        </div>
      </div>
      <!-- Row 3 Right: Empty Space -->
      <div class="hidden sm:block"></div>
    </div>

    <!-- 確認下單按鈕 -->
    <div class="w-full flex justify-center py-2">
      <button
        @click="emit('submit')"
        :disabled="disabled"
        class="bg-yellow-500 hover:bg-yellow-600 active:scale-95 text-nature-900 font-bold rounded-[10px] px-20 py-4 transition-all duration-200 font-sans text-02 cursor-pointer border-none outline-none shadow-lg shadow-yellow-500/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none"
      >
        確認下單
      </button>
    </div>

    <!-- Divider -->
    <hr class="w-full border-t-[3px] border-nature-500 my-2" />

    <!-- 頁籤與篩選器區域 -->
    <div class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-2 w-full my-4">
      <!-- 左側：相連按鈕頁籤 (風格仿 WatchlistCard.vue 上半部) -->
      <div class="flex gap-0 w-full sm:w-80">
        <button 
          type="button"
          @click="activeTab = 'kline'"
          :class="[
            'flex-1 h-12 rounded-l-xl! rounded-r-none! flex justify-center items-center font-sans font-bold text-base cursor-pointer border-none outline-none transition-colors duration-300',
            activeTab === 'kline'
              ? 'bg-nature-200 text-nature-900'
              : 'bg-nature-900 hover:bg-nature-750 text-nature-300'
          ]"
        >
          K線圖
        </button>
        <button 
          type="button"
          @click="activeTab = 'orders'"
          :class="[
            'flex-1 h-12 rounded-r-xl! rounded-l-none! flex justify-center items-center font-sans font-bold text-base cursor-pointer border-none outline-none transition-colors duration-300',
            activeTab === 'orders'
              ? 'bg-nature-200 text-nature-900'
              : 'bg-nature-900 hover:bg-nature-750 text-nature-300'
          ]"
        >
          委託單紀錄
        </button>
      </div>

      <!-- 右側：篩選按鈕 (僅在 activeTab === 'orders' 顯示) -->
      <div v-show="activeTab === 'orders'" class="flex gap-2 sm:gap-4 items-center">
        <!-- 按鈕 1: 待成交 -->
        <button
          type="button"
          @click="togglePending"
          :class="['px-3 sm:px-5 py-2 rounded-lg font-bold border border-solid transition-all duration-300 ease-out cursor-pointer text-xs sm:text-sm outline-none',
                   showPending ? 'bg-yellow-500 text-nature-900 border-yellow-500 shadow-md shadow-yellow-500/20' : 'bg-nature-900 text-nature-300 border-nature-600 hover:bg-nature-750']"
        >
          待成交
        </button>

        <!-- 按鈕 2: 今日委託單 -->
        <button
          type="button"
          @click="toggleToday"
          :class="['px-3 sm:px-5 py-2 rounded-lg font-bold border border-solid transition-all duration-300 ease-out cursor-pointer text-xs sm:text-sm outline-none',
                   showToday ? 'bg-green-300 text-green-900 border-green-300 shadow-md shadow-green-300/20' : 'bg-nature-900 text-nature-300 border-nature-600 hover:bg-nature-750']"
        >
          今日委託單
        </button>
      </div>
    </div>

    <!-- 內容展示區塊 -->
    <div class="w-full">
      <!-- 頁籤一：K 線圖 -->
      <div v-if="activeTab === 'kline'" class="w-full">
        <div v-if="!stockId" class="w-full min-h-[400px] rounded-[10px] bg-nature-900 border border-nature-600 flex items-center justify-center text-nature-500">
          <span class="text-03 font-bold">請輸入或選擇股票以顯示 K 線圖</span>
        </div>
        <div v-else class="w-full">
          <CandlestickChart 
            :prices="prices"
            :timeframe="timeframe"
            :theme="'dark'"
            :stockId="stockId"
            :stockName="stockName"
            @update:timeframe="(tf) => emit('update:timeframe', tf)"
          />
        </div>
      </div>

      <!-- 頁籤二：委託單狀態列表 -->
      <div v-else-if="activeTab === 'orders'" class="w-full">
        <OrderHistory 
          :orders="filteredOrders"
          @cancel-order="emit('cancel-order', $event)"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import StockInput from './StockInput.vue'
import BuySellSlider from './BuySellSlider.vue'
import OrderTypeSlider from './OrderTypeSlider.vue'
import CandlestickChart from './CandlestickChart.vue'
import OrderHistory from './OrderHistory.vue'

const props = defineProps({
  stocks: {
    type: Array,
    required: true,
    default: () => []
  },
  stockId: {
    type: String,
    default: ''
  },
  price: {
    type: [String, Number],
    default: ''
  },
  quantity: {
    type: Number,
    default: 1
  },
  side: {
    type: String,
    default: 'default'
  },
  orderType: {
    type: String,
    default: 'default'
  },
  isAfterHours: {
    type: Boolean,
    default: false
  },
  disabledMarket: {
    type: Boolean,
    default: false
  },
  stockError: {
    type: String,
    default: ''
  },
  priceError: {
    type: String,
    default: ''
  },
  quantityError: {
    type: String,
    default: ''
  },
  prices: {
    type: Array,
    default: () => []
  },
  timeframe: {
    type: String,
    default: 'daily'
  },
  stockName: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  orders: {
    type: Array,
    default: () => []
  },
  currentDate: {
    type: String,
    default: ''
  },
  currentPhase: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'update:stockId',
  'update:price',
  'update:quantity',
  'update:side',
  'update:orderType',
  'update:timeframe',
  'select-stock',
  'search-stock',
  'load-more-stocks',
  'submit',
  'cancel-order'
])

const activeTab = ref('orders')
const showPending = ref(true)
const showToday = ref(false)

const isPriceDisabled = computed(() => {
  return props.orderType === 'market' || props.orderType === 'after_hours'
})

// 根據 currentPhase 設定預設選取狀態
const initDefaults = () => {
  if (props.currentPhase === 'CLOSED') {
    showPending.value = false
    showToday.value = true
  } else {
    showPending.value = true
    showToday.value = false
  }
}

watch(() => props.currentPhase, () => {
  initDefaults()
}, { immediate: true })

// 監聽股號輸入：有輸入自動切至 K線圖，清空則自動切至委託單紀錄
watch(() => props.stockId, (newId) => {
  if (newId) {
    activeTab.value = 'kline'
  } else {
    activeTab.value = 'orders'
  }
}, { immediate: true })

// 互斥篩選按鈕點擊處理
const togglePending = () => {
  showPending.value = !showPending.value
  if (showPending.value) {
    showToday.value = false
  }
}

const toggleToday = () => {
  showToday.value = !showToday.value
  if (showToday.value) {
    showPending.value = false
  }
}

// 根據篩選條件過濾委託單列表
const filteredOrders = computed(() => {
  let list = props.orders

  if (showPending.value) {
    return list.filter(o => o.status === 'PENDING')
  }

  if (showToday.value) {
    if (!props.currentDate) return list
    const todayStr = props.currentDate.slice(0, 10)
    return list.filter(o => o.sim_date.slice(0, 10) === todayStr)
  }

  return list
})
</script>

<style scoped>
.order-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 15px;
  max-width: 1280px;
  width: 100%;
  padding: 15px;
  max-height: 80vh;
  overflow-y: auto;
}

@media (min-width: 640px) {
  .order-card {
    gap: 20px;
    padding: 20px;
  }
}

@media (min-width: 768px) {
  .order-card {
    gap: 30px;
    padding: 50px;
  }
}

/* Scrollbar customization for clean styling */
.order-card::-webkit-scrollbar {
  width: 6px;
}
.order-card::-webkit-scrollbar-track {
  background: color-mix(in srgb, var(--color-nature-900) 50%, transparent);
  border-radius: 4px;
}
.order-card::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-nature-500) 40%, transparent);
  border-radius: 4px;
}
.order-card::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--color-nature-500) 60%, transparent);
}
</style>
