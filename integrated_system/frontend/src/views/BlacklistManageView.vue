<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import AdminSidebar from '@/components/layout/AdminSidebar.vue'
import {
  Shield, LogOut, Search, Filter, RefreshCw, ChevronLeft, ChevronRight,
  Ban, CheckCircle, AlertTriangle, BookOpen, User, Calendar,
  ExternalLink, RotateCcw, Trash2, Eye
} from 'lucide-vue-next'

const router = useRouter()
const { user, logout } = useAuth()

const API_BASE = 'http://localhost:5000/api'

// 黑名单数据
const blacklist = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const totalPages = ref(0)

// 筛选状态
const filterStatus = ref<'all' | 'active' | 'removed'>('active')
const searchQuery = ref('')

// 确认对话框
const confirmDialog = ref({
  show: false,
  title: '',
  message: '',
  type: 'info' as 'info' | 'warning' | 'danger',
  confirmText: '确定',
  cancelText: '取消',
  onConfirm: () => {},
  onCancel: () => {}
})

// 详情弹窗
const detailModal = ref({
  show: false,
  item: null as any
})

// 获取黑名单列表
async function fetchBlacklist() {
  loading.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const params = new URLSearchParams()
    params.append('page', page.value.toString())
    params.append('per_page', pageSize.value.toString())
    params.append('status', filterStatus.value === 'all' ? 'all' : filterStatus.value)
    if (searchQuery.value.trim()) {
      params.append('search', searchQuery.value.trim())
    }
    
    console.log('Fetching blacklist with status:', filterStatus.value)
    
    const res = await fetch(`${API_BASE}/admin/blacklist/list?${params}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    if (res.ok) {
      const data = await res.json()
      console.log('Blacklist API response:', data)
      blacklist.value = data.items || []
      total.value = data.total || 0
      totalPages.value = data.total_pages || 0
    } else {
      const err = await res.text()
      console.error('获取黑名单失败:', err)
    }
  } catch (e) {
    console.error('获取黑名单失败:', e)
  } finally {
    loading.value = false
  }
}

// 搜索防抖
let searchTimer: any = null
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    fetchBlacklist()
  }, 400)
}

// 筛选切换
function onFilterChange() {
  page.value = 1
  fetchBlacklist()
}

// 分页导航
function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  fetchBlacklist()
}

// 显示确认对话框
function showConfirmDialog(options: {
  title: string,
  message: string,
  type?: 'info' | 'warning' | 'danger',
  confirmText?: string,
  cancelText?: string,
  onConfirm: () => void,
  onCancel?: () => void
}) {
  confirmDialog.value = {
    show: true,
    title: options.title,
    message: options.message,
    type: options.type || 'info',
    confirmText: options.confirmText || '确定',
    cancelText: options.cancelText || '取消',
    onConfirm: options.onConfirm,
    onCancel: options.onCancel || (() => {})
  }
}

function closeConfirmDialog() {
  confirmDialog.value.show = false
}

// 恢复书籍（移出黑名单）
function showRestoreDialog(item: any) {
  showConfirmDialog({
    title: '恢复书籍',
    message: `确定要将《${item.title}》移出黑名单并恢复上架吗？\n\n下架原因：${item.reason || '无'}`,
    type: 'warning',
    confirmText: '确认恢复',
    cancelText: '取消',
    onConfirm: () => doRestore(item),
    onCancel: () => closeConfirmDialog()
  })
}

async function doRestore(item: any) {
  closeConfirmDialog()
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/admin/whitelist`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        novel_id: item.novel_id,
        title: item.title,
        reason: '管理员手动恢复'
      })
    })
    
    if (res.ok) {
      showConfirmDialog({
        title: '恢复成功',
        message: `《${item.title}》已成功移出黑名单，恢复上架。`,
        type: 'info',
        confirmText: '我知道了',
        cancelText: '',
        onConfirm: () => {
          closeConfirmDialog()
          fetchBlacklist()
        }
      })
    } else {
      const data = await res.json()
      showConfirmDialog({
        title: '恢复失败',
        message: data.error || '操作失败，请重试',
        type: 'danger',
        confirmText: '我知道了',
        cancelText: '',
        onConfirm: () => closeConfirmDialog()
      })
    }
  } catch (e) {
    showConfirmDialog({
      title: '恢复失败',
      message: '网络错误，请检查连接',
      type: 'danger',
      confirmText: '我知道了',
      cancelText: '',
      onConfirm: () => closeConfirmDialog()
    })
  }
}

// 查看详情
function showDetail(item: any) {
  detailModal.value = { show: true, item }
}

function closeDetail() {
  detailModal.value.show = false
  detailModal.value.item = null
}

// 从详情弹窗恢复书籍
function restoreFromDetail() {
  const item = detailModal.value.item
  if (!item || item.status !== 'active') return
  closeDetail()
  // 延迟一下确保弹窗关闭后再显示确认对话框
  setTimeout(() => {
    showRestoreDialog(item)
  }, 50)
}

// 格式化日期
function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 状态标签样式
function statusStyle(status: string) {
  if (status === 'active') {
    return 'bg-rose-50 text-rose-600 border-rose-200'
  }
  return 'bg-emerald-50 text-emerald-600 border-emerald-200'
}

function statusLabel(status: string) {
  return status === 'active' ? '已下架' : '已恢复'
}

// 平台显示名
function platformLabel(p: string) {
  if (p === '起点' || p === 'Qidian') return '起点'
  if (p === '纵横' || p === 'Zongheng') return '纵横'
  return p || '未知'
}

// 退出登录
function handleLogout() {
  logout()
  router.push('/login')
}

// 监听筛选变化
watch(filterStatus, onFilterChange)

onMounted(() => {
  fetchBlacklist()
})
</script>

<template>
  <div class="min-h-screen w-full bg-slate-50">
    <AdminSidebar />
    <main class="ml-64 min-h-screen overflow-y-auto">
      <div class="p-6 text-slate-900 flex flex-col">
        <!-- Header -->
        <header class="flex justify-between items-center mb-8">
          <div>
            <h1 class="font-serif text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-3">
              <Shield class="w-8 h-8 text-rose-600" />
              下架管控黑名单
            </h1>
            <p class="text-slate-500 text-sm mt-1 ml-11">管理下架书籍，查看管控记录，恢复合规作品</p>
          </div>
          
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-3 pl-4 border-l border-slate-200">
              <div class="text-right hidden md:block">
                <div class="text-sm font-bold text-slate-900">{{ user?.username || 'Administrator' }}</div>
                <div class="text-xs text-emerald-600 font-medium">● 在线</div>
              </div>
              <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center font-bold shadow-md shadow-indigo-500/20 overflow-hidden">
                <img v-if="user?.avatar" :src="`http://localhost:5000${user.avatar}`" alt="Avatar" class="w-full h-full object-cover" />
                <span v-else>{{ user?.username?.charAt(0).toUpperCase() || 'A' }}</span>
              </div>
            </div>
            <button @click="handleLogout" class="p-2 text-slate-400 hover:text-rose-500 transition-colors" title="退出登录">
              <LogOut class="w-5 h-5" />
            </button>
          </div>
        </header>

        <!-- Stats Cards -->
        <div class="grid grid-cols-12 gap-4 mb-6">
          <div class="col-span-12 sm:col-span-4">
            <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">当前下架</div>
                  <div class="text-2xl font-bold text-rose-600">{{ total }}</div>
                </div>
                <div class="p-3 rounded-xl bg-rose-50">
                  <Ban class="w-6 h-6 text-rose-500" />
                </div>
              </div>
            </div>
          </div>
          <div class="col-span-12 sm:col-span-4">
            <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">今日下架</div>
                  <div class="text-2xl font-bold text-amber-600">{{ blacklist.filter(i => i.status === 'active' && new Date(i.created_at).toDateString() === new Date().toDateString()).length }}</div>
                </div>
                <div class="p-3 rounded-xl bg-amber-50">
                  <AlertTriangle class="w-6 h-6 text-amber-500" />
                </div>
              </div>
            </div>
          </div>
          <div class="col-span-12 sm:col-span-4">
            <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm">
              <div class="flex items-center justify-between">
                <div>
                  <div class="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">已恢复</div>
                  <div class="text-2xl font-bold text-emerald-600">{{ blacklist.filter(i => i.status === 'removed').length }}</div>
                </div>
                <div class="p-3 rounded-xl bg-emerald-50">
                  <CheckCircle class="w-6 h-6 text-emerald-500" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Filter & Search -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-4 shadow-sm mb-6">
          <div class="flex flex-wrap items-center gap-4">
            <!-- 状态筛选 -->
            <div class="flex items-center gap-2">
              <Filter class="w-4 h-4 text-slate-400" />
              <span class="text-sm text-slate-600">状态:</span>
              <div class="flex gap-1">
                <button 
                  @click="filterStatus = 'active'"
                  class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                  :class="filterStatus === 'active' ? 'bg-rose-500 text-white border border-rose-500 shadow-sm' : 'text-slate-500 hover:bg-slate-50 border border-slate-200 bg-white'"
                >
                  已下架
                </button>
                <button 
                  @click="filterStatus = 'removed'"
                  class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                  :class="filterStatus === 'removed' ? 'bg-emerald-500 text-white border border-emerald-500 shadow-sm' : 'text-slate-500 hover:bg-slate-50 border border-slate-200 bg-white'"
                >
                  已恢复
                </button>
                <button 
                  @click="filterStatus = 'all'"
                  class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                  :class="filterStatus === 'all' ? 'bg-indigo-500 text-white border border-indigo-500 shadow-sm' : 'text-slate-500 hover:bg-slate-50 border border-slate-200 bg-white'"
                >
                  全部
                </button>
              </div>
            </div>
            
            <!-- 搜索 -->
            <div class="flex-1 min-w-[200px]">
              <div class="relative">
                <Search class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input 
                  v-model="searchQuery"
                  @input="onSearch"
                  type="text"
                  placeholder="搜索书名、作者..."
                  class="w-full pl-10 pr-4 py-2 rounded-xl bg-white border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                />
              </div>
            </div>
            
            <!-- 刷新 -->
            <button 
              @click="fetchBlacklist"
              :disabled="loading"
              class="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              <RefreshCw class="w-4 h-4" :class="loading ? 'animate-spin' : ''" />
              刷新
            </button>
          </div>
        </div>

        <!-- Blacklist Table -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl shadow-sm overflow-hidden">
          <!-- Table Header -->
          <div class="grid grid-cols-12 gap-4 px-6 py-4 bg-slate-50/50 border-b border-slate-100 text-xs font-bold text-slate-500 uppercase tracking-wider">
            <div class="col-span-3">书名</div>
            <div class="col-span-2">作者</div>
            <div class="col-span-1">平台</div>
            <div class="col-span-2">下架原因</div>
            <div class="col-span-1">操作人</div>
            <div class="col-span-2">时间</div>
            <div class="col-span-1 text-right">操作</div>
          </div>
          
          <!-- Table Body -->
          <div v-if="loading" class="flex items-center justify-center py-20">
            <div class="w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
          
          <div v-else-if="blacklist.length === 0" class="flex flex-col items-center justify-center py-20 text-slate-400">
            <Ban class="w-12 h-12 mb-4 opacity-30" />
            <p class="text-sm">暂无{{ filterStatus === 'active' ? '已下架' : filterStatus === 'removed' ? '已恢复' : '' }}记录</p>
          </div>
          
          <div v-else class="divide-y divide-slate-100">
            <div 
              v-for="item in blacklist" 
              :key="item.novel_id"
              class="grid grid-cols-12 gap-4 px-6 py-4 items-center hover:bg-slate-50/50 transition-colors"
            >
              <div class="col-span-3">
                <div class="flex items-center gap-3">
                  <!-- 封面图片 -->
                  <div class="w-12 h-16 rounded-lg overflow-hidden flex-shrink-0 bg-slate-100">
                    <img 
                      v-if="item.cover_url" 
                      :src="item.cover_url" 
                      class="w-full h-full object-cover"
                      @error="($event.target as HTMLImageElement).style.display='none'"
                    />
                    <div v-else class="w-full h-full flex items-center justify-center">
                      <BookOpen class="w-5 h-5 text-slate-300" />
                    </div>
                  </div>
                  <div class="min-w-0">
                    <div class="font-medium text-slate-900 truncate">{{ item.title }}</div>
                    <div class="text-xs text-slate-400 mt-1">ID: {{ item.novel_id }}</div>
                  </div>
                </div>
              </div>
              <div class="col-span-2 text-sm text-slate-600">{{ item.author || '-' }}</div>
              <div class="col-span-1">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                  {{ platformLabel(item.platform) }}
                </span>
              </div>
              <div class="col-span-2">
                <span class="text-sm text-slate-600 line-clamp-1" :title="item.reason">
                  {{ item.reason || '未注明原因' }}
                </span>
              </div>
              <div class="col-span-1 text-sm text-slate-600">{{ item.admin_name || '-' }}</div>
              <div class="col-span-2 text-xs text-slate-400">
                <div>{{ formatDate(item.created_at) }}</div>
                <div v-if="item.status === 'removed'" class="text-emerald-500 mt-1">
                  恢复于 {{ formatDate(item.removed_at) }}
                </div>
              </div>
              <div class="col-span-1 text-right">
                <div class="flex items-center justify-end gap-2">
                  <span 
                    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border"
                    :class="statusStyle(item.status)"
                  >
                    {{ statusLabel(item.status) }}
                  </span>
                  <button 
                    @click="showDetail(item)"
                    class="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                    title="查看详情"
                  >
                    <Eye class="w-4 h-4" />
                  </button>
                  <button 
                    v-if="item.status === 'active'"
                    @click="showRestoreDialog(item)"
                    class="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    title="恢复上架"
                  >
                    <RotateCcw class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Pagination -->
          <div v-if="totalPages > 1" class="flex items-center justify-between px-6 py-4 border-t border-slate-100">
            <div class="text-xs text-slate-500">
              共 {{ total }} 条记录，第 {{ page }} / {{ totalPages }} 页
            </div>
            <div class="flex items-center gap-2">
              <button 
                @click="goPage(page - 1)"
                :disabled="page <= 1"
                class="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft class="w-4 h-4" />
              </button>
              <div class="flex items-center gap-1">
                <button 
                  v-for="p in Math.min(5, totalPages)" 
                  :key="p"
                  @click="goPage(p)"
                  class="w-8 h-8 rounded-lg text-xs font-medium transition-colors"
                  :class="page === p ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'"
                >
                  {{ p }}
                </button>
                <span v-if="totalPages > 5" class="text-slate-400 px-2">...</span>
              </div>
              <button 
                @click="goPage(page + 1)"
                :disabled="page >= totalPages"
                class="p-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
    
    <!-- Confirm Dialog -->
    <Teleport to="body">
      <div v-if="confirmDialog.show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="closeConfirmDialog"></div>
        <div class="relative bg-white rounded-2xl shadow-xl max-w-md w-full p-6 animate-fade-in">
          <div class="flex items-start gap-4">
            <div 
              class="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
              :class="{
                'bg-indigo-50 text-indigo-600': confirmDialog.type === 'info',
                'bg-amber-50 text-amber-600': confirmDialog.type === 'warning',
                'bg-rose-50 text-rose-600': confirmDialog.type === 'danger'
              }"
            >
              <AlertTriangle v-if="confirmDialog.type === 'warning'" class="w-6 h-6" />
              <Ban v-else-if="confirmDialog.type === 'danger'" class="w-6 h-6" />
              <CheckCircle v-else class="w-6 h-6" />
            </div>
            <div class="flex-1">
              <h3 class="text-lg font-bold text-slate-900 mb-2">{{ confirmDialog.title }}</h3>
              <p class="text-sm text-slate-600 whitespace-pre-line">{{ confirmDialog.message }}</p>
            </div>
          </div>
          <div class="flex items-center justify-end gap-3 mt-6">
            <button 
              v-if="confirmDialog.cancelText"
              @click="confirmDialog.onCancel"
              class="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors"
            >
              {{ confirmDialog.cancelText }}
            </button>
            <button 
              @click="confirmDialog.onConfirm"
              class="px-4 py-2 rounded-xl text-sm font-medium text-white transition-colors"
              :class="{
                'bg-indigo-600 hover:bg-indigo-700': confirmDialog.type === 'info',
                'bg-amber-600 hover:bg-amber-700': confirmDialog.type === 'warning',
                'bg-rose-600 hover:bg-rose-700': confirmDialog.type === 'danger'
              }"
            >
              {{ confirmDialog.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
    
    <!-- Detail Modal -->
    <Teleport to="body">
      <div v-if="detailModal.show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="closeDetail"></div>
        <div class="relative bg-white rounded-2xl shadow-xl max-w-lg w-full p-6 animate-fade-in">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-lg font-bold text-slate-900">下架详情</h3>
            <button @click="closeDetail" class="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors">
              <span class="sr-only">关闭</span>
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div v-if="detailModal.item" class="space-y-4">
            <div class="flex items-start gap-4 p-4 bg-slate-50 rounded-xl">
              <!-- 封面图片 -->
              <div class="w-16 h-22 rounded-lg overflow-hidden flex-shrink-0 bg-slate-100">
                <img 
                  v-if="detailModal.item.cover_url" 
                  :src="detailModal.item.cover_url" 
                  class="w-full h-full object-cover"
                  @error="($event.target as HTMLImageElement).style.display='none'"
                />
                <div v-else class="w-full h-full flex items-center justify-center">
                  <BookOpen class="w-6 h-6 text-slate-300" />
                </div>
              </div>
              <div>
                <div class="font-medium text-slate-900">{{ detailModal.item.title }}</div>
                <div class="text-xs text-slate-500 mt-1">书籍ID: {{ detailModal.item.novel_id }}</div>
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span class="text-slate-400">作者:</span>
                <span class="text-slate-700 ml-2">{{ detailModal.item.author || '-' }}</span>
              </div>
              <div>
                <span class="text-slate-400">平台:</span>
                <span class="text-slate-700 ml-2">{{ platformLabel(detailModal.item.platform) }}</span>
              </div>
              <div>
                <span class="text-slate-400">状态:</span>
                <span 
                  class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border"
                  :class="statusStyle(detailModal.item.status)"
                >
                  {{ statusLabel(detailModal.item.status) }}
                </span>
              </div>
              <div>
                <span class="text-slate-400">操作人:</span>
                <span class="text-slate-700 ml-2">{{ detailModal.item.admin_name || '-' }}</span>
              </div>
            </div>
            
            <div class="p-4 bg-rose-50 rounded-xl">
              <div class="flex items-center gap-2 mb-2">
                <Ban class="w-4 h-4 text-rose-500" />
                <span class="text-sm font-medium text-rose-700">下架原因</span>
              </div>
              <p class="text-sm text-rose-600">{{ detailModal.item.reason || '未注明原因' }}</p>
            </div>
            
            <div class="text-xs text-slate-400 space-y-1">
              <div>下架时间: {{ formatDate(detailModal.item.created_at) }}</div>
              <div v-if="detailModal.item.status === 'removed'">
                恢复时间: {{ formatDate(detailModal.item.removed_at) }}
              </div>
            </div>
          </div>
          
          <div class="flex items-center justify-end gap-3 mt-6">
            <button 
              @click="closeDetail"
              class="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors"
            >
              关闭
            </button>
            <button 
              v-if="detailModal.item?.status === 'active'"
              @click="restoreFromDetail"
              class="px-4 py-2 rounded-xl text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors"
            >
              <RotateCcw class="w-4 h-4 inline mr-1" />
              恢复上架
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
