import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import SignUp from '../views/SignUp.vue'
import WatchlistDemo from '../views/WatchlistDemo.vue'
import Custom from '../views/Custom.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'login',
      component: Login
    },
    {
      path: '/signup',
      name: 'signup',
      component: SignUp
    },
    {
      path: '/demo',
      name: 'demo',
      component: WatchlistDemo // 此路由用於展示展示，之後會刪掉
    },
    {
      path: '/custom',
      name: 'custom',
      component: Custom
    }
  ],
})

export default router
