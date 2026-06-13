<template>
  <div class="topbar-wrapper">
    <!-- 1. 頂部狀態列 (傳遞日期、狀態、餘額資料) -->
    <TopState 
      :date="date" 
      :status="status" 
      :savings="savings" 
      :delivery="delivery" 
    />
    <!-- 2. 下方導覽分頁列 (雙向綁定 activeTab) -->
    <NavBar v-model="currentTab" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import TopState from './TopState.vue'
import NavBar from './NavBar.vue'

const props = defineProps({
  // 雙向綁定目前選中的 Tab 頁面
  activeTab: {
    type: String,
    required: true
  },
  // 傳遞給 TopState 的資料
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

const emit = defineEmits(['update:activeTab'])

// 透過 computed 代理 v-model 的值，將異動同步回父組件
const currentTab = computed({
  get: () => props.activeTab,
  set: (val) => emit('update:activeTab', val)
})
</script>

<style scoped>
.topbar-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
}
</style>
