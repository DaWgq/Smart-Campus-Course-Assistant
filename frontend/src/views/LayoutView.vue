<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NAvatar, NButton, NDropdown } from 'naive-ui'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const active = computed(() => route.name as string)
const menus = [
  { key: 'home', label: '系统首页', icon: 'fa-solid fa-table-cells-large' },
  { key: 'schedule', label: '我的课表', icon: 'fa-regular fa-calendar-days' },
  { key: 'plan', label: '学习计划', icon: 'fa-solid fa-book' },
  { key: 'assistant', label: '课程助手', icon: 'fa-regular fa-comment-dots' },
]

function logout() {
  store.logout()
  router.push('/login')
}
</script>

<template>
  <div style="height: 100%; display: flex; flex-direction: column; overflow: hidden">
    <header class="top-header">
      <div class="brand" @click="router.push('/assistant')">
        <div class="logo-cal">
          <i class="fa-solid fa-graduation-cap"></i>
        </div>
        <h1>校园课程智能助手</h1>
      </div>
      <n-dropdown
        :options="[{ label: '退出登录', key: 'logout' }]"
        @select="(k) => k === 'logout' && logout()"
      >
        <div style="display: flex; align-items: center; gap: 10px; cursor: pointer">
          <n-avatar round size="small" style="background: #fef3c7; color: #b45309">
            {{ store.user?.nickname?.slice(0, 1) || '学' }}
          </n-avatar>
          <span style="font-size: 14px; color: #606266">{{ store.label }}</span>
        </div>
      </n-dropdown>
    </header>

    <div class="main-body">
      <aside class="side-nav">
        <nav>
          <router-link
            v-for="m in menus"
            :key="m.key"
            :to="`/${m.key}`"
            class="nav-link"
            :class="{ active: active === m.key }"
          >
            <i :class="m.icon" style="width: 16px; text-align: center"></i>
            <span>{{ m.label }}</span>
          </router-link>
        </nav>
        <div class="side-note">
          <div style="font-weight: 600; color: #606266; margin-bottom: 6px">
            <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10b981; margin-right: 6px"></span>Agent 服务在线
          </div>
          <p style="margin: 4px 0">当前查询用户：<code style="color: #409eff">{{ store.effectiveQueryUser }}</code></p>
          <p style="margin: 4px 0; line-height: 1.6">支持查课表、查课程资料、生成并保存学习计划</p>
        </div>
      </aside>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>
