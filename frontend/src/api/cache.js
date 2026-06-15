import { ref } from 'vue'

// 全域共享的記憶體快取，保存看過的股票基本資料（靜態資訊如全名、地址、官網等）
export const companyProfileCache = ref({})
