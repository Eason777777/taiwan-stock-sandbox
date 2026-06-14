<template>
  <div class="min-w-[1080px] gap-[10px] p-[30px] bg-nature-800 border-nature-500 border-[10px] w-[90%] h-fit flex flex-col">
    
    <div class="flex w-full h-full">
      <div class="text-07 text-nature-100 w-full"> 交易紀錄 </div>
      <div class="w-full flex flex-row-reverse"> <RecordSelect /> </div>
    </div>

    <div class="flex flex-col w-full h-full">
        <div class="text-04 text-nature-100 "> 已出帳投資總額 <span class="text-nature-200">{{ spendingAmount }}</span> </div>
        <div class="text-04 text-nature-100"> 
            原幣已實現損益 
            <span :class="profitLoss > 0 ? 'text-red-500' : (profitLoss < 0 ? 'text-green-500' : 'text-yellow-200')">
                {{ profitLoss }}
            </span> 
            </div>

        <div class="text-04 text-nature-100"> 
            投資報酬率 
            <span :class="returnRate > 0 ? 'text-red-500' : (returnRate < 0 ? 'text-green-500' : 'text-yellow-200')">
                {{ returnRate }}%
            </span> 
        </div>
    </div>

    <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px]">
      <table class="w-full text-center relative">
        
        <thead class="sticky top-0 bg-nature-200 border-b-3 text-nature-900 font-05 text-04">
          <tr>
            <th class="py-3 px-2">名稱</th>
            <th class="py-3 px-2">損益</th>
            <th class="py-3 px-2">報酬率</th>
            <th class="py-3 px-2">交易類別</th>
            <th class="py-3 px-2">成交股數</th>
            <th class="py-3 px-2">成交價格</th>
            <th class="py-3 px-2">出帳金額</th>
            <th class="py-3 px-2">投資成本</th>
          </tr>
        </thead>

        <tbody class="text-03">
          <tr 
            v-for="record in saveRecords" 
            :key="record.transaction_id" 
            class="border-b-[3px] border-nature-800 hover:bg-nature-600 hover:text-nature-200 transition-colors"
          >
            <td class="py-3 px-2">{{ record.stock_name_zh }} ({{ record.stock_id }})</td>
            
            <td class="py-3 px-2">
              {{ record.side === 'SELL' && record.avg_cost_at_transact 
                 ? Math.round((record.exec_price - record.avg_cost_at_transact) * record.quantity - record.fee - record.tax) 
                 : '-' 
              }}
            </td>
            
            <td class="py-3 px-2">
              {{ record.side === 'SELL' && record.avg_cost_at_transact 
                 ? (((record.exec_price - record.avg_cost_at_transact) / record.avg_cost_at_transact) * 100).toFixed(2) + '%' 
                 : '-' 
              }}
            </td>
            
            <td class="py-3 px-2">
              <span :class="record.side === 'BUY' ? 'text-red-500' : 'text-green-500'">
                {{ record.side === 'BUY' ? '買進' : '賣出' }}
              </span>
            </td>
            
            <td class="py-3 px-2">{{ record.quantity }}</td>
            
            <td class="py-3 px-2">{{ record.exec_price }}</td>
            
            <td class="py-3 px-2">
              {{ record.side === 'BUY' 
                 ? Math.round((record.exec_price * record.quantity) + record.fee) 
                 : Math.round((record.exec_price * record.quantity) - record.fee - record.tax) 
              }}
            </td>
            
            <td class="py-3 px-2">
              {{ record.avg_cost_at_transact !== null ? record.avg_cost_at_transact.toFixed(2) : '-' }}
            </td>
          </tr>
          
          <tr class="h-[50px] bg-nature-200">
            <td colspan="8"></td>
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
  
  const spendingAmount = ref(0)
  const profitLoss = ref(0)
  const returnRate = ref(0)

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