<template>
  <div>
    <div class="flex justify-around" data-tutorial="inventory-accounts">
      <!-- 1. 交割戶 -->
      <div class="flex flex-col justify-center">
        <span class="text-white font-sans text-04 text-left">
          交割戶
        </span>
        <span class="text-white font-sans text-07 font-05 text-right">
          {{ deliveryBalance }}
        </span>
      </div>

      <!-- 2. 中間互動箭頭按鈕 -->
      <div class="flex flex-col justify-center">
        <button 
          @click="openTransfer"
          class="text-nature-200 hover:text-yellow-500 active:text-yellow-700 transition-colors duration-300 cursor-pointer"
        >
          <!-- 這裡預留 SVG 區域，使用者可自行填寫 arrow SVG -->
          <svg xmlns="http://www.w3.org/2000/svg" width="90" height="90" viewBox="0 0 90 90" fill="none" class="w-[90px] h-[90px]">
            <path d="M75 22.5L78.1281 25.6281L81.2562 22.5L78.1281 19.3719L75 22.5ZM14.3262 41.25C14.3262 43.6932 16.3068 45.6738 18.75 45.6738C21.1932 45.6738 23.1738 43.6932 23.1738 41.25L18.75 41.25L14.3262 41.25ZM60 37.5L63.1281 40.6281L78.1281 25.6281L75 22.5L71.8719 19.3719L56.8719 34.3719L60 37.5ZM75 22.5L78.1281 19.3719L63.1281 4.37188L60 7.5L56.8719 10.6281L71.8719 25.6281L75 22.5ZM75 22.5L75 18.0762L36.4453 18.0762L36.4453 22.5L36.4453 26.9238L75 26.9238L75 22.5ZM18.75 40.1953L14.3262 40.1953L14.3262 41.25L18.75 41.25L23.1738 41.25L23.1738 40.1953L18.75 40.1953ZM36.4453 22.5L36.4453 18.0762C24.2292 18.0762 14.3262 27.9792 14.3262 40.1953L18.75 40.1953L23.1738 40.1953C23.1738 32.8657 29.1157 26.9238 36.4453 26.9238L36.4453 22.5ZM18.75 40.1953L14.3262 40.1953L14.3262 41.25L18.75 41.25L23.1738 41.25L23.1738 40.1953L18.75 40.1953ZM36.4453 22.5L36.4453 18.0762C24.2292 18.0762 14.3262 27.9792 14.3262 40.1953L18.75 40.1953L23.1738 40.1953C23.1738 32.8657 29.1157 26.9238 36.4453 26.9238L36.4453 22.5Z" fill="currentColor"/>
            <path d="M15 67.5L11.8719 64.3719L8.74376 67.5L11.8719 70.6281L15 67.5ZM75.6738 48.75C75.6738 46.3068 73.6932 44.3262 71.25 44.3262C68.8068 44.3262 66.8262 46.3068 66.8262 48.75L71.25 48.75L75.6738 48.75ZM30 52.5L26.8719 49.3719L11.8719 64.3719L15 67.5L18.1281 70.6281L33.1281 55.6281L30 52.5ZM15 67.5L11.8719 70.6281L26.8719 85.6281L30 82.5L33.1281 79.3719L18.1281 64.3719L15 67.5ZM15 67.5L15 71.9238L53.5547 71.9238L53.5547 67.5L53.5547 63.0762L15 63.0762L15 67.5ZM71.25 49.8047L75.6738 49.8047L75.6738 48.75L71.25 48.75L66.8262 48.75L66.8262 49.8047L71.25 49.8047ZM53.5547 67.5L53.5547 71.9238C65.7708 71.9238 75.6738 62.0208 75.6738 49.8047L71.25 49.8047L66.8262 49.8047C66.8262 57.1343 60.8843 63.0762 53.5547 63.0762L53.5547 67.5Z" fill="currentColor"/>
          </svg>
        </button>
      </div>

      <!-- 3. 存款戶 -->
      <div class="flex flex-col justify-center">
        <span class="account-name text-white font-sans text-04 font-normal text-left">
          存款戶
        </span>
        <span class="account-amount text-white font-sans text-07 font-05 text-right">
          {{ savingsBalance }}
        </span>
      </div>

      <!-- 轉帳彈窗 (獨立子元件) -->
      <TransferOverlap 
        v-if="showTransferModal"
        :delivery-balance="deliveryBalance"
        :savings-balance="savingsBalance"
        @close="showTransferModal = false"
        @update-balances="handleUpdateBalances"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import TransferOverlap from './TransferOverlap.vue'

defineProps({
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

const emit = defineEmits(['update-balances'])

const showTransferModal = ref(false)

const openTransfer = () => {
  showTransferModal.value = true
}

const handleUpdateBalances = (newDelivery, newSavings) => {
  emit('update-balances', newDelivery, newSavings)
}
</script>

<style scoped>
/* Scoped styles */
</style>
