<!-- 股票輸入框 (能有候選資料呈現) -->
<template>
  <div class="flex flex-col gap-2 w-full">
    <!-- Label (Figma Frame 55 & aligned with Input.vue) -->
    <label class="text-nature-200 font-06 text-03">{{ label }}</label>
    
    <!-- Input box + Error message Row -->
    <div class="flex items-center gap-4 w-full">
      <!-- Input Wrapper with relative positioning for dropdown -->
      <div class="relative w-[320px]" ref="containerRef">
        <input 
          type="text"
          :value="modelValue"
          @input="handleInput"
          @focus="isDropdownOpen = true"
          @keydown.enter.prevent="handleEnter"
          :placeholder="placeholder"
          class="w-full bg-nature-900 border border-nature-200 focus:border-yellow-400 text-nature-100 rounded-[10px] px-5 py-3 focus:outline-none transition-colors duration-200 font-sans"
        />
        
        <!-- Dropdown list (Styles aligned with Input.vue visual theme) -->
        <div 
          v-if="isDropdownOpen && stocks.length > 0"
          class="absolute left-0 right-0 mt-1 bg-nature-900 border border-nature-200 rounded-[10px] shadow-2xl z-50 overflow-hidden max-h-[200px] overflow-y-auto"
        >
          <div 
            v-for="stock in stocks"
            :key="stock.stock_id"
            class="grid grid-cols-[1.2fr_1.6fr_1.2fr] items-center justify-items-center text-center px-2 py-3 cursor-pointer hover:bg-nature-800 transition-colors duration-150 text-white border-b border-nature-800 last:border-b-0"
            @click="selectStock(stock)"
          >
            <!-- Left: stock_id (centered, auto-shrinking) -->
            <div 
              class="font-mono text-center text-nature-300 w-full px-1 truncate"
              :class="stock.stock_id.length >= 9 ? 'text-[10px]' : stock.stock_id.length >= 6 ? 'text-xs' : 'text-sm'"
              v-html="highlightText(stock.stock_id, modelValue)"
            ></div>
            
            <!-- Middle: stock_name_zh (centered, auto-shrinking) -->
            <div 
              class="font-bold text-center w-full px-1 truncate"
              :class="stock.stock_name_zh.length >= 8 ? 'text-[10px]' : stock.stock_name_zh.length >= 5 ? 'text-xs' : 'text-sm'"
              v-html="highlightText(stock.stock_name_zh, modelValue)"
            ></div>
            
            <!-- Right: market_type (centered) -->
            <div class="text-xs text-center text-nature-400 w-full px-1 truncate">
              {{ stock.market_type }}
            </div>
          </div>
        </div>
      </div>
      
      <!-- Error Message (Horizontal placement) -->
      <span v-if="errorMessage" class="text-red-500 text-sm font-medium shrink-0">
        {{ errorMessage }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: '股票編號'
  },
  placeholder: {
    type: String,
    default: '請輸入代碼或名稱'
  },
  errorMessage: {
    type: String,
    default: ''
  },
  stocks: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'select'])

const isDropdownOpen = ref(false)
const containerRef = ref(null)

// Handle input change
const handleInput = (e) => {
  isDropdownOpen.value = true
  emit('update:modelValue', e.target.value)
}

// Select a stock candidate
const selectStock = (stock) => {
  isDropdownOpen.value = false
  emit('update:modelValue', stock.stock_id)
  emit('select', stock)
}

// Handle Enter keypress when exactly one candidate is left
const handleEnter = () => {
  if (isDropdownOpen.value && props.stocks.length === 1) {
    selectStock(props.stocks[0])
  }
}

// Click outside handling to close dropdown
const handleClickOutside = (event) => {
  if (containerRef.value && !containerRef.value.contains(event.target)) {
    isDropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// Highlight matching search query characters in blue-500
const highlightText = (text, query) => {
  if (!text) return ''
  // escape HTML content
  const escapedText = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')

  const trimmedQuery = query.trim()
  if (!trimmedQuery) return escapedText

  const escapedQuery = trimmedQuery.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')
  const regex = new RegExp(`(${escapedQuery})`, 'gi')
  return escapedText.replace(regex, '<span class="text-blue-500 font-bold">$1</span>')
}
</script>
