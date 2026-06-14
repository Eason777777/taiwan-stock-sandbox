<template>
  <div class="min-w-[1280px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col">
    
    <div class="flex w-full h-full">
      <div class="text-07 text-nature-100 w-full"> 轉帳紀錄 </div>
      <div class="w-full flex flex-row-reverse"> <RecordSelect :titleType="2"/> </div>
    </div>

    <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px]">
        <table class="w-full text-center text-nature-800 relative">
            
            <thead class="sticky top-0 bg-nature-200 border-b-3 text-nature-900 font-05 text-04">
            <tr>
                <th class="py-3 px-2">交易日期</th>
                <th class="py-3 px-2">交易時間</th> 
                <th class="py-3 px-2">摘要</th>
                <th class="py-3 px-2">提款</th>
                <th class="py-3 px-2">存款</th>
                <th class="py-3 px-2">結餘</th>
                <th class="py-3 px-2">註記</th>
            </tr>
            </thead>

            <tbody class="text-04">
                <tr 
                    v-for="record in saveRecords" 
                    :key="record.seq" 
                    class="border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors"
                >
                    <td class="py-3 px-2">{{ record.sim_date.slice(0, 10) }}</td>
                    
                    <td class="py-3 px-2">{{ formatAccountType(record.account_type) }}</td>
                    
                    <td class="py-3 px-2">{{ formatChangeType(record.change_type) }}</td>
                    
                    <td class="py-3 px-2 text-green-500">
                        {{ isWithdrawal(record.change_type) ? formatNumber(record.amount) : '-' }}
                    </td>
                    
                    <td class="py-3 px-2 text-red-500">
                        {{ isDeposit(record.change_type) ? formatNumber(record.amount) : '-' }}
                    </td>
                    
                    <td class="py-3 px-2">{{ formatNumber(record.balance_after) }}</td>
                    
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

  const saveRecords = ref([])
  const isLoading = ref(true)

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
      const response = await fetch(`/api/saves/${saveId}/accounts/history`, {
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

    // --- 顯示轉換邏輯 (Formatters) ---

    // 轉換帳戶類型
    const formatAccountType = (type) => {
    if (type === 'SAVINGS') return '存款戶'
    if (type === 'TRADING') return '交割戶'
    return type
    }

    // 轉換摘要
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

    // 數字千分位格式化 (把 "1000000.00" 變成 "1,000,000")
    const formatNumber = (numStr) => {
    if (!numStr) return '0'
    // 轉成數字並加上千分位，同時自動去掉不必要的 .00
    return Number(numStr).toLocaleString()
    }

    // --- 提款/存款 判斷邏輯 ---

    // 判斷提款 (轉出、買股扣款)
    const isWithdrawal = (type) => ['TRANSFER_OUT', 'BUY'].includes(type)

    // 判斷存款 (初始存入、轉入、賣股入帳)
    const isDeposit = (type) => ['TRANSFER_IN', 'INITIAL_DEPOSIT', 'SELL'].includes(type)
</script>