<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import { MessageSquare, Send, Clock, User, AlertCircle, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-vue-next'

const API_BASE = 'http://localhost:5000/api'

// 状态
const messages = ref<any[]>([])
const newMessage = ref('')
const loading = ref(false)
const submitting = ref(false)
const unreadCount = ref(0)
const expandedMessages = ref<Set<number>>(new Set())
const errorMessage = ref('')
let refreshInterval: number | null = null

// 获取留言列表
const fetchMessages = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/messages/list`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    if (data.messages) {
      messages.value = data.messages
    }
  } catch (e) {
    console.error('获取留言失败:', e)
  } finally {
    if (!silent) loading.value = false
  }
}

// 获取未读数量
const fetchUnreadCount = async () => {
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/messages/unread_count`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    unreadCount.value = data.unread_count || 0
  } catch (e) {
    console.error('获取未读数量失败:', e)
  }
}

// 发送留言
const sendMessage = async () => {
  if (!newMessage.value.trim()) return
  
  submitting.value = true
  errorMessage.value = ''
  try {
    const token = localStorage.getItem('auth_token')
    console.log('Sending message to:', `${API_BASE}/messages/send`)
    console.log('Token:', token?.substring(0, 20) + '...')
    
    const res = await fetch(`${API_BASE}/messages/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ content: newMessage.value })
    })
    
    console.log('Response status:', res.status)
    const text = await res.text()
    console.log('Response body:', text)
    
    let data
    try {
      data = JSON.parse(text)
    } catch {
      data = { error: 'Invalid JSON response: ' + text.substring(0, 100) }
    }
    
    if (data.success) {
      newMessage.value = ''
      await fetchMessages()
    } else {
      errorMessage.value = data.error || `发送失败 (HTTP ${res.status})`
    }
  } catch (e: any) {
    console.error('发送留言失败:', e)
    errorMessage.value = `网络错误: ${e.message || '请检查后端服务是否运行'}`
  } finally {
    submitting.value = false
  }
}

// 标记为已读
const markAsRead = async (replyId: number) => {
  try {
    const token = localStorage.getItem('auth_token')
    await fetch(`${API_BASE}/messages/mark_read/${replyId}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    await fetchUnreadCount()
    await fetchMessages()
  } catch (e) {
    console.error('标记已读失败:', e)
  }
}

// 展开/收起回复
const toggleExpand = (messageId: number) => {
  if (expandedMessages.value.has(messageId)) {
    expandedMessages.value.delete(messageId)
  } else {
    expandedMessages.value.add(messageId)
    // 如果有未读的管理员回复，标记为已读
    const msg = messages.value.find(m => m.id === messageId)
    if (msg && msg.replies) {
      msg.replies.forEach((reply: any) => {
        if (reply.is_admin_reply && !reply.is_read) {
          markAsRead(reply.id)
        }
      })
    }
  }
}

// 格式化时间
const formatTime = (time: string) => {
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  fetchMessages()
  fetchUnreadCount()
  // 每10秒静默刷新一次
  refreshInterval = window.setInterval(() => {
    fetchMessages(true)
    fetchUnreadCount()
  }, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <EditorialLayout>
    <div class="min-h-screen pt-8 px-4 pb-24 max-w-4xl mx-auto">
      <!-- 页面标题 -->
      <div class="flex items-center gap-3 mb-8">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <MessageSquare class="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 class="text-3xl font-serif font-bold text-slate-900 tracking-tight">留言板</h1>
          <p class="text-slate-500 text-sm mt-1">
            与管理员沟通交流
            <span v-if="unreadCount > 0" class="ml-2 px-2 py-0.5 bg-red-100 text-red-600 rounded-full text-xs font-medium">
              {{ unreadCount }} 条未读
            </span>
          </p>
        </div>
      </div>

      <!-- 发送留言区域 -->
      <div class="bg-white/80 backdrop-blur-xl rounded-2xl p-6 shadow-sm border border-slate-200/60 mb-8">
        <!-- 错误提示 -->
        <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
          {{ errorMessage }}
        </div>
        
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center flex-shrink-0">
            <User class="w-5 h-5 text-slate-500" />
          </div>
          <div class="flex-1">
            <textarea
              v-model="newMessage"
              placeholder="请输入您的问题或建议...（Token有限制时，可通过此方式沟通）"
              class="w-full h-32 p-4 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-none transition-all"
              maxlength="1000"
            />
            <div class="flex items-center justify-between mt-3">
              <span class="text-xs text-slate-400">{{ newMessage.length }}/1000</span>
              <button
                @click="sendMessage"
                :disabled="!newMessage.trim() || submitting"
                class="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <Send class="w-4 h-4" />
                {{ submitting ? '发送中...' : '发送留言' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 留言列表 -->
      <div class="space-y-4">
        <div v-if="loading" class="flex items-center justify-center py-12">
          <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" />
        </div>

        <div v-else-if="messages.length === 0" class="text-center py-16">
          <div class="w-20 h-20 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <MessageSquare class="w-10 h-10 text-slate-300" />
          </div>
          <p class="text-slate-500">暂无留言</p>
          <p class="text-slate-400 text-sm mt-1">有问题或建议？发送第一条留言吧！</p>
        </div>

        <div
          v-for="message in messages"
          :key="message.id"
          class="bg-white/80 backdrop-blur-xl rounded-2xl p-5 shadow-sm border border-slate-200/60 transition-all hover:shadow-md"
          :class="{ 'ring-2 ring-indigo-500/20': message.reply_count > 0 && expandedMessages.has(message.id) }"
        >
          <!-- 留言头部 -->
          <div class="flex items-start gap-4">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center flex-shrink-0">
              <User class="w-5 h-5 text-indigo-600" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-1">
                <span class="font-medium text-slate-900">{{ message.username }}</span>
                <span class="text-xs text-slate-400 flex items-center gap-1">
                  <Clock class="w-3 h-3" />
                  {{ formatTime(message.created_at) }}
                </span>
              </div>
              <p class="text-slate-700 leading-relaxed whitespace-pre-wrap">{{ message.content }}</p>
              
              <!-- 展开回复按钮 -->
              <div v-if="message.reply_count > 0" class="mt-3">
                <button
                  @click="toggleExpand(message.id)"
                  class="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  <CheckCircle2 class="w-4 h-4" />
                  {{ message.reply_count }} 条回复
                  <ChevronDown v-if="!expandedMessages.has(message.id)" class="w-4 h-4" />
                  <ChevronUp v-else class="w-4 h-4" />
                  <span
                    v-if="message.unread_reply_count > 0 && !expandedMessages.has(message.id)"
                    class="ml-1 px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-xs"
                  >
                    {{ message.unread_reply_count }} 未读
                  </span>
                </button>
              </div>
              <div v-else class="mt-3 flex items-center gap-1 text-sm text-slate-400">
                <AlertCircle class="w-4 h-4" />
                等待管理员回复
              </div>
            </div>
          </div>

          <!-- 回复列表 -->
          <div v-if="expandedMessages.has(message.id) && message.replies?.length > 0" class="mt-4 pl-14 space-y-3">
            <div
              v-for="reply in message.replies"
              :key="reply.id"
              class="flex items-start gap-3 p-4 rounded-xl"
              :class="reply.is_admin_reply ? 'bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-100' : 'bg-slate-50'"
            >
              <div
                class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                :class="reply.is_admin_reply ? 'bg-gradient-to-br from-amber-400 to-orange-500' : 'bg-slate-200'"
              >
                <User class="w-4 h-4 text-white" v-if="reply.is_admin_reply" />
                <User class="w-4 h-4 text-slate-500" v-else />
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <span class="font-medium text-sm" :class="reply.is_admin_reply ? 'text-amber-700' : 'text-slate-700'">
                    {{ reply.is_admin_reply ? (reply.admin_name || '管理员') : reply.username }}
                  </span>
                  <span v-if="reply.is_admin_reply" class="px-1.5 py-0.5 bg-amber-100 text-amber-600 rounded text-xs font-medium">
                    官方
                  </span>
                  <span class="text-xs text-slate-400">{{ formatTime(reply.created_at) }}</span>
                </div>
                <p class="text-slate-700 text-sm leading-relaxed">{{ reply.content }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </EditorialLayout>
</template>
