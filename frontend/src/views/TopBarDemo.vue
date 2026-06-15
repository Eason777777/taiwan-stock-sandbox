<!-- TopBar 元件獨立預覽頁 (路由 /demo/topbar) -->
<template>
  <div class="min-h-screen flex flex-col bg-nature-900 text-white">
    <!-- 1. 被預覽的 TopBar 元件 -->
    <TopBar
      v-model:activeTab="currentTab"
      :date="date"
      :status="status"
      :savings="Number(savings).toLocaleString()"
      :delivery="Number(delivery).toLocaleString()"
      :username="username"
      :save-name="saveName"
    />

    <!-- 2. props 控制面板，方便單獨調整檢視 TopBar 各種狀態 -->
    <div class="flex-1 flex flex-col items-center p-6 w-full">
      <div class="w-full max-w-200 bg-white text-nature-900 rounded-xl p-6 shadow-lg">
        <h2 class="text-03 font-bold mb-4">TopBar 預覽控制台</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label class="flex flex-col gap-1 font-semibold">
            使用者帳號 username
            <input v-model="username" class="border rounded px-2 py-1 font-normal" />
          </label>
          <label class="flex flex-col gap-1 font-semibold">
            存檔名稱 saveName
            <input v-model="saveName" class="border rounded px-2 py-1 font-normal" />
          </label>
          <label class="flex flex-col gap-1 font-semibold">
            日期 date
            <input v-model="date" class="border rounded px-2 py-1 font-normal" />
          </label>
          <label class="flex flex-col gap-1 font-semibold">
            狀態 status
            <input v-model="status" class="border rounded px-2 py-1 font-normal" />
          </label>
          <label class="flex flex-col gap-1 font-semibold">
            存款戶 savings
            <input v-model="savings" type="number" class="border rounded px-2 py-1 font-normal" />
          </label>
          <label class="flex flex-col gap-1 font-semibold">
            交割戶 delivery
            <input v-model="delivery" type="number" class="border rounded px-2 py-1 font-normal" />
          </label>
        </div>
        <p class="mt-4 text-01 text-nature-600">
          目前選中分頁：<span class="font-bold text-nature-900">{{ currentTab }}</span>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import TopBar from '../components/TopBar.vue'

const currentTab = ref('自選')
const date = ref('2026/06/15')
const status = ref('盤前 (08:30)')
const savings = ref(1000)
const delivery = ref(2000)
const username = ref('demo_user')
const saveName = ref('我的第一個存檔')
</script>
