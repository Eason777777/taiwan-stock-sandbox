<template>
  <div 
    class="fixed inset-0 z-[110] flex justify-center items-center bg-black/60 backdrop-blur-sm"
    @click.self="emit('close')"
  >
    <div class="bg-nature-800 border-[10px] border-nature-500 rounded-lg px-16! py-10! flex flex-col gap-8 shadow-2xl w-full max-w-[950px] mx-4">

      <!-- 左右帳戶金額與箭頭佈局 -->
      <div class="flex items-start justify-between w-full gap-4">
        <!-- 左側交割戶 (文字與數字皆置中) -->
        <div class="flex flex-col gap-2 items-center flex-1 min-w-0">
          <span class="text-white font-sans text-04 font-normal w-full text-center">交割戶</span>
          <span class="text-white font-sans text-08 font-medium mt-1 truncate max-w-full">{{ deliveryBalance }}</span>
        </div>

        <!-- 中間箭頭 (與數字列垂直置中對齊) -->
        <div class="flex items-center justify-center shrink-0 self-start mt-[68px]">
          <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64" fill="none">
            <path d="M18.6665 32H55.9998" stroke="#DEE2E6" stroke-width="4.33333" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M5.95058 31.5591L21.2593 20.6242C22.4066 19.8048 24.0002 20.6249 24.0002 22.0347V41.965C24.0002 43.3748 22.4066 44.1949 21.2593 43.3754L5.95058 32.4406C5.64814 32.2246 5.64814 31.7751 5.95058 31.5591Z" fill="#DEE2E6"/>
          </svg>
        </div>

        <!-- 右側存款戶 (文字、數字、輸入框皆置中) -->
        <div class="flex flex-col gap-2 items-center flex-1 min-w-0 relative">
          <span class="text-white font-sans text-04 font-normal w-full text-center">存款戶 [修改金額]</span>
          <span class="text-white font-sans text-08 font-medium mt-1 truncate max-w-full">{{ savingsBalance }}</span>

          <!-- 輸入框與錯誤訊息 -->
          <div class="flex items-center justify-center mt-4 relative">
              <Input
                v-model="transferAmountStr"
                label=""
                placeholder="請輸入轉帳金額"
                variant="pill"
                type="text"
              />
            <span
              v-if="errorMessage"
              class="text-red-500 text-01 font-semibold absolute left-full ml-3 whitespace-nowrap animate-pulse"
            >
              {{ errorMessage }}
            </span>
          </div>
        </div>
      </div>

      <!-- 按鈕區 -->
      <div class="flex justify-center items-center gap-6 mt-4">
        <button 
          @click="emit('close')"
          class="bg-nature-200 hover:bg-nature-300 active:scale-95 text-nature-900 font-bold rounded-lg px-16 py-3.5 transition-all duration-200 cursor-pointer border-none text-02"
        >
          取消
        </button>
        <button 
          @click="confirmTransfer"
          class="bg-yellow-500 hover:bg-yellow-600 active:scale-95 text-nature-900 font-bold rounded-lg px-16 py-3.5 transition-all duration-200 cursor-pointer border-none text-02"
        >
          確認
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Input from './Input.vue'

const props = defineProps({
  deliveryBalance: {
    type: Number,
    required: true,
    default: 0
  },
  savingsBalance: {
    type: Number,
    required: true,
    default: 0
  }
})

const emit = defineEmits(['close', 'update-balances'])

const transferAmountStr = ref('')
const errorMessage = ref('')

const confirmTransfer = () => {
  errorMessage.value = ''
  const val = transferAmountStr.value.trim()

  if (!val) {
    errorMessage.value = '請輸入有效數字'
    return
  }

  // 驗證是否為數字 (包含小數、正負號)
  const amount = Number(val)
  if (isNaN(amount)) {
    errorMessage.value = '請輸入有效數字'
    return
  }

  if (amount === 0) {
    errorMessage.value = '轉帳金額不能為 0'
    return
  }

  if (amount > 0) {
    // 存款戶增加，交割戶減少 -> 檢查交割戶餘額是否足夠
    if (props.deliveryBalance - amount < 0) {
      errorMessage.value = '交割戶餘額不足'
      return
    }
  } else {
    // 存款戶減少，交割戶增加 -> 檢查存款戶餘額是否足夠
    if (props.savingsBalance + amount < 0) {
      errorMessage.value = '存款戶餘額不足'
      return
    }
  }

  // 計算新餘額並對外發送事件
  const newDelivery = props.deliveryBalance - amount
  const newSavings = props.savingsBalance + amount
  emit('update-balances', newDelivery, newSavings)
  emit('close')
}
</script>


<style scoped>
/* 穿透並覆寫內部的 input 寬度為您想要的數值（例如 250px） */
:deep(.relative input) {
  width: 200px; /* 或者 w-full、200px 等 */
}
</style>