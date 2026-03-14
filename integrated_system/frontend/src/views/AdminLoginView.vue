<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { Shield, Lock, User, Eye, EyeOff, ArrowRight } from 'lucide-vue-next'

const router = useRouter()
const { login, loading } = useAuth()

const showPassword = ref(false)
const errorMsg = ref('')

const form = ref({
  username: '',
  password: ''
})

async function handleSubmit() {
  errorMsg.value = ''

  if (!form.value.username || !form.value.password) {
    errorMsg.value = '请填写管理员账户和密码'
    return
  }

  const result = await login(form.value.username, form.value.password)
  if (result.success) {
    if (result.user?.role !== 'admin') {
      errorMsg.value = '该账户不是管理员账户'
      // 自动登出
      const { logout } = useAuth()
      logout()
      return
    }
    router.push('/')
  } else {
    errorMsg.value = result.error || '登录失败'
  }
}
</script>

<template>
  <div class="min-h-screen w-full relative overflow-hidden flex items-center justify-center"
    style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 40%, #312e81 70%, #1e293b 100%)"
  >
    <!-- 动态光斑（深色版） -->
    <div class="fixed inset-0 pointer-events-none z-0 overflow-hidden">
      <div class="absolute top-1/4 -left-20 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl animate-pulse" style="animation-duration: 8s" />
      <div class="absolute bottom-1/4 right-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style="animation-duration: 12s" />
      <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-3xl" />
    </div>

    <!-- 网格背景 -->
    <div
      class="fixed inset-0 pointer-events-none z-0 opacity-10"
      style="
        background-image:
          linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
        background-size: 60px 60px;
      "
    />

    <!-- 管理员登录卡片 -->
    <div class="relative z-10 w-full max-w-md mx-4">
      <!-- Logo 区域 -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-[0_0_40px_rgba(99,102,241,0.3)] mb-4">
          <Shield class="w-8 h-8 text-white" />
        </div>
        <h1 class="font-serif text-3xl font-bold tracking-tight text-white">管理控制台</h1>
        <p class="text-sm text-indigo-300/70 mt-1">IP Scout Administration</p>
      </div>

      <!-- 卡片主体（深色玻璃拟态） -->
      <div class="bg-white/[0.06] backdrop-blur-2xl border border-white/10 rounded-2xl shadow-[0_8px_60px_-12px_rgba(0,0,0,0.5)] p-8">
        <!-- 标题 -->
        <div class="text-center mb-6">
          <h2 class="text-lg font-semibold text-white/90">管理员登录</h2>
          <p class="text-sm text-indigo-300/60 mt-1">请使用管理员账户登录</p>
        </div>

        <!-- 错误消息 -->
        <Transition name="fade">
          <div v-if="errorMsg" class="mb-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm flex items-center gap-2">
            <span class="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
            {{ errorMsg }}
          </div>
        </Transition>

        <!-- 表单 -->
        <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- 用户名 -->
          <div class="relative">
            <div class="absolute left-4 top-1/2 -translate-y-1/2 text-indigo-300/50">
              <User class="w-4 h-4" />
            </div>
            <input
              v-model="form.username"
              type="text"
              placeholder="管理员账户"
              class="w-full pl-11 pr-4 py-3 rounded-xl bg-white/[0.06] border border-white/10 text-white placeholder:text-indigo-300/40 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400/30 transition-all text-sm"
              autocomplete="username"
            />
          </div>

          <!-- 密码 -->
          <div class="relative">
            <div class="absolute left-4 top-1/2 -translate-y-1/2 text-indigo-300/50">
              <Lock class="w-4 h-4" />
            </div>
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="密码"
              class="w-full pl-11 pr-11 py-3 rounded-xl bg-white/[0.06] border border-white/10 text-white placeholder:text-indigo-300/40 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-400/30 transition-all text-sm"
              autocomplete="current-password"
            />
            <button
              type="button"
              @click="showPassword = !showPassword"
              class="absolute right-4 top-1/2 -translate-y-1/2 text-indigo-300/40 hover:text-indigo-200 transition-colors"
            >
              <Eye v-if="!showPassword" class="w-4 h-4" />
              <EyeOff v-else class="w-4 h-4" />
            </button>
          </div>

          <!-- 提交按钮 -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-medium text-sm shadow-[0_4px_20px_rgba(99,102,241,0.3)] hover:shadow-[0_4px_30px_rgba(99,102,241,0.5)] hover:scale-[1.01] active:scale-[0.99] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            <template v-else>
              进入管理后台
              <ArrowRight class="w-4 h-4" />
            </template>
          </button>
        </form>

        <!-- 安全提示 -->
        <div class="mt-6 pt-4 border-t border-white/5 text-center">
          <p class="text-xs text-indigo-300/40">
            此页面仅限系统管理员使用
          </p>
        </div>
      </div>

      <!-- 返回用户登录 -->
      <div class="text-center mt-6">
        <router-link
          to="/login"
          class="text-xs text-indigo-300/40 hover:text-indigo-300/70 transition-colors"
        >
          ← 返回用户登录
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
