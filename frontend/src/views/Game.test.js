import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import Game from './Game.vue'

// 驗證「長時間未操作」流程：Game.vue 定期 ping /api/auth/me，
// 後端回 401 session_expired 時 apiFetch 發射 'session-expired' 事件，
// Game.vue 監聽並彈出 SessionExpiredModal。

async function mountGame() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' } },
      {
        path: '/game',
        component: Game,
        children: [{ path: 'custom', component: { template: '<div/>' } }],
      },
    ],
  })
  // router 的導航內部用到 timers，先用 real timers 把它 ready 完成
  vi.useRealTimers()
  router.push('/game/custom?saveId=1')
  await router.isReady()
  vi.useFakeTimers()

  return mount(Game, {
    global: {
      plugins: [router],
      stubs: { TopBar: true },
    },
  })
}

describe('Game.vue session 過期偵測', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    localStorage.setItem('session_id', 'fake-session')
    // saveId watch immediate 會打 /api/saves/1，先給它一個成功回應
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        current_trade_date: '2026-06-14',
        current_phase: 'PRE_MARKET',
        savings_balance: 1000,
        trading_balance: 2000,
      }),
      clone() { return this },
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('ping 收到 401 session_expired 時應彈出 Modal', async () => {
    const wrapper = await mountGame()
    await flushPromises()

    // Modal 一開始不應存在
    expect(wrapper.text()).not.toContain('長時間未操作')

    // 切換 fetch：下一次 ping (/api/auth/me) 回 401 session_expired
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: 'session_expired' }),
      clone() { return this },
    })

    // 推進 2 秒，觸發一次 ping
    await vi.advanceTimersByTimeAsync(2000)
    await flushPromises()

    expect(wrapper.text()).toContain('長時間未操作')
  })
})
