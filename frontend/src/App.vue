<script setup>
import { RouterLink, RouterView } from 'vue-router'
import Login from './views/Login.vue';
</script>

<template>
  <!-- <header>
    <nav class="navbar">
      <RouterLink :to="{ name: 'home' }">home</RouterLink> | 
      <RouterLink :to="{ name: 'test' }">test</RouterLink>
    </nav>
  </header>

  <main class="content">
    <RouterView />
  </main> -->
  <Login />
</template>

<style scoped></style>
