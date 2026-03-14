<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import {
  User, Mail, Lock, Camera, Shield,
  Calendar, LogOut, Save, Eye, EyeOff,
  CheckCircle, AlertCircle, ChevronRight
} from 'lucide-vue-next'
import axios from 'axios'

const router = useRouter()
const { user, logout, fetchUser } = useAuth()

// 区块展开状态
const activeSection = ref<string>('profile')

// 个人资料表单
const profileForm = ref({ username: '', email: '' })
const profileSaving = ref(false)
const profileMsg = ref({ type: '', text: '' })

// 密码表单
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' })
const passwordSaving = ref(false)
const passwordMsg = ref({ type: '', text: '' })
const showOldPwd = ref(false)
const showNewPwd = ref(false)

// 头像
const avatarUploading = ref(false)
const avatarMsg = ref({ type: '', text: '' })
const avatarInputRef = ref<HTMLInputElement | null>(null)

// 初始化
onMounted(() => {
  if (user.value) {
    profileForm.value.username = user.value.username || ''
    profileForm.value.email = user.value.email || ''
  }
})

// 头像 URL（Vite proxy 会代理 /uploads 到 Flask）
const avatarUrl = computed(() => {
  if (user.value?.avatar) {
    return user.value.avatar
  }
  return ''
})

// 用户首字母
const userInitial = computed(() => {
  return (user.value?.username || 'U').charAt(0).toUpperCase()
})

// 注册日期格式化
const joinDate = computed(() => {
  if (!user.value?.created_at) return '未知'
  const d = new Date(user.value.created_at)
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
})

// 保存个人资料
async function saveProfile() {
  profileMsg.value = { type: '', text: '' }
  if (!profileForm.value.username || profileForm.value.username.length < 2) {
    profileMsg.value = { type: 'error', text: '用户名至少需要2个字符' }
    return
  }
  if (!profileForm.value.email || !profileForm.value.email.includes('@')) {
    profileMsg.value = { type: 'error', text: '请提供有效的邮箱地址' }
    return
  }

  profileSaving.value = true
  try {
    const res = await axios.put('/api/auth/profile', profileForm.value)
    profileMsg.value = { type: 'success', text: '资料更新成功' }
    await fetchUser()
  } catch (err: any) {
    profileMsg.value = { type: 'error', text: err.response?.data?.error || '更新失败' }
  } finally {
    profileSaving.value = false
  }
}

// 修改密码
async function changePassword() {
  passwordMsg.value = { type: '', text: '' }
  if (!passwordForm.value.old_password) {
    passwordMsg.value = { type: 'error', text: '请输入当前密码' }
    return
  }
  if (!passwordForm.value.new_password || passwordForm.value.new_password.length < 6) {
    passwordMsg.value = { type: 'error', text: '新密码至少需要6个字符' }
    return
  }
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordMsg.value = { type: 'error', text: '两次输入的密码不一致' }
    return
  }

  passwordSaving.value = true
  try {
    await axios.put('/api/auth/password', {
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password
    })
    passwordMsg.value = { type: 'success', text: '密码修改成功' }
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (err: any) {
    passwordMsg.value = { type: 'error', text: err.response?.data?.error || '修改失败' }
  } finally {
    passwordSaving.value = false
  }
}

// 上传头像
function triggerAvatarUpload() {
  avatarInputRef.value?.click()
}

async function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return

  const file = input.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    avatarMsg.value = { type: 'error', text: '头像文件不能超过 2MB' }
    return
  }

  avatarMsg.value = { type: '', text: '' }
  avatarUploading.value = true

  const formData = new FormData()
  formData.append('avatar', file as Blob)

  try {
    await axios.post('/api/auth/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    avatarMsg.value = { type: 'success', text: '头像上传成功' }
    await fetchUser()
  } catch (err: any) {
    avatarMsg.value = { type: 'error', text: err.response?.data?.error || '上传失败' }
  } finally {
    avatarUploading.value = false
    input.value = ''
  }
}

// 退出登录
function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <EditorialLayout>
    <div class="max-w-3xl mx-auto py-8 px-4">
      <!-- 页面标题 -->
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-slate-800 tracking-tight">个人设置</h1>
        <p class="text-sm text-slate-400 mt-1">管理您的账户信息和安全设置</p>
      </div>

      <!-- 用户卡片 -->
      <div class="bg-white/60 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm p-6 mb-6">
        <div class="flex items-center gap-5">
          <!-- 头像 -->
          <div class="relative group">
            <div class="w-20 h-20 rounded-2xl overflow-hidden border-2 border-white shadow-lg">
              <img v-if="avatarUrl" :src="avatarUrl" alt="Avatar" class="w-full h-full object-cover" />
              <div v-else
                class="w-full h-full flex items-center justify-center text-2xl font-bold text-white"
                style="background: linear-gradient(135deg, #5a6a8a 0%, #6a7aaa 100%)"
              >
                {{ userInitial }}
              </div>
            </div>
            <!-- 上传按钮覆层 -->
            <button
              @click="triggerAvatarUpload"
              :disabled="avatarUploading"
              class="absolute inset-0 rounded-2xl bg-black/0 group-hover:bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 cursor-pointer"
            >
              <Camera class="w-5 h-5 text-white" />
            </button>
            <input
              ref="avatarInputRef"
              type="file"
              accept="image/png,image/jpeg,image/gif,image/webp"
              class="hidden"
              @change="handleAvatarChange"
            />
          </div>

          <!-- 用户信息 -->
          <div class="flex-1">
            <h2 class="text-lg font-semibold text-slate-800">{{ user?.username || '用户' }}</h2>
            <p class="text-sm text-slate-400">{{ user?.email || '' }}</p>
            <div class="flex items-center gap-3 mt-2">
              <span
                class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                :class="user?.role === 'admin'
                  ? 'bg-amber-50 text-amber-600 border border-amber-200'
                  : 'bg-indigo-50 text-indigo-600 border border-indigo-200'"
              >
                <Shield class="w-3 h-3" />
                {{ user?.role === 'admin' ? '管理员' : '普通用户' }}
              </span>
              <span class="inline-flex items-center gap-1 text-[11px] text-slate-400">
                <Calendar class="w-3 h-3" /> 加入于 {{ joinDate }}
              </span>
            </div>
          </div>
        </div>

        <!-- 头像消息 -->
        <Transition name="fade">
          <div v-if="avatarMsg.text"
            class="mt-3 px-3 py-2 rounded-xl text-xs flex items-center gap-2"
            :class="avatarMsg.type === 'success' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'"
          >
            <CheckCircle v-if="avatarMsg.type === 'success'" class="w-3.5 h-3.5" />
            <AlertCircle v-else class="w-3.5 h-3.5" />
            {{ avatarMsg.text }}
          </div>
        </Transition>
      </div>

      <!-- 设置区块 -->
      <div class="space-y-4">

        <!-- 基本资料 -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm overflow-hidden">
          <button @click="activeSection = activeSection === 'profile' ? '' : 'profile'"
            class="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50/50 transition-colors"
          >
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center">
                <User class="w-4 h-4 text-indigo-500" />
              </div>
              <div class="text-left">
                <p class="text-sm font-medium text-slate-800">基本资料</p>
                <p class="text-[11px] text-slate-400">修改用户名和邮箱</p>
              </div>
            </div>
            <ChevronRight class="w-4 h-4 text-slate-400 transition-transform duration-300" :class="activeSection === 'profile' ? 'rotate-90' : ''" />
          </button>

          <Transition name="expand">
            <div v-if="activeSection === 'profile'" class="px-6 pb-5 border-t border-slate-100">
              <form @submit.prevent="saveProfile" class="space-y-4 pt-4">
                <div>
                  <label class="text-xs font-medium text-slate-500 mb-1.5 block">用户名</label>
                  <div class="relative">
                    <User class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input v-model="profileForm.username"
                      class="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50/80 border border-slate-200/80 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400/50 focus:bg-white transition-all" />
                  </div>
                </div>
                <div>
                  <label class="text-xs font-medium text-slate-500 mb-1.5 block">邮箱地址</label>
                  <div class="relative">
                    <Mail class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input v-model="profileForm.email" type="email"
                      class="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50/80 border border-slate-200/80 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400/50 focus:bg-white transition-all" />
                  </div>
                </div>

                <!-- 消息 -->
                <Transition name="fade">
                  <div v-if="profileMsg.text"
                    class="px-3 py-2 rounded-xl text-xs flex items-center gap-2"
                    :class="profileMsg.type === 'success' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'"
                  >
                    <CheckCircle v-if="profileMsg.type === 'success'" class="w-3.5 h-3.5" />
                    <AlertCircle v-else class="w-3.5 h-3.5" />
                    {{ profileMsg.text }}
                  </div>
                </Transition>

                <button type="submit" :disabled="profileSaving"
                  class="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-medium text-white transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
                  style="background: linear-gradient(135deg, #4a5a8a 0%, #5a6aaa 100%); box-shadow: 0 2px 12px rgba(74,90,138,0.3);"
                >
                  <Save class="w-4 h-4" />
                  {{ profileSaving ? '保存中...' : '保存修改' }}
                </button>
              </form>
            </div>
          </Transition>
        </div>

        <!-- 安全设置 -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm overflow-hidden">
          <button @click="activeSection = activeSection === 'security' ? '' : 'security'"
            class="w-full flex items-center justify-between px-6 py-4 hover:bg-slate-50/50 transition-colors"
          >
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-xl bg-amber-50 flex items-center justify-center">
                <Lock class="w-4 h-4 text-amber-500" />
              </div>
              <div class="text-left">
                <p class="text-sm font-medium text-slate-800">安全设置</p>
                <p class="text-[11px] text-slate-400">修改密码和安全选项</p>
              </div>
            </div>
            <ChevronRight class="w-4 h-4 text-slate-400 transition-transform duration-300" :class="activeSection === 'security' ? 'rotate-90' : ''" />
          </button>

          <Transition name="expand">
            <div v-if="activeSection === 'security'" class="px-6 pb-5 border-t border-slate-100">
              <form @submit.prevent="changePassword" class="space-y-4 pt-4">
                <div>
                  <label class="text-xs font-medium text-slate-500 mb-1.5 block">当前密码</label>
                  <div class="relative">
                    <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input v-model="passwordForm.old_password" :type="showOldPwd ? 'text' : 'password'"
                      class="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-50/80 border border-slate-200/80 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400/50 focus:bg-white transition-all" />
                    <button type="button" @click="showOldPwd = !showOldPwd"
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                      <Eye v-if="!showOldPwd" class="w-4 h-4" />
                      <EyeOff v-else class="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div>
                  <label class="text-xs font-medium text-slate-500 mb-1.5 block">新密码</label>
                  <div class="relative">
                    <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input v-model="passwordForm.new_password" :type="showNewPwd ? 'text' : 'password'"
                      class="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-50/80 border border-slate-200/80 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400/50 focus:bg-white transition-all" />
                    <button type="button" @click="showNewPwd = !showNewPwd"
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                      <Eye v-if="!showNewPwd" class="w-4 h-4" />
                      <EyeOff v-else class="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div>
                  <label class="text-xs font-medium text-slate-500 mb-1.5 block">确认新密码</label>
                  <div class="relative">
                    <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input v-model="passwordForm.confirm_password" :type="showNewPwd ? 'text' : 'password'"
                      class="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-50/80 border border-slate-200/80 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400/50 focus:bg-white transition-all" />
                  </div>
                </div>

                <!-- 消息 -->
                <Transition name="fade">
                  <div v-if="passwordMsg.text"
                    class="px-3 py-2 rounded-xl text-xs flex items-center gap-2"
                    :class="passwordMsg.type === 'success' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'"
                  >
                    <CheckCircle v-if="passwordMsg.type === 'success'" class="w-3.5 h-3.5" />
                    <AlertCircle v-else class="w-3.5 h-3.5" />
                    {{ passwordMsg.text }}
                  </div>
                </Transition>

                <button type="submit" :disabled="passwordSaving"
                  class="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-medium text-white transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
                  style="background: linear-gradient(135deg, #8a6a4a 0%, #aa7a5a 100%); box-shadow: 0 2px 12px rgba(138,106,74,0.3);"
                >
                  <Lock class="w-4 h-4" />
                  {{ passwordSaving ? '修改中...' : '修改密码' }}
                </button>
              </form>
            </div>
          </Transition>
        </div>

        <!-- 退出登录 -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm overflow-hidden">
          <button @click="handleLogout"
            class="w-full flex items-center justify-between px-6 py-4 hover:bg-red-50/50 transition-colors group"
          >
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-xl bg-red-50 flex items-center justify-center">
                <LogOut class="w-4 h-4 text-red-500" />
              </div>
              <div class="text-left">
                <p class="text-sm font-medium text-red-600 group-hover:text-red-700">退出登录</p>
                <p class="text-[11px] text-slate-400">退出当前账户并返回登录页</p>
              </div>
            </div>
            <ChevronRight class="w-4 h-4 text-red-300" />
          </button>
        </div>
      </div>
    </div>
  </EditorialLayout>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.expand-enter-active { transition: all 0.35s ease; overflow: hidden; }
.expand-leave-active { transition: all 0.25s ease; overflow: hidden; }
.expand-enter-from { max-height: 0; opacity: 0; }
.expand-leave-to { max-height: 0; opacity: 0; }
.expand-enter-to, .expand-leave-from { max-height: 500px; opacity: 1; }
</style>
