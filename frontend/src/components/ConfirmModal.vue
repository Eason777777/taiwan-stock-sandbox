<template>
  <!-- 遮罩沿用既有 modal 寫法，與 SessionExpiredModal.vue 一致 -->
  <div class="absolute inset-0 flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm z-50">
    <!-- 卡片：深色底配色與主畫面一致（nature-800 / 白字） -->
    <div class="w-full max-w-sm mx-6 bg-nature-800 rounded-2xl px-8 py-7 shadow-xl flex flex-col items-center gap-4">
      <h2 class="text-2xl font-bold text-white">{{ title }}</h2>
      <!-- whitespace-pre-line 讓訊息內的 \n 換行可正常顯示 -->
      <p class="text-nature-300 text-center whitespace-pre-line">{{ message }}</p>

      <div class="flex w-full gap-3 mt-2">
        <button
          type="button"
          @click="$emit('cancel')"
          class="flex-1 bg-nature-600 hover:bg-nature-500 hover:cursor-pointer text-white font-bold text-lg py-3 rounded-full transition-colors"
        >
          {{ cancelText }}
        </button>
        <button
          type="button"
          @click="$emit('confirm')"
          class="flex-1 bg-red-700 hover:bg-red-600 hover:cursor-pointer text-white font-bold text-lg py-3 rounded-full transition-colors"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '確認操作',
  },
  message: {
    type: String,
    default: '',
  },
  confirmText: {
    type: String,
    default: '確定',
  },
  cancelText: {
    type: String,
    default: '取消',
  },
})

defineEmits(['confirm', 'cancel'])
</script>
