<template>
    <div class="flex w-full h-full">
      <div class="text-06 text-nature-100 "> 存檔紀錄 </div>
    </div>

    <div class="flex w-full h-fit gap-[5px]">
      <!-- 移除存檔按鈕 -->
      <button @click="$emit('close')" class="group w-full h-[64px] bg-red-900 flex justify-center items-center transition-colors cursor-pointer rounded-[10px] hover:bg-red-700 transition-colors duration-300 ease-in-out">
        <div class="absolute opacity-100 group-hover:opacity-0 transition-opacity duration-300 ease-in-out">
          <div class="text-red-700 text-05 font-sans font-06"> 移除存檔 </div>
        </div>
        <div class="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-in-out">
          <div class="text-red-300 text-05 font-sans font-06"> 返回 </div>
        </div>
      </button>
    </div>
    <!-- 存檔們 -->
    <div class="bg-nature-200 rounded-[10px] overflow-y-auto max-h-[400px]">
      <table class="w-full text-center relative">
        
        <thead class="sticky top-0 z-10 bg-nature-200 border-b-3 text-nature-900 font-05 text-04">
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
            class="border-b-[3px] border-nature-800 bg-red-200 text-red-900 hover:bg-red-700 hover:text-red-400 transition-colors cursor-pointer"
            @click="removeSave(record.save_id)"
          >
            <td class="py-3 px-2">{{ record.save_name }}</td>
            <td class="py-3 px-2">{{ record.start_date }}</td>
            <td class="py-3 px-2">{{ record.current_trade_date || '無' }}</td>
            <td class="py-3 px-2">{{ formatCurrency(record.total_asset) }}</td>
            <td class="py-3 px-2">{{ formatPercent(record.cumulative_return) }}</td>
            <td class="py-3 px-2">{{ record.status === 'ACTIVE' ? '遊玩中' : '已結束' }}</td>
            <td class="py-3 px-2">{{ record.note || '-' }}</td>
          </tr>
          
          <tr class="h-[50px] bg-nature-200">
            <td colspan="7"></td>
          </tr>
        </tbody>
      </table>
    </div>
</template>

<script setup>  
import { apiFetch } from '../api/client.js'

// 🚀 1. 宣告接收從父元件傳來的 saveRecords
const props = defineProps({
  saveRecords: {
    type: Array,
    required: true,
    default: () => []
  },
  // 玩家目前在遊戲中所在的存檔 ID（不在遊戲內時為 null）
  currentSaveId: {
    type: Number,
    default: null
  }
})

// 🚀 2. 多宣告一個 'refresh' 事件，等等刪除成功後可以用來通知父元件更新畫面
const emit = defineEmits(['close', 'refresh'])

const formatCurrency = (value) => {
  if (value === undefined || value === null) return '0'
  return Number(value).toLocaleString()
}

const formatPercent = (value) => {
  if (value === undefined || value === null) return '0%'
  return (Number(value) * 100).toFixed(2) + '%'
}

// 🗑️ 3. 刪除 fetchSaves 函式與 onMounted，因為資料現在是由父元件給的！

const removeSave = async (recordId) => {
  // 1. 防呆確認 (特別提醒玩家相關資料都會消失，呼應你後端清空多張表的設計)
  const isConfirm = confirm('確定要刪除這個存檔嗎？\n刪除後，所有的交易紀錄與資產都將無法恢復喔！')
  if (!isConfirm) return

  try {
    // 2. 發送 DELETE 請求（x-session-id 與 401 過期處理統一交給 apiFetch）
    const response = await apiFetch(`/api/saves/${recordId}`, {
      method: 'DELETE',
    })

    // 3. 處理回應 (小心 204 陷阱)
    if (response.ok) {
      // 🚀 注意：因為後端是 204 No Content，這裡不需要也「不能」寫 response.json()
      if (recordId === props.currentSaveId) {
        // 刪除的是玩家目前正在遊玩的存檔，狀態已不存在，強制登出回登入頁
        alert('你已刪除目前所在的存檔，將強制登出。')
        localStorage.removeItem('session_id')
        window.location.assign('/')
        return
      }

      alert('存檔已徹底刪除！')

      // 告訴父元件 (SaveRecords.vue) 去重新要一次最新的列表
      emit('refresh')
    } else {
      // 只有失敗時 (例如 403, 404)，後端才會傳回含有 detail 的 JSON 錯誤訊息
      const errorData = await response.json()
      alert(`刪除失敗：${errorData.detail || '未知錯誤'}`)
    }
  } catch (error) {
    console.error('刪除 API 連線失敗:', error)
    alert('伺服器連線異常，請稍後再試。')
  }
}
</script>