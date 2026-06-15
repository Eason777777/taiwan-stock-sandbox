<template>
  <div class="fixed inset-0 z-[100] flex justify-center items-center w-full h-full bg-black/60 backdrop-blur-sm"
       v-if="currentView === 'add'" 
       @click.self="currentView = 'list'">
    <AddSave @close="currentView = 'list'" @refresh="onRefresh" />
  </div>

  <div class="w-[98%] sm:w-[80%] max-w-[1000px] gap-[10px] z-50 p-[6px] sm:p-[20px] md:p-[30px] bg-nature-800 border-nature-500 border-[3px] sm:border-[6px] md:border-[10px] h-fit flex flex-col"
      v-if="currentView === 'remove'"
      @click.self="currentView = 'list'"
  >
    <RemoveSave :saveRecords="saveRecords" @close="currentView = 'list'" @refresh="onRefresh" />
  </div>

  <div class="w-[98%] sm:w-[80%] max-w-[1000px] gap-[10px] z-50 p-[6px] sm:p-[20px] md:p-[30px] bg-nature-800 border-nature-500 border-[3px] sm:border-[6px] md:border-[10px] h-fit flex flex-col"
      v-if="currentView === 'add' || currentView === 'list'"
  >

    <div class="flex w-full h-full">
      <div class="text-02 sm:text-03 md:text-05 lg:text-06 text-nature-100 "> 存檔紀錄 </div>
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
    <!-- 存檔們 -->
    <div class="bg-nature-200 rounded-[10px] overflow-x-auto">
      <table class="w-full text-center relative min-w-[640px]">

        <thead class="sticky top-0 z-10 bg-nature-200 border-b-3 text-nature-900 font-05 text-01 sm:text-02 md:text-03 lg:text-04">
          <tr>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2">名稱</th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2">日期</th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2">時間</th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2">總資產</th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2">報酬率</th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2">存檔狀態</th>
            <th class="py-1.5 px-1 sm:py-3 sm:px-2">註記</th>
          </tr>
        </thead>

        <tbody class="text-01 sm:text-02 lg:text-03">
          <tr 
            v-for="record in saveRecords" 
            :key="record.save_id" 
            class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors cursor-pointer"
            @click="loadGame(record.save_id)"
          >
            <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ record.save_name }}</td>
            <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ record.start_date }}</td>
            <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ record.current_trade_date || '無' }}</td>
            <td class="py-1.5 px-1 sm:py-3 sm:px-2" >
              <span :class="record.total_asset > 0 ? 'text-red-600 group-hover:text-red-300' : (record.total_asset < 0 ? 'text-green-500 group-hover:text-green-300' : 'text-yellow-600 group-hover:text-yellow-300')">
                {{ formatCurrency(record.total_asset) }}
              </span></td> 
            <td class="py-1.5 px-1 sm:py-3 sm:px-2">
              <span :class="record.cumulative_return > 0.00001 ? 'text-red-600 group-hover:text-red-300' : (record.cumulative_return < -0.00001 ? 'text-green-500 group-hover:text-green-300' : 'text-yellow-700 group-hover:text-yellow-300')">
                {{ formatPercent(record.cumulative_return) }}
              </span>
            </td>
            <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ record.status === 'ACTIVE' ? '遊玩中' : '已結束' }}</td>
            <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ record.note || '-' }}</td>
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
  import AddSave from './AddSave.vue'
  import RemoveSave from './RemoveSave.vue'
  import { useRouter } from 'vue-router'
  import { apiFetch } from '../api/client.js'

  const router = useRouter()

  const saveRecords = ref([])
  const isLoading = ref(true)
  const currentView = ref('list')

  // --- 新增：數值格式化函式 ---
  const formatCurrency = (value) => {
    if (value === undefined || value === null) return '0';
    return Number(value).toLocaleString();
  }

  const formatPercent = (value) => {
    if (value === undefined || value === null) return '0%';

    return (Number(value) * 100).toFixed(2) + '%'; 
  }
  // -----------------------------

  const fetchSaves = async () => {
    try {
      const response = await apiFetch('/api/saves', {
        method: 'GET',
      })

      if (response.ok) {
        const data = await response.json()
        saveRecords.value = data
      }
    } catch {
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

  const loadGame = (recordId) => {
    router.push({
      path: '/game/custom',
      query: { saveId: recordId }
    })
  }
</script>