<template>
  <!-- 外層：維持滿版藍色背景，並將內容水平置中 (flex justify-center) -->
  <div class="w-full bg-[#3FA2F6] text-white text-sm py-3.5 flex justify-center font-sans font-medium shadow-sm">
    
    <!-- 內層：限制最大寬度 (max-w-6xl) 並水平置中，再做 justify-between -->
    <div class="w-full max-w-6xl px-8 flex justify-between items-center">
      
      <!-- 左側：日期與狀態 -->
      <div class="flex items-center gap-4">
        <div>日期：<span class="text-white font-semibold">{{ date }}</span></div>
        <div>狀態：<span class="text-white font-semibold">{{ status }}</span></div>
      </div>
      
      <!-- 右側：帳戶餘額 -->
      <div class="right-info">
        <div>存款戶：<span class="text-white font-bold">{{ savings }}</span></div>
        <div>交割戶：<span class="text-white font-bold">{{ delivery }}</span></div>
      </div>
      
    </div>
  </div>
</template>

<script setup>
defineProps({
  date: {
    type: String,
    default: '2026/04/31'
  },
  status: {
    type: String,
    default: '09:00'
  },
  savings: {
    type: [Number, String],
    default: 888
  },
  delivery: {
    type: [Number, String],
    default: 999
  }
})
</script>

<style scoped>
.right-info {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16px;
  flex: 1 0 0;
}
</style>
