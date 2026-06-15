<!-- 頂部工具列 -->
<template>
  <div class="w-full flex flex-col">
    <!-- 1. 頂部狀態列 TopState -->
    <div class="w-full bg-topbar-blue text-white text-01 px-8.5 py-0.25 flex justify-between items-center font-sans font-medium shadow-sm">
      <!-- 左側：目前使用者與登出鍵 -->
      <div class="flex items-center gap-4 flex-1">
        <div>目前使用者：<span class="text-white font-semibold">{{ username }}</span></div>
        <button
          @click="handleLogout"
          class="rounded-lg border border-white my-1 px-2 py-0.5 text-01 font-bold text-white bg-sky-400 cursor-pointer transition-colors duration-150 hover:bg-topbar-blue"
        >
          LOGOUT
        </button>
      </div>

      <!-- 中間：日期與狀態 -->
      <div class="flex items-center justify-center gap-4 flex-1">
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
import { apiFetch } from '../api/client.js'

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
  },
  // 目前登入的使用者帳號
  username: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:activeTab'])

const tabs = ['自選', '交易', '資產', '紀錄']

const selectTab = (tab) => {
  emit('update:activeTab', tab)
}

// 登出：呼叫後端清除 session，並清空本機憑證後導回登入頁
const handleLogout = async () => {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' })
  } catch (error) {
    console.error('登出 API 連線異常:', error)
  } finally {
    localStorage.removeItem('session_id')
    localStorage.setItem('logout_message', '已登出')
    window.location.assign('/')
  }
}
</script>
