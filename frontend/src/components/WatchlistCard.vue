<!-- 自選卡片 -->
<template>
  <div class="watchlist-card w-full max-w-275 min-h-150 flex flex-col items-stretch gap-6 border-10 border-solid border-nature-500 bg-nature-800 rounded-xl shadow-2xl">
    
    <!-- 1. 上半部：兩個相連按鈕 (新增自選股 & 進入下一階段) -->
    <div class="flex gap-0 w-full">
      <!-- 左：新增自選股按鈕 -->
      <button 
        class="group relative flex justify-center items-center flex-1 h-16 rounded-l-xl! rounded-r-none! bg-yellow-500 hover:bg-yellow-700 transition-colors duration-300 ease-out cursor-pointer border-none outline-none"
        @click="$emit('add-stock')"
      >
        <!-- 預設狀態 (Default) 加號 SVG -->
        <div class="absolute inset-0 flex justify-center items-center transition-all duration-300 ease-out transform scale-100 opacity-100 group-hover:scale-90 group-hover:opacity-0">
          <svg xmlns="http://www.w3.org/2000/svg" width="54" height="54" viewBox="0 0 54 54" fill="none">
            <circle cx="27" cy="27" r="20.25" stroke="#B89300" stroke-width="5.66667"/>
            <path d="M27 33.75L27 20.25" stroke="#B89300" stroke-width="5.66667" stroke-linecap="square"/>
            <path d="M33.75 27L20.25 27" stroke="#B89300" stroke-width="5.66667" stroke-linecap="square"/>
          </svg>
        </div>
        <!-- Hover 狀態 (Variant2) 文字 -->
        <div class="absolute inset-0 flex justify-center items-center transition-all duration-300 ease-out transform scale-90 opacity-0 text-yellow-500 font-sans font-bold text-03 group-hover:scale-100 group-hover:opacity-100">
          新增自選股
        </div>
      </button>

      <!-- 右：進入下一階段按鈕 -->
      <button 
        class="group relative flex justify-center items-center flex-1 h-16 rounded-r-xl! rounded-l-none! bg-green-300 hover:bg-green-700 active:bg-green-900 active:transition-none transition-colors duration-300 ease-out cursor-pointer border-none outline-none"
        @click="$emit('next-phase')"
      >
        <!-- 預設狀態 (Default) 箭頭 SVG -->
        <div class="absolute inset-0 flex justify-center items-center transition-all duration-300 ease-out transform scale-100 opacity-100 group-hover:scale-90 group-hover:opacity-0 active:scale-90 active:opacity-0 active:transition-none">
          <svg xmlns="http://www.w3.org/2000/svg" width="54" height="54" viewBox="0 0 54 54" fill="none">
            <path d="M11.0901 42.9099C14.2368 46.0566 18.2459 48.1995 22.6105 49.0677C26.975 49.9358 31.499 49.4903 35.6104 47.7873C39.7217 46.0843 43.2357 43.2004 45.7081 39.5003C48.1804 35.8002 49.5 31.4501 49.5 27C49.5 22.5499 48.1804 18.1998 45.7081 14.4997C43.2357 10.7996 39.7217 7.91568 35.6104 6.21271C31.499 4.50974 26.975 4.06416 22.6105 4.93233C18.2459 5.8005 14.2368 7.94341 11.0901 11.0901" stroke="#134611" stroke-width="3.91667"/>
            <path d="M33.75 27L35.2792 25.7766L36.2579 27L35.2792 28.2234L33.75 27ZM6.75 28.9583C5.66844 28.9583 4.79167 28.0816 4.79167 27C4.79167 25.9184 5.66844 25.0417 6.75 25.0417V27V28.9583ZM24.75 15.75L26.2792 14.5266L35.2792 25.7766L33.75 27L32.2208 28.2234L23.2208 16.9734L24.75 15.75ZM33.75 27L35.2792 28.2234L26.2792 39.4734L24.75 38.25L23.2208 37.0266L32.2208 25.7766L33.75 27ZM33.75 27V28.9583H6.75V27V25.0417H33.75V27Z" fill="#134611"/>
          </svg>
        </div>
        <!-- Hover/Pressed 狀態中文字 -->
        <div class="absolute inset-0 flex justify-center items-center transition-all duration-300 ease-out transform scale-90 opacity-0 text-green-300 font-sans font-bold text-03 group-hover:scale-100 group-hover:opacity-100 group-active:scale-100 group-active:opacity-100 group-active:text-green-700 group-active:transition-none">
          進入下一階段
        </div>
      </button>
    </div>

    <!-- 2. 下半部：股票資訊表格 (限制最大高度與滾動) -->
    <div class="w-full max-h-96 overflow-y-auto pr-1">
      <div class="w-full flex flex-col gap-2.5 font-sans">
        <!-- 2.1 表頭 (Table Header) -->
        <div class="w-full bg-nature-200 rounded-t-lg px-4 py-3 flex text-center font-bold text-02 text-nature-900">
          <div class="flex-1">代碼</div>
          <div class="flex-1">名稱</div>
          <div class="flex-1">股價</div>
          <div class="flex-1">漲跌</div>
          <div class="flex-1">漲跌幅</div>
        </div>

        <!-- 2.2 資料列 (Table Rows) -->
        <div class="flex flex-col gap-2.5">
          <div
            v-for="stock in stocks"
            :key="stock.id"
            class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-lg items-center transition-colors duration-300 ease-out cursor-pointer"
            @click="$emit('select-stock', stock.id)"
          >
            <!-- 代碼與名稱：懸停時變色 -->
            <div class="flex-1 font-mono text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">
              {{ stock.id }}
            </div>
            <div class="flex-1 text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">
              {{ stock.name }}
            </div>
            <!-- 價格、漲跌幅：動態樣式（平盤使用 yellow-700/yellow-500） -->
            <div :class="['flex-1 font-semibold transition-colors duration-300 ease-out', getStockColorClass(stock.change)]">
              {{ stock.price }}
            </div>
            <div :class="['flex-1 font-semibold transition-colors duration-300 ease-out', getStockColorClass(stock.change)]">
              {{ formatChange(stock.change) }}
            </div>
            <div :class="['flex-1 font-semibold transition-colors duration-300 ease-out', getStockColorClass(stock.change)]">
              {{ formatPercent(stock.changePercent) }}
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
defineProps({
  stocks: {
    type: Array,
    required: true,
    default: () => []
  }
})

defineEmits(['select-stock', 'add-stock', 'next-phase'])

// 根據漲跌幅回傳對應的顏色樣式（包含您追加的平盤黃色規則）
const getStockColorClass = (change) => {
  if (change > 0) {
    return 'text-red-600 group-hover:text-red-300' // 漲 (紅)
  }
  if (change < 0) {
    return 'text-green-700 group-hover:text-green-300' // 跌 (綠)
  }
  return 'text-yellow-700 group-hover:text-yellow-500' // 平盤 (黃)
}

// 格式化漲跌文字
const formatChange = (change) => {
  if (change > 0) return `+${change}`
  if (change < 0) return `${change}`
  return '0'
}

// 格式化漲跌幅百分比文字
const formatPercent = (percent) => {
  if (percent > 0) return `+${percent}%`
  if (percent < 0) return `${percent}%`
  return '0.00%'
}
</script>

<style scoped>
.watchlist-card {
  padding: 50px;
}
</style>
