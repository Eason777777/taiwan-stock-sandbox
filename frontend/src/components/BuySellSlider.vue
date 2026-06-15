<!-- 買賣滑桿 -->
<template>
  <div 
    class="relative w-50 h-11.5 rounded-[30px] transition-all duration-300 ease-out select-none overflow-hidden"
    :class="containerClass"
  >
    <!-- Slider Handle/Thumb -->
    <div 
      class="absolute top-0 bottom-0 w-1/2 rounded-full transition-all duration-300 ease-out z-0"
      :class="thumbClass"
    ></div>

    <!-- Text Labels -->
    <div class="absolute inset-0 flex z-10 pointer-events-none">
      <div 
        class="flex-1 flex justify-center items-center text-02 font-bold font-sans transition-all duration-300 ease-out"
        :class="leftLabelClass"
      >
        買
      </div>
      <div 
        class="flex-1 flex justify-center items-center text-02 font-bold font-sans transition-all duration-300 ease-out"
        :class="rightLabelClass"
      >
        賣
      </div>
    </div>

    <!-- Clickable Areas -->
    <div class="absolute inset-0 flex z-20" @click="switchState()">
      <div class="flex-1 cursor-pointer"></div>
      <div class="flex-1 cursor-pointer"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: 'default' // 'default' | 'buy' | 'sell'
  }
})

const emit = defineEmits(['update:modelValue'])

// Container styles based on the active state
const containerClass = computed(() => {
  if (props.modelValue === 'buy') {
    return 'bg-red-800 border-[3px] border-transparent'
  }
  if (props.modelValue === 'sell') {
    return 'bg-green-700 border-[3px] border-transparent'
  }
  // default / pre-active
  return 'bg-nature-800 border-[3px] border-nature-200'
})

// Sliding thumb style, position and color
const thumbClass = computed(() => {
  if (props.modelValue === 'buy') {
    return 'left-1/2 bg-red-500 opacity-100 scale-x-100'
  }
  if (props.modelValue === 'sell') {
    return 'left-0 bg-green-300 opacity-100 scale-x-100'
  }
  // default: hidden/collapsed thumb
  return 'left-1/4 bg-transparent opacity-0 scale-x-0'
})

// Left label ("買") styles
const leftLabelClass = computed(() => {
  if (props.modelValue === 'buy') {
    return 'text-red-300 opacity-100'
  }
  if (props.modelValue === 'sell') {
    return 'opacity-0' // Hidden when covered by the sell handle on the left
  }
  // default state
  return 'text-nature-200 opacity-100'
})

// Right label ("賣") styles
const rightLabelClass = computed(() => {
  if (props.modelValue === 'buy') {
    return 'opacity-0' // Hidden when covered by the buy handle on the right
  }
  if (props.modelValue === 'sell') {
    return 'text-green-200 opacity-100'
  }
  // default state
  return 'text-nature-200 opacity-100'
})

// Handle selection click
const switchState = () => {
  if (props.modelValue === 'buy') {
    emit('update:modelValue', 'sell')
  } else {
    emit('update:modelValue', 'buy')
  }
}

// Handle selection click
const selectState = (state) => {
  emit('update:modelValue', state)
}
</script>
