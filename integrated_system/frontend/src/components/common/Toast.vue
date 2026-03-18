<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { X, AlertCircle, CheckCircle2, Info } from 'lucide-vue-next'

export interface ToastOptions {
  message: string
  type?: 'error' | 'success' | 'warning' | 'info'
  duration?: number
}

const toasts = ref<Array<{
  id: number
  message: string
  type: 'error' | 'success' | 'warning' | 'info'
  show: boolean
}>>([])

let toastId = 0
let timer: ReturnType<typeof setTimeout> | null = null

function showToast(options: ToastOptions) {
  const id = ++toastId
  const type = options.type || 'info'
  
  toasts.value.push({
    id,
    message: options.message,
    type,
    show: false
  })
  
  // 动画进入
  setTimeout(() => {
    const toast = toasts.value.find(t => t.id === id)
    if (toast) toast.show = true
  }, 10)
  
  // 自动关闭
  const duration = options.duration || 5000
  setTimeout(() => {
    removeToast(id)
  }, duration)
}

function removeToast(id: number) {
  const toast = toasts.value.find(t => t.id === id)
  if (toast) {
    toast.show = false
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 300)
  }
}

function closeToast(id: number) {
  removeToast(id)
}

// 导出全局方法
function showError(message: string, duration?: number) {
  showToast({ message, type: 'error', duration })
}

function showSuccess(message: string, duration?: number) {
  showToast({ message, type: 'success', duration })
}

function showWarning(message: string, duration?: number) {
  showToast({ message, type: 'warning', duration })
}

function showInfo(message: string, duration?: number) {
  showToast({ message, type: 'info', duration })
}

// 暴露给全局
if (typeof window !== 'undefined') {
  (window as any).$toast = {
    show: showToast,
    error: showError,
    success: showSuccess,
    warning: showWarning,
    info: showInfo
  }
}

const iconMap = {
  error: AlertCircle,
  success: CheckCircle2,
  warning: AlertCircle,
  info: Info
}

const styleMap = {
  error: 'bg-rose-50 border-rose-200 text-rose-700',
  success: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  warning: 'bg-amber-50 border-amber-200 text-amber-700',
  info: 'bg-indigo-50 border-indigo-200 text-indigo-700'
}

const iconColorMap = {
  error: 'text-rose-500',
  success: 'text-emerald-500',
  warning: 'text-amber-500',
  info: 'text-indigo-500'
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 px-5 py-4 rounded-xl shadow-lg border backdrop-blur-sm min-w-[320px] max-w-[480px] transition-all duration-300"
          :class="[styleMap[toast.type], toast.show ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0']"
        >
          <div class="flex-shrink-0 mt-0.5">
            <component :is="iconMap[toast.type]" class="w-5 h-5" :class="iconColorMap[toast.type]" />
          </div>
          <div class="flex-1 text-sm font-medium leading-relaxed">
            {{ toast.message }}
          </div>
          <button
            @click="closeToast(toast.id)"
            class="flex-shrink-0 p-1 rounded-full hover:bg-black/5 transition-colors"
            :class="iconColorMap[toast.type]"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
