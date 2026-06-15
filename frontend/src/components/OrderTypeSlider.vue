<!-- 委託類型滑桿 -->
<template>
  <div 
    class="relative w-50 h-11.5 rounded-[30px] transition-all duration-300 ease-out select-none overflow-hidden"
    :class="containerClass"
  >
    <!-- Slider Handle/Thumb (only for regular mode and when not default/disabled) -->
    <div 
      v-if="!isAfterHours"
      class="absolute top-0 bottom-0 w-1/2 rounded-full transition-all duration-300 ease-out z-0"
      :class="thumbClass"
    ></div>

    <!-- Regular Mode Labels -->
    <div v-if="!isAfterHours" class="absolute inset-0 flex z-10 pointer-events-none">
      <div 
        class="flex-1 flex justify-center items-center text-02 font-bold font-sans transition-all duration-300 ease-out"
        :class="leftLabelClass"
      >
        限價
      </div>
      <div 
        class="flex-1 flex justify-center items-center text-02 font-bold font-sans transition-all duration-300 ease-out"
        :class="rightLabelClass"
      >
        市價
      </div>
    </div>

    <!-- After Hours Mode Label -->
    <div 
      v-else 
      class="absolute inset-0 flex items-center justify-center text-02 font-bold font-sans text-white z-10 pointer-events-none"
    >
      盤後定價
    </div>

    <!-- Clickable Areas -->
    <div class="absolute inset-0 flex z-20" @click="switchState">
      <template v-if="!isAfterHours">
        <div class="flex-1 cursor-pointer"></div>
        <div 
          class="flex-1" 
          :class="disabledMarket ? 'cursor-not-allowed' : 'cursor-pointer'"
        ></div>
      </template>
      <template v-else>
        <div class="w-full h-full cursor-pointer" @click="toggleAfterHours"></div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: 'default' // 'default' | 'limit' | 'market' | 'after_hours'
  },
  isAfterHours: {
    type: Boolean,
    default: false
  },
  disabledMarket: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'after-hours-click'])

// Container styles based on state
const containerClass = computed(() => {
  if (props.isAfterHours) {
    if (props.modelValue === 'after_hours') {
      return 'bg-nature-700 border-[3px] border-transparent'
    }
    return 'bg-nature-800 border-[3px] border-nature-200'
  }

  // Regular Mode
  if (props.modelValue === 'limit' || props.modelValue === 'market') {
    return 'bg-nature-700 border-[3px] border-transparent'
  }
  return 'bg-nature-800 border-[3px] border-nature-200'
})

// Sliding thumb style (Regular Mode only)
const thumbClass = computed(() => {
  if (props.disabledMarket) {
    return 'left-1/4 bg-transparent opacity-0 scale-x-0'
  }
  if (props.modelValue === 'limit') {
    return 'left-1/2 bg-nature-300 opacity-100 scale-x-100'
  }
  if (props.modelValue === 'market') {
    return 'left-0 bg-nature-300 opacity-100 scale-x-100'
  }
  return 'left-1/4 bg-transparent opacity-0 scale-x-0'
})

// Left label ("限價") styles
const leftLabelClass = computed(() => {
  if (props.modelValue === 'limit') {
    return 'text-white opacity-100'
  }
  if (props.modelValue === 'market') {
    return 'opacity-0'
  }
  return 'text-nature-200 opacity-100'
})

// Right label ("市價") styles
const rightLabelClass = computed(() => {
  if (props.disabledMarket) {
    return 'text-nature-600 opacity-100'
  }
  if (props.modelValue === 'limit') {
    return 'opacity-0'
  }
  if (props.modelValue === 'market') {
    return 'text-white opacity-100'
  }
  return 'text-nature-200 opacity-100'
})

const switchState = () => {
  if (props.modelValue === 'limit') {
    emit('update:modelValue', 'market')
  } else {
    emit('update:modelValue', 'limit')
  }
}

// Handle selection click in regular mode
const selectState = (state) => {
  if (state === 'market' && props.disabledMarket) return
  emit('update:modelValue', state)
}

// Handle click in after hours mode
const toggleAfterHours = () => {
  const nextVal = props.modelValue === 'after_hours' ? 'default' : 'after_hours'
  emit('update:modelValue', nextVal)
  emit('after-hours-click')
}
</script>
