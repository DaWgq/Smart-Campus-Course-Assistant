<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NSelect, NSpin, NTag } from 'naive-ui'
import { academicApi, type Period, type ScheduleItem, type Term, type UserInfo } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const store = useUserStore()
const loading = ref(true)
const courses = ref<ScheduleItem[]>([])
const users = ref<UserInfo[]>([])
const periods = ref<Period[]>([])
const term = ref<Term | null>(null)

const DAYS = computed(() => periods.value.map((p) => p.day_label))

const userOptions = computed(() =>
  users.value.map((u) => ({ label: `用户 ${u.username} (${u.nickname} · ${u.major || ''})`, value: u.username })),
)

async function load() {
  loading.value = true
  try {
    const [w, p, t] = await Promise.all([
      academicApi.weekly(store.effectiveQueryUser),
      academicApi.periods(),
      academicApi.term(),
    ])
    courses.value = w.data
    periods.value = p.data
    term.value = t.data
    // 用户列表仅管理员可读，普通用户跳过
    if (store.isAdmin) {
      try {
        users.value = (await academicApi.users()).data
      } catch {
        users.value = []
      }
    } else {
      users.value = []
    }
  } finally {
    loading.value = false
  }
}

function cell(weekday: number, slot: number) {
  return courses.value.find((c) => c.day === weekday + 1 && c.slot === slot)
}

onMounted(load)
</script>

<template>
  <n-card style="height: 100%; display: flex; flex-direction: column" :bordered="true">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px">
        <div style="display: flex; align-items: center; gap: 12px">
          <strong style="font-size: 15px">我的课表</strong>
          <n-tag v-if="term" type="info" size="small">{{ term.label }}</n-tag>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; font-size: 12px">
          <span style="color: #606266">当前用户：</span>
          <n-tag type="info" size="small">{{ store.effectiveQueryUser }}</n-tag>
          <n-tag v-if="store.isAdmin" type="success" size="small">管理员可切换</n-tag>
          <n-select
            v-if="store.isAdmin"
            :value="store.effectiveQueryUser"
            :options="userOptions"
            size="small"
            style="width: 220px"
            @update:value="store.queryUser = $event; load()"
          />
          <n-button type="primary" size="small" @click="router.push({ name: 'assistant', query: { q: '帮我查下我今天的课程表' } })">
            在助手中查今日课表
          </n-button>
        </div>
      </div>
    </template>
    <n-spin :show="loading">
      <div style="overflow: auto">
        <div class="sched-grid">
          <div class="sched-head">
            <div>节次 / 时间</div>
            <div v-for="(d, i) in DAYS" :key="i" :style="i === 0 ? { color: '#409eff', background: 'rgba(239,246,255,.6)' } : {}">{{ d }}</div>
          </div>
          <div v-for="p in periods" :key="p.slot" class="sched-row">
            <div class="sched-cell" style="background: #f7f8fa; display: flex; flex-direction: column; justify-content: center; align-items: center">
              <strong>{{ p.name }}</strong><span style="font-size: 11px; color: #909399">{{ p.time_range }}</span>
            </div>
            <div v-for="d in periods" :key="d.weekday" class="sched-cell">
              <div v-if="cell(d.weekday, p.slot)" class="course-chip" :class="`chip-${cell(d.weekday, p.slot)!.color}`"
                @click="router.push({ name: 'assistant', query: { q: `帮我查一下《${cell(d.weekday, p.slot)!.course_name}》的课程资料` } })">
                <div>
                  <div style="font-weight: 700">{{ cell(d.weekday, p.slot)!.course_name }}</div>
                  <div style="font-size: 11px; opacity: .8; margin-top: 4px">{{ cell(d.weekday, p.slot)!.teacher }}</div>
                </div>
                <div style="font-size: 11px; opacity: .75; margin-top: 8px; display: flex; justify-content: space-between">
                  <span>📍 {{ cell(d.weekday, p.slot)!.room }}</span><span>{{ cell(d.weekday, p.slot)!.weeks }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </n-spin>
  </n-card>
</template>
