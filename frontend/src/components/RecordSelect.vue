<template>
    <!-- 未點選 -->
    <div class="max-w-[600px] w-full"
        v-if="!isPressed"
        @click="isPressed = true"
    >
        <button class="cursor-pointer ml-auto flex items-center gap-[10px] rounded-full bg-nature-700 border-nature-500 border-[5px] p-[20px] w-full max-w-[300px]"
            @click="isPressed = true"
        >
            <div class="text-nature-200 text-05 font-06">{{ titleName }}</div>
            <svg width="26" height="21" viewBox="0 0 26 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M11.0122 19.8668L0.574954 4.9564C-0.88647 2.86865 0.607112 -1.75429e-06 3.15553 -1.64289e-06L22.5554 -7.94897e-07C25.1038 -6.83502e-07 26.5974 2.86865 25.136 4.9564L14.6987 19.8668C13.803 21.1464 11.9079 21.1464 11.0122 19.8668Z" fill="#E9ECEF"/>
            </svg>
        </button>
    </div>

    <!-- 已點選 -->
    <div class="relative max-w-[600px] w-full"
        v-else
    >
        <button class="cursor-pointer ml-auto flex items-center gap-[10px] rounded-full bg-nature-400 border-nature-700 border-[5px] p-[20px] w-full max-w-[300px]"
            @click="isPressed = false"
        >
            <div class="text-nature-600 text-05 font-06">{{ titleName }}</div>
            <svg width="26" height="21" viewBox="0 0 26 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M11.0122 19.8668L0.574954 4.9564C-0.88647 2.86865 0.607112 -1.75429e-06 3.15553 -1.64289e-06L22.5554 -7.94897e-07C25.1038 -6.83502e-07 26.5974 2.86865 25.136 4.9564L14.6987 19.8668C13.803 21.1464 11.9079 21.1464 11.0122 19.8668Z" fill="#6C757D"/>
            </svg>
        </button>
        <div class="absolute z-10 right-0">
            <RecordSelectBox :titleType="1" @select="selectedType = $event" />
            <RecordSelectBox :titleType="2" @select="selectedType = $event" />
            <RecordSelectBox :titleType="3" :hasBottomBorder="true" @select="selectedType = $event" />
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import RecordSelectBox from './RecordSelectBox.vue'

const props = defineProps({
    titleType: {
        type: Number,
        default: 1,
    },
})
const isPressed = ref(false)
const selectedType = ref(props.titleType)

const titleName = computed(() => {
    if (selectedType.value === 1) {
        return '交易紀錄'
    } else if (selectedType.value === 2) {
        return '轉帳紀錄'
    } else if (selectedType.value === 3) {
        return '存檔記錄'
    }

    return 'NaN'
})

</script>