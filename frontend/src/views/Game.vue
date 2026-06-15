<template>
  <div class="min-h-screen flex flex-col bg-nature-900 text-white">
    <!-- 1. 置頂狀態與導覽列 -->
    <TopBar
      :activeTab="currentTab"
      @update:activeTab="handleTabChange"
      :date="formattedDate"
      :status="formattedPhase"
      :savings="savingsAmount.toLocaleString()"
      :delivery="deliveryAmount.toLocaleString()"
      :username="username"
    />

    <!-- 2. 主內容渲染區 (透過 router-view 傳遞狀態至各分頁，使用 keep-alive 快取狀態) -->
    <div class="flex-1 flex flex-col items-center p-6 w-full">
      <!-- 存檔已破產/結束的常駐警示 -->
      <div
        v-if="saveLoaded && saveStatus !== 'ACTIVE'"
        class="w-full max-w-275 mb-4 px-6 py-3 rounded-xl text-center font-bold text-03 bg-red-700 text-nature-100"
      >
        {{ saveStatus === 'BANKRUPT' ? '⚠ 此存檔已破產，無法繼續交易' : '此存檔已結束' }}
      </div>

      <div v-if="saveLoaded" class="w-full h-full flex flex-col items-center justify-center">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component
              :is="Component"
              :key="$route.path"
              :save-id="saveId"
              :savings-balance="savingsAmount"
              :delivery-balance="deliveryAmount"
              :current-phase="gamePhase"
              :current-date="gameDate"
              :save-status="saveStatus"
              @update-balances="syncBalances"
              @refresh-save="fetchSaveDetail"
            />
          </keep-alive>
        </router-view>
      </div>
      <div v-else class="text-xl font-bold animate-pulse text-nature-200">
        正在載入存檔資料...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from '../components/TopBar.vue'
import { apiFetch } from '../api/client.js'

const route = useRoute()
const router = useRouter()

// 1. 取得網址的存檔 ID
const saveId = computed(() => {
  const id = route.query.saveId
  return id ? parseInt(id) : null
})

// 2. 存檔核心數據狀態
const saveLoaded = ref(false)
const gameDate = ref('2026-06-14')
const gamePhase = ref('PRE_MARKET')
const saveStatus = ref('ACTIVE')
const savingsAmount = ref(1000)
const deliveryAmount = ref(2000)
const username = ref('')

// 3. 格式化顯示欄位
const formattedDate = computed(() => {
  return gameDate.value.replace(/-/g, '/')
})

const formattedPhase = computed(() => {
  const phaseMap = {
    'PRE_MARKET': '盤前 (08:30)',
    'INTRADAY': '盤中 (09:00 - 13:30)',
    'POST_MARKET': '盤後 (13:30 - 14:30)',
    'CLOSED': '收市 (14:30 以後)'
  }
  return phaseMap[gamePhase.value] || gamePhase.value
})

// 4. 根據當前路由路徑，向 TopBar 同步目前的 activeTab
const currentTab = computed(() => {
  const path = route.path
  if (path.includes('transact')) return '交易'
  if (path.includes('inventory')) return '資產'
  if (path.includes('record')) return '紀錄'
  return '自選'
})

// 5. 點選導覽列分頁時，執行路由跳轉（並維持 query 中的 saveId）
const handleTabChange = (tabName) => {
  let targetPath = '/game/custom'
  if (tabName === '交易') targetPath = '/game/transact'
  if (tabName === '資產') targetPath = '/game/inventory'
  if (tabName === '紀錄') targetPath = '/game/record'

  router.push({
    path: targetPath,
    query: { saveId: saveId.value }
  })
}

// 6. 用來供資產頁面轉帳完畢後，同步更新 TopBar 餘額的事件監聽
const syncBalances = (newDelivery, newSavings) => {
  deliveryAmount.value = newDelivery
  savingsAmount.value = newSavings
}

// 7. 撈取後端存檔 API 的詳細狀態
const fetchSaveDetail = async () => {
  if (!saveId.value) {
    console.error('未指定存檔 ID！')
    // 降級處理：若無存檔 ID，先顯示預設值避免阻礙前端開發
    saveLoaded.value = true
    return
  }

  try {
    const response = await fetch(`/api/saves/${saveId.value}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'x-session-id': localStorage.getItem('session_id') || ''
      }
    })

    if (response.ok) {
      const data = await response.json()
      gameDate.value = data.current_trade_date
      gamePhase.value = data.current_phase
      saveStatus.value = data.status
      savingsAmount.value = data.savings_balance
      deliveryAmount.value = data.trading_balance
      saveLoaded.value = true
    } else {
      console.error('取得存檔資料失敗，可能登入已逾期。')
      // 降級退回登入頁
      router.push('/')
    }
  } catch (error) {
    console.error('連線後端 API 異常:', error)
    // 降級以 Mock 運作，利於本機前端展示
    saveLoaded.value = true
  }
}

// 監聽 saveId 的變化（例如使用者在存檔列表選擇不同存檔）
// session 閒置偵測與過期彈窗已上移至 App.vue（全域生效，不再侷限於 /game）。
watch(saveId, () => {
  if (saveId.value) {
    saveLoaded.value = false
    fetchSaveDetail()
  }
}, { immediate: true })

// 8. 取得目前登入的使用者帳號，顯示於 TopBar 左側
onMounted(async () => {
  const response = await apiFetch('/api/auth/me')
  if (response.ok) {
    const data = await response.json()
    username.value = data.account
  }
})
</script>

<style scoped>
/* 版面容器樣式 */
</style>
