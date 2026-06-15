<template>
  <div class="min-h-screen flex flex-col items-center justify-center gap-8 bg-nature-900 text-white p-6">
    <h1 class="text-2xl font-bold">ConfirmModal 元件預覽</h1>

    <!-- 即時調整參數的控制面板 -->
    <div class="w-full max-w-md flex flex-col gap-4 bg-nature-800 rounded-2xl p-6">
      <label class="flex flex-col gap-1">
        <span class="text-nature-300 text-sm">標題 title</span>
        <input v-model="title" class="rounded-md px-3 py-2 text-nature-900" />
      </label>

      <label class="flex flex-col gap-1">
        <span class="text-nature-300 text-sm">訊息 message</span>
        <textarea v-model="message" rows="2" class="rounded-md px-3 py-2 text-nature-900" />
      </label>

      <div class="flex gap-3">
        <label class="flex flex-col gap-1 flex-1">
          <span class="text-nature-300 text-sm">確認文字 confirmText</span>
          <input v-model="confirmText" class="rounded-md px-3 py-2 text-nature-900" />
        </label>
        <label class="flex flex-col gap-1 flex-1">
          <span class="text-nature-300 text-sm">取消文字 cancelText</span>
          <input v-model="cancelText" class="rounded-md px-3 py-2 text-nature-900" />
        </label>
      </div>

      <label class="flex flex-col gap-1">
        <span class="text-nature-300 text-sm">類型 type</span>
        <select v-model="type" class="rounded-md px-3 py-2 text-nature-900">
          <option value="info">info（一般）</option>
          <option value="warning">warning（警告）</option>
          <option value="danger">danger（危險）</option>
        </select>
      </label>
    </div>

    <!-- 開啟彈窗 -->
    <button
      @click="show = true"
      class="bg-[#FFC107] hover:bg-[#B79300] hover:cursor-pointer text-[#212529] font-bold text-lg px-8 py-3 rounded-full transition-colors"
    >
      開啟彈窗
    </button>

    <!-- 顯示最近一次互動結果，方便確認事件有正常觸發 -->
    <p class="text-nature-400">最近一次操作：{{ lastAction }}</p>

    <!-- 被預覽的元件本體 -->
    <ConfirmModal
      v-model:show="show"
      :title="title"
      :message="message"
      :confirm-text="confirmText"
      :cancel-text="cancelText"
      :type="type"
      @confirm="lastAction = '點擊了「確認」'"
      @cancel="lastAction = '點擊了「取消」'"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ConfirmModal from '../components/ConfirmModal.vue'

const show = ref(false)
const title = ref('確定要刪除這個存檔嗎？')
const message = ref('刪除後，所有的交易紀錄與資產都將無法恢復喔！')
const confirmText = ref('刪除')
const cancelText = ref('返回')
const type = ref('danger')

const lastAction = ref('尚未操作')
</script>
