<template>
  <div class="company-info bg-nature-800 border-[10px] border-nature-500 rounded-lg text-white font-sans flex flex-col gap-6 shadow-2xl">
    <!-- 標頭 -->
    <div class="flex justify-between items-center w-full border-b border-nature-600 pb-3">
      <div class="flex items-center gap-2.5">
        <span class="text-04 font-bold text-nature-100 font-mono">{{ stock.stock_id }}</span>
        <span class="text-04 font-bold text-nature-100">{{ stock.stock_name_zh }}</span>
        <span class="text-02 text-nature-300 ml-2">暫停交易紀錄</span>
      </div>
      <button
        @click="emit('close')"
        class="text-nature-400 hover:text-white bg-transparent border-none text-2xl cursor-pointer leading-none p-1 transition-colors"
      >
        &times;
      </button>
    </div>

    <!-- 內容 -->
    <div class="w-full">
      <!-- 載入中 -->
      <div v-if="isLoading" class="text-center text-nature-300 py-10">
        載入中…
      </div>

      <!-- 錯誤 -->
      <div v-else-if="error" class="text-center text-red-400 py-10">
        無法載入暫停交易紀錄
      </div>

      <!-- 空狀態 -->
      <div v-else-if="records.length === 0" class="text-center text-nature-300 py-10">
        目前無暫停交易紀錄
      </div>

      <!-- 表格 -->
      <div v-else class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px]">
        <table class="w-full text-center relative">
          <thead class="sticky top-0 bg-nature-200 border-b-3 text-nature-900 font-05 text-04">
            <tr>
              <th class="py-3 px-2">暫停交易起日</th>
              <th class="py-3 px-2">暫停交易迄日</th>
              <th class="py-3 px-2">暫停交易原因</th>
            </tr>
          </thead>
          <tbody class="text-03">
            <tr
              v-for="(record, index) in records"
              :key="`${record.suspend_start_date}-${index}`"
              class="border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors"
            >
              <td class="py-3 px-2 font-mono">{{ record.suspend_start_date }}</td>
              <td class="py-3 px-2 font-mono">
                <span v-if="record.resume_date">{{ record.resume_date }}</span>
                <span v-else class="text-nature-500 italic">未知 / 預告中</span>
              </td>
              <td class="py-3 px-2">{{ record.reason }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 返回 -->
    <div class="w-full flex justify-center mt-2">
      <button
        @click="emit('close')"
        class="bg-nature-200 hover:bg-nature-300 text-nature-900 font-bold rounded-[10px] px-16 py-3 transition-colors duration-200 cursor-pointer border-none text-02"
      >
        返回
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '../api/client.js'

const props = defineProps({
  stock: {
    type: Object,
    required: true,
    default: () => ({ stock_id: '', stock_name_zh: '' })
  },
  saveId: {
    type: [Number, String],
    required: true
  }
})

const emit = defineEmits(['close'])

const records = ref([])
const isLoading = ref(true)
const error = ref(false)

onMounted(async () => {
  try {
    const res = await apiFetch(
      `/api/stocks/${props.stock.stock_id}/suspensions?save_id=${props.saveId}`
    )
    if (res.ok) {
      records.value = await res.json()
    } else {
      error.value = true
    }
  } catch {
    error.value = true
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.company-info {
  padding: 30px;
  width: 720px;
  max-width: 95vw;
  height: fit-content;
  max-height: 90vh;
  overflow-y: auto;
}
</style>
