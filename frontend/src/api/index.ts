import api from './http'

export interface UserInfo { id: number; username: string; nickname: string; major: string; grade: string; role: string }
export interface Period { id: number; slot: number; name: string; time_range: string; day_label: string; weekday: number; sort_order: number }
export interface Term { id: number; label: string; is_current: boolean }
export interface ScheduleItem { id: number; day: number; slot: number; time_range: string; course_name: string; teacher: string; room: string; weeks: string; color: string; material_key: string }
export interface Material { id: number; course: string; code: string; docs: string; focus: string }
export interface StudyPlan { id: number; user_id: number; title: string; plan_type: string; status: string; items: string[]; created_at: string }

export const authApi = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  register: (data: Record<string, string>) => api.post('/auth/register', data),
  me: () => api.get<UserInfo>('/auth/me'),
}

export const academicApi = {
  today: (username?: string) => api.get<ScheduleItem[]>('/academic/schedule/today', { params: { username } }),
  weekly: (username?: string) => api.get<ScheduleItem[]>('/academic/schedule/weekly', { params: { username } }),
  materials: (course?: string) => api.get<Material[]>('/academic/materials', { params: { course } }),
  users: () => api.get<UserInfo[]>('/academic/users'),
  periods: () => api.get<Period[]>('/academic/periods'),
  term: () => api.get<Term | null>('/academic/term'),
  ragSync: () => api.post('/academic/rag/sync'),
}

export const planApi = {
  list: (username?: string) => api.get<StudyPlan[]>('/plans', { params: { username } }),
  create: (data: { title: string; plan_type?: string; status?: string; items?: string[] }) => api.post('/plans', data),
  remove: (id: number) => api.delete(`/plans/${id}`),
}

export const chatApi = {
  sessions: () => api.get('/chat/sessions'),
  session: (id: number) => api.get(`/chat/sessions/${id}`),
  fresh: () => api.post('/chat/sessions'),
  remove: (id: number) => api.delete(`/chat/sessions/${id}`),
}

/** SSE 流式对话（POST）。onEvent 收到 {type, content, ...} */
export async function streamChat(
  message: string,
  opts: { username?: string; sessionId?: number | null; onEvent: (ev: any) => void; signal?: AbortSignal },
): Promise<void> {
  const token = localStorage.getItem('cca_token')
  const resp = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify({ message, username: opts.username, session_id: opts.sessionId }),
    signal: opts.signal,
  })
  if (!resp.ok || !resp.body) throw new Error(`对话请求失败: ${resp.status}`)
  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const parts = buf.split('\n\n')
    buf = parts.pop() ?? ''
    for (const p of parts) {
      const line = p.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      try { opts.onEvent(JSON.parse(line.slice(5).trim())) } catch { /* ignore */ }
    }
  }
}
