<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import { NButton, NCard, NInput, useMessage } from 'naive-ui'
import { chatApi, streamChat, academicApi, type Material } from '../api'
import { useUserStore } from '../stores/user'

const md = new MarkdownIt({ breaks: true })
const route = useRoute()
const router = useRouter()
const store = useUserStore()
const message = useMessage()

interface Msg { role: 'user' | 'ai'; text: string; streaming?: boolean }

const WELCOME = '您好，我是校园课程助手。你可以问我课表、课程资料，也可以让我帮你整理学习计划（预习或复习）；确认要保存时再说「保存」即可。'
const messages = ref<Msg[]>([{ role: 'ai', text: WELCOME }])
const input = ref('')
const thinking = ref(false)
const sessionId = ref<number | null>(null)
const steps = ref<string[]>([])
const scrollBox = ref<HTMLElement | null>(null)
const courses = ref<Material[]>([])

const quickToday = computed(() => `帮我查下用户 ${store.effectiveQueryUser} 今天的课程表`)
const quickMaterial = computed(() => {
  const c = courses.value[0]?.course
  return c ? `帮我查一下《${c}》的课程资料和复习重点` : ''
})
const quickPlan = computed(() => {
  const c = courses.value[0]?.course
  return c ? `帮我针对《${c}》制定一份复习学习计划` : ''
})
const QUICK = computed(() => [
  { label: '查今天课表', text: quickToday.value },
  { label: '查课程资料', text: quickMaterial.value },
  { label: '生成学习计划', text: quickPlan.value },
  { label: '说「保存」', text: '保存' },
].filter((q) => q.text))

function scrollBottom() {
  nextTick(() => { if (scrollBox.value) scrollBox.value.scrollTop = scrollBox.value.scrollHeight })
}

function render(text: string) {
  return md.render(text)
}

async function loadHistory(id: number) {
  const { data } = await chatApi.session(id)
  messages.value = [{ role: 'ai', text: WELCOME }]
  for (const m of data.history || []) {
    messages.value.push({ role: m.role === 'user' ? 'user' : 'ai', text: m.content })
  }
  scrollBottom()
}

async function send(raw?: string) {
  const text = (raw ?? input.value).trim()
  if (!text || thinking.value) return
  input.value = ''
  messages.value.push({ role: 'user', text })
  thinking.value = true
  steps.value = []
  const aiMsg: Msg = { role: 'ai', text: '', streaming: true }
  messages.value.push(aiMsg)
  scrollBottom()
  try {
    await streamChat(text, {
      username: store.effectiveQueryUser,
      sessionId: sessionId.value,
      onEvent: (ev) => {
        if (ev.type === 'session') sessionId.value = ev.content
        else if (ev.type === 'step') steps.value.push(ev.content)
        else if (ev.type === 'delta') { aiMsg.text += ev.content; scrollBottom() }
        else if (ev.type === 'plan') {
          aiMsg.text += `\n\n> 📋 已生成计划草稿《${ev.content.title}》，回复「保存」即可入库。`
        } else if (ev.type === 'error') {
          aiMsg.text += `\n\n> ⚠️ ${ev.content}`
          message.error('助手调用失败')
        }
        scrollBottom()
      },
    })
  } catch (e: any) {
    aiMsg.text += `\n\n> ⚠️ 请求失败：${e?.message || e}`
  } finally {
    aiMsg.streaming = false
    thinking.value = false
    scrollBottom()
  }
}

async function reset() {
  const { data } = await chatApi.fresh()
  sessionId.value = data.id
  messages.value = [{ role: 'ai', text: WELCOME }]
  input.value = quickToday.value
  message.success('已开始新的对话')
}

onMounted(async () => {
  const { data } = await chatApi.fresh()
  sessionId.value = data.id
  try {
    const res = await academicApi.materials()
    courses.value = res.data
  } catch { courses.value = [] }
  input.value = quickToday.value
  const q = route.query.q as string | undefined
  if (q) { input.value = q; send(q) }
})

watch(() => route.query.q, (q) => { if (typeof q === 'string' && q) send(q) })
</script>

<template>
  <n-card style="height: 100%; display: flex; flex-direction: column" :bordered="true">
    <template #header>
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px">
        <div>
          <strong style="font-size: 15px">课程助手</strong>
          <span style="font-size: 12px; color: #909399; margin-left: 8px">（支持查询课表、课程资料检索、预习/复习计划生成与保存）</span>
        </div>
        <div style="display: flex; gap: 8px; align-items: center">
          <n-button v-for="q in QUICK" :key="q.label" size="small" type="info" ghost @click="send(q.text)">{{ q.label }}</n-button>
          <n-button size="small" quaternary @click="reset" title="清空对话"><i class="fa-solid fa-rotate-right"></i></n-button>
        </div>
      </div>
    </template>

    <div style="padding: 16px 20px 12px; flex: 1; display: flex; flex-direction: column; overflow: hidden">
      <div ref="scrollBox" class="chat-scroll">
        <div v-for="(m, i) in messages" :key="i" :class="m.role === 'user' ? 'bubble-user' : 'bubble-ai'">
          <template v-if="m.role === 'user'">{{ m.text }}</template>
          <template v-else>
            <div v-if="m.streaming && !m.text" class="typing-dots"><span></span><span></span><span></span> 课程助手正在查询...</div>
            <div v-else v-html="render(m.text)"></div>
          </template>
        </div>
        <div v-if="thinking && steps.length" style="font-size: 12px; color: #909399">
          <span v-for="(s, i) in steps" :key="i" style="margin-right: 8px">⚙️ {{ s }}</span>
        </div>
      </div>
    </div>

    <div style="padding: 4px 20px 16px; display: flex; gap: 12px; align-items: flex-end">
      <n-input
        v-model:value="input"
        type="textarea"
        :rows="3"
        placeholder="请输入问题，例如：帮我查下今天的课程表..."
        :disabled="thinking"
        @keydown.enter.exact.prevent="send()"
        style="flex: 1"
      />
      <n-button type="primary" :loading="thinking" @click="send()" style="height: 36px; padding: 0 20px">发送</n-button>
    </div>
  </n-card>
</template>
