<template>
  <Teleport to="body">
    <div 
      v-if="show" 
      class="fixed inset-0 z-[200] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
      @click.self="handleCancel"
    >
      <div class="z-[201] min-w-[450px] w-[450px] h-fit bg-nature-800 border-nature-500 border-[10px] rounded-lg p-[25px] flex flex-col gap-6 text-white font-sans shadow-2xl">
        <!-- 標題與圖示 -->
        <div class="text-05 font-bold text-nature-200 flex items-center gap-2.5">
          <svg 
            v-if="type === 'danger' || type === 'warning'" 
            xmlns="http://www.w3.org/2000/svg" 
            width="24" 
            height="24" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            class="text-yellow-500 animate-pulse" 
            stroke-width="2.5" 
            stroke-linecap="round" 
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <svg 
            v-else 
            xmlns="http://www.w3.org/2000/svg" 
            width="24" 
            height="24" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            class="text-nature-300" 
            stroke-width="2.5" 
            stroke-linecap="round" 
            stroke-linejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>{{ title }}</span>
        </div>

        <!-- 內容文字 -->
        <div class="text-03 text-nature-200 leading-relaxed whitespace-pre-line">
          {{ message }}
        </div>

        <!-- 按鈕區 -->
        <div class="flex w-full h-fit gap-5">
          <button 
            type="button"
            @click="handleCancel" 
            class="cursor-pointer w-full text-nature-800 bg-nature-200 text-04 font-07 rounded-[10px] py-3 border-none outline-none hover:bg-nature-300 transition-colors"
          >
            {{ cancelText }}
          </button>
          <button 
            type="button"
            @click="handleConfirm" 
            class="cursor-pointer w-full text-04 font-07 rounded-[10px] py-3 border-none outline-none transition-colors"
            :class="confirmButtonClass"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: '確認'
  },
  message: {
    type: String,
    required: true
  },
  confirmText: {
    type: String,
    default: '確定'
  },
  cancelText: {
    type: String,
    default: '取消'
  },
  type: {
    type: String,
    default: 'info' // 'info', 'warning', 'danger'
  }
})

const emit = defineEmits(['update:show', 'confirm', 'cancel'])

const handleCancel = () => {
  emit('update:show', false)
  emit('cancel')
}

const handleConfirm = () => {
  emit('update:show', false)
  emit('confirm')
}

const confirmButtonClass = computed(() => {
  if (props.type === 'danger') {
    return 'text-white bg-red-600 hover:bg-red-700'
  } else if (props.type === 'warning') {
    return 'text-yellow-900 bg-yellow-500 hover:bg-yellow-600'
  } else {
    return 'text-white bg-nature-500 hover:bg-nature-600'
  }
})
</script>
