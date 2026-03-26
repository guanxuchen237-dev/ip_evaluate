<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import AdminSidebar from '@/components/layout/AdminSidebar.vue'
import { 
  MessageSquare, Send, Clock, User, CheckCircle2, 
  AlertCircle, Search, Trash2, ChevronDown, ChevronUp,
  Filter, RefreshCw, Bell
} from 'lucide-vue-next'

const API_BASE = 'http://localhost:5000/api'

// 状态
const messages = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const stats = ref({ total: 0, today: 0, unreplied: 0, unread: 0 })
const filterStatus = ref('all') // all, unread, replied, unreplied
const searchQuery = ref('')
const expandedMessages = ref<Set<number>>(new Set())
const replyContent = ref<{ [key: number]: string }>({})
let refreshInterval: number | null = null

// 统计
const fetchStats = async () => {
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/messages/admin/stats`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    if (!data.error) {
      stats.value = data
    }
  } catch (e) {
    console.error('获取统计失败:', e)
  }
}

// 获取所有留言
const fetchMessages = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const params = new URLSearchParams({
      status: filterStatus.value,
      page: '1',
      page_size: '50'
    })
    const res = await fetch(`${API_BASE}/messages/admin/list?${params}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    if (data.messages) {
      messages.value = data.messages
    }
  } catch (e) {
    console.error('获取留言失败:', e)
  } finally {
    loading.value = false
  }
}

// 过滤后的留言
const filteredMessages = computed(() => {
  let result = messages.value
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(m => 
      m.content.toLowerCase().includes(query) ||
      m.username.toLowerCase().includes(query) ||
      m.user_email?.toLowerCase().includes(query)
    )
  }
  return result
})

// 回复留言
const replyMessage = async (messageId: number) => {
  const content = replyContent.value[messageId]?.trim()
  if (!content) return
  
  submitting.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/messages/admin/reply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ parent_id: messageId, content })
    })
    const data = await res.json()
    if (data.success) {
      replyContent.value[messageId] = ''
      await fetchMessages()
      await fetchStats()
    }
  } catch (e) {
    console.error('回复失败:', e)
  } finally {
    submitting.value = false
  }
}

// 删除留言
const deleteMessage = async (messageId: number) => {
  if (!confirm('确定要删除这条留言吗？相关的回复也会被删除。')) return
  
  try {
    const token = localStorage.getItem('auth_token')
    await fetch(`${API_BASE}/messages/admin/delete/${messageId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    await fetchMessages()
    await fetchStats()
  } catch (e) {
    console.error('删除失败:', e)
  }
}

// 展开/收起
const toggleExpand = (messageId: number) => {
  if (expandedMessages.value.has(messageId)) {
    expandedMessages.value.delete(messageId)
  } else {
    expandedMessages.value.add(messageId)
  }
}

// 格式化时间
const formatTime = (time: string) => {
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 相对时间
const relativeTime = (time: string) => {
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return formatTime(time)
}

onMounted(() => {
  fetchStats()
  fetchMessages()
  // 每10秒自动刷新统计数据
  refreshInterval = window.setInterval(() => {
    fetchStats()
  }, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

// 菜单项
const adminDockItems = [
  { title: "总览", titleEn: "Overview", url: "/admin?tab=overview", icon: 'LayoutDashboard' },
  { title: "用户管理", titleEn: "Users", url: "/admin?tab=users", icon: 'Users' },
  { title: "书籍管理", titleEn: "Books", url: "/admin?tab=books", icon: 'Library' },
  { title: "留言管理", titleEn: "Messages", url: "/admin/messages", icon: 'MessageSquare' },
  { title: "黑名单", titleEn: "Blacklist", url: "/admin/blacklist", icon: 'Ban' },
  { title: "设置", titleEn: "Settings", url: "/admin?tab=settings", icon: 'Settings' },
]
</script>

<template>
  <div class="flex min-h-screen bg-slate-50">
    <!-- 侧边栏 -->
    <AdminSidebar :items="adminDockItems" />
    
    <!-- 主内容区 -->
    <div class="flex-1 ml-64">
      <div class="p-8 max-w-7xl mx-auto">
        <!-- 页面标题 -->
        <div class="flex items-center justify-between mb-8">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <MessageSquare class="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 class="text-3xl font-serif font-bold text-slate-900 tracking-tight">留言管理</h1>
              <p class="text-slate-500 text-sm mt-1">管理用户留言与反馈</p>
            </div>
          </div>
          <button 
            @click="fetchMessages"
            class="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 transition-all"
          >
            <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': loading }" />
            刷新
          </button>
        </div>

        <!-- 统计卡片 -->
        <div class="grid grid-cols-4 gap-4 mb-8">
          <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center">
                <MessageSquare class="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <p class="text-2xl font-bold text-slate-900">{{ stats.total }}</p>
                <p class="text-xs text-slate-500">总留言数</p>
              </div>
            </div>
          </div>
          <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center">
                <Clock class="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p class="text-2xl font-bold text-slate-900">{{ stats.today }}</p>
                <p class="text-xs text-slate-500">今日新增</p>
              </div>
            </div>
          </div>
          <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center">
                <AlertCircle class="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p class="text-2xl font-bold text-slate-900">{{ stats.unreplied }}</p>
                <p class="text-xs text-slate-500">待回复</p>
              </div>
            </div>
          </div>
          <div class="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center">
                <Bell class="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p class="text-2xl font-bold text-slate-900">{{ stats.unread }}</p>
                <p class="text-xs text-slate-500">用户未读</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 筛选和搜索 -->
        <div class="flex items-center gap-4 mb-6">
          <div class="flex items-center gap-2 bg-white rounded-xl p-1 border border-slate-200">
            <button
              v-for="status in ['all', 'unreplied', 'replied', 'unread']"
              :key="status"
              @click="filterStatus = status; fetchMessages()"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-all"
              :class="filterStatus === status ? 'bg-indigo-500 text-white' : 'text-slate-600 hover:bg-slate-100'"
            >
              {{ { all: '全部', unreplied: '待回复', replied: '已回复', unread: '未读' }[status] }}
            </button>
          </div>
          <div class="flex-1 relative">
            <Search class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              v-model="searchQuery"
              placeholder="搜索留言内容、用户名..."
              class="w-full pl-11 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>
        </div>

        <!-- 留言列表 -->
        <div v-if="loading" class="flex items-center justify-center py-16">
          <div class="w-10 h-10 border-4 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" />
        </div>

        <div v-else-if="filteredMessages.length === 0" class="text-center py-16 bg-white rounded-2xl border border-slate-200">
          <MessageSquare class="w-16 h-16 text-slate-200 mx-auto mb-4" />
          <p class="text-slate-500">暂无留言</p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="message in filteredMessages"
            :key="message.id"
            class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 transition-all"
            :class="{ 
              'ring-2 ring-amber-500/30': message.unread_reply_count > 0,
              'ring-2 ring-indigo-500/20': !message.reply_count 
            }"
          >
            <!-- 留言头部 -->
            <div class="flex items-start justify-between mb-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
                  <User class="w-5 h-5 text-indigo-600" />
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-slate-900">{{ message.username }}</span>
                    <span class="text-xs text-slate-400">{{ message.user_email }}</span>
                  </div>
                  <div class="flex items-center gap-2 text-xs text-slate-400">
                    <Clock class="w-3 h-3" />
                    {{ formatTime(message.created_at) }}
                    <span class="text-slate-300">|</span>
                    {{ relativeTime(message.created_at) }}
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span
                  v-if="message.reply_count === 0"
                  class="px-2 py-1 bg-amber-100 text-amber-600 rounded-lg text-xs font-medium"
                >
                  待回复
                </span>
                <span
                  v-else-if="message.unread_reply_count > 0"
                  class="px-2 py-1 bg-red-100 text-red-600 rounded-lg text-xs font-medium"
                >
                  {{ message.unread_reply_count }} 未读
                </span>
                <span
                  v-else
                  class="px-2 py-1 bg-emerald-100 text-emerald-600 rounded-lg text-xs font-medium"
                >
                  已回复
                </span>
                <button
                  @click="deleteMessage(message.id)"
                  class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                  title="删除"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- 留言内容 -->
            <p class="text-slate-700 leading-relaxed mb-4 whitespace-pre-wrap">{{ message.content }}</p>

            <!-- 展开/收起回复 -->
            <div v-if="message.reply_count > 0" class="mb-4">
              <button
                @click="toggleExpand(message.id)"
                class="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
              >
                <CheckCircle2 class="w-4 h-4" />
                {{ message.reply_count }} 条回复
                <ChevronDown v-if="!expandedMessages.has(message.id)" class="w-4 h-4" />
                <ChevronUp v-else class="w-4 h-4" />
              </button>
            </div>

            <!-- 回复列表 -->
            <div v-if="expandedMessages.has(message.id) && message.replies?.length > 0" class="mb-4 space-y-3">
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
                  <User class="w-4 h-4 text-white" />
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
                    <span v-if="reply.is_admin_reply && !reply.is_read" class="px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-xs">
                      用户未读
                    </span>
                  </div>
                  <p class="text-slate-700 text-sm">{{ reply.content }}</p>
                </div>
              </div>
            </div>

            <!-- 回复输入框 -->
            <div class="flex items-start gap-3 pt-4 border-t border-slate-100">
              <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0">
                <User class="w-4 h-4 text-white" />
              </div>
              <div class="flex-1">
                <textarea
                  v-model="replyContent[message.id]"
                  placeholder="输入回复内容..."
                  class="w-full h-24 p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  maxlength="1000"
                />
                <div class="flex items-center justify-between mt-2">
                  <span class="text-xs text-slate-400">
                    {{ (replyContent[message.id] || '').length }}/1000
                  </span>
                  <button
                    @click="replyMessage(message.id)"
                    :disabled="!replyContent[message.id]?.trim() || submitting"
                    class="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg text-sm font-medium hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    <Send class="w-4 h-4" />
                    {{ submitting ? '发送中...' : '回复' }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
