<template>
  <div 
    class="fixed inset-0 z-[110] flex justify-center items-center bg-black/60 backdrop-blur-sm"
    @click.self="emit('close')"
  >
    <div class="bg-nature-800 border-[2px] sm:border-[4px] border-nature-500 px-3 sm:px-8 md:px-12 py-4 sm:py-6 md:py-10 flex flex-col gap-3 sm:gap-8 shadow-2xl w-[95vw] sm:min-w-[700px] sm:w-auto">

      <div class="flex items-center justify-between w-full gap-1 sm:gap-0">

        <div class="flex flex-col items-center w-[90px] sm:w-[180px] md:w-[220px] min-w-0">
          <span class="text-nature-300 font-sans text-01 sm:text-02 md:text-03 text-center">交割戶 [目標]</span>
          <span class="text-nature-100 font-sans text-02 sm:text-04 md:text-06 font-05 truncate">{{ dynamicDelivery }}</span>
        </div>

        <div class="flex items-center justify-center shrink-0">
          <svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#DEE2E6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-6 h-6 sm:w-10 sm:h-10 md:w-[60px] md:h-[60px]">
            <line x1="20" y1="12" x2="4" y2="12"></line>
            <polygon points="10,6 4,12 10,18" fill="#DEE2E6"></polygon>
          </svg>
        </div>

        <div class="flex flex-col items-center w-[140px] sm:w-[200px] md:w-[250px] min-w-0">
          <span class="text-nature-300 font-sans text-01 sm:text-02 md:text-03 mb-1 sm:mb-3 text-center">存款戶 [來源]</span>

          <div class="flex flex-row items-center gap-[5px]">
            <!-- 減號按鈕 -->
            <div class="transition duration-200 group hover:bg-nature-400 flex items-center border border-nature-500 rounded-l-[10px] bg-nature-900">
              <button
                @click="adjustTransfer(10000)"
                class="transition duration-200 flex items-center justify-center w-6 h-12 sm:w-8 sm:h-16 md:w-10 md:h-20 group-hover:text-green-500 text-green-300 cursor-pointer"
              >
                <svg width="22" height="6" viewBox="0 0 22 6" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-3 h-1 sm:w-4 sm:h-1.5 md:w-[22px] md:h-[6px]">
                  <path d="M18.8335 2.83325L2.8335 2.83325" stroke="currentColor" stroke-width="5.66667" stroke-linecap="square"/>
                </svg>

              </button>
            </div>

            <!-- Input -->
            <div class="flex items-center border border-nature-500 bg-nature-900 min-w-0">
              <input
                v-model.number="savingsInput"
                type="number"
                class="w-[90px] sm:w-[160px] md:w-[220px] text-center bg-transparent py-1 h-fit text-nature-100 font-sans text-02 sm:text-04 md:text-06 font-05 focus:outline-none"
                @input="validateInput"
              />
            </div>

            <!-- 加號按鈕 -->
            <div class="transition duration-200 group hover:bg-nature-400 flex items-center border border-nature-500 rounded-r-[10px] bg-nature-900">
              <button
                @click="adjustTransfer(-10000)"
                class="transition duration-200 flex items-center justify-center w-6 h-12 sm:w-8 sm:h-16 md:w-10 md:h-20 group-hover:text-red-700 text-red-400 cursor-pointer"
              >
                <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 sm:w-4 sm:h-4 md:w-[22px] md:h-[22px]">
                  <path d="M10.8335 18.8333L10.8335 2.83325" stroke="currentColor" stroke-width="5.66667" stroke-linecap="square"/>
                  <path d="M18.8335 10.8333L2.8335 10.8333" stroke="currentColor" stroke-width="5.66667" stroke-linecap="square"/>
                </svg>

              </button>
            </div>
          </div>

          <div class="h-6 mt-2 w-full text-center">
            <span v-if="errorMessage" class="text-[#FF4D4F] text-xs sm:text-sm font-medium">
              {{ errorMessage }}
            </span>
          </div>
        </div>

      </div>

      <div class="flex w-full h-fit gap-2 sm:gap-5">
          <button @click="$emit('close')"
                  class="hover:bg-nature-600 hover:text-nature-400 transform duration-200 cursor-pointer w-full text-nature-800 bg-nature-200 text-02 sm:text-03 md:text-04 font-07 rounded-[10px] py-2 sm:py-3"
          >
              取消
          </button>
          <button @click="confirmTransfer"
                  class="hover:bg-yellow-700 hover:text-yellow-500 transform duration-200 cursor-pointer w-full text-yellow-900 bg-yellow-500 text-02 sm:text-03 md:text-04 font-07 rounded-[10px] py-2 sm:py-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
              確認
          </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

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

// 1. 計算兩戶總金額 (資金池總數不變)
const totalBalance = computed(() => props.deliveryBalance + props.savingsBalance)

// 2. Input 綁定當前存款戶餘額
const savingsInput = ref(props.savingsBalance)
const errorMessage = ref('')

// 3. 動態計算交割戶金額 (總額 - 存款戶)
const dynamicDelivery = computed(() => {
  const currentSavings = Number(savingsInput.value) || 0
  return totalBalance.value - currentSavings
})

// 驗證邏輯
const validateInput = () => {
  errorMessage.value = ''
  const currentSavings = Number(savingsInput.value)
  
  if (isNaN(currentSavings)) {
    errorMessage.value = '請輸入有效數字'
    return false
  }
  
  if (currentSavings < 0) {
    errorMessage.value = '存款戶餘額不能低於 0'
    return false
  }
  
  if (dynamicDelivery.value < 0) {
    errorMessage.value = '交割戶餘額不能低於 0'
    return false
  }
  
  return true
}

// 4. 按鈕加減邏輯
const adjustTransfer = (deliveryDelta) => {
  errorMessage.value = ''
  let currentSavings = Number(savingsInput.value)
  if (isNaN(currentSavings)) {
    currentSavings = props.savingsBalance
  }
  
  // 需求：按 + 讓交割戶增加 (代表存款戶要減少)
  const newSavings = currentSavings - deliveryDelta
  
  // 邊界驗證
  if (newSavings < 0) {
    errorMessage.value = '已達存款戶扣款上限'
    savingsInput.value = 0 // 直接到底
    return
  }
  
  if (totalBalance.value - newSavings < 0) {
    errorMessage.value = '已達交割戶扣款上限'
    savingsInput.value = totalBalance.value // 直接到底
    return
  }

  savingsInput.value = newSavings
}

// 確認送出
const confirmTransfer = () => {
  if (!validateInput()) return
  
  // 回傳最終的 (交割戶餘額, 存款戶餘額)
  emit('update-balances', dynamicDelivery.value, savingsInput.value)
  emit('close')
}
</script>

<style scoped>
/* 隱藏原生 number input 的上下小箭頭 */
input[type=number]::-webkit-inner-spin-button, 
input[type=number]::-webkit-outer-spin-button { 
  -webkit-appearance: none; 
  appearance: none;
  margin: 0; 
}
input[type=number] {
  -moz-appearance: textfield;
  appearance: textfield;
}
</style>