import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { authApi, type UserInfo } from '../api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('cca_token') || '')
  const user = ref<UserInfo | null>(JSON.parse(localStorage.getItem('cca_user') || 'null'))

  /** 课表/助手查询用的目标学生用户名，默认当前登录用户（登录后自动同步） */
  const queryUser = ref(localStorage.getItem('cca_query_user') || '')

  const isLogin = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const label = computed(() => (user.value ? `${user.value.nickname} (${user.value.username})` : ''))

  /** 查询目标：普通用户恒为本人；仅管理员可切换他人 */
  const effectiveQueryUser = computed(() =>
    isAdmin.value ? queryUser.value || user.value?.username || '' : user.value?.username || '',
  )

  watch(queryUser, (v) => {
    if (v) localStorage.setItem('cca_query_user', v)
  })

  watch(
    () => user.value?.username,
    (u) => {
      if (!u) return
      if (!queryUser.value) queryUser.value = u
      if (!isAdmin.value) queryUser.value = u
    },
    { immediate: true },
  )

  function persist() {
    if (token.value) localStorage.setItem('cca_token', token.value)
    else localStorage.removeItem('cca_token')
    if (user.value) localStorage.setItem('cca_user', JSON.stringify(user.value))
    else localStorage.removeItem('cca_user')
    if (!queryUser.value) {
      queryUser.value = user.value?.username || ''
      if (user.value?.username) localStorage.setItem('cca_query_user', user.value.username)
    }
  }

  async function login(username: string, password: string) {
    const { data } = await authApi.login(username, password)
    token.value = data.access_token
    user.value = data.user
    persist()
  }

  async function register(payload: Record<string, string>) {
    const { data } = await authApi.register(payload)
    token.value = data.access_token
    user.value = data.user
    persist()
  }

  function logout() {
    token.value = ''
    user.value = null
    queryUser.value = ''
    localStorage.removeItem('cca_query_user')
    persist()
  }

  return { token, user, queryUser, effectiveQueryUser, isLogin, isAdmin, label, login, register, logout }
})
