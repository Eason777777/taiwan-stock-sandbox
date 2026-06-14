<template>
    <div class="flex flex-col gap-2">
        <label class="text-nature-200 font-06 text-03">{{ label }}</label>
        <input
            :value="modelValue"
            :type="type"
            :placeholder="placeholder"
            :class="inputClass"
            @input="emit('update:modelValue', $event.target.value)"
        />
    </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
    modelValue: {
        type: String,
        default: '',
    },
    label: {
        type: String,
        default: 'Input',
    },
    type: {
        type: String,
        default: 'text',
    },
    placeholder: {
        type: String,
        default: '',
    },
    variant: {
        type: String,
        default: 'pill',
        validator: (value) => ['pill', 'soft'].includes(value),
    },
})

const emit = defineEmits(['update:modelValue'])

const inputClass = computed(() => {
    const variantClass = props.variant === 'soft' ? 'rounded-[30px]' : 'rounded-[10px]'

    return [
        'w-fill bg-nature-900 border border-nature-200 text-nature-100 px-5 py-3 focus:outline-none focus:border-yellow-400 transition-colors',
        variantClass,
    ]
})

</script>