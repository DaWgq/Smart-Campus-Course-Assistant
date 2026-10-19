import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import LayoutView from '../views/LayoutView.vue'
import { useUserStore } from '../stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginView },
    { path: '/', component: LayoutView, redirect: '/assistant', children: [
      { path: 'home', name: 'home', component: () => import('../views/HomeView.vue') },
      { path: 'schedule', name: 'schedule', component: () => import('../views/ScheduleView.vue') },
      { path: 'plan', name: 'plan', component: () => import('../views/PlanView.vue') },
      { path: 'assistant', name: 'assistant', component: () => import('../views/AssistantView.vue') },
    ] },
  ],
})

router.beforeEach((to) => {
  const store = useUserStore()
  if (to.path !== '/login' && !store.token) return '/login'
  if (to.path === '/login' && store.token) return '/assistant'
})

export default router
