<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
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

// 展平所有消息（用于微信聊天样式）
const allMessages = computed(() => {
  const result: any[] = []
  messages.value.forEach(msg => {
    // 用户留言
    result.push({
      ...msg,
      isMe: true,
      type: 'message'
    })
    // 管理员回复
    if (msg.replies?.length > 0) {
      msg.replies.forEach((reply: any) => {
        result.push({
          ...reply,
          isMe: false,
          type: 'reply',
          parentId: msg.id
        })
      })
    }
  })
  // 按时间排序
  return result.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
})
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

      <!-- 微信聊天式留言区域 -->
      <div class="bg-[#f5f5f5] rounded-2xl overflow-hidden shadow-sm border border-slate-200/60 mb-8">
        <!-- 聊天消息区域 -->
        <div class="h-[500px] overflow-y-auto p-4 space-y-3" ref="chatContainer">
          <div v-if="loading" class="flex items-center justify-center h-full">
            <div class="w-8 h-8 border-4 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" />
          </div>
          
          <div v-else-if="allMessages.length === 0" class="flex flex-col items-center justify-center h-full text-center">
            <div class="w-20 h-20 rounded-full bg-slate-200 flex items-center justify-center mb-4">
              <MessageSquare class="w-10 h-10 text-slate-400" />
            </div>
            <p class="text-slate-500">暂无消息</p>
            <p class="text-slate-400 text-sm mt-1">有问题或建议？发送第一条消息吧！</p>
          </div>

          <div
            v-for="(item, index) in allMessages"
            :key="item.id + '-' + index"
            class="flex"
            :class="item.isMe ? 'flex-row-reverse' : 'flex-row'"
          >
            <!-- 头像 -->
            <div 
              class="w-10 h-10 rounded-lg flex-shrink-0 flex items-center justify-center"
              :class="item.isMe ? 'bg-gradient-to-br from-indigo-400 to-purple-500 ml-3' : 'bg-gradient-to-br from-amber-400 to-orange-500 mr-3'"
            >
              <User class="w-5 h-5 text-white" />
            </div>
            
            <!-- 消息内容 -->
            <div class="max-w-[70%]">
              <!-- 时间和标签 -->
              <div 
                class="flex items-center gap-2 mb-1 text-xs"
                :class="item.isMe ? 'justify-end' : ''"
              >
                <span class="text-slate-500">{{ item.isMe ? '我' : (item.admin_name || '管理员') }}</span>
                <span v-if="!item.isMe" class="px-1.5 py-0.5 bg-amber-100 text-amber-600 rounded text-[10px] font-medium">官方</span>
                <span class="text-slate-400">{{ formatTime(item.created_at) }}</span>
              </div>
              
              <!-- 气泡 -->
              <div 
                class="px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap"
                :class="item.isMe 
                  ? 'bg-[#95ec69] text-slate-800 rounded-tr-none' 
                  : 'bg-white border border-slate-200 rounded-tl-none'"
              >
                {{ item.content }}
              </div>
            </div>
          </div>
        </div>

        <!-- 底部输入框 -->
        <div class="bg-white border-t border-slate-200 p-4">
          <div class="flex items-end gap-3">
            <textarea
              v-model="newMessage"
              placeholder="输入消息..."
              class="flex-1 h-12 max-h-24 p-3 bg-slate-100 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white transition-all"
              maxlength="1000"
              @keydown.enter.prevent="sendMessage"
            />
            <button
              @click="sendMessage"
              :disabled="!newMessage.trim() || submitting"
              class="px-6 py-3 bg-[#07c160] text-white rounded-xl text-sm font-medium hover:bg-[#06ad56] disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
            >
              <Send class="w-4 h-4" />
              {{ submitting ? '发送中' : '发送' }}
            </button>
          </div>
          <div class="flex justify-between items-center mt-2">
            <span class="text-xs text-slate-400">按 Enter 发送</span>
            <span class="text-xs text-slate-400">{{ newMessage.length }}/1000</span>
          </div>
          <!-- 错误提示 -->
          <div v-if="errorMessage" class="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
            {{ errorMessage }}
          </div>
        </div>
      </div>

    </div>
  </EditorialLayout>
</template>
