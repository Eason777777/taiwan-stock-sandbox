<template>
  <div class="absolute flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
      v-if="isShowSaveModal" 
      @close="isShowSaveModal = false" >
    <SaveRecords />
  </div>
  
  <div class="min-h-screen w-full flex items-center justify-center bg-nature-900 font-sans">
    <div class="w-full max-w-md flex flex-col items-center px-6">

      <h1 class="text-7xl font-bold text-white mb-5">
        錢錢錢市
      </h1>

      <form class="w-full flex flex-col gap-6" @submit.prevent="handleLogin">
        <Input
          v-model="username"
          label="User Name"
          placeholder="請輸入帳號"
          variant="soft"
        />

        <Input
          v-model="password"
          label="Password"
          type="password"
          placeholder="請輸入密碼"
          variant="soft"
        />

        <div v-if="errorMessage" class="text-red-500 text-sm text-center font-medium">
          {{ errorMessage }}
        </div>

        <div class="flex flex-col items-center gap-4 mt-2">
          <button 
            type="submit"
            :disabled="isLoading"
            class="w-full bg-yellow-500 hover:bg-yellow-700 hover:cursor-pointer text-nature-900 font-bold text-xl py-3 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ isLoading ? '登入中...' : 'Login' }}
          </button>
          
          <p class="text-nature-300 text-sm mt-2">
            Don't have account? 
            <router-link to="/signup" class="text-white hover:underline hover:cursor-pointer">
              sign up
            </router-link>
          </p>
        </div>

      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import SaveRecords from '../components/SaveRecords.vue'
import Input from '../components/Input.vue'

// --- 變數狀態管理 ---
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const isLoading = ref(false)
const isShowSaveModal = ref(false)

const saveRecords = ref([
  { id: 1, name: '存檔一', date: '4/31', time: '9:00', assets: 1000, returnRate: '10%', status: '遊玩中', note: '別點我' },
])
// --- 登入邏輯 ---
const handleLogin = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = '請填寫完整的帳號與密碼！'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    // 透過 Vite dev server 的 proxy 轉發到後端（見 vite.config.js），
    // 避免外部裝置（如透過 tailscale funnel）直連 127.0.0.1:8000 連不到的問題
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        account: username.value,  // 這裡將前端的 username 映射給後端的 account
        password: password.value
      })
    })

    const data = await response.json()

    if (response.ok) {
      // 成功：接收 session_id
      console.log('登入成功，取得 Session ID:', data.session_id)
      localStorage.setItem('session_id', data.session_id)
      isShowSaveModal.value = true
    } else {
      // 失敗：接住 FastAPI 的 detail 錯誤訊息
      errorMessage.value = data.detail || '登入失敗，請檢查帳號密碼'
    }

  } catch (error) {
    console.error('API 請求發生錯誤:', error)
    errorMessage.value = '無法連線到伺服器，請確保後端已啟動。'
  } finally {
    isLoading.value = false
  }
}

</script>