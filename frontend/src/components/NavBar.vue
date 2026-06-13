<template>
  <div class="navbar-container">
    <button
      v-for="tab in tabs"
      :key="tab"
      @click="selectTab(tab)"
      class="nav-button"
      :class="{ 'active': modelValue === tab }"
    >
      {{ tab }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

const tabs = ['自選', '交易', '資產', '紀錄']

const selectTab = (tab) => {
  emit('update:modelValue', tab)
}
</script>

<style scoped>
.navbar-container {
  display: flex;
  width: 100%;
  max-width: 1920px;
  background: var(--Navbar-Background, #E9ECEF);
  padding: 5px;
  gap: 10px;
  font-family: var(--font-sans);
}

.nav-button {
  flex: 1;
  padding: 12px 0;
  text-align: center;
  font-size: 20px;
  font-weight: 700;
  border-radius: 4px;
  border: 2px solid transparent;
  background-color: #FFFFFF;
  color: var(--color-nature-900, #212529);
  cursor: pointer;
  transition: all 0.15s ease;
  outline: none;
}

.nav-button:hover {
  background-color: var(--color-nature-100, #F8F9FA);
}

.nav-button.active {
  background-color: var(--color-nature-600, #6C757D);
  color: #FFFFFF;
  border-color: #FFFFFF;
}
</style>
