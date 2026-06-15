import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from './App.vue'

// 驗證全域「長時間未操作」流程：App.vue 在登入後（localStorage 有 session_id）
// 定期 ping /api/auth/me，後端回 401 session_expired 時 apiFetch 發射 'session-expired'
// 事件，App.vue 監聽並彈出 SessionExpiredModal —— 不論目前在哪個頁面。

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div>login</div>' } }],
  })
}

async function mountApp() {
  const router = makeRouter()
  router.push('/')
  await router.isReady()
  return mount(App, { global: { plugins: [router] } })
}

describe('App.vue 全域 session 過期偵測', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.setItem('session_id', 'fake-session')
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('有 session 時 ping 收到 401 session_expired 應彈出 Modal', async () => {
    const wrapper = await mountApp()

    expect(wrapper.text()).not.toContain('長時間未操作')

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: 'session_expired' }),
      clone() { return this },
    })

    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    expect(wrapper.text()).toContain('長時間未操作')
  })

  it('沒有 session（登入頁未登入）時不應 ping', async () => {
    localStorage.removeItem('session_id')
    const fetchSpy = vi.fn()
    global.fetch = fetchSpy

    await mountApp()
    await vi.advanceTimersByTimeAsync(6000)
    await flushPromises()

    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
