<template>
  <!-- 遮罩沿用既有 modal 寫法，與 Login.vue 一致 -->
  <div class="absolute inset-0 flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm z-50">
    <!-- 卡片：深色底配色與主畫面一致（nature-800 / 白字） -->
    <div class="w-full max-w-sm mx-6 bg-nature-800 rounded-2xl px-8 py-7 shadow-xl flex flex-col items-center gap-4">
      <h2 class="text-2xl font-bold text-white">請重新登入</h2>
      <p class="text-nature-300 text-center">長時間未操作，請重新登入</p>

      <button
        type="button"
        @click="$emit('close')"
        class="w-full bg-[#FFC107] hover:bg-[#B79300] hover:cursor-pointer text-[#212529] font-bold text-lg py-3 rounded-full transition-colors mt-2"
      >
        重新登入
      </button>
    </div>
  </div>
</template>

<script setup>
defineEmits(['close'])
</script>
