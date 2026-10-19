<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCheckbox, NForm, NFormItem, NInput, useMessage } from 'naive-ui'
import { useUserStore } from '../stores/user'
import schoolBusUrl from '../assets/school-bus-amico.svg'

const router = useRouter()
const store = useUserStore()
const message = useMessage()
const tab = ref<'login' | 'register'>('login')
const loading = ref(false)
const remember = ref(false)
const form = ref({ username: '', password: '', nickname: '', major: '', grade: '' })

async function submit() {
  if (!form.value.username || !form.value.password) return message.warning('请输入账号和密码')
  loading.value = true
  try {
    if (tab.value === 'login') {
      await store.login(form.value.username, form.value.password)
    } else {
      await store.register({ ...form.value })
    }
    message.success('登录成功')
    router.push('/assistant')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '登录失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}

function switchTo(next: 'login' | 'register') {
  tab.value = next
  form.value.password = ''
}
</script>

<template>
  <div class="login-page">
    <aside class="login-visual">
      <img :src="schoolBusUrl" class="visual-svg" alt="校园校车插画" />
    </aside>

    <section class="login-panel">
        <header class="panel-head">
          <div class="logo"><i class="fa-solid fa-graduation-cap"></i></div>
          <div>
            <h1>校园课程智能助手</h1>
            <p>教务 Agent · DeepSeek 驱动</p>
          </div>
        </header>

        <div class="switch">
          <button :class="{ active: tab === 'login' }" type="button" @click="switchTo('login')">登录</button>
          <button :class="{ active: tab === 'register' }" type="button" @click="switchTo('register')">注册</button>
        </div>

        <n-form :model="form" label-placement="top" class="auth-form" :show-require-mark="false">
          <n-form-item v-if="tab === 'register'" label="昵称">
            <n-input v-model:value="form.nickname" placeholder="怎么称呼你" />
          </n-form-item>
          <n-form-item v-if="tab === 'register'" label="专业">
            <n-input v-model:value="form.major" placeholder="如：计算机科学与技术" />
          </n-form-item>
          <n-form-item label="用户名">
            <n-input v-model:value="form.username" placeholder="请输入用户名" clearable />
          </n-form-item>
          <n-form-item label="密码">
            <n-input
              v-model:value="form.password"
              type="password"
              placeholder="请输入密码"
              show-password-on="click"
              @keyup.enter="submit"
            />
          </n-form-item>
        </n-form>

        <div v-if="tab === 'login'" class="row-between">
          <n-checkbox v-model:checked="remember">记住密码</n-checkbox>
          <a class="link" href="#" @click.prevent="message.info('请联系教务管理员重置密码')">忘记密码?</a>
        </div>

        <n-button
          class="submit"
          type="primary"
          block
          round
          :loading="loading"
          @click="submit"
        >
          {{ tab === 'login' ? '登录' : '注册并登录' }}
        </n-button>

        <p class="tip">登录即代表您同意服务条款</p>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background: #fff;
  box-sizing: border-box;
}

/* 整屏左右各半铺满，不做居中卡片 */
.login-visual,
.login-panel {
  flex: 1 1 50%;
  min-width: 0;
}

.login-visual {
  background: linear-gradient(160deg, #d9f0ff, #e8f8ee);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.visual-svg {
  width: 100%;
  max-width: 560px;
  max-height: 78vh;
  height: auto;
  object-fit: contain;
  filter: drop-shadow(0 12px 24px rgba(60, 110, 90, 0.12));
}

.login-panel {
  padding: 48px 56px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: #fff;
}

/* 半屏变宽后，表单内容限宽居中，避免输入框被拉得过长 */
.login-panel > * {
  width: 100%;
  max-width: 440px;
  margin-left: auto;
  margin-right: auto;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 26px;
}

.panel-head .logo {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 20px;
  color: #fff;
  background: linear-gradient(135deg, #409eff, #2f7fe0);
  box-shadow: 0 3px 10px rgba(64, 158, 255, 0.35);
}

.panel-head h1 {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: #1f2937;
  letter-spacing: 0.5px;
}

.panel-head p {
  margin: 4px 0 0;
  font-size: 12px;
  color: #9aa4b2;
}

.switch {
  display: flex;
  background: #f2f5f9;
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 22px;
}

.switch button {
  flex: 1;
  border: none;
  background: transparent;
  padding: 9px 0;
  font-size: 14px;
  color: #7b8794;
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.switch button.active {
  background: #fff;
  color: #1f9d55;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(31, 64, 104, 0.08);
}

.auth-form :deep(.n-form-item-label__text) {
  font-size: 13px;
  color: #52606d;
}

.row-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -4px 0 18px;
  font-size: 13px;
}

.link {
  color: #1f9d55;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.submit {
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #22a95f, #17864a);
  border: none;
}

.tip {
  margin: 18px 0 0;
  text-align: center;
  font-size: 12px;
  color: #a3adb8;
}

@media (max-width: 860px) {
  .login-visual {
    display: none;
  }

  .login-panel {
    width: 100%;
    padding: 32px 24px;
  }
}
</style>
