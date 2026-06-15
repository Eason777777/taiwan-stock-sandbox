<template>
  <!-- 遮罩背景 -->
  <div 
    class="fixed inset-0 z-[150] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
    @click.self="emit('close')"
  >
    <!-- 卡片容器 -->
    <div class="trade-settlement-card w-full max-w-[1000px] max-h-[90vh] overflow-y-auto flex flex-col items-stretch p-8 gap-5 border-10 border-solid border-nature-500 bg-nature-800 rounded-xl shadow-2xl relative text-white font-sans custom-scrollbar">
      
      <!-- 關閉按鈕 -->
      <button 
        @click="emit('close')"
        class="absolute top-3 right-5 text-nature-400 hover:text-white bg-transparent border-none text-3xl cursor-pointer leading-none p-1 transition-colors z-50"
      >
        &times;
      </button>

      <!-- 標頭 -->
      <div class="text-center font-bold text-03 text-nature-100 mt-1 mb-1 tracking-wide font-sans">
        本階段委託結算總覽
      </div>

      <!-- 說明文字 -->
      <p class="text-center text-01 text-nature-300 -mt-2 mb-2">
        以下為自 <span class="font-bold text-yellow-500">{{ previousPhaseName }}</span> 推進後已結算之委託交易明細。
      </p>

      <!-- 結算列表 -->
      <div class="flex flex-col gap-2">
        <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[350px] custom-scrollbar">
          <table class="w-full border-collapse text-nature-800 relative table-fixed">
            <thead class="sticky top-0 bg-nature-200 border-b-[3px] border-nature-800 text-nature-900 font-bold text-02 z-10">
              <tr>
                <th class="py-3 px-4 text-center w-[80px]">股票</th>
                <th class="py-3 px-4 text-center w-[120px]">委託類型</th>
                <th class="py-3 px-4 text-center w-[100px]">買賣</th>
                <th class="py-3 px-4 text-center w-[100px]">狀態</th>
                <th class="py-3 px-4 text-center w-[120px]">成交單價</th>
                <th class="py-3 px-4 text-center w-[150px]">交割戶變動款項</th>
              </tr>
            </thead>
            <tbody class="text-01">
              <tr 
                v-for="order in settledOrders" 
                :key="order.order_id" 
                class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors duration-300 ease-out"
              >
                <!-- 商品 (代號/中文名) -->
                <td class="py-3 px-4 text-center font-mono">
                  <div class="font-bold">{{ order.stock_id }}</div>
                  <div class="text-xs text-nature-700 group-hover:text-nature-300 transition-colors">{{ order.stock_name_zh }}</div>
                </td>
                <!-- 委託類型 (市價/限價/盤後定價) -->
                <td class="py-3 px-4 text-center">
                  <span class="font-bold">
                    {{ getOrderTypeName(order) }}
                  </span>
                </td>

                <!-- 種類 (買入/賣出 & 數量) -->
                <td class="py-3 px-4 text-center">
                  <span :class="['font-bold', order.side === 'BUY' ? 'text-red-600 group-hover:text-red-300' : 'text-green-700 group-hover:text-green-300']">
                    {{ order.side === 'BUY' ? '買入' : '賣出' }}
                  </span>
                  <div class="text-xs font-mono">{{ order.quantity }} 張</div>
                </td>

                <!-- 狀態 (已成交/已逾期) -->
                <td class="py-3 px-4 text-center">
                  <span v-if="order.status === 'FILLED'" class="font-bold text-nature-900 group-hover:text-nature-100 transition-colors">已成交</span>
                  <span v-else-if="order.status === 'EXPIRED'" class="text-nature-900 group-hover:text-nature-300 transition-colors">逾期失效</span>
                  <span v-else class="text-nature-400">{{ order.status }}</span>
                </td>

                <!-- 成交單價 -->
                <td class="py-3 px-4 text-center font-mono font-bold">
                  <span v-if="order.status === 'FILLED'" class="text-nature-900 group-hover:text-nature-100 transition-colors">
                    {{ formatPrice(order.exec_price) }}
                  </span>
                  <span v-else class="text-nature-400 group-hover:text-nature-300 transition-colors">
                    -
                  </span>
                </td>

                <!-- 變動款項 -->
                <td class="py-3 px-4 text-center font-mono font-bold">
                  <span v-if="order.status === 'FILLED'">
                    <span :class="order.side === 'BUY' ? 'text-red-600 group-hover:text-red-300' : 'text-green-700 group-hover:text-green-300'">
                      {{ order.side === 'BUY' ? '-' : '+' }}${{ formatAmount(order.net_amount) }}
                    </span>
                  </span>
                  <span v-else class="text-nature-400 group-hover:text-nature-300 transition-colors">
                    -
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 按鈕區域 -->
      <div class="flex justify-center mt-3">
        <button 
          @click="emit('close')"
          class="w-full h-12 bg-green-300 hover:bg-green-700 text-green-900 hover:text-white transition-colors duration-300 ease-out rounded-xl font-bold cursor-pointer border-none outline-none flex justify-center items-center text-03"
        >
          我知道了
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  settledOrders: {
    type: Array,
    required: true,
    default: () => []
  },
  previousPhase: {
    type: String,
    required: true,
    default: ''
  }
})

const emit = defineEmits(['close'])

const previousPhaseName = computed(() => {
  const phaseMap = {
    'PRE_MARKET': '盤前階段',
    'INTRADAY': '盤中階段',
    'POST_MARKET': '盤後階段',
    'CLOSED': '收市階段'
  }
  return phaseMap[props.previousPhase] || props.previousPhase
})

const formatPrice = (val) => {
  if (val === null || val === undefined) return '-'
  return val.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })
}

const formatAmount = (val) => {
  if (val === null || val === undefined) return '0'
  return Math.round(val).toLocaleString()
}

const getOrderTypeName = (order) => {
  // 如果是從盤後或收市推進的，代表此時結算的是盤後定價委託
  if (props.previousPhase === 'POST_MARKET' || props.previousPhase === 'CLOSED') {
    return '盤後定價'
  }
  return order.order_type === 'MARKET' ? '市價' : '限價'
}

</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.5);
}
</style>
