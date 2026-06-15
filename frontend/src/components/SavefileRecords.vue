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
    <RemoveSave :saveRecords="saveRecords" :current-save-id="currentSaveId" @close="currentView = 'list'" @refresh="onRefresh" />
  </div>

  <div class="min-w-[1280px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col"
      v-if="currentView === 'add' || currentView === 'list'"
    >
    
    <div class="flex w-full h-full">
      <div class="text-07 text-nature-100 w-full"> 存檔紀錄 </div>
      <div class="w-full flex flex-row-reverse"> <RecordSelect :titleType=3 /> </div>
    </div>

    <div class="flex w-full h-fit gap-[5px]">
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
        
        <thead class="sticky top-0 z-10 bg-nature-200 border-b-3 text-nature-900 font-05 text-04">
          <tr>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('save_name')">
              名稱 <SortIcon :active="sortKey === 'save_name'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('start_date')">
              日期 <SortIcon :active="sortKey === 'start_date'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('current_trade_date')">
              時間 <SortIcon :active="sortKey === 'current_trade_date'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('total_asset')">
              總資產 <SortIcon :active="sortKey === 'total_asset'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('cumulative_return')">
              報酬率 <SortIcon :active="sortKey === 'cumulative_return'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('status')">
              存檔狀態 <SortIcon :active="sortKey === 'status'" :order="sortOrder" />
            </th>
            <th class="py-3 px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('note')">
              註記 <SortIcon :active="sortKey === 'note'" :order="sortOrder" />
            </th>
          </tr>
        </thead>

        <tbody class="text-04 text-nature-800">
          <tr 
            v-for="record in sortedRecords" 
            :key="record.save_id" 
            class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors cursor-pointer"
            @click="loadGame(record.save_id)"
          >
            <td class="py-3 px-2">{{ record.save_name }}</td>
            <td class="py-3 px-2">{{ record.start_date }}</td>
            <td class="py-3 px-2">{{ record.current_trade_date || '無' }}</td>
            <td class="py-3 px-2" >
              <span :class="record.total_asset > 0 ? 'text-red-600 group-hover:text-red-300' : (record.total_asset < 0 ? 'text-green-500 group-hover:text-green-300' : 'text-yellow-600 group-hover:text-yellow-300')">
                {{ formatCurrency(record.total_asset) }}
              </span></td> 
            <td class="py-3 px-2">
              <span :class="record.cumulative_return > 0.00001 ? 'text-red-600 group-hover:text-red-300' : (record.cumulative_return < -0.00001 ? 'text-green-500 group-hover:text-green-300' : 'text-yellow-700 group-hover:text-yellow-300')">
                {{ formatPercent(record.cumulative_return) }}
              </span>
            </td>
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
  // 🚀 引入 computed, defineComponent, h
  import { ref, onMounted, computed, defineComponent, h } from 'vue'
  import RecordSelect from './RecordSelect.vue'
  import AddSave from './AddSave.vue'
  import RemoveSave from './RemoveSave.vue'
  import { useRouter } from 'vue-router'

  // 🚀 排序圖示元件
  const SortIcon = defineComponent({
    props: ['active', 'order'],
    setup(props) {
      return () => {
        let iconText = '⇅'
        let colorClass = 'text-nature-900'

        if (props.active) {
          if (props.order === 'asc') {
            iconText = '▲'
            colorClass = 'text-nature-900'
          } else if (props.order === 'desc') {
            iconText = '▼'
            colorClass = 'text-nature-900'
          }
        }

        return h('span', { 
          class: `inline-block ml-1 align-middle text-03 font-bold transition-colors ${colorClass}` 
        }, iconText)
      }
    }
  })

  defineProps({
    currentSaveId: {
      type: Number,
      default: null
    }
  })

  const router = useRouter()

  const saveRecords = ref([])
  const isLoading = ref(true)
  const currentView = ref('list')

  // 🚀 定義排序狀態
  const sortKey = ref('')
  const sortOrder = ref('') // 'asc' 或 'desc' 或 ''

  // 🚀 點擊表頭的排序切換邏輯
  const sortBy = (key) => {
    if (sortKey.value === key) {
      if (sortOrder.value === 'asc') {
        sortOrder.value = 'desc'
      } else if (sortOrder.value === 'desc') {
        sortOrder.value = ''
        sortKey.value = ''
      }
    } else {
      sortKey.value = key
      sortOrder.value = 'asc'
    }
  }

  // 🚀 依據排序狀態動態計算的陣列
  const sortedRecords = computed(() => {
    if (!sortKey.value || !sortOrder.value) return saveRecords.value

    return [...saveRecords.value].sort((a, b) => {
      let valA = a[sortKey.value]
      let valB = b[sortKey.value]

      // 確保數字欄位轉型正確，以便正確比對大小
      if (!isNaN(valA) && valA !== null && valA !== '') valA = Number(valA)
      if (!isNaN(valB) && valB !== null && valB !== '') valB = Number(valB)

      // 將 null 或 undefined 的值往後排
      if (valA === null || valA === undefined || valA === '') return 1
      if (valB === null || valB === undefined || valB === '') return -1

      if (valA < valB) return sortOrder.value === 'asc' ? -1 : 1
      if (valA > valB) return sortOrder.value === 'asc' ? 1 : -1
      return 0
    })
  })

  const formatCurrency = (value) => {
    if (value === undefined || value === null) return '0';
    return Number(value).toLocaleString();
  }

  const formatPercent = (value) => {
    if (value === undefined || value === null) return '0%';
    return (Number(value) * 100).toFixed(2) + '%'; 
  }

  // 呼叫 API 的函式
  const fetchSaves = async () => {
    try {
        const response = await fetch('/api/saves', {headers: {
          'Content-Type': 'application/json',
          'x-session-id': localStorage.getItem('session_id') || ''
        }
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