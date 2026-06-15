import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import ConfirmModal from './ConfirmModal.vue'

// 共用的掛載函式：把 Teleport 攤平在原地渲染，方便用 wrapper 直接查到內容
const mountModal = (props = {}) =>
  mount(ConfirmModal, {
    props: {
      show: true,
      message: '確定要刪除這個存檔嗎？',
      ...props,
    },
    global: {
      // teleport: true → 不要真的傳送到 document.body，留在 wrapper 內好驗證
      stubs: { teleport: true },
    },
  })

describe('ConfirmModal.vue 確認彈窗 UI 測試', () => {
  it('show 為 false 時，畫面上不應該渲染任何彈窗內容', () => {
    const wrapper = mountModal({ show: false })

    // v-if="show" 關閉時，整個遮罩與卡片都不該存在
    expect(wrapper.find('.fixed').exists()).toBe(false)
    expect(wrapper.text()).toBe('')
  })

  it('show 為 true 時，應該顯示標題、訊息與兩顆按鈕文字', () => {
    const wrapper = mountModal({
      show: true,
      title: '刪除存檔',
      message: '刪除後無法恢復喔！',
      confirmText: '刪除',
      cancelText: '返回',
    })

    expect(wrapper.find('.fixed').exists()).toBe(true)
    expect(wrapper.text()).toContain('刪除存檔')
    expect(wrapper.text()).toContain('刪除後無法恢復喔！')

    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(2)
    // 第一顆是取消、第二顆是確認
    expect(buttons[0].text()).toBe('返回')
    expect(buttons[1].text()).toBe('刪除')
  })

  it('沒有給標題與按鈕文字時，應該使用預設值', () => {
    const wrapper = mountModal({ show: true, message: '提示內容' })

    expect(wrapper.text()).toContain('確認') // title 預設
    const buttons = wrapper.findAll('button')
    expect(buttons[0].text()).toBe('取消') // cancelText 預設
    expect(buttons[1].text()).toBe('確定') // confirmText 預設
  })

  it('type 為 danger 時，確認按鈕應該套用紅色危險樣式', () => {
    const wrapper = mountModal({ show: true, type: 'danger' })

    const confirmBtn = wrapper.findAll('button')[1]
    expect(confirmBtn.classes()).toContain('bg-red-600')
  })

  it('type 為 warning 時，確認按鈕應該套用黃色警告樣式', () => {
    const wrapper = mountModal({ show: true, type: 'warning' })

    const confirmBtn = wrapper.findAll('button')[1]
    expect(confirmBtn.classes()).toContain('bg-yellow-500')
  })

  it('type 為預設 info 時，確認按鈕應該套用一般 nature 樣式', () => {
    const wrapper = mountModal({ show: true })

    const confirmBtn = wrapper.findAll('button')[1]
    expect(confirmBtn.classes()).toContain('bg-nature-500')
  })

  it('danger / warning 類型應該顯示警示圖示（黃色 pulse）', () => {
    const wrapper = mountModal({ show: true, type: 'danger' })

    // 警示圖示帶有 text-yellow-500 與 animate-pulse class
    expect(wrapper.find('svg.text-yellow-500').exists()).toBe(true)
    expect(wrapper.find('svg.animate-pulse').exists()).toBe(true)
  })

  it('info 類型應該顯示一般資訊圖示（非黃色 pulse）', () => {
    const wrapper = mountModal({ show: true, type: 'info' })

    expect(wrapper.find('svg.text-yellow-500').exists()).toBe(false)
    expect(wrapper.find('svg.text-nature-300').exists()).toBe(true)
  })

  it('點擊確認按鈕，應該送出 confirm 與 update:show=false 事件', async () => {
    const wrapper = mountModal({ show: true })

    await wrapper.findAll('button')[1].trigger('click')

    expect(wrapper.emitted('confirm')).toHaveLength(1)
    expect(wrapper.emitted('update:show')[0]).toEqual([false])
  })

  it('點擊取消按鈕，應該送出 cancel 與 update:show=false 事件', async () => {
    const wrapper = mountModal({ show: true })

    await wrapper.findAll('button')[0].trigger('click')

    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(wrapper.emitted('update:show')[0]).toEqual([false])
  })

  it('點擊遮罩本身（卡片外），應該視為取消', async () => {
    const wrapper = mountModal({ show: true })

    // @click.self 綁在最外層遮罩，trigger 在它本身即視為點到背景
    await wrapper.find('.fixed').trigger('click')

    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(wrapper.emitted('update:show')[0]).toEqual([false])
  })
})