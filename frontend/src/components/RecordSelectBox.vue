<template>
    <button
        type="button"
        class="z-10 cursor-pointer hover:bg-nature-600 transition duration-300 w-full h-fit max-w-[500px] bg-nature-700 border-nature-500 border-[3px]"
        :class="{ 'border-b-0': !hasBottomBorder }"
        @click="$emit('select', titleType)"
    >
        <div class="text-03 font-06 text-nature-200 text-center p-[5px] w-full">
            {{ title }}
        </div>
    </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
    titleType: {
        type: Number,
        default: 0,
    },

    hasBottomBorder: {
        type: Boolean,
        default: false,
    },
})

defineEmits(['select'])

const title = computed(() => {
    if (props.titleType === 1) {
        return '交易紀錄'
    } else if (props.titleType === 2) {
        return '轉帳紀錄'
    } else if (props.titleType === 3) {
        return '存檔記錄'
    }

    return 'NaN'
})
</script>