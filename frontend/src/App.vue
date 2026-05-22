<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header>
    <nav class="navbar">
      <RouterLink :to="{ name: 'home' }">home</RouterLink> | 
      <RouterLink :to="{ name: 'test' }">test</RouterLink>
    </nav>
  </header>

  <main class="content">
    <RouterView />
  </main>
</template>

<style scoped></style>
