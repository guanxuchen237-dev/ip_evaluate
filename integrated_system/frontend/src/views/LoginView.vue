<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import LiquidHero from '@/components/hero/LiquidHero.vue'
import {
  Lock, Mail, User, Eye, EyeOff, ArrowRight, X,
  TrendingUp, BarChart3, Shield, Sparkles, BookOpen, Zap, CheckCircle2
} from 'lucide-vue-next'

const router = useRouter()
const { login, register, logout, loading } = useAuth()

const isLoginMode = ref(true)
const showPassword = ref(false)
const errorMsg = ref('')
const ready = ref(false)

// 忘记密码相关
const showForgotModal = ref(false)
const forgotEmail = ref('')
const forgotCode = ref('')
const forgotNewPassword = ref('')
const forgotUsername = ref('')
const forgotStep = ref(1) // 1: 输入邮箱, 2: 输入验证码和新密码
const forgotLoading = ref(false)
const forgotError = ref('')
const forgotSuccess = ref('')

const form = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 登录页统计数据
const loginStats = ref({
  total_tracking: 2847,
  dark_horse_count: 156,
  prediction_accuracy: 78,
  total_books: 5000
})
const statsLoading = ref(false)

// 获取登录页统计数据
async function fetchLoginStats() {
  statsLoading.value = true
  try {
    const res = await fetch('http://localhost:5000/api/stats/login')
    if (res.ok) {
      const result = await res.json()
      if (result.data) {
        loginStats.value = {
          total_tracking: result.data.total_tracking || 2847,
          dark_horse_count: result.data.dark_horse_count || 156,
          prediction_accuracy: result.data.prediction_accuracy || 78,
          total_books: result.data.total_books || 5000
        }
      }
    }
  } catch (e) {
    console.error('获取登录页统计数据失败:', e)
    // 使用默认值
  } finally {
    statsLoading.value = false
  }
}

onMounted(() => {
  setTimeout(() => { ready.value = true }, 150)
  fetchLoginStats() // 获取真实统计数据
})

function toggleMode() {
  isLoginMode.value = !isLoginMode.value
  errorMsg.value = ''
  form.value = { username: '', email: '', password: '', confirmPassword: '' }
}

async function handleSubmit() {
  errorMsg.value = ''

  if (isLoginMode.value) {
    if (!form.value.username || !form.value.password) {
      errorMsg.value = '请填写用户名和密码'
      return
    }
    
    // 登录逻辑
    const result = await login(form.value.username, form.value.password)
    
    if (result.success) {
      const user = result.user
      
      // 根据角色自动分发路由
      if (user?.role === 'admin') {
        router.push('/admin') // 管理员进入后台
      } else {
        router.push('/') // 普通用户进入主页
      }
    } else {
      errorMsg.value = result.error || '登录失败'
    }

  } else {
    // 注册逻辑 (仅限普通用户)
    if (!form.value.username || !form.value.email || !form.value.password) {
      errorMsg.value = '请填写所有必填字段'
      return
    }
    if (form.value.password !== form.value.confirmPassword) {
      errorMsg.value = '两次输入的密码不一致'
      return
    }
    if (form.value.password.length < 6) {
      errorMsg.value = '密码至少需要6个字符'
      return
    }
    const result = await register(form.value.username, form.value.email, form.value.password)
    if (result.success) {
      router.push('/')
    } else {
      errorMsg.value = result.error || '注册失败'
    }
  }
}

// 忘记密码功能
async function handleForgotPassword() {
  forgotError.value = ''
  forgotSuccess.value = ''
  
  if (forgotStep.value === 1) {
    // 第一步：发送验证码
    if (!forgotEmail.value) {
      forgotError.value = '请输入邮箱地址'
      return
    }
    
    forgotLoading.value = true
    try {
      const res = await fetch('http://localhost:5000/api/auth/forgot_password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotEmail.value })
      })
      
      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(`HTTP ${res.status}: ${errorText}`)
      }
      
      const data = await res.json()
      
      if (data.success) {
        forgotUsername.value = data.username || ''
        forgotStep.value = 2
        if (data.code) {
          forgotCode.value = data.code // 开发环境自动填充
        }
        forgotSuccess.value = '验证码已发送'
      } else {
        forgotError.value = data.error || '发送失败'
      }
    } catch (e: any) {
      console.error('Forgot password error:', e)
      forgotError.value = '请求失败: ' + (e.message || '请检查后端服务是否运行')
    } finally {
      forgotLoading.value = false
    }
  } else {
    // 第二步：重置密码
    if (!forgotCode.value || !forgotNewPassword.value) {
      forgotError.value = '请填写验证码和新密码'
      return
    }
    if (forgotNewPassword.value.length < 6) {
      forgotError.value = '密码至少需要6个字符'
      return
    }
    
    forgotLoading.value = true
    try {
      const res = await fetch('http://localhost:5000/api/auth/reset_password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: forgotEmail.value,
          code: forgotCode.value,
          new_password: forgotNewPassword.value
        })
      })
      
      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(`HTTP ${res.status}: ${errorText}`)
      }
      
      const data = await res.json()
      
      if (data.success) {
        forgotSuccess.value = '密码重置成功！'
        setTimeout(() => {
          showForgotModal.value = false
          forgotStep.value = 1
          forgotEmail.value = ''
          forgotCode.value = ''
          forgotNewPassword.value = ''
        }, 1500)
      } else {
        forgotError.value = data.error || '重置失败'
      }
    } catch (e: any) {
      console.error('Reset password error:', e)
      forgotError.value = '请求失败: ' + (e.message || '请检查后端服务是否运行')
    } finally {
      forgotLoading.value = false
    }
  }
}

function closeForgotModal() {
  showForgotModal.value = false
  forgotStep.value = 1
  forgotEmail.value = ''
  forgotCode.value = ''
  forgotNewPassword.value = ''
  forgotError.value = ''
  forgotSuccess.value = ''
}
</script>

<template>
  <div class="min-h-screen flex font-sans text-slate-900 bg-white selection:bg-indigo-500/30">

    <!-- ============================================ -->
    <!--  左侧：艺术感深色区 (55%)                     -->
    <!-- ============================================ -->
    <div class="hidden lg:flex lg:w-[55%] relative overflow-hidden bg-[#0F172A] text-white">
      
      <!-- 纯净深邃背景 -->
      <div class="absolute inset-0 z-0 bg-gradient-to-br from-[#0B1121] via-[#0F172A] to-[#162032]"></div>

      <!-- 3D 液态球体：还原第二张图 -->
      <!-- 位置：上移 (top-[10%])，取消垂直居中，靠右，大尺寸 -->
      <div class="absolute top-[8%] -right-[20%] w-[100%] h-[100%] z-10 pointer-events-none mix-blend-screen filter saturate-100 brightness-110 opacity-80">
        <LiquidHero disable-parallax />
      </div>

      <!-- 内容容器：左对齐 -->
      <div class="relative z-20 flex flex-col justify-between w-full h-full p-20 pl-24">
        
        <!-- Header -->
        <div class="flex items-center gap-3 animate-fade-in-down">
          <div class="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center backdrop-blur-md shadow-lg">
            <BookOpen class="w-5 h-5 text-sky-400" />
          </div>
          <div>
            <h1 class="font-bold text-lg tracking-tight text-white">IP Scout</h1>
            <p class="text-slate-400 text-xs font-medium tracking-wide">网络文学智能情报</p>
          </div>
        </div>

        <!-- Main Content -->
        <div class="max-w-xl relative z-30 mb-20">
           
           <div class="space-y-10 transition-all duration-1000 ease-out" :class="ready ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'">
              
              <!-- 胶囊标签 -->
              <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[10px] font-bold tracking-wider backdrop-blur-md">
                <Sparkles class="w-3 h-3" />
                <span>AI 驱动 · 价值分析 v2.0</span>
              </div>

              <!-- 主标题 -->
              <h2 class="text-7xl font-bold leading-[1.05] tracking-tight text-white drop-shadow-2xl">
                洞察网文 IP <br/>
                <span class="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-indigo-400">
                  价值密码与潜力
                </span>
              </h2>
              
              <!-- 描述 -->
              <p class="text-slate-300/80 text-lg leading-relaxed font-light max-w-lg">
                融合多维数据分析与机器学习模型，<br/>为内容投资决策提供精准的量化支撑。
              </p>

              <!-- 极简数据展示 -->
              <div class="flex items-center gap-8 pt-8">
                 <div>
                    <div class="text-4xl font-bold text-white mb-1 transition-opacity" :class="statsLoading ? 'opacity-50' : 'opacity-100'">
                      {{ loginStats.total_books.toLocaleString() }}
                    </div>
                    <div class="text-slate-500 text-sm font-medium">总入库书籍</div>
                 </div>
                 <div class="w-px h-10 bg-white/10"></div>
                 <div>
                    <div class="text-4xl font-bold text-white mb-1 transition-opacity" :class="statsLoading ? 'opacity-50' : 'opacity-100'">
                      {{ loginStats.total_tracking.toLocaleString() }}
                    </div>
                    <div class="text-slate-500 text-sm font-medium">实时追踪作品</div>
                 </div>
                 <div class="w-px h-10 bg-white/10"></div>
                 <div>
                    <div class="text-4xl font-bold text-white mb-1 transition-opacity" :class="statsLoading ? 'opacity-50' : 'opacity-100'">
                      {{ loginStats.dark_horse_count }}
                    </div>
                    <div class="text-slate-500 text-sm font-medium">潜力黑马</div>
                 </div>
                 <div class="w-px h-10 bg-white/10"></div>
                 <div>
                    <div class="text-4xl font-bold text-white mb-1 flex items-center gap-1 transition-opacity" :class="statsLoading ? 'opacity-50' : 'opacity-100'">
                      {{ loginStats.prediction_accuracy }}% <Zap class="w-5 h-5 text-amber-400" />
                    </div>
                    <div class="text-slate-500 text-sm font-medium">预测准确率</div>
                 </div>
              </div>

           </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center gap-6 text-slate-500 text-sm font-medium transition-opacity duration-1000 delay-500">
           <span>企业级安全加密</span>
           <span class="w-1 h-1 rounded-full bg-slate-700"></span>
           <span>SOC2 合规认证</span>
        </div>

      </div>
    </div>

    <!-- ============================================ -->
    <!--  右侧：极简表单区 (45%)                      -->
    <!-- ============================================ -->
    <div class="w-full lg:w-[45%] flex items-center justify-center p-8 bg-white relative">
      
      <div class="relative z-10 w-full max-w-[380px] transition-all duration-700 delay-200" 
           :class="ready ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'">
        
        <!-- Logo (Mobile only) -->
        <div class="lg:hidden flex justify-center mb-8">
           <div class="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white">
             <BookOpen class="w-6 h-6" />
           </div>
        </div>

        <!-- 标题 -->
        <div class="mb-10 text-center lg:text-left">
          <h2 class="text-4xl font-bold tracking-tight text-slate-900">
            {{ isLoginMode ? '欢迎回来' : '开始探索' }}
          </h2>
          <p class="text-slate-500 text-sm mt-3">
            {{ isLoginMode ? '登录以继续您的 IP 价值探索之旅' : '创建一个免费账户，开启 AI 驱动的情报分析' }}
          </p>
        </div>

        <!-- 错误提示 -->
         <Transition name="fade">
          <div v-if="errorMsg" class="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-100 text-rose-600 text-xs font-medium flex items-center gap-3">
             <div class="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></div>
             {{ errorMsg }}
          </div>
        </Transition>

        <!-- 表单 -->
        <form @submit.prevent="handleSubmit" class="space-y-5">
          
          <div class="space-y-1.5">
            <label class="text-xs font-bold text-slate-700 ml-1">用户名</label>
            <div class="relative group">
               <User class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300 group-focus-within:text-indigo-600 transition-colors" />
               <input v-model="form.username" type="text" placeholder="请输入用户名"
                      class="w-full h-12 pl-11 pr-4 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium text-sm hover:border-slate-300" />
            </div>
          </div>

          <Transition name="slide">
            <div v-if="!isLoginMode" class="space-y-1.5">
               <label class="text-xs font-bold text-slate-700 ml-1">电子邮箱</label>
               <div class="relative group">
                  <Mail class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300 group-focus-within:text-indigo-600 transition-colors" />
                  <input v-model="form.email" type="email" placeholder="name@company.com"
                         class="w-full h-12 pl-11 pr-4 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium text-sm hover:border-slate-300" />
               </div>
            </div>
          </Transition>

          <div class="space-y-1.5">
            <div class="flex justify-between items-center ml-1">
              <label class="text-xs font-bold text-slate-700">密码</label>
              <a v-if="isLoginMode" href="#" @click.prevent="showForgotModal = true" class="text-xs font-medium text-indigo-600 hover:text-indigo-700">忘记密码？</a>
            </div>
            <div class="relative group">
               <Lock class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300 group-focus-within:text-indigo-600 transition-colors" />
               <input v-model="form.password" :type="showPassword ? 'text' : 'password'" placeholder="••••••••"
                      class="w-full h-12 pl-11 pr-12 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium text-sm hover:border-slate-300" />
               <button type="button" @click="showPassword = !showPassword" class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-300 hover:text-slate-500 transition-colors">
                  <Eye v-if="!showPassword" class="w-4 h-4" />
                  <EyeOff v-else class="w-4 h-4" />
               </button>
            </div>
          </div>

          <Transition name="slide">
             <div v-if="!isLoginMode" class="space-y-1.5">
               <label class="text-xs font-bold text-slate-700 ml-1">确认密码</label>
               <div class="relative group">
                  <Lock class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300 group-focus-within:text-indigo-600 transition-colors" />
                  <input v-model="form.confirmPassword" :type="showPassword ? 'text' : 'password'" placeholder="••••••••"
                         class="w-full h-12 pl-11 pr-4 bg-white border border-slate-200 rounded-xl text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium text-sm hover:border-slate-300" />
               </div>
            </div>
          </Transition>

          <button type="submit" :disabled="loading"
                  class="w-full h-12 rounded-xl text-white font-semibold shadow-lg transition-all hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed mt-4 bg-[#4F46E5] hover:bg-[#4338CA] shadow-indigo-500/30">
              <span v-if="loading" class="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              <span v-else>{{ isLoginMode ? '登 录' : '创建账户' }}</span>
              <ArrowRight v-if="!loading" class="w-4 h-4" />
          </button>

        </form>

        <!-- Footer Switch -->
        <div class="text-center pt-8">
           <p class="text-sm text-slate-500">
             {{ isLoginMode ? "还没有账户？" : "已有账户？" }}
             <button @click="toggleMode" class="font-semibold text-indigo-600 hover:text-indigo-700 ml-1 transition-colors">
               {{ isLoginMode ? "免费注册" : "返回登录" }}
             </button>
           </p>
        </div>

      </div>

      <!-- 忘记密码弹窗 -->
      <Transition name="fade">
        <div v-if="showForgotModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40" @click.self="closeForgotModal">
          <div class="bg-white rounded-lg shadow-xl w-full max-w-sm mx-4">
            <!-- 头部 -->
            <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 class="font-semibold text-slate-800">重置密码</h3>
              <button @click="closeForgotModal" class="text-slate-400 hover:text-slate-600">
                <X class="w-4 h-4" />
              </button>
            </div>
            
            <!-- 内容 -->
            <div class="p-5 space-y-4">
              <!-- 成功提示 -->
              <div v-if="forgotSuccess" class="p-3 rounded bg-emerald-50 border border-emerald-100 text-emerald-600 text-sm">
                {{ forgotSuccess }}
              </div>
              
              <!-- 错误提示 -->
              <div v-if="forgotError" class="p-3 rounded bg-red-50 border border-red-100 text-red-500 text-sm">
                {{ forgotError }}
              </div>
              
              <!-- 第一步：输入邮箱 -->
              <div v-if="forgotStep === 1">
                <label class="block text-sm font-medium text-slate-700 mb-1">注册邮箱</label>
                <input v-model="forgotEmail" type="email" placeholder="your@email.com"
                       class="w-full h-10 px-3 bg-white border border-slate-200 rounded text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-400 text-sm" />
              </div>
              
              <!-- 第二步：输入验证码和新密码 -->
              <div v-else class="space-y-3">
                <div class="text-sm text-slate-500">
                  验证码已发送至 <span class="font-medium text-slate-700">{{ forgotEmail }}</span>
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">验证码</label>
                  <input v-model="forgotCode" type="text" placeholder="6位数字" maxlength="6"
                         class="w-full h-10 px-3 bg-white border border-slate-200 rounded text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-400 text-sm text-center tracking-widest" />
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">新密码</label>
                  <input v-model="forgotNewPassword" type="password" placeholder="至少6位字符"
                         class="w-full h-10 px-3 bg-white border border-slate-200 rounded text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-400 text-sm" />
                </div>
              </div>
            </div>
            
            <!-- 底部按钮 -->
            <div class="px-5 py-4 border-t border-slate-100 flex gap-3">
              <button @click="closeForgotModal" class="flex-1 h-9 rounded border border-slate-200 text-slate-600 text-sm hover:bg-slate-50">
                取消
              </button>
              <button @click="handleForgotPassword" :disabled="forgotLoading"
                      class="flex-1 h-9 rounded bg-slate-800 text-white text-sm hover:bg-slate-700 disabled:opacity-50 flex items-center justify-center gap-1">
                <span v-if="forgotLoading" class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                <span>{{ forgotStep === 1 ? '发送验证码' : '重置密码' }}</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>

    </div>
  </div>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active { transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); overflow: hidden; }
.slide-leave-active { transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1); overflow: hidden; }
.slide-enter-from { opacity: 0; max-height: 0; transform: translateY(-8px); }
.slide-leave-to { opacity: 0; max-height: 0; transform: translateY(-8px); }
.slide-enter-to, .slide-leave-from { max-height: 100px; opacity: 1; transform: translateY(0); }

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-down {
  animation: fadeInDown 0.8s ease-out forwards;
}
</style>
