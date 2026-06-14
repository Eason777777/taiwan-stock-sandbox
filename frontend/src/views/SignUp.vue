<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-nature-900 font-sans">
    <div class="w-full max-w-md flex flex-col items-center px-6">
      
      <h1 class="text-7xl font-bold text-white mb-5">
        註冊帳號
      </h1>

      <form class="w-full flex flex-col gap-6" @submit.prevent="handleSignUp">
        
        <div class="flex flex-col gap-2">
          <label class="text-white font-bold text-lg">User Name</label>
          <input 
            v-model="username"
            type="text" 
            placeholder="請輸入帳號" 
            class="w-full bg-transparent border border-nature-400 text-white rounded-full px-5 py-3 focus:outline-none focus:border-yellow-500 transition-colors"
          />
        </div>

        <div class="flex flex-col gap-2">
          <label class="text-white font-bold text-lg">Password</label>
          <input 
            v-model="password"
            type="password" 
            placeholder="請輸入密碼" 
            class="w-full bg-transparent border border-nature-400 text-white rounded-full px-5 py-3 focus:outline-none focus:border-yellow-500 transition-colors"
          />
        </div>

        <div v-if="errorMessage" class="text-red-500 text-sm text-center font-medium">
          {{ errorMessage }}
        </div>

        <div class="flex flex-col items-center gap-4 mt-2">
          <button 
            type="submit"
            :disabled="isLoading"
            class="w-full bg-yellow-500 hover:bg-yellow-700 hover:cursor-pointer text-nature-900 font-bold text-xl py-3 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ isLoading ? '註冊中...' : 'Sign Up' }}
          </button>
          
          <p class="text-nature-300 text-sm mt-2">
            Already have an account? 
            <router-link to="/" class="text-white hover:underline hover:cursor-pointer">
              login
            </router-link>
          </p>
        </div>

      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
// 如果你有設定 Vue Router，通常登入成功後會用它來跳轉頁面
// import { useRouter } from 'vue-router'
// const router = useRouter()

// --- 變數狀態管理 ---
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const isLoading = ref(false)

// --- 註冊邏輯 ---
const handleSignUp = async () => {
  if (!username.value || !password.value) {
    errorMessage.value = '請填寫完整的帳號與密碼！'
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    // 透過 Vite dev server 的 proxy 轉發到後端（見 vite.config.js），
    // 避免外部裝置（如透過 tailscale funnel）直連 127.0.0.1:8000 連不到的問題
    const response = await fetch('/api/auth/register', {
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
      console.log('註冊成功', data.message)
      alert('註冊成功！')
    } else {
      // 失敗：接住 FastAPI 的 detail 錯誤訊息
      errorMessage.value = data.detail || '註冊失敗，請檢查輸入資訊'
    }

  } catch (error) {
    console.error('API 請求發生錯誤:', error)
    errorMessage.value = '無法連線到伺服器，請確保後端已啟動。'
  } finally {
    isLoading.value = false
  }
}

</script>