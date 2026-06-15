<template>
    <div class="text-nature-300 flex flex-col items-center gap-[20px] w-full h-full" data-tutorial="record-area">
        <OrderRecords v-if="selectedType === 1" />
        <TransactRecords v-else-if="selectedType === 2" />
        <SavefileRecords v-else-if="selectedType === 3" :current-save-id="saveId" />
        <RecordOrderHistory v-else-if="selectedType === 4" :current-date="currentDate" :current-phase="currentPhase" />
        <AssetChartRecord v-else-if="selectedType === 5" :save-id="saveId" :current-date="currentDate" :current-phase="currentPhase" />
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SavefileRecords from '../components/SavefileRecords.vue'
import OrderRecords from '../components/OrderRecords.vue'
import TransactRecords from '@/components/TransactRecords.vue';
import RecordOrderHistory from '../components/RecordOrderHistory.vue'
import AssetChartRecord from '../components/AssetChartRecord.vue'

const route = useRoute()

const selectedType = computed(() => {
    const type = Number(route.query.recordType)

    if ([1, 2, 3, 4, 5].includes(type)) {
        return type
    }

    return 1
})

defineProps({
  saveId: {
    type: Number,
    required: true
  },
  savingsBalance: {
    type: Number,
    required: true
  },
  deliveryBalance: {
    type: Number,
    required: true
  },
  currentPhase: {
    type: String,
    required: true
  },
  currentDate: {
    type: String,
    required: true
  }
})
</script>

<style scoped>
/* 預留紀錄樣式 */
</style>