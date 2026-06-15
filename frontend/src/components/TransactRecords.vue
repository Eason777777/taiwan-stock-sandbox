<template>
  <div class="rounded-[10px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col">
    
    <div class="flex w-full h-full">
      <div class="text-04 lg:text-06 text-nature-100 w-full"> 轉帳紀錄 </div>
      <div class="w-full flex flex-row-reverse"> <RecordSelect :titleType="2"/> </div>
    </div>

    <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px]">
        <table class="min-w-[900px] md:min-w-[1200px] w-full text-center text-nature-800 relative">
            
            <thead class="text-[12px] lg:text-02 sticky top-0 z-10 bg-nature-200 border-b-3 text-nature-900 font-05 text-03">
            <tr>
                <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('sim_date')">
                  交易日期 <SortIcon :active="sortKey === 'sim_date'" :order="sortOrder" />
                </th>
                <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('account_type')">
                  帳戶類型 <SortIcon :active="sortKey === 'account_type'" :order="sortOrder" />
                </th> 
                <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('change_type')">
                  摘要 <SortIcon :active="sortKey === 'change_type'" :order="sortOrder" />
                </th>
                <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('amount_withdrawal')">
                  提款 <SortIcon :active="sortKey === 'amount_withdrawal'" :order="sortOrder" />
                </th>
                <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('amount_deposit')">
                  存款 <SortIcon :active="sortKey === 'amount_deposit'" :order="sortOrder" />
                </th>
                <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('balance_after')">
                  結餘 <SortIcon :active="sortKey === 'balance_after'" :order="sortOrder" />
                </th>
                <th class="py-1.5 px-1 sm:py-3 sm:px-2 cursor-pointer hover:bg-nature-300 select-none transition-colors" @click="sortBy('note')">
                  註記 <SortIcon :active="sortKey === 'note'" :order="sortOrder" />
                </th>
            </tr>
            </thead>

            <tbody class="text-[10px] sm:text-01 md:text-02 lg:text-03">
                <tr 
                    v-for="record in sortedRecords" 
                    :key="record.seq" 
                    class="group border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors"
                >
                    <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ record.sim_date.slice(0, 10) }}</td>
                    
                    <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ formatAccountType(record.account_type) }}</td>
                    
                    <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ formatChangeType(record.change_type) }}</td>
                    
                    <td class="group-hover:text-green-300 py-1.5 px-1 sm:py-3 sm:px-2 text-green-500">
                        {{ isWithdrawal(record.change_type) ? formatNumber(record.amount) : '-' }}
                    </td>
                    
                    <td class="group-hover:text-red-300 py-1.5 px-1 sm:py-3 sm:px-2 text-red-600">
                        {{ isDeposit(record.change_type) ? formatNumber(record.amount) : '-' }}
                    </td>
                    
                    <td class="py-1.5 px-1 sm:py-3 sm:px-2">{{ formatNumber(record.balance_after) }}</td>
                    
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
  import { ref, onMounted, computed, defineComponent, h } from 'vue'
  import { useRoute } from 'vue-router'
  import RecordSelect from './RecordSelect.vue'

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
          class: `inline-block ml-1 align-middle text-[10px] lg:text-01 font-bold transition-colors ${colorClass}` 
        }, iconText)
      }
    }
  })

  const saveRecords = ref([])
  const isLoading = ref(true)

  // 🚀 定義排序狀態
  const sortKey = ref('')
  const sortOrder = ref('')

  const route = useRoute()

  // ==========================================
  // --- 顯示轉換與判斷邏輯 (Formatters) ---
  // 💡 移至上方，確保 sortedRecords 可以讀取到這些函式
  // ==========================================

  const formatAccountType = (type) => {
    if (type === 'SAVINGS') return '存款戶'
    if (type === 'TRADING') return '交割戶'
    return type
  }

  const formatChangeType = (type) => {
    const typeMap = {
      'INITIAL_DEPOSIT': '開戶存入',
      'TRANSFER_IN': '帳戶轉入',
      'TRANSFER_OUT': '帳戶轉出',
      'BUY': '買進扣款',
      'SELL': '賣出入帳'
    }
    return typeMap[type] || type
  }

  const formatNumber = (numStr) => {
    if (!numStr) return '0'
    return Number(numStr).toLocaleString()
  }

  const isWithdrawal = (type) => ['TRANSFER_OUT', 'BUY'].includes(type)
  const isDeposit = (type) => ['TRANSFER_IN', 'INITIAL_DEPOSIT', 'SELL'].includes(type)

  // ==========================================
  // --- 排序邏輯 ---
  // ==========================================

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

  const sortedRecords = computed(() => {
    if (!sortKey.value || !sortOrder.value) return saveRecords.value

    return [...saveRecords.value].sort((a, b) => {
      let valA = a[sortKey.value]
      let valB = b[sortKey.value]

      // 針對衍生欄位與需要中文比對的欄位做特殊處理
      if (sortKey.value === 'amount_withdrawal') {
        valA = isWithdrawal(a.change_type) ? Number(a.amount) : null
        valB = isWithdrawal(b.change_type) ? Number(b.amount) : null
      } else if (sortKey.value === 'amount_deposit') {
        valA = isDeposit(a.change_type) ? Number(a.amount) : null
        valB = isDeposit(b.change_type) ? Number(b.amount) : null
      } else if (sortKey.value === 'account_type') {
        valA = formatAccountType(a.account_type)
        valB = formatAccountType(b.account_type)
      } else if (sortKey.value === 'change_type') {
        valA = formatChangeType(a.change_type)
        valB = formatChangeType(b.change_type)
      }

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

  // ==========================================
  // --- API 獲取資料 ---
  // ==========================================

  const fetchSaves = async () => {
    const saveId = route.query.saveId

    if (!saveId) {
      isLoading.value = false
      return
    }

    try {
      const response = await fetch(`/api/saves/${saveId}/accounts/history`, {
        headers: {
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

</script>