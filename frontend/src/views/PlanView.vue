<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NEmpty, NPopconfirm, NSpin, NTag, useMessage } from 'naive-ui'
import { academicApi, planApi, type Material, type StudyPlan } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const store = useUserStore()
const message = useMessage()
const loading = ref(true)
const plans = ref<StudyPlan[]>([])
const courses = ref<Material[]>([])

const newPlanPrompt = computed(() => {
  const c = courses.value[0]?.course
  return c ? `帮我针对《${c}》整理一份预习学习计划` : '帮我整理一份学习计划'
})

async function load() {
  loading.value = true
  try {
    const [plansRes, matsRes] = await Promise.all([planApi.list(store.effectiveQueryUser), academicApi.materials()])
    plans.value = plansRes.data
    courses.value = matsRes.data
  } finally {
    loading.value = false
  }
}

async function remove(id: number) {
  await planApi.remove(id)
  message.success('已删除该学习计划')
  load()
}

onMounted(load)
</script>

<template>
  <n-card style="height: 100%; display: flex; flex-direction: column" title="学习计划">
    <template #header-extra>
      <n-button type="primary" size="small" @click="router.push({ name: 'assistant', query: { q: newPlanPrompt } })">
        让课程助手生成新计划
      </n-button>
    </template>
    <div style="font-size: 12px; color: #909399; margin-bottom: 16px">在「课程助手」中让 AI 整理预习/复习计划并回复「保存」后，会自动同步至此</div>
    <n-spin :show="loading">
      <n-empty v-if="!plans.length && !loading" description="暂无学习计划，去课程助手生成一份吧" />
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px">
        <n-card v-for="p in plans" :key="p.id" hoverable>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <n-tag :type="p.plan_type === '预习计划' ? 'info' : 'warning'" size="small">{{ p.plan_type }}</n-tag>
            <span style="font-size: 12px; color: #909399">{{ p.created_at }}</span>
          </div>
          <h3 style="font-size: 14px; margin: 8px 0">{{ p.title }}</h3>
          <ul style="font-size: 12px; color: #606266; padding-left: 16px; margin: 0; display: flex; flex-direction: column; gap: 6px">
            <li v-for="(it, i) in p.items" :key="i">{{ it }}</li>
          </ul>
          <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #ebeef5; display: flex; justify-content: space-between; font-size: 12px">
            <span style="color: #059669">已保存入库</span>
            <n-popconfirm @positive-click="remove(p.id)">
              <template #trigger><a style="color: #909399; cursor: pointer">删除</a></template>
              确认删除该计划吗？
            </n-popconfirm>
          </div>
        </n-card>
      </div>
    </n-spin>
  </n-card>
</template>
