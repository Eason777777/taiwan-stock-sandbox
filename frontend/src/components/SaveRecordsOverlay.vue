<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
    <div class="bg-nature-800 border-[4px] border-gray-400 rounded-lg p-6 w-full max-w-4xl shadow-2xl">
      
      <h2 class="text-3xl text-white font-bold mb-4">存檔紀錄</h2>
      
      <div class="flex w-full mb-4 rounded-md overflow-hidden font-bold text-xl">
        
        <button class="group flex-1 bg-yellow-500 hover:bg-yellow-700 flex justify-center items-center transition-colors cursor-pointer">
          <span class="block group-hover:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-7 h-7 text-yellow-800" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" fill="none" stroke-linecap="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M9 12h6m-3-3v6" />
            </svg>
          </span>
          <span class="hidden group-hover:block text-yellow-500 text-[24px]">新增存檔</span>
        </button>

        <button class="group flex-1 bg-[#F5A9B8] hover:bg-[#A12035] py-2 flex justify-center items-center transition-colors cursor-pointer">
          <span class="block group-hover:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-7 h-7 text-red-800" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" fill="none" stroke-linecap="round">
              <circle cx="12" cy="12" r="9" />
              <path d="M10 10l4 4m0-4l-4 4" />
            </svg>
          </span>
          <span class="hidden group-hover:block text-[#F5A9B8] tracking-widest">移除存檔</span>
        </button>
        
      </div>

      <div class="bg-white rounded overflow-hidden">
        <table class="w-full text-center border-collapse">
          <thead class="border-b-[3px] border-gray-400 text-black font-bold">
            <tr>
              <th class="py-3 px-2">名稱</th>
              <th class="py-3 px-2">日期</th>
              <th class="py-3 px-2">時間</th>
              <th class="py-3 px-2">總資產</th>
              <th class="py-3 px-2">報酬率</th>
              <th class="py-3 px-2">存檔狀態</th>
              <th class="py-3 px-2">註記</th>
            </tr>
          </thead>
          <tbody class="text-gray-800">
            <tr 
              v-for="record in saveRecords" 
              :key="record.id" 
              class="border-b-[3px] border-gray-300 font-medium hover:bg-gray-500 hover:text-white transition-colors cursor-pointer"
              @click="loadGame(record.id)"
            >
              <td class="py-3 px-2">{{ record.name }}</td>
              <td class="py-3 px-2">{{ record.date }}</td>
              <td class="py-3 px-2">{{ record.time }}</td>
              <td class="py-3 px-2">{{ record.assets }}</td>
              <td class="py-3 px-2">{{ record.returnRate }}</td>
              <td class="py-3 px-2">{{ record.status }}</td>
              <td class="py-3 px-2">{{ record.note }}</td>
            </tr>
            <tr class="h-12 bg-gray-100"><td colspan="7"></td></tr>
          </tbody>
        </table>
      </div>
      
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const saveRecords = ref([
  { id: 1, name: '存檔一', date: '4/31', time: '9:00', assets: 1000, returnRate: '10%', status: '遊玩中', note: '別點我' },
])

const loadGame = (recordId) => {
  console.log('準備讀取存檔 ID:', recordId)
  alert(`讀取存檔 ${recordId}，準備進入遊戲！`)
}
</script>