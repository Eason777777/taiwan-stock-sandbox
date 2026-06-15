<template>
  <div class="fixed inset-0 z-[100] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
       v-if="currentView === 'add'" 
       @click.self="currentView = 'list'">
        <AddSave @close="currentView = 'list'" />
  </div>

  <div class="min-w-[1280px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col"
      v-if="currentView === 'remove'" 
      @click.self="currentView = 'list'"
  >
    <RemoveSave :saveRecords="saveRecords" @close="currentView = 'list'" @refresh="onRefresh" />
  </div>

  <div class="min-w-[1280px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col"
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

        <tbody class="text-04 text-nature-800">
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
  import RecordSelect from './RecordSelect.vue'
  import AddSave from './AddSave.vue'
  import RemoveSave from './RemoveSave.vue'
  import { useRouter } from 'vue-router' 

  const router = useRouter()

  // 準備一個空的陣列，用來裝後端傳回來的真實存檔資料
  const saveRecords = ref([])
  const isLoading = ref(true)
  const currentView = ref('list')

  // 呼叫 API 的函式
  const fetchSaves = async () => {
    try {
        headers: {
          'Content-Type': 'application/json',
          // 🚀 關鍵修正：必須用後端規定的 x-session-id
          'x-session-id': localStorage.getItem('session_id') || ''
        }
      })

      if (response.ok) {
        const data = await response.json()
        console.log('✅ 成功拿到後端資料:', data) // 👉 打開 F12 看這裡！確認後端的欄位名稱
        saveRecords.value = data
      } else {
        console.error('無法取得存檔，可能是尚未登入或 Session 過期')
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

  const onRefresh = () => {
    fetchSaves()
    currentView.value = 'list'
  }

  // 🗑️ 注意：請把原本底下的 mockSaveRecords 跟 saveRecords.value = ... 整段刪除！
  // 讓表格保持乾淨，才能確認真資料有沒有進來。

  const loadGame = (recordId) => {
    console.log('準備讀取存檔 ID:', recordId)
    router.push({
      path: '/custom', 
      query: { saveId: recordId } 
    })
  }
</script>