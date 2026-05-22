<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

async function goHomePage() {
  router.push({ name: 'home' }) 
}
</script>

<template>
  <nav></nav>

  <main>
    <div>
      <h1>Test</h1>
      <button @click="goHomePage" :disabled="isLoading">
        go to home page
      </button>
    </div>
  </main>
</template>