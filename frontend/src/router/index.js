import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import SignUp from '../views/SignUp.vue'

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
      path: '/game',
      component: () => import('../views/Game.vue'),
      children: [
        {
          path: 'custom',
          name: 'custom',
          component: () => import('../views/Watchlist.vue')
        },
        {
          path: 'transact',
          name: 'transact',
          component: () => import('../views/Transact.vue')
        },
        {
          path: 'inventory',
          name: 'inventory',
          component: () => import('../views/Inventory.vue')
        },
        {
          path: 'record',
          name: 'record',
          component: () => import('../views/Record.vue')
        }
      ]
    },
    {
      path: '/demo',
      name: 'demo',
      component: () => import('../views/WatchlistDemo.vue')
    },
    {
      path: '/demo/confirm',
      name: 'confirm-demo',
      component: () => import('../views/ConfirmModalDemo.vue')
    },
    {
      path: '/demo/topbar',
      name: 'topbar-demo',
      component: () => import('../views/TopBarDemo.vue')
    }
  ],
})

export default router
