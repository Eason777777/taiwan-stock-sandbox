<template>
  <!-- 新手教學主畫面：遮罩 + 聚光燈高亮 + 說明框 -->
  <div v-if="tutorialActive && currentStepData" class="fixed inset-0 z-[400]" @click.prevent @contextmenu.prevent>
    <!-- 無高亮目標時（總結步驟）：純黑色遮罩 -->
    <div v-if="!highlightRect" class="absolute inset-0 bg-black/60"></div>

    <!-- 高亮聚光燈框：用超大 box-shadow 把畫面其他區域變暗 -->
    <div
      v-else
      class="fixed rounded-lg pointer-events-none tutorial-highlight"
      :style="highlightBoxStyle"
    ></div>

    <!-- 說明框 -->
    <Transition name="tutorial-fade" mode="out-in">
      <div :key="currentStep" class="fixed bg-nature-800 text-white rounded-2xl shadow-2xl p-6 border-2 border-yellow-500 flex flex-col gap-3 overflow-y-auto" :style="tooltipStyle">
        <div class="text-nature-300 text-sm font-bold">{{ currentStep + 1 }} / {{ steps.length }}</div>
        <h3 class="text-xl font-bold text-yellow-500">{{ currentStepData.title }}</h3>
        <p class="text-nature-100 text-sm whitespace-pre-line leading-relaxed">{{ currentStepData.desc }}</p>
        <div class="flex justify-between items-center gap-2 mt-2">
          <button @click="skipTutorial" class="text-nature-300 hover:text-white text-sm cursor-pointer transition-colors">
            跳過教學
          </button>
          <div class="flex gap-2">
            <button
              v-if="currentStep > 0"
              @click="prevStep"
              class="px-4 py-2 rounded-full bg-nature-600 hover:bg-nature-500 text-white text-sm font-bold cursor-pointer transition-colors"
            >
              上一步
            </button>
            <button
              @click="nextStep"
              class="px-4 py-2 rounded-full bg-yellow-500 hover:bg-yellow-700 text-nature-900 text-sm font-bold cursor-pointer transition-colors"
            >
              {{ isLastStep ? '完成' : '下一步' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>

  <!-- 新帳號首次登入：詢問是否進行新手教學 -->
  <div v-if="showWelcomePrompt" class="fixed inset-0 z-[400] flex justify-center items-center bg-black/60 backdrop-blur-sm">
    <div class="w-full max-w-sm mx-6 bg-nature-800 rounded-2xl px-8 py-7 shadow-xl flex flex-col items-center gap-4">
      <h2 class="text-2xl font-bold text-white">歡迎來到股票交易模擬！</h2>
      <p class="text-nature-300 text-center">要不要進行新手教學，帶你熟悉一下操作介面？</p>
      <div class="w-full flex gap-3 mt-2">
        <button
          @click="declineTutorial"
          class="flex-1 bg-nature-600 hover:bg-nature-500 text-white font-bold text-lg py-3 rounded-full transition-colors cursor-pointer"
        >
          不用了
        </button>
        <button
          @click="startTutorial"
          class="flex-1 bg-yellow-500 hover:bg-yellow-700 text-nature-900 font-bold text-lg py-3 rounded-full transition-colors cursor-pointer"
        >
          開始教學
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { apiFetch } from '../api/client.js'

// 全域共享的新手教學狀態
export const tutorialActive = ref(false)
export const showWelcomePrompt = ref(false)

// 通知後端：這個使用者已經看過新手教學提示，之後登入不再詢問
export function markTutorialSeen() {
  apiFetch('/api/auth/mark-tutorial-seen', { method: 'POST' }).catch(() => {})
}

// 新帳號第一次進入遊戲時呼叫：彈出「要不要新手教學」詢問
export function offerTutorial() {
  showWelcomePrompt.value = true
}

export function declineTutorial() {
  showWelcomePrompt.value = false
  markTutorialSeen()
}

export function startTutorial() {
  showWelcomePrompt.value = false
  tutorialActive.value = true
  markTutorialSeen()
}

// 各分頁名稱對應的路由路徑，與 Game.vue 的 handleTabChange 一致
const TAB_PATHS = {
  自選: '/game/custom',
  交易: '/game/transact',
  資產: '/game/inventory',
  紀錄: '/game/record',
}

// 教學步驟：依序高亮畫面元素並用白話文說明操作方式與數值計算邏輯
const steps = [
  {
    target: '[data-tutorial="topbar-user"]',
    title: '歡迎來到股票交易模擬！',
    desc: '這裡顯示你目前登入的帳號，右邊的 LOGOUT 按鈕可以隨時登出，回到登入畫面。',
  },
  {
    target: '[data-tutorial="topbar-status"]',
    title: '日期與市場階段',
    desc: '這裡顯示目前的交易日期，以及市場現在所處的階段：盤前、盤中、盤後、收市。\n委託單只有在符合條件的階段才會撮合成交，下單前記得留意現在是哪個階段！',
  },
  {
    target: '[data-tutorial="topbar-balance"]',
    title: '帳戶餘額',
    desc: '存款戶：目前還沒投入交易的資金。\n交割戶：真正用來買股票扣款、賣股票收款的帳戶。\n想下單買股票，記得先把錢從存款戶轉到交割戶！',
  },
  {
    tab: '自選',
    target: '[data-tutorial="watchlist-add"]',
    title: '新增自選股',
    desc: '點這顆按鈕可以搜尋股票，加入你的自選清單，方便追蹤行情與後續下單。',
  },
  {
    tab: '自選',
    target: '[data-tutorial="watchlist-next"]',
    title: '進入下一階段',
    desc: '點這顆按鈕會把市場推進到下一個階段（例如：盤前 → 盤中 → 盤後 → 收市 → 下一交易日）。\n所有等待中的委託單，會在符合條件的階段自動撮合成交，成交結果會用彈出視窗列出每一筆明細，並用提示訊息告訴你「已推進至下一階段」或「你已經破產了」。',
  },
  {
    tab: '交易',
    target: '[data-tutorial="order-form"]',
    title: '認識「張」：股票的交易單位',
    desc: '台股不是一股一股買賣，而是以「張」為單位：1 張 ＝ 1000 股。\n例如某支股票股價是 50 元，買 1 張大約需要 50 × 1000 ＝ 50,000 元（還沒算手續費）。\n下方「委託張數」欄位填的數字，就是你要買／賣幾張。',
  },
  {
    tab: '交易',
    target: '[data-tutorial="order-form"]',
    title: '限價單 vs 市價單',
    desc: '限價單：自己指定一個價格，只有當市場成交價達到你指定的價格（或更好）時才會成交。\n市價單：不指定價格，以目前市場上最好的價格直接成交，速度快但成交價格較不確定。\n\n委託價格還有兩個限制：\n1. 每天都有「漲停」「跌停」價，超出範圍無法下單。\n2. 價格要符合「升降單位」（例如 50 元以下最小跳動是 0.05 元），不能隨意填小數。\n\n另外，不同階段能下的單也不同：\n盤前只能下「限價單」，盤後只能下「市價單」，收市階段則完全無法下單。',
  },
  {
    tab: '交易',
    target: '[data-tutorial="order-form"]',
    title: '下單金額怎麼算？',
    desc: '買進時，會被扣多少錢：\n金額 ＝ 股價 × 1000 × 張數\n手續費 ＝ 金額 × 0.1425%（不滿 20 元算 20 元）\n實際扣款 ＝ 金額 ＋ 手續費\n\n賣出時，會拿回多少錢：\n手續費算法相同，另外還要扣「證交稅」＝ 金額 × 0.3%（只有賣出才收）\n實際入帳 ＝ 金額 － 手續費 － 證交稅\n\n舉例：以 50 元買 1 張（1000 股）\n金額 ＝ 50 × 1000 ＝ 50,000 元\n手續費 ＝ 50,000 × 0.1425% ≈ 71 元\n總共會扣款 50,071 元',
  },
  {
    tab: '資產',
    target: '[data-tutorial="inventory-accounts"]',
    title: '帳戶轉帳',
    desc: '左邊是交割戶、右邊是存款戶，點中間的箭頭可以打開轉帳視窗，讓兩個帳戶互相撥款。\n記得：下單買股票要用交割戶的錢，賣股票的錢也會先進交割戶！',
  },
  {
    tab: '資產',
    target: '[data-tutorial="inventory-holdings"]',
    title: '持股明細',
    desc: '這裡列出你目前持有的所有股票、庫存張數，以及目前的損益與獲利率，點一筆可以看更詳細的報價與走勢圖。\n\n當你賣出股票後，已實現損益的算法是：\n已實現損益 ＝ 賣出實拿金額 － (持有均價 × 1000 × 張數)\n獲利率 ＝ 已實現損益 ÷ 投入成本 × 100%',
  },
  {
    tab: '紀錄',
    target: '[data-tutorial="record-area"]',
    title: '查看紀錄',
    desc: '這裡可以切換查看「交易紀錄」「轉帳紀錄」「存檔記錄」，回顧你做過的每一筆買賣與轉帳。',
  },
  {
    target: null,
    title: '小提醒：總資產與報酬率怎麼算？',
    desc: '總資產 ＝ 存款戶 ＋ 交割戶 ＋ 目前持股市值\n報酬率 ＝ (目前總資產 － 一開始的本金) ÷ 一開始的本金\n這兩個數字會顯示在登入後的存檔列表中，讓你知道自己賺了還是賠了。\n\n教學結束，祝你投資順利！',
  },
]
</script>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const currentStep = ref(0)
const highlightRect = ref(null)

const currentStepData = computed(() => steps[currentStep.value])
const isLastStep = computed(() => currentStep.value === steps.length - 1)

// 依目前高亮目標的位置，計算聚光燈框的樣式（用超大 box-shadow 把其他區域變暗）
const highlightBoxStyle = computed(() => {
  if (!highlightRect.value) return {}
  const pad = 8
  const r = highlightRect.value
  return {
    top: `${r.top - pad}px`,
    left: `${r.left - pad}px`,
    width: `${r.width + pad * 2}px`,
    height: `${r.height + pad * 2}px`,
  }
})

// 計算說明框位置：盡量貼在高亮目標下方，超出畫面則改貼上方／置中
// 寬度與高度都依視窗大小限制，內容過長時交給 overflow-y-auto 內部捲動，避免說明框跑出畫面外
const tooltipStyle = computed(() => {
  const margin = 16
  const width = Math.min(340, window.innerWidth - margin * 2)

  if (!highlightRect.value) {
    return {
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      width: `${width}px`,
      maxHeight: `${window.innerHeight - margin * 2}px`,
    }
  }

  const r = highlightRect.value
  const estHeight = 240

  let top = r.bottom + margin
  if (top + estHeight > window.innerHeight) {
    top = r.top - estHeight - margin
    if (top < margin) top = margin
  }
  // 即使估計高度不足，也確保說明框底部不超出視窗
  if (top + estHeight > window.innerHeight - margin) {
    top = Math.max(margin, window.innerHeight - margin - estHeight)
  }

  let left = r.left
  if (left + width > window.innerWidth - margin) {
    left = window.innerWidth - width - margin
  }
  if (left < margin) left = margin

  return {
    top: `${top}px`,
    left: `${left}px`,
    width: `${width}px`,
    maxHeight: `${window.innerHeight - top - margin}px`,
  }
})

// 嘗試定位目標元素，若切換分頁後內容尚未渲染完成則重試幾次
const updateHighlight = async () => {
  await nextTick()
  const step = steps[currentStep.value]
  if (!step.target) {
    highlightRect.value = null
    return
  }
  for (let i = 0; i < 15; i++) {
    const el = document.querySelector(step.target)
    if (el) {
      highlightRect.value = el.getBoundingClientRect()
      return
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  highlightRect.value = null
}

const goToStep = async (index) => {
  currentStep.value = index
  const step = steps[index]
  if (step.tab) {
    const targetPath = TAB_PATHS[step.tab]
    if (route.path !== targetPath) {
      await router.push({ path: targetPath, query: { saveId: route.query.saveId } })
    }
  }
  await updateHighlight()
}

const nextStep = () => {
  if (isLastStep.value) {
    tutorialActive.value = false
    return
  }
  goToStep(currentStep.value + 1)
}

const prevStep = () => {
  if (currentStep.value > 0) {
    goToStep(currentStep.value - 1)
  }
}

const skipTutorial = () => {
  tutorialActive.value = false
}

// 教學進行中鎖定頁面捲動，避免使用者滑走聚光燈鎖定的元素
watch(tutorialActive, (active) => {
  document.body.style.overflow = active ? 'hidden' : ''
  if (active) {
    currentStep.value = 0
    goToStep(0)
  }
})

let resizeHandler
onMounted(() => {
  resizeHandler = () => {
    if (tutorialActive.value) updateHighlight()
  }
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.tutorial-highlight {
  transition: top 0.3s ease, left 0.3s ease, width 0.3s ease, height 0.3s ease;
  animation: tutorial-pulse 1.6s ease-in-out infinite;
}

.tutorial-fade-enter-active,
.tutorial-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.tutorial-fade-enter-from,
.tutorial-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>

<style>
@keyframes tutorial-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.55), 0 0 0 4px rgba(255, 193, 7, 0.9);
  }
  50% {
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.55), 0 0 0 10px rgba(255, 193, 7, 0);
  }
}
</style>
