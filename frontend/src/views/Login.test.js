import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Login from './Login.vue' // 確保路徑對應到你的 Login.vue

// 測試套件 (Test Suite)
describe('Login.vue 登入頁面測試', () => {
  
  // 每次測試前，清空所有的 Mock 紀錄，保持環境乾淨
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('當帳號密碼正確時，應該要成功呼叫 API 並顯示成功訊息', async () => {
    // -----------------------------------------
    // 1. Arrange (準備階段：設定 Mock 假資料)
    // -----------------------------------------
    
    // 攔截瀏覽器的 alert 彈窗，並記錄它有沒有被呼叫
    const alertMock = vi.spyOn(window, 'alert').mockImplementation(() => {})

    // 攔截 fetch API，不讓它真的發送網路請求，而是直接回傳我們捏造的假成功資料
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ session_id: 'fake-session-123456' })
    })

    // 把 Login 元件掛載到虛擬環境中
    const wrapper = mount(Login)

    // -----------------------------------------
    // 2. Act (操作階段：模擬使用者行為)
    // -----------------------------------------
    
    // 找到帳號與密碼的 input，並填入文字
    // 注意：這裡假設你的第一個 input 是帳號，第二個是密碼
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('test_account')
    await inputs[1].setValue('password123')

    // 找到 form 表單並觸發 submit 送出事件
    await wrapper.find('form').trigger('submit.prevent')

    // -----------------------------------------
    // 3. Assert (驗證階段：檢查程式有沒有做對事情)
    // -----------------------------------------
    
    // 驗證 1：確認 fetch 真的有被呼叫
    expect(fetch).toHaveBeenCalledTimes(1)
    
    // 驗證 2：確認 fetch 送出去的網址和資料格式正不正確 (這非常重要，確保前端沒送錯欄位)
    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        account: 'test_account', // 驗證是否有轉成後端要的 account 欄位
        password: 'password123'
      })
    })

    // 驗證 3：確認登入成功的 alert 有沒有跳出來
    expect(alertMock).toHaveBeenCalledWith('登入成功！')
  })

  it('當後端回傳錯誤時，應該要顯示錯誤訊息', async () => {
    // -----------------------------------------
    // 1. Arrange (準備階段：設定 Mock 假資料)
    // -----------------------------------------
    
    // 攔截瀏覽器的 alert 彈窗，並記錄它有沒有被呼叫
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: '帳號或密碼錯誤' })
    })

    const wrapper = mount(Login)

    // -----------------------------------------
    // 2. Act (操作階段：模擬使用者行為)
    // -----------------------------------------
    
    // 填入錯誤的帳號密碼
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('wrong_account')
    await inputs[1].setValue('wrong_password')

    // 觸發表單送出
    await wrapper.find('form').trigger('submit.prevent')

    // 關鍵：等待所有的 Promise (包含 fetch 與 Vue 的重新渲染) 執行完畢
    await flushPromises()

    // -----------------------------------------
    // 3. Assert (驗證階段：檢查程式有沒有做對事情)
    // -----------------------------------------
    
    // 驗證 1：確認 fetch 真的有被呼叫
    expect(fetch).toHaveBeenCalledTimes(1)

    // 驗證畫面上是否出現了預期的紅色錯誤訊息
    // wrapper.text() 會抓取整個元件渲染出來的所有純文字
    expect(wrapper.text()).toContain('帳號或密碼錯誤')
  })
})