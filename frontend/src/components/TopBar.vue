<!-- 頂部工具列 -->
<template>
  <div class="w-full flex flex-col">
    <!-- 1. 頂部狀態列 TopState -->
    <div class="w-full bg-topbar-blue text-white text-01 px-8.5 py-3.5 flex justify-between items-center font-sans font-medium shadow-sm">
      <!-- 左側：日期與狀態 -->
      <div class="flex items-center gap-4 flex-1">
        <div>日期：<span class="text-white font-semibold">{{ date }}</span></div>
        <div>狀態：<span class="text-white font-semibold">{{ status }}</span></div>
      </div>
      
      <!-- 右側：帳戶餘額 -->
      <div class="flex justify-end items-center gap-4 flex-1">
        <div>存款戶：<span class="text-white font-bold">{{ savings }}</span></div>
        <div>交割戶：<span class="text-white font-bold">{{ delivery }}</span></div>
      </div>
    </div>

    <!-- 2. 下方導覽分頁列 NavBar  -->
    <div class="w-full max-w-480 bg-navbar-background p-1.25 gap-2.5 flex font-sans">
      <button
        v-for="tab in tabs"
        :key="tab"
        @click="selectTab(tab)"
        class="flex-1 py-3 text-center text-02 font-bold rounded border-2 cursor-pointer transition-all duration-150 outline-none"
        :class="[
          activeTab === tab
            ? 'bg-nature-600 text-white border-white'
            : 'bg-white text-nature-900 border-transparent hover:bg-nature-100'
        ]"
      >
        {{ tab }}
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  // 雙向綁定目前選中的 Tab
  activeTab: {
    type: String,
    required: true
  },
  // 傳遞給狀態列的資料
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

const tabs = ['自選', '交易', '資產', '紀錄']

const selectTab = (tab) => {
  emit('update:activeTab', tab)
}
</script>
