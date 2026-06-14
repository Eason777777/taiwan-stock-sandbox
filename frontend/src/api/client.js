// 集中式 API 包裝：統一帶上 x-session-id，並攔截 401。
// 目的：讓「session 過期」與其他需重新登入的情況有單一處理點，
// 避免每個元件各自手刻 header 與錯誤處理。

// 收到 401 時的共用處理：清除本機 session，視原因設定旗標。
// detail === 'session_expired' 代表閒置過久（由後端 get_current_user 回報），
// 此時發射 'session-expired' 自訂事件讓遊戲頁面在當頁顯示 Modal；
// 若是一般未授權則直接導回登入頁。
function handleUnauthorized(detail) {
  localStorage.removeItem('session_id')
  if (detail === 'session_expired') {
    window.dispatchEvent(new CustomEvent('session-expired'))
  } else if (window.location.pathname !== '/') {
    window.location.assign('/')
  }
}

// 包裝 fetch：自動補上 session header 與 JSON Content-Type（呼叫端傳入的 headers 優先）。
export async function apiFetch(url, options = {}) {
  const sessionId = localStorage.getItem('session_id')
  const headers = {
    'Content-Type': 'application/json',
    ...(sessionId ? { 'x-session-id': sessionId } : {}),
    ...options.headers,
  }

  const response = await fetch(url, { ...options, headers })

  if (response.status === 401) {
    // 讀取 detail 判斷是否為過期（讀取失敗則視為一般未授權）
    let detail
    try {
      detail = (await response.clone().json()).detail
    } catch {
      detail = undefined
    }
    handleUnauthorized(detail)
  }

  return response
}
