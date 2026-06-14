<template>
  <!-- 遮罩背景 -->
  <div class="fixed inset-0 z-[150] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm" @click.self="emit('close')">
    
    <!-- 圓角卡片容器：恢復為精簡規格 (max-w-[800px], p-8, gap-5) -->
    <div class="company-info-card w-full max-w-[800px] max-h-[90vh] overflow-y-auto flex flex-col items-stretch p-8 gap-5 border-10 border-solid border-nature-500 bg-nature-800 rounded-xl shadow-2xl relative text-white font-sans custom-scrollbar">
      
      <!-- 關閉按鈕 -->
      <button 
        @click="emit('close')"
        class="absolute top-3 right-5 text-nature-400 hover:text-white bg-transparent border-none text-3xl cursor-pointer leading-none p-1 transition-colors z-50"
      >
        &times;
      </button>

      <!-- 標頭：股票編號 股票中文簡稱 -->
      <div class="text-center font-bold text-03 text-nature-100 mt-1 mb-1 tracking-wide font-sans">
        {{ stock.stock_id }} {{ stock.stock_name_zh }}
      </div>

      <!-- 1. 股票資訊表區域 -->
      <div class="flex flex-col gap-2.5">
        <!-- 表頭 -->
        <div class="w-full bg-nature-200 rounded-t-lg px-4 py-3 flex text-center font-bold text-02 text-nature-900">
          <div class="flex-1">資訊</div>
          <div class="flex-1">內容</div>
        </div>

        <!-- 表身 (限制最多顯示 5 筆，多出時內部滾動，高度剛好 5 筆 * 52px + 4 筆 * 10px = 300px) -->
        <div class="flex flex-col gap-2.5 max-h-[300px] overflow-y-auto pr-1 custom-scrollbar">
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">股票中文全名</div>
            <div class="flex-1 text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ stock.stock_full_name_zh || '無' }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">股票英文簡稱</div>
            <div class="flex-1 font-mono text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ stock.stock_name_en || '無' }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">股票英文全名</div>
            <div class="flex-1 font-mono text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ stock.stock_full_name_en || '無' }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">產業別</div>
            <div class="flex-1 text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ stock.sector_name || '無' }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">上市日期</div>
            <div class="flex-1 font-mono text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ formatListingDate(stock.listing_date) }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">股票面額</div>
            <div class="flex-1 font-mono text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ stock.par_value || '無' }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">市場類型</div>
            <div class="flex-1 text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ stock.market_type || '無' }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">聯絡電話</div>
            <div class="flex-1 font-mono text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ stock.phone || '無' }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">公司地址</div>
            <div class="flex-1 text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ stock.address || '無' }}</div>
          </div>
          <div class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out">
            <div class="flex-1 font-bold text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">公司網址</div>
            <div class="flex-1 text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">
              <a 
                v-if="stock.website" 
                :href="stock.website" 
                target="_blank" 
                class="text-blue-600 group-hover:text-blue-300 hover:underline font-mono break-all"
              >
                {{ stock.website }}
              </a>
              <span v-else>無</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 分隔線 -->
      <hr class="w-full border-t-[3px] border-nature-500 my-1" />

      <!-- 2. 暫停交易表區域 -->
      <div class="flex flex-col gap-2.5">
        <!-- 表頭 -->
        <div class="w-full bg-nature-200 rounded-t-lg px-4 py-3 flex text-center font-bold text-02 text-nature-900">
          <div class="flex-1">暫停交易起日</div>
          <div class="flex-1">暫停交易迄日</div>
          <div class="flex-1">暫停交易原因</div>
        </div>

        <!-- 表身 (限制最多顯示 3 筆，多出時內部滾動，高度剛好 3 筆 * 52px + 2 筆 * 10px = 176px) -->
        <div class="flex flex-col gap-2.5 max-h-[176px] overflow-y-auto pr-1 custom-scrollbar">
          <div v-if="!suspensions || suspensions.length === 0" class="w-full bg-nature-200 rounded px-4 py-4 text-center text-01 text-nature-600 font-medium">
            無暫停交易紀錄
          </div>
          <div 
            v-else
            v-for="(item, index) in suspensions" 
            :key="index"
            class="group w-full bg-nature-200 hover:bg-nature-600 rounded px-4 py-3.5 flex text-center text-01 items-center transition-colors duration-300 ease-out"
          >
            <div class="flex-1 font-mono text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ formatDate(item.suspend_start_date || item.start_date) }}</div>
            <div class="flex-1 font-mono text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out">{{ formatDate(item.resume_date) }}</div>
            <div class="flex-1 text-nature-900 group-hover:text-nature-200 transition-colors duration-300 ease-out truncate px-2" :title="item.reason">{{ item.reason }}</div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  stock: {
    type: Object,
    required: true
  },
  suspensions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close'])

// 格式化為 YYYY / MM / DD
const formatDate = (dateStr) => {
  if (!dateStr) return '無'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y} / ${m} / ${d}`
}

const formatListingDate = (dateStr) => {
  if (!dateStr) return '無'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return dateStr
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y} / ${m} / ${d}`
}
</script>

<style scoped>
/* 滾動條美化，與 Nature 灰黑主題一致 */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: color-mix(in srgb, var(--color-nature-900) 50%, transparent);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-nature-500) 40%, transparent);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--color-nature-500) 60%, transparent);
}

.company-info-card::-webkit-scrollbar {
  width: 6px;
}
.company-info-card::-webkit-scrollbar-track {
  background: color-mix(in srgb, var(--color-nature-900) 50%, transparent);
  border-radius: 4px;
}
.company-info-card::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-nature-500) 40%, transparent);
  border-radius: 4px;
}
.company-info-card::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--color-nature-500) 60%, transparent);
}
</style>
