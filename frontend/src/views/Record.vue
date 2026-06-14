<template>
  <div class="record-page w-full max-w-[1200px] bg-nature-800 border-[10px] border-nature-500 rounded-xl p-[50px] flex flex-col gap-8 shadow-2xl text-white font-sans text-center items-center justify-center min-h-[300px]">
    <h2 class="text-3xl font-bold text-nature-100">交易與存檔紀錄</h2>
    <p class="text-lg text-nature-300 mt-2">記錄此存檔所有的委託單、帳戶變動與交易明細。</p>
    
    <div class="border border-dashed border-nature-500 rounded-[10px] p-10 mt-6 bg-nature-900/30 max-w-lg w-full">
      <span class="text-nature-300 font-bold block animate-pulse">🛠️ 同學的 RecordCard 元件拼裝預留區 🛠️</span>
      <span class="text-nature-400 text-sm block mt-2">存檔 ID: {{ saveId }} | 日期: {{ currentDate }}</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  saveId: {
    type: Number,
    required: true
  },
  savingsBalance: {
    type: Number,
    required: true
  },
  deliveryBalance: {
    type: Number,
    required: true
  },
  currentPhase: {
    type: String,
    required: true
  },
  currentDate: {
    type: String,
    required: true
  }
})
</script>

<style scoped>
/* 預留紀錄樣式 */
</style>