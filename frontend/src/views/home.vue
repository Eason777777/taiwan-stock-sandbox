<script setup>
import { ref } from 'vue'

const serverStatus = ref('尚未連線')
const isLoading = ref(false)

async function checkBackend() {
  isLoading.value = true
  try {
    // 💡 關鍵：精準瞄準你 FastAPI 的首頁路徑 "/"
    const response = await fetch('http://127.0.0.1:8000/')
    console.log('後端回應：', response)
    const data = await response.json()
    
    console.log('後端回應：', data)
    
    // 把後端回傳的 {"message": "API is running"} 塞給變數
    serverStatus.value = data.message 
  } catch (error) {
    serverStatus.value = '連線失敗，請檢查後端是否有點亮！'
    console.error(error)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="test-connect">
    <h2>📡 測試與 FastAPI 後端連線</h2>
    
    <button @click="checkBackend" :disabled="isLoading">
      {{ isLoading ? '連線中...' : '檢查後端狀態' }}
    </button>

    <div class="status-box">
      伺服器回應：<strong>{{ serverStatus }}</strong>
    </div>
  </div>
</template>

<style scoped>
</style>