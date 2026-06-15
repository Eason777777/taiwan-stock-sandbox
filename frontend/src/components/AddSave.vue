<template>
    <div class="z-101 min-w-[500px] w-[500px] h-fit bg-nature-800 border-nature-500 border-[10px] rounded-lg p-[20px]">
        <div class="gap-5 flex w-full h-full flex-col font-sans">
            <div class="text-06 text-nature-200 font-05"> 新增存檔 </div>
            <Input v-model="saveName" label="存檔名稱" placeholder="請輸入存檔名稱" />
            <Input v-model="startDate" label="存檔日期" placeholder="YYYY-MM-DD (選填)" />
            <Input v-model="initialFunds" type="number" label="初始金額" placeholder="50000 ~ 1000000 (選填)" />
            
            <div class="flex w-full h-fit gap-5">
                <button @click="$emit('close')" class="cursor-pointer w-full text-nature-800 bg-nature-200 text-04 font-07 rounded-[10px]">
                    取消
                </button>
                <button @click="submitSave" :disabled="isSubmitting" class="cursor-pointer w-full text-yellow-900 bg-yellow-500 text-04 font-07 rounded-[10px] disabled:opacity-50 disabled:cursor-not-allowed">
                    {{ isSubmitting ? '建立中...' : '確認' }}
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import Input from './Input.vue'
import { apiFetch } from '../api/client.js'

const emit = defineEmits(['close', 'refresh'])

const saveName = ref('')
const startDate = ref('')
const initialFunds = ref('')
const isSubmitting = ref(false) // 防止重複點擊

// 執行新增存檔的函式
const submitSave = async () => {
    // 簡單的前端防呆：存檔名稱必填
    if (!saveName.value.trim()) {
        alert('請輸入存檔名稱！')
        return
    }

    isSubmitting.value = true

    // 準備要送給後端的資料 payload (確保欄位名稱跟後端 CreateSaveRequest 屬性一模一樣)
    const payload = {
        save_name: saveName.value,
        // 如果使用者沒填，就傳 null 給後端，讓後端用你寫好的隨機邏輯處理
        start_date: startDate.value ? startDate.value : null,
        initial_funds: initialFunds.value ? parseInt(initialFunds.value) : null
    }

    try {
        // x-session-id 與 401 過期處理統一交給 apiFetch
        const response = await apiFetch('/api/saves', {
            method: 'POST',
            body: JSON.stringify(payload)
        })

        if (response.ok) {
        alert('存檔建立成功！')
        emit('refresh')
        emit('close')
    } else {
        // 💡 解析後端傳來的錯誤
        const errorData = await response.json()
        
        // 判斷是不是 FastAPI 的 Pydantic 陣列錯誤 (422 錯誤)
        if (Array.isArray(errorData.detail)) {
            // 把陣列裡面的錯誤訊息一個個抓出來，用換行符號組合
            const errorMessages = errorData.detail.map(err => {
                // err.loc 通常會告訴你是哪個欄位出錯，例如 ['body', 'initial_funds']
                const field = err.loc[err.loc.length - 1]; 
                return `- 欄位 [${field}]: ${err.msg}`;
            }).join('\n');
            
            alert(`資料格式錯誤：\n${errorMessages}`);
            console.error("詳細驗證錯誤:", errorData.detail); // 偷偷印在 F12 方便工程師除錯
            
        } else {
            // 普通字串錯誤 (例如你寫的「已存在同名存檔」)
            alert(`建立失敗：${errorData.detail}`)
        }
}
    } catch (error) {
        console.error('API 連線失敗:', error)
        alert('伺服器連線異常，請稍後再試。')
    } finally {
        isSubmitting.value = false
    }
}

</script>