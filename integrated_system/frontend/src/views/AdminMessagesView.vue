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
const submittingReply = ref<{ [key: number]: boolean }>({})
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

// 按用户分组的留言
const groupedByUser = computed(() => {
  const groups: { [key: number]: { user: any, messages: any[], unreadCount: number } } = {}
  
  messages.value.forEach(msg => {
    if (!groups[msg.user_id]) {
      groups[msg.user_id] = {
        user: {
          id: msg.user_id,
          username: msg.username,
          email: msg.user_email || ''
        },
        messages: [],
        unreadCount: 0
      }
    }
    groups[msg.user_id]!.messages.push(msg)
    // 计算该用户未读的回复数
    if (msg.unread_reply_count > 0) {
      groups[msg.user_id]!.unreadCount += msg.unread_reply_count
    }
  })
  
  // 转换为数组并按最后消息时间排序
  return Object.values(groups).sort((a, b) => {
    const aLast = a.messages[a.messages.length - 1]?.created_at || ''
    const bLast = b.messages[b.messages.length - 1]?.created_at || ''
    return new Date(bLast).getTime() - new Date(aLast).getTime()
  })
})

// 过滤后的用户列表
const filteredUsers = computed(() => {
  if (!searchQuery.value.trim()) return groupedByUser.value
  const query = searchQuery.value.toLowerCase()
  return groupedByUser.value.filter(u => 
    u.user.username.toLowerCase().includes(query) ||
    u.user.email?.toLowerCase().includes(query) ||
    u.messages.some(m => m.content.toLowerCase().includes(query))
  )
})

// 当前选中的用户
const selectedUser = ref<number | null>(null)
const currentReply = ref('')

// 回复用户
const replyUser = async () => {
  if (!selectedUser.value || !currentReply.value.trim()) return
  
  const userMessages = groupedByUser.value.find(u => u.user.id === selectedUser.value)?.messages
  if (!userMessages || userMessages.length === 0) return
  
  // 回复最后一条留言
  const lastMessage = userMessages[userMessages.length - 1]
  
  submittingReply.value[selectedUser.value] = true
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/messages/admin/reply`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ parent_id: lastMessage.id, content: currentReply.value })
    })
    const data = await res.json()
    if (data.success) {
      currentReply.value = ''
      await fetchMessages()
      await fetchStats()
    }
  } catch (e) {
    console.error('回复失败:', e)
  } finally {
    if (selectedUser.value) {
      submittingReply.value[selectedUser.value] = false
    }
  }
}

// 回复单个留言
const replyMessage = async (messageId: number) => {
  const content = replyContent.value[messageId]?.trim()
  if (!content) return
  
  submittingReply.value[messageId] = true
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
    submittingReply.value[messageId] = false
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

// 展平消息列表（用于微信聊天样式）- 按时间正序排列
const flattenMessages = (messages: any[]) => {
  const result: any[] = []
  // 先按时间正序排序消息（旧的在前面）
  const sortedMessages = [...messages].sort((a, b) => 
    new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  )
  sortedMessages.forEach(msg => {
    // 用户留言
    result.push({
      ...msg,
      isMe: false  // 用户消息，管理员视角是"对方"
    })
    // 管理员回复
    if (msg.replies?.length > 0) {
      // 回复也按时间排序
      const sortedReplies = [...msg.replies].sort((a, b) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      )
      sortedReplies.forEach((reply: any) => {
        result.push({
          ...reply,
          isMe: true  // 管理员回复，是"我自己"
        })
      })
    }
  })
  return result
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
              placeholder="搜索用户或留言内容..."
              class="w-full pl-11 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="flex items-center justify-center py-16">
          <div class="w-10 h-10 border-4 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" />
        </div>

        <!-- 空状态 -->
        <div v-else-if="filteredUsers.length === 0" class="text-center py-16 bg-white rounded-2xl border border-slate-200">
          <MessageSquare class="w-16 h-16 text-slate-200 mx-auto mb-4" />
          <p class="text-slate-500">暂无留言</p>
        </div>

        <!-- 用户对话框列表 -->
        <div v-else class="space-y-6">
          <div
            v-for="userGroup in filteredUsers"
            :key="userGroup.user.id"
            class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden"
            :class="{ 'ring-2 ring-indigo-500/20': selectedUser === userGroup.user.id }"
          >
            <!-- 用户头部 -->
            <div 
              class="p-4 bg-gradient-to-r from-slate-50 to-white border-b border-slate-100 cursor-pointer flex items-center justify-between"
              @click="selectedUser = selectedUser === userGroup.user.id ? null : userGroup.user.id"
            >
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
                  <User class="w-6 h-6 text-indigo-600" />
                </div>
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-slate-900">{{ userGroup.user.username }}</span>
                    <span class="text-xs text-slate-400">{{ userGroup.user.email }}</span>
                  </div>
                  <div class="flex items-center gap-2 text-xs text-slate-500">
                    <span>{{ userGroup.messages.length }} 条留言</span>
                    <span class="text-slate-300">|</span>
                    <span>最后活跃: {{ relativeTime(userGroup.messages[userGroup.messages.length - 1]?.created_at) }}</span>
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span
                  v-if="userGroup.messages.some(m => m.reply_count === 0)"
                  class="px-2 py-1 bg-amber-100 text-amber-600 rounded-lg text-xs font-medium"
                >
                  待回复
                </span>
                <span
                  v-else-if="userGroup.unreadCount > 0"
                  class="px-2 py-1 bg-red-100 text-red-600 rounded-lg text-xs font-medium"
                >
                  {{ userGroup.unreadCount }} 未读
                </span>
                <span
                  v-else
                  class="px-2 py-1 bg-emerald-100 text-emerald-600 rounded-lg text-xs font-medium"
                >
                  已回复
                </span>
                <ChevronDown 
                  class="w-5 h-5 text-slate-400 transition-transform" 
                  :class="{ 'rotate-180': selectedUser === userGroup.user.id }"
                />
              </div>
            </div>

            <!-- 展开的微信聊天式对话内容 -->
            <div v-if="selectedUser === userGroup.user.id" class="bg-[#f5f5f5]">
              <!-- 聊天消息区域 -->
              <div class="h-[400px] overflow-y-auto p-4 space-y-3">
                <div
                  v-for="(item, index) in flattenMessages(userGroup.messages)"
                  :key="item.id + '-' + index"
                  class="flex"
                  :class="item.isMe ? 'flex-row-reverse' : 'flex-row'"
                >
                  <!-- 头像 -->
                  <div 
                    class="w-10 h-10 rounded-lg flex-shrink-0 flex items-center justify-center"
                    :class="item.isMe ? 'bg-gradient-to-br from-amber-400 to-orange-500 ml-3' : 'bg-gradient-to-br from-indigo-400 to-purple-500 mr-3'"
                  >
                    <User class="w-5 h-5 text-white" />
                  </div>
                  
                  <!-- 消息内容 -->
                  <div class="max-w-[70%]">
                    <!-- 用户名和时间 -->
                    <div 
                      class="flex items-center gap-2 mb-1 text-xs"
                      :class="item.isMe ? 'justify-end' : ''"
                    >
                      <span class="text-slate-500">{{ item.isMe ? (item.admin_name || '我') : item.username }}</span>
                      <span class="text-slate-400">{{ formatTime(item.created_at) }}</span>
                      <span v-if="item.isMe && !item.is_read" class="px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-[10px]">未读</span>
                    </div>
                    
                    <!-- 气泡 -->
                    <div 
                      class="px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap relative"
                      :class="item.isMe 
                        ? 'bg-[#95ec69] text-slate-800 rounded-tr-none' 
                        : 'bg-white border border-slate-200 rounded-tl-none'"
                    >
                      {{ item.content }}
                      <!-- 删除按钮 -->
                      <button
                        v-if="!item.isMe"
                        @click="deleteMessage(item.id)"
                        class="absolute -left-6 top-1/2 -translate-y-1/2 p-1 text-slate-300 hover:text-red-500 transition-all opacity-0 group-hover:opacity-100"
                        title="删除"
                      >
                        <Trash2 class="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 底部输入框 -->
              <div class="bg-white border-t border-slate-200 p-3">
                <div class="flex items-end gap-3">
                  <textarea
                    v-model="currentReply"
                    placeholder="输入消息..."
                    class="flex-1 h-12 max-h-24 p-3 bg-slate-100 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white transition-all"
                    maxlength="1000"
                    @keydown.enter.prevent="replyUser()"
                  />
                  <button
                    @click="replyUser()"
                    :disabled="!currentReply.trim() || submittingReply[userGroup.user.id]"
                    class="px-6 py-3 bg-[#07c160] text-white rounded-xl text-sm font-medium hover:bg-[#06ad56] disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                  >
                    <Send class="w-4 h-4" />
                    {{ submittingReply[userGroup.user.id] ? '发送中' : '发送' }}
                  </button>
                </div>
                <div class="flex justify-between items-center mt-2">
                  <span class="text-xs text-slate-400">按 Enter 发送</span>
                  <span class="text-xs text-slate-400">{{ currentReply.length }}/1000</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
