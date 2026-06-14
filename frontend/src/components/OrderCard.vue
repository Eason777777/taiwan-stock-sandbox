<!-- 下單卡片(尚須調整) -->
<template>
  <div class="order-card bg-nature-800 border-[10px] border-nature-500 rounded-xl shadow-2xl text-white font-sans">
    <!-- Main Form Area (2-Column Grid Layout) -->
    <div class="grid grid-cols-2 gap-x-24 gap-y-6 w-full items-start">
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
        />
      </div>
      <!-- Row 1 Right: Buy/Sell Slider -->
      <div class="flex flex-col gap-2">
        <span class="text-nature-200 font-06 text-03">買賣設定</span>
        <BuySellSlider 
          :model-value="side"
          @update:model-value="emit('update:side', $event)"
        />
      </div>

      <!-- Row 2 Left: Price Input -->
      <div class="flex flex-col gap-2">
        <label class="text-nature-200 font-06 text-03">委託價格</label>
        <div class="flex items-center gap-4">
          <input 
            type="text"
            :value="price"
            @input="emit('update:price', $event.target.value)"
            :disabled="isPriceDisabled"
            placeholder="請輸入委託價格"
            class="w-[320px] bg-nature-900 border border-nature-200 focus:border-yellow-400 text-nature-100 rounded-[10px] px-5 py-3 focus:outline-none transition-colors duration-200 disabled:bg-nature-950 disabled:border-nature-600 disabled:text-nature-500 disabled:cursor-not-allowed"
          />
          <span v-if="priceError" class="text-red-500 text-sm font-medium">
            {{ priceError }}
          </span>
        </div>
      </div>
      <!-- Row 2 Right: Order Type Slider -->
      <div class="flex flex-col gap-2">
        <span class="text-nature-200 font-06 text-03">委託類型</span>
        <OrderTypeSlider 
          :model-value="orderType"
          @update:model-value="emit('update:orderType', $event)"
          :is-after-hours="isAfterHours"
          :disabled-market="disabledMarket"
        />
      </div>

      <!-- Row 3 Left: Quantity Input -->
      <div class="flex flex-col gap-2">
        <label class="text-nature-200 font-06 text-03">委託張數</label>
        <div class="flex items-center gap-4">
          <input 
            type="number"
            :value="quantity"
            @input="emit('update:quantity', parseInt($event.target.value) || 1)"
            min="1"
            placeholder="請輸入委託張數"
            class="w-[320px] bg-nature-900 border border-nature-200 focus:border-yellow-400 text-nature-100 rounded-[10px] px-5 py-3 focus:outline-none transition-colors duration-200"
          />
          <span v-if="quantityError" class="text-red-500 text-sm font-medium">
            {{ quantityError }}
          </span>
        </div>
      </div>
      <!-- Row 3 Right: Empty Space -->
      <div></div>
    </div>

    <!-- 確認下單按鈕 -->
    <div class="w-full flex justify-center py-2">
      <button 
        @click="emit('submit')"
        class="bg-yellow-500 hover:bg-yellow-600 active:scale-95 text-nature-900 font-bold rounded-[10px] px-20 py-4 transition-all duration-200 font-sans text-02 cursor-pointer border-none outline-none shadow-lg shadow-yellow-500/20"
      >
        確認下單
      </button>
    </div>

    <!-- Divider -->
    <hr class="w-full border-t-[3px] border-nature-500 my-2" />

    <!-- 下方空白區塊 -->
    <div class="w-full min-h-[400px] rounded-[10px] bg-nature-900 border border-nature-600 flex items-center justify-center text-nature-500">
      <span class="text-03 font-bold">（K線圖 與 委託單列表 暫存區塊）</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StockInput from './StockInput.vue'
import BuySellSlider from './BuySellSlider.vue'
import OrderTypeSlider from './OrderTypeSlider.vue'

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
  }
})

const emit = defineEmits([
  'update:stockId',
  'update:price',
  'update:quantity',
  'update:side',
  'update:orderType',
  'select-stock',
  'submit'
])

const isPriceDisabled = computed(() => {
  return props.orderType === 'market' || props.orderType === 'after_hours'
})
</script>

<style scoped>
.order-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 30px;
  max-width: 1100px;
  width: 100%;
  padding: 50px;
  max-height: 80vh;
  overflow-y: auto;
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
