<template>
  <div class="fixed inset-0 z-[100] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
       v-if="currentView === 'add'" 
       @click.self="currentView = 'list'">
        <AddSave @close="currentView = 'list'" />
  </div>

  <div class="min-w-[1080px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col"
      v-if="currentView === 'remove'" 
      @click.self="currentView = 'list'"
  >
    <RemoveSave :saveRecords="saveRecords" @close="currentView = 'list'" @refresh="onRefresh" />
  </div>

  <div class="min-w-[1080px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col"
      v-if="currentView === 'add' || currentView === 'list'"
    >
    
    <div class="flex w-full h-full">
      <div class="text-07 text-nature-100 w-full"> 存檔紀錄 </div>
      <div class="w-full flex flex-row-reverse"> <RecordSelect :titleType=3 /> </div>
    </div>

    <div class="flex w-full h-fit gap-[5px]">
    <!-- 新增存檔按鈕 -->
        <button @click="currentView = 'add'" class="relative group w-full h-[64px] bg-yellow-500 flex justify-center items-center cursor-pointer rounded-l-[10px] hover:bg-yellow-700 transition-colors duration-300 ease-in-out"> 
            <div class="absolute opacity-100 group-hover:opacity-0 transition-opacity duration-300 ease-in-out">
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="32" cy="32" r="24" stroke="#B89300" stroke-width="5.66667"/>
                <path d="M32 40L32 24" stroke="#B89300" stroke-width="5.66667" stroke-linecap="square"/>
                <path d="M40 32L24 32" stroke="#B89300" stroke-width="5.66667" stroke-linecap="square"/>
                </svg>
            </div>
            <div class="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-in-out">
                <div class="text-yellow-500 text-05 font-sans font-06"> 新增存檔 </div>
            </div>
        </button>

        <!-- 移除存檔按鈕 -->
        <button @click="currentView = 'remove'" class="group w-full h-[64px] bg-red-300 flex justify-center items-center transition-colors cursor-pointer rounded-r-[10px] hover:bg-red-700 transition-colors duration-300 ease-in-out">
            <div class="absolute opacity-100 group-hover:opacity-0 transition-opacity duration-300 ease-in-out">
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="32" cy="32" r="24" stroke="#A4133C" stroke-width="4.83333"/>
                <path d="M24 39.9991L40 23.9991" stroke="#A4133C" stroke-width="4.83333"/>
                <path d="M40 40L24 24" stroke="#A4133C" stroke-width="4.83333"/>
            </svg>
            </div>
            <div class="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-in-out">
            <div class="text-red-300 text-05 font-sans font-06"> 移除存檔 </div>
            </div>
        </button>
    </div>

    <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px]">
      <table class="w-full text-center relative">
        
        <thead class="sticky top-0 bg-nature-200 border-b-3 text-nature-900 font-05 text-04">
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

        <tbody class="text-03">
          <tr 
            v-for="record in saveRecords" 
            :key="record.save_id" 
            class="border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors cursor-pointer"
            @click="loadGame(record.save_id)"
          >
            <td class="py-3 px-2">{{ record.save_name }}</td>
            <td class="py-3 px-2">{{ record.start_date }}</td>
            <td class="py-3 px-2">{{ record.current_trade_date || '無' }}</td>
            <td class="py-3 px-2">{{ record.savings_balance }}</td> 
            <td class="py-3 px-2">{{ record.returnRate || '0%' }}</td>
            <td class="py-3 px-2">{{ record.status === 'ACTIVE' ? '遊玩中' : '已結束' }}</td>
            <td class="py-3 px-2">{{ record.note || '-' }}</td>
          </tr>
          
          <tr class="h-[50px] bg-nature-200">
            <td colspan="7"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
  import { ref, onMounted } from 'vue'
  import { useRoute } from 'vue-router'
  import RecordSelect from './RecordSelect.vue'
  import AddSave from './AddSave.vue'
  import RemoveSave from './RemoveSave.vue'

  const saveRecords = ref([])
  const isLoading = ref(true)
  const currentView = ref('list')

  // 🚀 2. 啟動 route 物件，用來讀取當前網址的資訊
  const route = useRoute()

  const fetchSaves = async () => {
    // 🚀 3. 從網址列提取 saveId (例如網址是 /custom?saveId=5，這裡就會拿到 '5')
    const saveId = route.query.saveId

    // 🚀 4. 防呆機制：如果網址沒有 saveId，就阻擋後續的 API 請求
    if (!saveId) {
      console.error('缺少存檔 ID，無法載入資料')
      isLoading.value = false
      return
    }

    try {
      // 將拿到的 saveId 動態帶入 API 網址中
      const response = await fetch(`/api/holding/transactions?save_id=${saveId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'x-session-id': localStorage.getItem('session_id')
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('成功拿到後端資料:', data)
        saveRecords.value = data
      } else {
        console.error('無法取得交易紀錄，可能是尚未登入、Session 過期，或無權限存取此存檔')
      }
    } catch (error) {
      console.error('API 連線失敗:', error)
    } finally {
      isLoading.value = false
    }
  }

  onMounted(() => {
    fetchSaves()
  })
</script>