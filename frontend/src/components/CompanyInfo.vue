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
      <div class="flex flex-col gap-2">
        <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[300px] custom-scrollbar">
          <table class="w-full border-collapse text-nature-800 relative table-fixed">
            <thead class="sticky top-0 bg-nature-200 border-b-[3px] border-nature-800 text-nature-900 font-bold text-02 z-10">
              <tr>
                <th class="py-3 px-4 text-center w-[200px]">資訊</th>
                <th class="py-3 px-4 text-center">內容</th>
              </tr>
            </thead>
            <tbody class="text-01">
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">股票中文全名</td>
                <td class="py-3 px-4 text-center">{{ stock.stock_full_name_zh || '無' }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">股票英文簡稱</td>
                <td class="py-3 px-4 font-mono text-center">{{ stock.stock_name_en || '無' }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">股票英文全名</td>
                <td class="py-3 px-4 font-mono text-center">{{ stock.stock_full_name_en || '無' }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">產業別</td>
                <td class="py-3 px-4 text-center">{{ stock.sector_name || '無' }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">上市日期</td>
                <td class="py-3 px-4 font-mono text-center">{{ formatListingDate(stock.listing_date) }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">股票面額</td>
                <td class="py-3 px-4 font-mono text-center">{{ stock.par_value || '無' }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">市場類型</td>
                <td class="py-3 px-4 text-center">{{ stock.market_type || '無' }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">聯絡電話</td>
                <td class="py-3 px-4 font-mono text-center">{{ stock.phone || '無' }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">公司地址</td>
                <td class="py-3 px-4 text-center">{{ stock.address || '無' }}</td>
              </tr>
              <tr class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out">
                <td class="py-3 px-4 font-bold text-center">公司網址</td>
                <td class="py-3 px-4 text-center">
                  <a 
                    v-if="stock.website" 
                    :href="stock.website" 
                    target="_blank" 
                    class="text-blue-600 group-hover:text-blue-300 hover:underline font-mono break-all"
                  >
                    {{ stock.website }}
                  </a>
                  <span v-else>無</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 分隔線 -->
      <hr class="w-full border-t-[3px] border-nature-500 my-1" />

      <!-- 2. 暫停交易表區域 -->
      <div class="flex flex-col gap-2">
        <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[176px] custom-scrollbar">
          <table class="w-full border-collapse text-nature-800 relative table-fixed">
            <thead class="sticky top-0 bg-nature-200 border-b-[3px] border-nature-800 text-nature-900 font-bold text-02 z-10">
              <tr>
                <th class="py-3 px-4 text-center w-[180px]">暫停交易起日</th>
                <th class="py-3 px-4 text-center w-[180px]">暫停交易迄日</th>
                <th class="py-3 px-4 text-center">暫停交易原因</th>
              </tr>
            </thead>
            <tbody class="text-01">
              <tr v-if="!suspensions || suspensions.length === 0">
                <td colspan="3" class="py-6 px-4 text-center text-nature-600 font-medium bg-nature-200">
                  無暫停交易紀錄
                </td>
              </tr>
              <tr 
                v-else
                v-for="(item, index) in suspensions" 
                :key="index"
                class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out"
              >
                <td class="py-3 px-4 font-mono text-center">{{ formatDate(item.suspend_start_date || item.start_date) }}</td>
                <td class="py-3 px-4 font-mono text-center">{{ formatDate(item.resume_date) }}</td>
                <td class="py-3 px-4 text-left break-all whitespace-normal">{{ item.reason }}</td>
              </tr>
            </tbody>
          </table>
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
