<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NSpin, NTag } from 'naive-ui'
import { academicApi, planApi, type Material, type ScheduleItem, type StudyPlan } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const store = useUserStore()
const loading = ref(true)
const today = ref<ScheduleItem[]>([])
const materials = ref<Material[]>([])
const plans = ref<StudyPlan[]>([])

const planCount = computed(() => plans.value.length)

onMounted(async () => {
  try {
    const [t, m, p] = await Promise.all([
      academicApi.today(store.effectiveQueryUser),
      academicApi.materials(),
      planApi.list(store.effectiveQueryUser),
    ])
    today.value = t.data
    materials.value = m.data
    plans.value = p.data
  } finally {
    loading.value = false
  }
})

function goAssistant(text: string) {
  router.push({ name: 'assistant', query: { q: text } })
}
</script>

<template>
  <n-spin :show="loading" style="height: 100%">
    <div style="display: flex; flex-direction: column; gap: 16px; height: 100%; overflow-y: auto; padding-right: 4px">
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px">
        <n-card hoverable>
          <div style="font-size: 12px; color: #909399">当前绑定学生账号</div>
          <div style="font-size: 18px; font-weight: 700; margin-top: 6px">{{ store.label }}</div>
          <div style="font-size: 12px; color: #409eff; margin-top: 4px">{{ store.user?.major }} · {{ store.user?.grade }}</div>
        </n-card>
        <n-card hoverable @click="router.push('/schedule')" style="cursor: pointer">
          <div style="font-size: 12px; color: #909399">今日待上课程</div>
          <div style="font-size: 24px; font-weight: 700; margin-top: 6px">{{ today.length }} 门</div>
          <div v-if="today[1]" style="font-size: 12px; color: #059669; margin-top: 4px">下节课 {{ today[1].time_range.split(' - ')[0] }} {{ today[1].course_name }}</div>
        </n-card>
        <n-card hoverable @click="router.push('/plan')" style="cursor: pointer">
          <div style="font-size: 12px; color: #909399">已保存学习计划</div>
          <div style="font-size: 24px; font-weight: 700; margin-top: 6px">{{ planCount }} 份</div>
          <div style="font-size: 12px; color: #b45309; margin-top: 4px">含预习与期末复习清单</div>
        </n-card>
        <n-card hoverable @click="router.push('/assistant')" style="cursor: pointer">
          <div style="font-size: 12px; color: #909399">RAG 课程资料库</div>
          <div style="font-size: 24px; font-weight: 700; margin-top: 6px">{{ materials.length }} 门全覆盖</div>
          <div style="font-size: 12px; color: #409eff; margin-top: 4px">点击向课程助手提问 →</div>
        </n-card>
      </div>

      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 16px">
        <n-card :title="`用户 ${store.effectiveQueryUser} · 今日课程安排 (周一)`">
          <template #header-extra><a style="font-size: 12px; color: #409eff; cursor: pointer" @click="router.push('/schedule')">查看完整周课表 →</a></template>
          <div style="display: flex; flex-direction: column; gap: 12px">
            <div v-for="c in today" :key="c.id" style="padding: 14px; border-radius: 8px; border: 1px solid #ebeef5; background: rgba(247,248,250,.6); display: flex; align-items: center; justify-content: space-between; gap: 12px">
              <div>
                <n-tag type="info" size="small">{{ c.time_range }}</n-tag>
                <div style="font-weight: 700; font-size: 14px; margin-top: 6px">{{ c.course_name }}</div>
                <div style="font-size: 12px; color: #909399">{{ c.teacher }} · {{ c.room }} · {{ c.weeks }}</div>
              </div>
              <n-button size="small" @click="goAssistant(`帮我整理一份《${c.course_name}》的预习计划`)">生成预习计划</n-button>
            </div>
            <div v-if="!today.length" style="color: #909399; font-size: 13px">今日暂无课程</div>
          </div>
        </n-card>

        <n-card title="已接入课程资料库">
          <template #header-extra><span style="font-size: 12px; color: #909399">支持向助手提问</span></template>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <div v-for="m in materials" :key="m.id" style="padding: 12px; border-radius: 8px; background: #f7f8fa; border: 1px solid #ebeef5; display: flex; justify-content: space-between; gap: 8px; align-items: center">
              <div style="min-width: 0">
                <div style="font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">《{{ m.course }}》</div>
                <div style="font-size: 11px; color: #909399; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ m.docs }}</div>
              </div>
              <a style="color: #409eff; font-size: 12px; cursor: pointer; flex-shrink: 0" @click="goAssistant(`帮我查一下《${m.course}》的课程资料和复习重点`)">提问</a>
            </div>
          </div>
        </n-card>
      </div>
    </div>
  </n-spin>
</template>
