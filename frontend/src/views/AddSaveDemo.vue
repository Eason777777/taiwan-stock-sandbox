<template>
  <!-- 臨時 demo 頁面：不需登入 / 不需後端，純粹預覽 AddSave 彈窗 UI -->
  <div class="min-h-screen flex items-center justify-center bg-nature-900">
    <AddSave @close="() => {}" @refresh="() => {}" />
  </div>
</template>

<script setup>
import AddSave from '../components/AddSave.vue'
</script>
