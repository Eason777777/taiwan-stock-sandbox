<template>
  <div class="w-full max-w-[1000px] bg-nature-800 border-[10px] border-nature-500 rounded-[10px] py-5 px-[50px]! flex flex-col gap-4 text-nature-100 font-sans">
    <!-- 帳戶餘額資訊區 (交割戶/存款戶與轉帳控制) -->
    <AccountInfo 
      :delivery-balance="deliveryBalance"
      :savings-balance="savingsBalance"
      @update-balances="handleUpdateBalances"
    />
    
    <!-- 下方水平分隔線 -->
    <hr class="w-full border-t-[3px] border-nature-500 my-0" />
    
    <!-- 持股明細資訊區 -->
    <HoldingInfo 
      :holdings="holdings"
      @select-stock="handleSelectStock"
    />
  </div>
</template>

<script setup>
import AccountInfo from './AccountInfo.vue'
import HoldingInfo from './HoldingInfo.vue'

const props = defineProps({
  deliveryBalance: {
    type: Number,
    required: true
  },
  savingsBalance: {
    type: Number,
    required: true
  },
  holdings: {
    type: Array,
    required: true,
    default: () => []
  }
})

const emit = defineEmits(['update-balances', 'select-stock'])

const handleUpdateBalances = (newDelivery, newSavings) => {
  emit('update-balances', newDelivery, newSavings)
}

const handleSelectStock = (stockId) => {
  emit('select-stock', stockId)
}
</script>

<style scoped>
/* 容器層面樣式，內部子元件樣式皆在各自的元件中進行 Scope 限制 */
</style>
