import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import SignUp from '../views/SignUp.vue'
import Custom from '../views/Custom.vue'
import WatchlistDemo from '../views/WatchlistDemo.vue'

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
      path: '/custom',
      name: 'custom',
      component: Custom
    },
    {
      path: '/demo',
      name: 'demo',
      component: WatchlistDemo
    }
  ],
})

export default router
