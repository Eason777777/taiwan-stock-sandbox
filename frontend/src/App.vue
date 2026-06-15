<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { RouterView } from 'vue-router'
import SessionExpiredModal from './components/SessionExpiredModal.vue'
import { apiFetch } from './api/client.js'

// 全域 session 閒置偵測：只要登入後（localStorage 有 session_id），
// 就定期 ping /auth/me 偵測 session 是否仍有效。後端的 /auth/me 不會滑動續期，
// 因此使用者若長時間沒有任何實際操作，TTL 到期後 ping 會收到 401 session_expired，
// apiFetch 隨即發射 'session-expired' 事件，這裡監聽並彈出 Modal。
// 放在 App.vue（最頂層、永遠掛載）而非 Game.vue，讓偵測在任何頁面都生效。

const showExpiredModal = ref(false)

const PING_INTERVAL_MS = 2000
let _pingTimer = null

const startSessionPing = () => {
  if (_pingTimer !== null) return
  _pingTimer = setInterval(async () => {
    // 沒有 session（未登入或登入頁）就不 ping，避免無謂請求與誤觸
    if (!localStorage.getItem('session_id')) return
    await apiFetch('/api/auth/me')
  }, PING_INTERVAL_MS)
}

const stopSessionPing = () => {
  if (_pingTimer !== null) {
    clearInterval(_pingTimer)
    _pingTimer = null
  }
}

const onSessionExpired = () => {
  showExpiredModal.value = true
}

const handleExpiredClose = () => {
  showExpiredModal.value = false
  // apiFetch 收到 session_expired 時已清掉 session_id。
  // 用整頁導向（而非 router.push）回登入頁：使用者可能已經在 '/' 路由
  // （例如停在登入頁彈出的存檔列表子彈窗上），此時 router.push('/') 不會有作用；
  // 整頁重載可一併清掉所有殘留的 in-memory 狀態，確保回到乾淨的登入畫面。
  window.location.assign('/')
}

onMounted(() => {
  window.addEventListener('session-expired', onSessionExpired)
  startSessionPing()
})

onUnmounted(() => {
  window.removeEventListener('session-expired', onSessionExpired)
  stopSessionPing()
})
</script>

<template>
  <RouterView />
  <!-- session 因長時間未操作而過期時，在任何頁面都能彈出提示 -->
  <SessionExpiredModal v-if="showExpiredModal" @close="handleExpiredClose" />
</template>

<style scoped></style>
