<template>
  <div class="fixed top-6 left-1/2 -translate-x-1/2 z-[200] flex flex-col gap-3 items-center pointer-events-none">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        :class="['pointer-events-auto relative min-w-[240px] overflow-hidden rounded-xl px-6 pt-3 pb-4 shadow-2xl backdrop-blur-md text-white font-bold font-sans text-03 text-center', toast.bgClass]"
      >
        {{ toast.message }}
        <!-- 剩餘時間進度條：貼齊底部，從右往左消 -->
        <div
          class="absolute bottom-0 left-0 h-1 w-full origin-left bg-white/80"
          :style="{ animation: `toast-shrink ${toast.duration}ms linear forwards` }"
        ></div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script>
import { ref } from 'vue'

// 全域共享的提示訊息佇列，取代 alert()
export const toasts = ref([])

let nextId = 0

// 依 type 提供預設背景色（淺色透明底 + 邊框，沿用既有 tailwind 色票），也可用 bgClass 自訂覆寫
const TYPE_CLASSES = {
  info: 'bg-nature-700/40 border border-nature-300/40',
  success: 'bg-green-700/40 border border-green-300/40',
  error: 'bg-red-700/40 border border-red-300/40',
  warning: 'bg-yellow-600/40 border border-yellow-300/40',
}

export function showToast(message, { type = 'info', bgClass, duration = 3000 } = {}) {
  const id = nextId++
  toasts.value.push({
    id,
    message,
    bgClass: bgClass || TYPE_CLASSES[type] || TYPE_CLASSES.info,
    duration,
  })
  return id
}

export function removeToast(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}
</script>

<script setup>
import { watch } from 'vue'

// 每筆 toast 推入後啟動倒數計時，時間到自動移除（淡出由 TransitionGroup 處理）
watch(
  toasts,
  (list) => {
    list.forEach((toast) => {
      if (!toast._timer) {
        toast._timer = setTimeout(() => removeToast(toast.id), toast.duration)
      }
    })
  },
  { deep: true, immediate: true }
)
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-16px);
}
</style>

<style>
@keyframes toast-shrink {
  from {
    transform: scaleX(1);
  }
  to {
    transform: scaleX(0);
  }
}
</style>
