<template>
  <div class="min-h-screen w-full flex items-center justify-center bg-[#212529] font-sans">
    
    <div class="w-full max-w-md flex flex-col items-center px-6">
      
      <h1 class="text-7xl font-bold text-white mb-5">
        錢錢錢市
      </h1>

      <form class="w-full flex flex-col gap-6" @submit.prevent>
        
        <div class="flex flex-col gap-2">
          <label class="text-white font-bold text-lg">User Name</label>
          <input 
            type="text" 
            placeholder="Content" 
            class="w-full bg-transparent border border-gray-400 text-white rounded-full px-5 py-3 focus:outline-none focus:border-yellow-400 transition-colors"
          />
          <span class="text-red-500 text-sm">錯誤訊息在這裡</span>
        </div>

        <div class="flex flex-col gap-2">
          <label class="text-white font-bold text-lg">Password</label>
          <input 
            type="password" 
            placeholder="Content" 
            class="w-full bg-transparent border border-gray-400 text-white rounded-full px-5 py-3 focus:outline-none focus:border-yellow-400 transition-colors"
          />
          <span class="text-red-500 text-sm">錯誤訊息在這裡</span>
        </div>

        <div class="flex flex-col items-center gap-4 mt-6">
          <button 
            type="submit"
            class="w-full bg-[#FFC107] hover:bg-[#ffcd38] text-[#212529] font-bold text-xl py-3 rounded-full transition-colors"
          >
            Login
          </button>
          <p class="text-gray-300 text-sm mt-2">
            Don't have account? <a href="#" class="text-white hover:underline">sign up</a>
          </p>
        </div>

      </form>
    </div>
  </div>
</template>