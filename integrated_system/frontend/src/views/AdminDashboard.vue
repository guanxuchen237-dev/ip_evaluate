<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import AdminSidebar from '@/components/layout/AdminSidebar.vue'
import { parseAIError, showAIError } from '@/utils/aiErrorHandler'
import {
  Users, Activity, Shield, Server, Globe, Bell, Search, 
  MoreHorizontal, CheckCircle2, AlertTriangle, Clock, LogOut,
  Cpu, HardDrive, Database, LayoutDashboard, Library, Settings, BookOpen, TrendingUp,
  Zap, FileText, AlertOctagon, RotateCcw, Eye, EyeOff, ChevronLeft, ChevronRight, Filter,
  Save, TestTube, Info, RefreshCw, KeyRound, Link, Bot, Bug,
  Download, Sparkles, Radar, MessageSquare, BarChart3, Scan, Crown, Cloud, Grid3X3
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const { user, logout, fetchUser } = useAuth()

const currentTab = computed(() => route.query.tab || 'overview')

// Interactive Chart State
const hoveredPoint = ref<{ x: number, y?: number, time: string, pv: number, uv: number, api?: number, tokens?: number } | null>(null)

// Define Admin Menu Items
const adminDockItems = [
  { title: "总览", titleEn: "Overview", url: "/admin?tab=overview", icon: LayoutDashboard },
  { title: "用户管理", titleEn: "Users", url: "/admin?tab=users", icon: Users },
  { title: "书籍管理", titleEn: "Books", url: "/admin?tab=books", icon: Library },
  { title: "平台监控", titleEn: "Platform", url: "/admin?tab=platform", icon: Globe },
  { title: "数据采集", titleEn: "Pipeline", url: "/admin?tab=monitor", icon: Database },
  { title: "智能审计", titleEn: "Audit", url: "/admin?tab=audit", icon: Shield },
  { title: "设置", titleEn: "Settings", url: "/admin?tab=settings", icon: Settings },
]

// Mock Data
const stats = [
  { label: '总用户数', value: '2,847', change: '+12%', icon: Users, color: 'text-indigo-500', bg: 'bg-indigo-500/10' },
  { label: '在线人数', value: '142', change: '+5%', icon: Globe, color: 'text-emerald-500', bg: 'bg-emerald-50' },
  { label: 'API 调用', value: '8.4k', change: '+24%', icon: Activity, color: 'text-sky-500', bg: 'bg-sky-500/10' },
  { label: '系统负载', value: '24%', change: 'Stable', icon: Server, color: 'text-amber-500', bg: 'bg-amber-500/10' },
]

const recentUsers = ref<any[]>([])
const usersLoading = ref(false)

async function fetchAdminUsers() {
  usersLoading.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/auth/admin/users`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    const data = await res.json()
    if (data.users) {
      recentUsers.value = data.users.map((u: any) => ({ ...u, name: u.username }))
    } else {
      console.error('获取用户列表接口响应异常:', data.error || data)
    }
  } catch(e) { console.error('获取所有用户失败', e) }
  finally { usersLoading.value = false }
}

const showUserModal = ref(false)
const isEditingUser = ref(false)
const userForm = ref({ id: null as number|null, username: '', password: '', email: '', role: 'user', is_active: 1, token_limit: 0 })
const showPassword = ref(false)

function openAddUser() {
  isEditingUser.value = false
  showPassword.value = false
  userForm.value = { id: null, username: '', password: '', email: '', role: 'user', is_active: 1, token_limit: 0 }
  showUserModal.value = true
}

function openEditUser(u: any) {
  isEditingUser.value = true
  showPassword.value = false
  userForm.value = { id: u.id, username: u.name || u.username, password: '', email: u.email || '', role: u.role, is_active: u.is_active, token_limit: u.token_limit || 0 }
  showUserModal.value = true
}

async function submitUserForm() {
  try {
    const token = localStorage.getItem('auth_token')
    const url = isEditingUser.value ? `${API_BASE}/auth/admin/users/${userForm.value.id}` : `${API_BASE}/auth/admin/users`
    const method = isEditingUser.value ? 'PUT' : 'POST'
    const body = { ...userForm.value }
    if (isEditingUser.value && !body.password) {
      delete (body as any).password
    }
    
    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(body)
    })
    
    const data = await res.json()
    if (res.ok) {
      showUserModal.value = false
      fetchAdminUsers()
    } else {
      alert(data.error || '保存失败')
    }
  } catch (e) {
    console.error(e)
    alert('网络错误')
  }
}

async function deleteUser(id: number) {
  if (!confirm('确定要永久删除该用户吗？')) return
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/auth/admin/users/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      fetchAdminUsers()
    } else {
      const data = await res.json()
      alert(data.error || '删除失败')
    }
  } catch (e) {
    console.error(e)
    alert('网络错误')
  }
}

async function resetUserTokens(id: number, name: string) {
  if (!confirm(`确定要重置用户「${name}」的 Token 用量吗？`)) return
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/auth/admin/users/${id}/reset_tokens`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      fetchAdminUsers()
    } else {
      const data = await res.json()
      alert(data.error || '重置失败')
    }
  } catch (e) {
    console.error(e)
    alert('网络错误')
  }
}


// === 书籍管理 - 真实数据库连接 ===
const books = ref<any[]>([])
const booksTotal = ref(0)
const booksTotalPages = ref(0)
const booksPage = ref(1)
const booksPageSize = 20
const booksLoading = ref(false)
const booksSearch = ref('')
const booksFilterCategory = ref('')
const booksFilterPlatform = ref('')
const booksFilterStatus = ref('')
const booksFilterYear = ref('')
const booksFilterMonth = ref('')
const booksCategories = ref<string[]>([])
const booksYears = ['', ...Array.from({length: 6}, (_, i) => (2025 - i).toString())]
const booksMonths = ['', ...Array.from({length: 12}, (_, i) => (i + 1).toString())]

// === 大屏指标 - 真实数据库连接 ===
const metricsData = ref({
    system: { cpu: 0, memory: 0, disk: 0 },
    metrics: { total_users: 0, online_users: 0, total_pv: 0, total_uv: 0, total_api_calls: 0, total_ai_tokens: 0 },
    traffic_series: [] as {time: string, pv: number, uv: number, api: number, tokens: number}[],
    services: [] as any[],
    source_dist: { mobile: 0, desktop: 0, api: 0 } as any,
    alerts: [] as {level: string, title: string, desc: string, time: string}[]
})

const API_BASE = 'http://localhost:5000/api'


// 获取书籍列表
async function fetchBooks() {
  booksLoading.value = true
  try {
    const params = new URLSearchParams({
      page: booksPage.value.toString(),
      pageSize: booksPageSize.toString(),
      search: booksSearch.value,
      category: booksFilterCategory.value,
      platform: booksFilterPlatform.value === '起点' ? 'Qidian' : booksFilterPlatform.value === '纵横' ? 'Zongheng' : '',
      status: booksFilterStatus.value,
      year: booksFilterYear.value,
      month: booksFilterMonth.value,
    })
    const res = await fetch(`${API_BASE}/admin/books?${params}`)
    const data = await res.json()
    books.value = data.items || []
    booksTotal.value = data.total || 0
    booksTotalPages.value = data.total_pages || 0
  } catch (e) {
    console.error('获取书籍失败:', e)
  } finally {
    booksLoading.value = false
  }
}

// === 平台监控全局筛选 ===
const platformFilter = ref('all') // 'all', 'qidian', 'zongheng'
const selectedBookTrend = ref('') // 显式指定的书籍走势名
const trendSearchQuery = ref('')
const trendGranularity = ref('day') // 'day', 'month', 'year' - 时间粒度

function searchTrendBook() {
    selectedBookTrend.value = trendSearchQuery.value.trim()
}

watch(platformFilter, () => {
    selectedBookTrend.value = '' // 切换平台时清空选中书名
    trendSearchQuery.value = ''
    fetchRealtimeTracking()
    fetchWeeklyGrowth()
    fetchRealtimeRanking()
})

watch(selectedBookTrend, () => {
    fetchRealtimeTracking()
})

watch(trendGranularity, () => {
    fetchRealtimeTracking()
})

// 实时追踪模型数据
const realtimeTrackingData = ref<any>({ title: '', dates: [], monthly_tickets: [], collection_count: [], predicted_tickets: [] })
const realtimeLoading = ref(false)
async function fetchRealtimeTracking() {
   realtimeLoading.value = true
   try {
       const params = new URLSearchParams()
       if (platformFilter.value !== 'all') params.append('source', platformFilter.value)
       if (selectedBookTrend.value) params.append('title', selectedBookTrend.value)
       params.append('granularity', trendGranularity.value)

       const res = await fetch(`${API_BASE}/admin/realtime_tracking?${params}`)
       if (res.ok) {
           const data = await res.json()
           if (data.dates && data.dates.length === 1) {
               data.dates.push(data.dates[0] + ' (至今)')
               if (data.monthly_tickets && data.monthly_tickets.length === 1) data.monthly_tickets.push(data.monthly_tickets[0])
               if (data.collection_count && data.collection_count.length === 1) data.collection_count.push(data.collection_count[0])
               const pred = data.predicted_tickets || data.predicted
               if (pred && pred.length === 1) pred.push(pred[0])
           }
           realtimeTrackingData.value = {
               ...data,
               predicted_tickets: data.predicted_tickets || data.predicted || []
           }
       }
   } catch(e) { console.error('获取实时监控数据失败', e) }
   finally { realtimeLoading.value = false }
}

// === 爬虫调度器状态 ===
const spiderSchedulerStatus = ref({
  is_running: false,
  status: 'Loading...',
  last_run_time: null as string | null,
  next_run_time: null as string | null,
  interval_minutes: 120,
  target_platform: 'all',
  crawl_history: [] as any[]
})

// 爬虫实时日志流
const liveLogs = ref<string[]>([])
let liveLogsTimer: any = null

async function pollSpiderLogs() {
   try {
       const res = await fetch(`${API_BASE}/admin/spider_scheduler/logs`)
       if (res.ok) {
           const data = await res.json()
           liveLogs.value = data.logs || []
           if (data.is_running || data.status.includes('正在抓取')) {
               // 继续轮询
               if (!liveLogsTimer) {
                   liveLogsTimer = setInterval(pollSpiderLogs, 1500)
               }
           } else {
               // 停止轮询
               if (liveLogsTimer) {
                   clearInterval(liveLogsTimer)
                   liveLogsTimer = null
               }
           }
           // 自动滚动到底部
           setTimeout(() => {
               const el = document.getElementById('live-logs-container')
               if (el) el.scrollTop = el.scrollHeight
           }, 100)
       }
   } catch (e) { console.error('获取爬虫日志失败', e) }
}

async function fetchSpiderSchedulerStatus() {
  try {
    const res = await fetch(`${API_BASE}/admin/spider_scheduler/status`)
    if (res.ok) {
        spiderSchedulerStatus.value = await res.json()
        if (spiderSchedulerStatus.value.status.includes('正在抓取')) {
            pollSpiderLogs()
        }
    }
  } catch(e) { console.error('获取爬虫状态失败', e) }
}

async function toggleSpiderScheduler(action: string) {
  try {
    const body: any = { action }
    // 如果是触发立即执行，同时传递当前选中的平台
    if (action === 'trigger') {
      body.target_platform = spiderSchedulerStatus.value.target_platform
    }
    const res = await fetch(`${API_BASE}/admin/spider_scheduler/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })
    if (res.ok) fetchSpiderSchedulerStatus()
  } catch(e) { console.error('操作爬虫失败', e) }
}

// 获取题材列表
async function fetchCategories() {
  try {
    const res = await fetch(`${API_BASE}/admin/books/categories`)
    const data = await res.json()
    booksCategories.value = data.categories || []
  } catch (e) {
    console.error('获取题材失败:', e)
  }
}

// 获取用户真实预测记录与虚拟读者评价 (训练回流池)
const userPredictions = ref<any[]>([])
const vrComments = ref<any[]>([])
const loadingPoolData = ref(false)

async function fetchTrainingPoolData() {
    loadingPoolData.value = true
    try {
        const token = localStorage.getItem('auth_token')
        const hdrs = { 'Authorization': `Bearer ${token}` }
        
        // 1. User Predictions
        const upRes = await fetch(`${API_BASE}/admin/user_predictions`, { headers: hdrs })
        if (upRes.ok) {
            const upData = await upRes.json()
            userPredictions.value = upData.items || []
        }
        
        // 2. VR Comments
        const vrRes = await fetch(`${API_BASE}/admin/vr_comments?limit=30`, { headers: hdrs })
        if (vrRes.ok) {
            const vrData = await vrRes.json()
            vrComments.value = vrData.items || []
        }
    } catch(e) {
        console.error('获取回流训练池数据失败', e)
    } finally {
        loadingPoolData.value = false
    }
}

// 搜索防抖
let searchTimer: any = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    booksPage.value = 1
    fetchBooks()
  }, 400)
}

// 筛选变更
function onFilterChange() {
  booksPage.value = 1
  fetchBooks()
}

// 分页
function goPage(p: number) {
  if (p < 1 || p > booksTotalPages.value) return
  booksPage.value = p
  fetchBooks()
}

// 格式化数字
function formatNum(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return n.toString()
}

// IP 评分颜色
function scoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600 bg-emerald-50 border-emerald-100'
  if (score >= 60) return 'text-indigo-600 bg-indigo-50 border-indigo-100'
  return 'text-slate-500 bg-slate-50 border-slate-100'
}

// 平台显示名
function platformLabel(p: string): string {
  if (p === 'Qidian') return '起点'
  if (p === 'Zongheng') return '纵横'
  return p
}

// Tab 切换时加载数据
watch(currentTab, (tab) => {
  if (tab === 'books' && books.value.length === 0) {
    fetchBooks()
    fetchCategories()
  }
  if (tab === 'users' && recentUsers.value.length === 0) {
    fetchAdminUsers()
  }
  if (tab === 'platform') {
    fetchPlatformStats()
    fetchRealtimeTracking()
    fetchWeeklyGrowth()
    fetchRealtimeRanking()
  }
  if (tab === 'monitor') {
    fetchPipelineStats()
  }
  if (tab === 'audit') {
    fetchAuditLogs()
    fetchMultiSourceOverview()
    fetchAiScores()
  }
  if (tab === 'settings') {
    fetchSettings()
  }
  if (tab === 'overview') {
    fetchTrainingPoolData()
    fetchLongTermTrending()
    fetchRealtimeRanking()
  }
})

// 组件挂载时如果在 books tab 则加载
onMounted(() => {
  if (currentTab.value === 'books') {
    fetchBooks()
    fetchCategories()
  }
  if (currentTab.value === 'users') {
    fetchAdminUsers()
  }
  if (currentTab.value === 'platform') {
    fetchPlatformStats()
    fetchRealtimeTracking()
    fetchWeeklyGrowth()
    fetchRealtimeRanking()
  }
  if (currentTab.value === 'monitor') {
    fetchPipelineStats()
  }
  if (currentTab.value === 'audit') {
    fetchAuditLogs()
    fetchMultiSourceOverview()
    fetchAiScores()
  }
  if (currentTab.value === 'model') {
    fetchTrainConfig()
    pollStatus() // check if running
  }
  if (currentTab.value === 'settings') {
    fetchSettings()
  }
  if (currentTab.value === 'overview') {
      fetchTrainingPoolData()
      fetchLongTermTrending()
      fetchRealtimeRanking()
  }
  fetchDashboardMetrics()
  // 每 15 秒刷新一次监控大屏数据
  setInterval(fetchDashboardMetrics, 15000)
})

// ======== 获取真实大屏数据 ========
const timeRange = ref('24h')

async function fetchDashboardMetrics() {
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/admin/dashboard_metrics?range=${timeRange.value}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
        const data = await res.json()
        metricsData.value = data
    }
  } catch(e) { console.error('获取大屏数据失败', e) }
}

// 动态构建 stats 展示面板
const dynamicStats = computed(() => {
   const m = metricsData.value.metrics
   const sys = metricsData.value.system
   return [
     { label: '总用户数', value: m.total_users || 0, change: 'Active', icon: Users, color: 'text-indigo-500', bg: 'bg-indigo-500/10' },
     { label: 'Token开销', value: formatNum(m.total_ai_tokens || 0), change: 'Tokens', icon: Activity, color: 'text-rose-500', bg: 'bg-rose-500/10' },
     { label: '在线人数', value: m.online_users || 0, change: '15m+', icon: Globe, color: 'text-emerald-500', bg: 'bg-emerald-50' },
     { label: '系统负载(CPU)', value: `${sys.cpu.toFixed(1)}%`, change: 'Realtime', icon: Server, color: 'text-amber-500', bg: 'bg-amber-500/10' },
   ]
})


// === 模型训练逻辑 ===
const trainConfig = ref({
  n_estimators: 100,
  max_depth: 6,
  learning_rate: 0.1
})
const isTraining = ref(false)
const trainLogs = ref<string[]>([])
let accTimer: any = null

async function fetchTrainConfig() {
  try {
    const res = await fetch(`${API_BASE}/admin/model/config`)
    const data = await res.json()
    if (data.config) {
        // Only take what we care about for UI
        trainConfig.value.n_estimators = data.config.n_estimators || 100
        trainConfig.value.max_depth = data.config.max_depth || 6
        trainConfig.value.learning_rate = data.config.learning_rate || 0.1
    }
  } catch(e) { console.error(e) }
}

async function startTraining() {
  if (isTraining.value) return
  isTraining.value = true
  trainLogs.value = ['正在启动训练任务...']
  
  try {
    const res = await fetch(`${API_BASE}/admin/model/train`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trainConfig.value)
    })
    const data = await res.json()
    if (data.status === 'success') {
        pollStatus()
    } else {
        trainLogs.value.push(`启动失败: ${data.message}`)
        isTraining.value = false
    }
  } catch(e) {
      trainLogs.value.push(`网络错误: ${e}`)
      isTraining.value = false
  }
}

async function pollStatus() {
  // Clear existing timer if any
  if (accTimer) clearTimeout(accTimer)
  
  const check = async () => {
    try {
        const res = await fetch(`${API_BASE}/admin/model/status`)
        const data = await res.json()
        isTraining.value = data.is_training
        if (data.log && data.log.length > 0) {
            trainLogs.value = data.log
        }
        
        if (data.is_training) {
            accTimer = setTimeout(check, 1000)
        } else if (trainLogs.value.length > 0) {
             const lastLog = trainLogs.value[trainLogs.value.length - 1]
             if (lastLog && lastLog.includes('Training completed')) {
                 // Done
             }
        }
    } catch(e) {
        console.error(e)
    }
  }
  check()
}


// 平台真实数据
const platformStatus = ref<any[]>([])
const platformLoading = ref(false)
const weeklyGrowthData = ref<any[]>([])
const weeklyGrowthLoading = ref(false)
const realtimeTicketRanking = ref<any[]>([])
const ticketPlatform = ref<'qidian' | 'zongheng'>('qidian')

// 过滤后的月票排行榜
const filteredTicketRanking = computed(() => {
    if (!realtimeTicketRanking.value.length) return []
    return realtimeTicketRanking.value.filter(item => {
        if (ticketPlatform.value === 'qidian') return item.platform === '起点'
        if (ticketPlatform.value === 'zongheng') return item.platform === '纵横'
        return true
    })
})

async function fetchRealtimeRanking() {
    try {
        const platform = ticketPlatform.value || 'qidian'
        const res = await fetch(`${API_BASE}/admin/realtime_ticket_ranking?limit=20&platform=${platform}`)
        if (res.ok) {
            const data = await res.json()
            realtimeTicketRanking.value = data.items || []
        }
    } catch(e) { console.error('获取实时月票排行失败', e) }
}

async function fetchPlatformStats() {
    platformLoading.value = true
    try {
        const token = localStorage.getItem('auth_token')
        const res = await fetch(`${API_BASE}/admin/platform_stats`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
            const data = await res.json()
            platformStatus.value = data.platforms || []
            // 同步更新调度器状态
            if (data.scheduler) spiderSchedulerStatus.value = data.scheduler
        }
    } catch(e) { console.error('获取平台状态失败', e) }
    finally { platformLoading.value = false }
}

async function fetchWeeklyGrowth() {
    weeklyGrowthLoading.value = true
    try {
        const params = new URLSearchParams()
        if (platformFilter.value !== 'all') params.append('source', platformFilter.value)
        const res = await fetch(`${API_BASE}/admin/weekly_ticket_growth?${params}`)
        if (res.ok) {
            const data = await res.json()
            weeklyGrowthData.value = data.items || []
            // 自动选中增幅榜第一名为默认走势图书籍，前提是当前没有显式选择
            if (weeklyGrowthData.value.length > 0 && !selectedBookTrend.value) {
                // 不触发 selectedBookTrend 的 watch（避免重复请求），或者在 fetchRealtimeTracking 里去取
            }
        }
    } catch(e) { console.error('获取月票增幅数据失败', e) }
    finally { weeklyGrowthLoading.value = false }
}

// 更新调度器配置（间隔 / 平台）
async function updateSchedulerConfig() {
    try {
        await fetch(`${API_BASE}/admin/spider_scheduler/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                interval_minutes: spiderSchedulerStatus.value.interval_minutes,
                target_platform: spiderSchedulerStatus.value.target_platform
            })
        })
        fetchSpiderSchedulerStatus()
    } catch(e) { console.error('更新配置失败', e) }
}

const trendLabel = (t: string) => {
    const map: Record<string, string> = { hot: '🔥 爆款', dark_horse: '🐴 黑马', weakening: '📉 走弱', rising: '📈 上升', stable: '➡️ 稳定' }
    return map[t] || '➡️ 稳定'
}
const trendColor = (t: string) => {
    const map: Record<string, string> = { hot: 'bg-rose-500 text-white border-rose-600 shadow-sm shadow-rose-200/50', dark_horse: 'bg-purple-50 text-purple-600 border-purple-200', weakening: 'bg-slate-50 text-slate-500 border-slate-200', rising: 'bg-emerald-50 text-emerald-600 border-emerald-200', stable: 'bg-white text-slate-400 border-slate-100' }
    return map[t] || 'bg-white text-slate-400 border-slate-100'
}

const trafficData = ref<any[]>([])
const recentCrawledBooks = ref<any[]>([])
const pipelineExtra = ref({ qidian_total: 0, zongheng_total: 0, qidian_today: 0, zongheng_today: 0, last_crawl_time: '--', qidian_count: 0, zongheng_count: 0 })

// 去重和日期筛选
const dedupEnabled = ref(true)  // 默认开启去重
const dateFilter = ref('')  // 格式: YYYY-MM-DD 或 YYYY-MM 或 YYYY

// 分页控制（platformFilter已在215行定义）
const currentPage = ref(1)
const pageSize = 20
const pagination = ref({ page: 1, page_size: 20, total: 0, total_pages: 0 })

const pipelineStats = computed(() => [
   { label: '在线数据源', value: '2/2', icon: Globe, color: 'text-indigo-600', bg: 'bg-indigo-50' },
   { label: '今日采集', value: formatNum(pipelineExtra.value.qidian_today + pipelineExtra.value.zongheng_today), icon: Database, color: 'text-emerald-600', bg: 'bg-emerald-50' },
   { label: '起点入库', value: formatNum(pipelineExtra.value.qidian_total), icon: BookOpen, color: 'text-sky-600', bg: 'bg-sky-50' },
   { label: '纵横入库', value: formatNum(pipelineExtra.value.zongheng_total), icon: BookOpen, color: 'text-rose-600', bg: 'bg-rose-50' },
])

async function fetchPipelineStats() {
    try {
        const token = localStorage.getItem('auth_token')
        let url = `${API_BASE}/admin/monitor/pipeline?platform=${platformFilter.value}&page=${currentPage.value}&page_size=${pageSize}&dedup=${dedupEnabled.value}`
        if (dateFilter.value) {
            url += `&date=${dateFilter.value}`
        }
        const res = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        if (res.ok) {
            const data = await res.json()
            trafficData.value = data.traffic_series || []
            recentCrawledBooks.value = data.recent_books || []
            pagination.value = data.pagination || { page: 1, page_size: 20, total: 0, total_pages: 0 }
            pipelineExtra.value = {
                qidian_total: data.qidian_total || 0,
                zongheng_total: data.zongheng_total || 0,
                qidian_today: data.qidian_today || 0,
                zongheng_today: data.zongheng_today || 0,
                last_crawl_time: data.last_crawl_time || '--',
                qidian_count: data.qidian_count || 0,
                zongheng_count: data.zongheng_count || 0
            }
        }
    } catch(e) { console.error('Error fetching pipeline stats:', e) }
}

// 切换平台时重置页码
function switchPlatform(p: 'all' | 'qidian' | 'zongheng') {
    platformFilter.value = p
    currentPage.value = 1
    fetchPipelineStats()
}

// 分页导航
function goToPage(p: number) {
    if (p >= 1 && p <= pagination.value.total_pages) {
        currentPage.value = p
        fetchPipelineStats()
    }
}

// 图表交互状态
const chartHover = ref<any>(null)

// 预计算每个数据点的 SVG 坐标
const chartPoints = computed(() => {
    const data = trafficData.value
    if (!data || data.length === 0) return []
    const W = 800, H = 200, PAD = 8
    const maxVal = Math.max(...data.map((d: any) => Math.max(Number(d.qidian) || 0, Number(d.zongheng) || 0)), 1)
    const stepX = W / Math.max(data.length - 1, 1)
    return data.map((d: any, i: number) => {
        const x = i * stepX
        const qv = Number(d.qidian) || 0
        const zv = Number(d.zongheng) || 0
        return {
            x,
            qy: H - PAD - (qv / maxVal) * (H - PAD * 2),
            zy: H - PAD - (zv / maxVal) * (H - PAD * 2),
            qv, zv,
            time: d.time || ''
        }
    })
})

// SVG 路径：折线
const getSmoothLine = (pts: any[], yField: string) => {
    if (!pts || pts.length === 0) return ''
    return 'M' + pts.map((p: any) => `${p.x},${p[yField]}`).join(' L')
}

// SVG 路径：面积填充
const getAreaPath = (pts: any[], yField: string) => {
    if (!pts || pts.length === 0) return ''
    const H = 200
    const line = pts.map((p: any) => `${p.x},${p[yField]}`).join(' L')
    return `M${pts[0].x},${H} L${line} L${pts[pts.length - 1].x},${H} Z`
}

const getPath = (data: any[], width: number, height: number) => {
  if (!data || data.length === 0) return `M0,${height} L${width},${height} Z`
  const max = Math.max(...data.map((d: any) => Number(d.value) || 0), 1) // 兜底防止为 0
  const stepX = width / Math.max(data.length - 1, 1)
  const points = data.map((d: any, i: number) => {
    const x = i * stepX
    const y = height - (d.value / max) * height
    return `${x},${y}`
  }).join(' ')
  return `M0,${height} L${points} L${width},${height} Z`
}

const getLinePath = (data: any[], width: number, height: number, field: string = 'value') => {
   if (!data || data.length === 0) return `M0,${height} L${width},${height}`
   // Always scale against the maximum "value" (total) so that the y-axis represents the same magnitude across series
   const max = Math.max(...data.map((d: any) => Number(d.value) || 0), 1)
   const stepX = width / Math.max(data.length - 1, 1)
   return 'M' + data.map((d: any, i: number) => {
     const x = i * stepX
     const val = (d as any)[field] || 0
     const y = height - (val / max) * height
     return `${x},${y}`
   }).join(' L')
}

const handleLogout = () => {
  logout()
  router.push('/login')
}

// Audit Data
const auditLogs = ref<any[]>([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = ref(10)
const auditLoading = ref(false)
const auditStats = ref({
   total: 0,
   high_risk: 0,
   auto_passed: 0,
   pending: 0
})

const auditStatsCards = computed(() => [
   { label: '今日审计', value: auditStats.value.total, icon: FileText, color: 'text-slate-600', bg: 'bg-slate-50' },
   { label: '高风险预警', value: auditStats.value.high_risk, icon: AlertOctagon, color: 'text-rose-600', bg: 'bg-rose-50' },
   { label: '自动通过', value: auditStats.value.auto_passed, icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
   { label: '待人工复核', value: auditStats.value.pending, icon: Clock, color: 'text-indigo-600', bg: 'bg-indigo-50' },
])

const auditFilterLevel = ref('')
const auditFilterStatus = ref('')

async function fetchAuditLogs() {
  auditLoading.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const params = new URLSearchParams()
    const offset = (auditPage.value - 1) * auditPageSize.value
    params.append('limit', auditPageSize.value.toString())
    params.append('offset', offset.toString())
    if (auditFilterLevel.value) params.append('risk_level', auditFilterLevel.value)
    if (auditFilterStatus.value) params.append('status', auditFilterStatus.value)

    const res = await fetch(`${API_BASE}/admin/audit_logs?${params}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      const json = await res.json()
      auditLogs.value = json.data || []
      auditTotal.value = json.total || 0
      // 统计各类数据
      const all = json.data || []
      auditStats.value = {
        total: json.total || 0,
        high_risk: all.filter((l: any) => l.risk_level === 'High').length,
        auto_passed: all.filter((l: any) => l.status === 'Resolved' || l.status === 'RESOLVED').length,
        pending: all.filter((l: any) => l.status === 'Pending' || l.status === 'PENDING').length,
      }
    }
  } catch (e) { console.error('获取审计日志失败:', e) }
  finally { auditLoading.value = false }
}

async function resolveAuditLog(id: number, action: string) {
    if (!confirm(`确定要${action === 'resolve' ? '标记为已处理' : '忽略'}该预警吗？`)) return;
    try {
        const token = localStorage.getItem('auth_token')
        const res = await fetch(`${API_BASE}/admin/audit_logs/${id}/resolve`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify({ action: action === 'resolve' ? 'Resolved' : 'Ignored' })
        })
        if (res.ok) {
            fetchAuditLogs()
        }
    } catch (e) {
        console.error(e)
    }
}

const gemScanLoading = ref(false)

async function triggerGemScan() {
    console.log('[Gem Scan] 按钮被点击，开始扫描...')
    gemScanLoading.value = true
    try {
        const token = localStorage.getItem('auth_token');
        console.log('[Gem Scan] 发送请求到 /admin/scan_gems')
        const res = await fetch(`${API_BASE}/admin/scan_gems`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        console.log('[Gem Scan] 收到响应:', res.status)
        const data = await res.json();
        if (res.ok) {
            const total_scanned = data.total_scanned || 0;
            const gems_count = data.gems_count || 0;
            const global_gems_count = data.global_gems_count || 0;
            const inserted = data.inserted || 0;
            
            if (inserted > 0) {
                let message = `扫描完成！扫描了 ${total_scanned} 本书`;
                if (gems_count > 0) {
                    message += `，发现 ${gems_count} 本潜力遗珠`;
                }
                if (global_gems_count > 0) {
                    message += `，${global_gems_count} 本出海优选`;
                }
                showGemScanToast(message, 'success', inserted);
            } else {
                showGemScanToast(`扫描了 ${total_scanned} 本书，暂未发现新的潜力遗珠`, 'success', 0);
            }
            fetchAuditLogs();
            fetchMultiSourceOverview(); // 刷新概览数据
        } else {
            showGemScanToast(data.error || '扫描失败，请重试', 'error', 0);
        }
    } catch (e) {
        console.error('[Gem Scan] 错误:', e);
        showGemScanToast('网络错误，请稍后重试', 'error', 0);
    } finally {
        gemScanLoading.value = false
    }
}

// === 审计增强：多源数据概览 / 深度审计 / AI 评分表 / 报告展开 ===

// 多源数据概览
const multiSourceOverview = ref<any>({
  vr: { total: 0, positive: 0, neutral: 0, negative: 0 },
  ai_eval: { total: 0, avg_overall: 0, avg_story: 0, avg_character: 0, avg_world: 0, avg_commercial: 0 },
  realtime: { active_books: 0, last_crawl: '--', qidian_count: 0, zongheng_count: 0 },
  audit: { total: 0, gems: 0, global_gems: 0, deep_audits: 0 }
})
const overviewLoading = ref(false)

async function fetchMultiSourceOverview() {
  overviewLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/admin/audit/multi_source_overview`)
    if (res.ok) {
      const json = await res.json()
      if (json.data) multiSourceOverview.value = json.data
    }
  } catch (e) { console.error('获取多源概览失败:', e) }
  finally { overviewLoading.value = false }
}

// 深度审计搜索
const deepScanQuery = ref('')
const deepScanLoading = ref(false)
const deepScanResult = ref<any>(null)

async function triggerDeepScan() {
  const title = deepScanQuery.value.trim()
  if (!title) { alert('请输入书名'); return }
  deepScanLoading.value = true
  deepScanResult.value = null
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/admin/audit/deep_scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ book_title: title })
    })
    const data = await res.json()
    if (res.ok && data.status === 'success') {
      deepScanResult.value = data
      fetchAuditLogs()
      fetchMultiSourceOverview()
    } else {
      showAIError({ response: { data, status: res.status } })
    }
  } catch (e: any) { console.error('深度审计失败:', e); showAIError(e) }
  finally { deepScanLoading.value = false }
}

// AI 评分表
const aiScores = ref<any[]>([])
const aiScoresLoading = ref(false)
const aiScoresPage = ref(1)
const aiScoresPageSize = ref(15)
const aiScoresTotal = ref(0)

const paginatedAiScores = computed(() => {
  const start = (aiScoresPage.value - 1) * aiScoresPageSize.value
  const end = start + aiScoresPageSize.value
  return aiScores.value.slice(start, end)
})

const aiScoresTotalPages = computed(() => Math.ceil(aiScores.value.length / aiScoresPageSize.value))

async function fetchAiScores() {
  aiScoresLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/admin/audit/ai_scores?limit=100`)
    if (res.ok) {
      const json = await res.json()
      aiScores.value = json.data || []
      aiScoresTotal.value = json.total || aiScores.value.length
    }
  } catch (e) { console.error('获取AI评分失败:', e) }
  finally { aiScoresLoading.value = false }
}

// 报告展开状态
const expandedLogId = ref<number | null>(null)
const reportLoading = ref(false)

async function toggleLogExpand(logId: number) {
  if (expandedLogId.value === logId) {
    expandedLogId.value = null
    return
  }
  
  // 检查是否需要生成报告
  const log = auditLogs.value.find(l => l.id === logId)
  if (!log) return
  
  // 如果报告为空或太短，调用API生成
  if (!log.markdown_report || log.markdown_report.length < 100) {
    reportLoading.value = true
    try {
      const token = localStorage.getItem('auth_token')
      const res = await fetch(`http://localhost:5000/api/admin/audit_logs/${logId}/generate_report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      })
      const data = await res.json()
      if (res.ok && data.status === 'success') {
        // 更新本地数据
        const idx = auditLogs.value.findIndex(l => l.id === logId)
        if (idx >= 0) {
          auditLogs.value[idx].markdown_report = data.report
          auditLogs.value[idx].status = 'RESOLVED'
        }
        expandedLogId.value = logId
        console.log('[Audit] Report generated, cached:', data.cached)
      } else {
        console.error('[Audit] Generate report failed:', data.error)
      }
    } catch (e) {
      console.error('[Audit] Generate report error:', e)
    } finally {
      reportLoading.value = false
    }
  } else {
    expandedLogId.value = logId
  }
}

// 导出审计报告为 Markdown 文件
function exportAuditReport(report: string, bookTitle: string, score?: number) {
  const now = new Date().toISOString().split('T')[0]
  const header = `# 《${bookTitle}》AI 商业决策审计报告\n\n` +
      `> 生成日期: ${now}` +
      (score ? ` | 模型评分: ${score}` : '') +
      `\n> 由 IP Lumina 六维数据融合引擎生成\n\n---\n\n`
  const content = header + report
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `审计报告_${bookTitle}_${now}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// === Settings Tab 数据与逻辑 ===
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const settingsToast = ref({ show: false, message: '', type: 'success' as 'success' | 'error' })

// 卡片详情弹窗状态
const showVrDetailModal = ref(false)
const showAiEvalModal = ref(false)
const showRealtimeModal = ref(false)
const showAuditModal = ref(false)

// Gem Scan Toast
const gemScanToast = ref({ show: false, message: '', type: 'success' as 'success' | 'error', count: 0 })

function showGemScanToast(message: string, type: 'success' | 'error', count: number = 0) {
  gemScanToast.value = { show: true, message, type, count }
  setTimeout(() => { gemScanToast.value.show = false }, 3000)
}
const dbTestResult = ref<Record<'zongheng' | 'qidian', { status: string, message: string }>>({ zongheng: { status: '', message: '' }, qidian: { status: '', message: '' } })
const dbTesting = ref<Record<'zongheng' | 'qidian', boolean>>({ zongheng: false, qidian: false })

const settingsData = ref({
  ai: { provider: '', base_url: '', api_key: '', model_name: '', temperature: 0.7, max_tokens: 1024 },
  spider: { interval_minutes: 120, target_platform: 'all', is_running: false, status: '' },
  database: {
    zongheng: { host: '', port: 3306, database: '', user: '', password: '' },
    qidian: { host: '', port: 3306, database: '', user: '', password: '' },
  },
  system: { online_window_minutes: 15, page_size: 20, cache_ttl_minutes: 30, log_level: 'INFO', data_refresh_interval: 15 },
  model: { n_estimators: 100, max_depth: 6, learning_rate: 0.1 },
  about: { version: '', tech_stack: '', python_version: '', total_books: 0, model_loaded: false },
})

async function fetchSettings() {
  settingsLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/admin/settings`)
    if (res.ok) {
      const data = await res.json()
      settingsData.value = { ...settingsData.value, ...data }
    }
  } catch (e) { console.error('获取设置失败:', e) }
  finally { settingsLoading.value = false }
}

async function saveSettings(section: string) {
  settingsSaving.value = true
  try {
    const values = (settingsData.value as any)[section]
    const res = await fetch(`${API_BASE}/admin/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section, values })
    })
    const data = await res.json()
    if (res.ok) {
      showSettingsToast(data.message || '保存成功', 'success')
    } else {
      showSettingsToast(data.error || '保存失败', 'error')
    }
  } catch (e) {
    showSettingsToast('网络错误', 'error')
  } finally {
    settingsSaving.value = false
  }
}

async function testDbConnection(platform: 'zongheng' | 'qidian') {
  dbTesting.value[platform] = true
  dbTestResult.value[platform] = { status: '', message: '' }
  try {
    const res = await fetch(`${API_BASE}/admin/test_db`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform })
    })
    const data = await res.json()
    dbTestResult.value[platform] = { status: data.status, message: data.message }
  } catch (e) {
    dbTestResult.value[platform] = { status: 'error', message: '网络错误' }
  } finally {
    dbTesting.value[platform] = false
  }
}

function showSettingsToast(message: string, type: 'success' | 'error') {
  settingsToast.value = { show: true, message, type }
  setTimeout(() => { settingsToast.value.show = false }, 3000)
}

// === 个人信息修改 ===
const profileSaving = ref(false)
const profileForm = ref({
  username: '',
  email: '',
  password: ''
})

// 初始化个人信息表单
function initProfileForm() {
  if (user.value) {
    profileForm.value = {
      username: user.value.username || '',
      email: user.value.email || '',
      password: ''
    }
  }
}

// 监听 user 变化初始化表单
watch(user, () => {
  initProfileForm()
}, { immediate: true })

// 上传头像
async function handleAvatarUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('avatar', file)
  
  try {
    const token = localStorage.getItem('auth_token')
    const res = await fetch(`${API_BASE}/auth/upload_avatar`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    })
    const data = await res.json()
    if (data.success) {
      showSettingsToast('头像上传成功', 'success')
      // 刷新用户信息
      fetchUser()
    } else {
      showSettingsToast(data.error || '上传失败', 'error')
    }
  } catch (e) {
    showSettingsToast('网络错误', 'error')
  }
}

// 保存个人信息
async function saveAdminProfile() {
  profileSaving.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const body: any = {
      username: profileForm.value.username,
      email: profileForm.value.email
    }
    if (profileForm.value.password) {
      body.password = profileForm.value.password
    }
    
    const res = await fetch(`${API_BASE}/auth/admin/users/${user.value?.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(body)
    })
    const data = await res.json()
    if (data.success) {
      showSettingsToast('个人信息已更新', 'success')
      profileForm.value.password = ''
      fetchUser()
    } else {
      showSettingsToast(data.error || '保存失败', 'error')
    }
  } catch (e) {
    showSettingsToast('网络错误', 'error')
  } finally {
    profileSaving.value = false
  }
}

// --- 周期长热度高作品趋势图 ---
const longTermTrendingData = ref<any[]>([])
const longTermTrendingLoading = ref(false)
const longTermTrendingTimeRange = ref({ start: '', end: '' })
const longTermTrendingHover = ref<any>(null)

// 预设颜色方案（与第二张图片类似的多色线条）
const trendColors = [
  { line: '#6366f1', fill: 'rgba(99, 102, 241, 0.1)', label: 'indigo' },   // Indigo
  { line: '#f59e0b', fill: 'rgba(245, 158, 11, 0.1)', label: 'amber' },   // Amber
  { line: '#10b981', fill: 'rgba(16, 185, 129, 0.1)', label: 'emerald' }, // Emerald
  { line: '#ec4899', fill: 'rgba(236, 72, 153, 0.1)', label: 'pink' },     // Pink
  { line: '#3b82f6', fill: 'rgba(59, 130, 246, 0.1)', label: 'blue' },      // Blue
  { line: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.1)', label: 'violet' },   // Violet
  { line: '#ef4444', fill: 'rgba(239, 68, 68, 0.1)', label: 'red' },        // Red
  { line: '#14b8a6', fill: 'rgba(20, 184, 166, 0.1)', label: 'teal' },      // Teal
  { line: '#f97316', fill: 'rgba(249, 115, 22, 0.1)', label: 'orange' },   // Orange
  { line: '#84cc16', fill: 'rgba(132, 204, 22, 0.1)', label: 'lime' },     // Lime
]

async function fetchLongTermTrending() {
  longTermTrendingLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/admin/long_term_trending?limit=10`)
    if (res.ok) {
      const data = await res.json()
      if (data.status === 'success') {
        longTermTrendingData.value = data.books || []
        longTermTrendingTimeRange.value = data.time_range || { start: '', end: '' }
      }
    }
  } catch (e) { console.error('获取周期长热度高作品趋势失败', e) }
  finally { longTermTrendingLoading.value = false }
}

// 生成平滑曲线路径
const getTrendLinePath = (book: any, chartWidth: number, chartHeight: number, maxTickets: number) => {
  if (!book.monthly_data || book.monthly_data.length === 0) return ''
  
  const stepX = chartWidth / Math.max(book.all_periods.length - 1, 1)
  const points = book.monthly_data.map((m: any, i: number) => {
    const x = i * stepX
    const y = chartHeight - (m.tickets / Math.max(maxTickets, 1)) * chartHeight
    return `${x},${y}`
  })
  
  return 'M' + points.join(' L')
}

// 计算图表中使用的最大月票值（用于统一Y轴）
const maxTrendingTickets = computed(() => {
  if (!longTermTrendingData.value.length) return 1
  let max = 0
  for (const book of longTermTrendingData.value) {
    for (const m of book.monthly_data || []) {
      if (m.tickets > max) max = m.tickets
    }
  }
  return max
})

// 起点书籍
const qidianBooks = computed(() => {
  return longTermTrendingData.value.filter(b => b.platform === '起点')
})

// 纵横书籍
const zonghengBooks = computed(() => {
  return longTermTrendingData.value.filter(b => b.platform === '纵横')
})

// 起点最大月票值
const maxQidianTickets = computed(() => {
  const books = qidianBooks.value
  if (!books.length) return 1
  let max = 0
  for (const book of books) {
    for (const m of book.monthly_data || []) {
      if (m.tickets > max) max = m.tickets
    }
  }
  return max
})

// 纵横最大月票值
const maxZonghengTickets = computed(() => {
  const books = zonghengBooks.value
  if (!books.length) return 1
  let max = 0
  for (const book of books) {
    for (const m of book.monthly_data || []) {
      if (m.tickets > max) max = m.tickets
    }
  }
  return max
})

// 格式化月份显示
const formatPeriod = (period: string) => {
  if (!period) return ''
  const [year, month] = period.split('-')
  return `${year}-${month}`
}
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
             <Shield class="w-8 h-8 text-indigo-600" />
             系统管理控制台
           </h1>
           <p class="text-slate-500 text-sm mt-1 ml-11">全域数据监控与资源管理中心</p>
        </div>
        
        <div class="flex items-center gap-4">
           <!-- Admin Profile -->
           <div class="flex items-center gap-3 pl-4 border-l border-slate-200">
               <div class="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity" @click="router.push('/admin?tab=settings')">
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
        </div>
      </header>

      <!-- ==================== TAB: OVERVIEW ==================== -->
      <div v-if="currentTab === 'overview'" class="space-y-6 animate-fade-in">
        <!-- 1. Stats Row -->
        <div class="grid grid-cols-12 gap-6">
            <div v-for="stat in dynamicStats" :key="stat.label" class="col-span-12 sm:col-span-6 lg:col-span-3">
               <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all group overflow-hidden relative">
                  <div class="absolute inset-0 bg-gradient-to-br from-white/40 to-transparent pointer-events-none"></div>
                  <div class="relative z-10 flex justify-between items-start">
                     <div>
                        <div class="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">{{ stat.label }}</div>
                        <div class="text-3xl font-bold text-slate-900 mb-2">{{ stat.value }}</div>
                        <div class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-600 border border-emerald-100">
                          {{ stat.change }}
                        </div>
                     </div>
                     <div class="p-3 rounded-xl" :class="stat.bg">
                        <component :is="stat.icon" class="w-6 h-6" :class="stat.color" />
                     </div>
                  </div>
               </div>
            </div>
        </div>

        <!-- 2. 全宽流量图表 -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-4 shadow-sm">
             <div class="flex items-center justify-between mb-1">
                 <div>
                    <h3 class="font-bold text-slate-900 flex items-center gap-2 text-sm">
                        <Activity class="w-4 h-4 text-indigo-600" />
                        {{ timeRange === '24h' ? '24h' : timeRange === '7d' ? '7天' : '30天' }} 流量与趋势
                    </h3>
                    <div class="flex items-center gap-4 mt-0.5" v-if="metricsData.metrics">
                        <span class="flex items-center gap-1 text-[11px] text-slate-500">
                            <span class="w-1.5 h-1.5 rounded-full bg-indigo-500"></span> PV
                            <span class="text-slate-800 font-mono font-bold">{{ formatNum(metricsData.metrics.total_pv) }}</span>
                        </span>
                        <span class="flex items-center gap-1 text-[11px] text-slate-500">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> UV
                            <span class="text-slate-800 font-mono font-bold">{{ formatNum(metricsData.metrics.total_uv) }}</span>
                        </span>
                        <span class="flex items-center gap-1 text-[11px] text-slate-500">
                            <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span> AI Tokens
                            <span class="text-slate-800 font-mono font-bold">{{ formatNum(metricsData.metrics.total_ai_tokens) }}</span>
                        </span>
                    </div>
                 </div>
                 <div class="flex gap-1">
                    <button @click="timeRange = '24h'; fetchDashboardMetrics()" class="px-2.5 py-1 rounded-md text-[10px] font-bold transition-all" :class="timeRange==='24h'?'bg-indigo-50 border border-indigo-200 text-indigo-600':'text-slate-400 hover:text-slate-600 hover:bg-slate-50 border border-transparent'">24H</button>
                    <button @click="timeRange = '7d'; fetchDashboardMetrics()" class="px-2.5 py-1 rounded-md text-[10px] font-bold transition-all" :class="timeRange==='7d'?'bg-indigo-50 border border-indigo-200 text-indigo-600':'text-slate-400 hover:text-slate-600 hover:bg-slate-50 border border-transparent'">7D</button>
                    <button @click="timeRange = '30d'; fetchDashboardMetrics()" class="px-2.5 py-1 rounded-md text-[10px] font-bold transition-all" :class="timeRange==='30d'?'bg-indigo-50 border border-indigo-200 text-indigo-600':'text-slate-400 hover:text-slate-600 hover:bg-slate-50 border border-transparent'">30D</button>
                 </div>
              </div>
              
              <!-- 全宽图表 - 180px -->
              <div class="w-full h-[180px] relative" @mouseleave="hoveredPoint = null">
                 <div v-if="hoveredPoint" 
                      class="absolute top-0 bottom-0 w-[1px] bg-indigo-400/40 pointer-events-none z-0"
                      :style="{ left: hoveredPoint.x + '%' }"></div>
                 
                 <!-- 真实的 SVG 折线图需要动态计算 -->
                 <svg viewBox="0 0 1200 170" class="w-full h-full block" preserveAspectRatio="none" style="overflow: visible;">
                    <defs>
                      <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#818cf8" stop-opacity="0.2"/>
                        <stop offset="80%" stop-color="#818cf8" stop-opacity="0.02"/>
                        <stop offset="100%" stop-color="#818cf8" stop-opacity="0"/>
                      </linearGradient>
                    </defs>
                    <!-- 网格 -->
                    <line x1="0" y1="42" x2="1200" y2="42" stroke="#f1f5f9" stroke-width="0.5" />
                    <line x1="0" y1="85" x2="1200" y2="85" stroke="#f1f5f9" stroke-width="0.5" />
                    <line x1="0" y1="128" x2="1200" y2="128" stroke="#f1f5f9" stroke-width="0.5" />
                    
                    <g v-if="metricsData.traffic_series && metricsData.traffic_series.length > 0">
                       <path :d="getPath(metricsData.traffic_series.map(t => ({time: t.time, value: t.pv})), 1200, 160)" fill="url(#chartGrad)" />
                       <path :d="getLinePath(metricsData.traffic_series.map(t => ({time: t.time, value: t.pv})), 1200, 160)" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </g>
                    <g v-else>
                        <!-- 备用默认样式 -->
                        <path d="M0,160 L0,120 L25,100 L50,85 L75,110 L100,95 L125,55 L150,80 L175,70 L200,85 L225,60 L250,90 L275,105 L300,130 L325,110 L350,85 L375,60 L400,72 L425,95 L450,120 L475,100 L500,65 L525,80 L550,55 L575,75 L600,95 L625,110 L650,88 L675,65 L700,45 L725,58 L750,72 L775,90 L800,108 L825,95 L850,70 L875,50 L900,62 L925,78 L950,95 L975,115 L1000,100 L1025,80 L1050,55 L1075,42 L1100,52 L1125,68 L1150,85 L1175,75 L1200,48 L1200,160 Z" fill="url(#chartGrad)" />
                        <path d="M0,120 L25,100 L50,85 L75,110 L100,95 L125,55 L150,80 L175,70 L200,85 L225,60 L250,90 L275,105 L300,130 L325,110 L350,85 L375,60 L400,72 L425,95 L450,120 L475,100 L500,65 L525,80 L550,55 L575,75 L600,95 L625,110 L650,88 L675,65 L700,45 L725,58 L750,72 L775,90 L800,108 L825,95 L850,70 L875,50 L900,62 L925,78 L950,95 L975,115 L1000,100 L1025,80 L1050,55 L1075,42 L1100,52 L1125,68 L1150,85 L1175,75 L1200,48" fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                    </g>

                    <!-- 时间 (X轴刻度) -->
                    <text x="0" y="158" fill="#94a3b8" style="font-size: 9px;" v-if="metricsData.traffic_series && metricsData.traffic_series.length">{{ metricsData.traffic_series[0]?.time }}</text>
                    <text x="500" y="158" fill="#94a3b8" style="font-size: 9px;" v-if="metricsData.traffic_series && metricsData.traffic_series.length > 5">{{ metricsData.traffic_series[Math.floor(metricsData.traffic_series.length/2)]?.time }}</text>
                    <text x="1175" y="158" fill="#94a3b8" style="font-size: 9px;" v-if="metricsData.traffic_series && metricsData.traffic_series.length">{{ metricsData.traffic_series[metricsData.traffic_series.length-1]?.time }}</text>

                    <!-- 悬停侦测块 -->
                    <rect v-for="(v, i) in metricsData.traffic_series" :key="'hover-'+i"
                          :x="(i - 0.5) * (1200 / (Math.max((metricsData.traffic_series?.length || 2) - 1, 1)))" y="0" 
                          :width="1200 / (Math.max((metricsData.traffic_series?.length || 2) - 1, 1))" height="155" fill="transparent"
                          @mouseenter="() => {
                              const len = metricsData.traffic_series?.length || 2
                              const item = metricsData.traffic_series ? metricsData.traffic_series[i] : null;
                              hoveredPoint = { 
                                  x: (i / (len - 1 || 1)) * 100, 
                                  time: item ? item.time : '', 
                                  pv: item ? item.pv : 0,
                                  uv: item ? item.uv : 0,
                                  api: item ? item.api : 0,
                                  tokens: item ? item.tokens : 0
                              }
                          }"
                    />
                 </svg>
                 <!-- 悬停提示 -->
                 <div v-if="hoveredPoint && hoveredPoint.time" 
                      class="absolute top-1 bg-slate-900 text-white text-[10px] rounded-md px-2.5 py-1.5 shadow-lg pointer-events-none z-20 whitespace-nowrap"
                      :style="{ left: `clamp(80px, ${hoveredPoint.x}%, calc(100% - 80px))`, transform: 'translateX(-50%)' }">
                      <span class="font-mono font-bold">{{ hoveredPoint.time }}</span>
                      <span class="text-slate-500 mx-1">|</span>
                      <span class="text-indigo-300">PV {{ hoveredPoint.pv }}</span>
                      <span class="text-emerald-300 ml-1">UV {{ hoveredPoint.uv }}</span>
                      <div class="mt-0.5 pt-0.5 border-t border-slate-700/50">
                          <span class="text-rose-300">Tokens {{ formatNum(hoveredPoint.tokens || 0) }}</span>
                      </div>
                 </div>
              </div>
        </div>

        <!-- 4. 底部 4 列均等卡片 -->
        <div class="grid grid-cols-12 gap-4">
            <!-- 来源分布 -->
            <div class="col-span-12 sm:col-span-6 lg:col-span-3">
                <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-4 shadow-sm overflow-hidden h-full">
                    <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                        <Globe class="w-3.5 h-3.5 text-emerald-500" /> 来源分布
                    </h4>
                    <div class="space-y-3" v-if="metricsData.source_dist">
                        <div>
                            <div class="flex justify-between text-[11px] mb-1"><span class="text-slate-600">移动应用</span><span class="font-mono font-bold text-slate-800">{{ metricsData.source_dist.mobile }}%</span></div>
                            <div class="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden"><div class="h-full bg-indigo-500 rounded-full transition-all" :style="{width: metricsData.source_dist.mobile + '%'}"></div></div>
                        </div>
                        <div>
                            <div class="flex justify-between text-[11px] mb-1"><span class="text-slate-600">桌面端</span><span class="font-mono font-bold text-slate-800">{{ metricsData.source_dist.desktop }}%</span></div>
                            <div class="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden"><div class="h-full bg-emerald-400 rounded-full transition-all" :style="{width: metricsData.source_dist.desktop + '%'}"></div></div>
                        </div>
                        <div>
                            <div class="flex justify-between text-[11px] mb-1"><span class="text-slate-600">API / 其他</span><span class="font-mono font-bold text-slate-800">{{ metricsData.source_dist.api }}%</span></div>
                            <div class="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden"><div class="h-full bg-amber-400 rounded-full transition-all" :style="{width: metricsData.source_dist.api + '%'}"></div></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 核心服务 -->
            <div class="col-span-12 sm:col-span-6 lg:col-span-3">
                <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-4 shadow-sm overflow-hidden h-full">
                    <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                        <Server class="w-3.5 h-3.5 text-purple-600" /> 核心服务
                    </h4>
                    <div class="space-y-2">
                        <div v-for="sc in metricsData.services" :key="sc.name" class="flex justify-between items-center p-1.5 rounded-lg bg-white/50 border border-slate-100/50">
                            <div class="flex items-center gap-2">
                                <span class="w-1.5 h-1.5 rounded-full" :class="sc.status==='Normal'?'bg-emerald-500':'bg-amber-500 animate-pulse'"></span>
                                <span class="text-[11px] text-slate-700">{{ sc.name }}</span>
                            </div>
                            <span class="text-[9px] px-1.5 py-0.5 rounded font-mono font-bold" 
                                  :class="sc.status==='Normal'?'bg-emerald-50 text-emerald-600':'bg-amber-50 text-amber-600'">{{ sc.status === 'Normal' ? '正常' : '忙碌' }} {{ sc.latency }}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 资源监控 -->
            <div class="col-span-12 sm:col-span-6 lg:col-span-3">
                 <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-4 shadow-sm overflow-hidden h-full">
                    <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                        <Cpu class="w-3.5 h-3.5 text-sky-600" /> 资源监控
                    </h4>
                    <div class="space-y-3" v-if="metricsData.system">
                        <div>
                            <div class="flex justify-between text-[11px] mb-1"><span class="text-slate-600">CPU 负载</span><span class="font-mono font-bold text-slate-800">{{ metricsData.system.cpu.toFixed(1) }}%</span></div>
                            <div class="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                <div class="h-full rounded-full transition-all" :class="metricsData.system.cpu>70?'bg-rose-500':'bg-indigo-500'" :style="{width: metricsData.system.cpu + '%'}"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between text-[11px] mb-1"><span class="text-slate-600">内存占用</span><span class="font-mono font-bold text-slate-800">{{ metricsData.system.memory.toFixed(1) }}%</span></div>
                            <div class="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                <div class="h-full rounded-full transition-all" :class="metricsData.system.memory>80?'bg-rose-500':'bg-pink-500'" :style="{width: metricsData.system.memory + '%'}"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between text-[11px] mb-1"><span class="text-slate-600">存储空间</span><span class="font-mono font-bold text-slate-800">{{ metricsData.system.disk.toFixed(1) }}%</span></div>
                            <div class="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                                <div class="h-full bg-emerald-500 rounded-full transition-all" :style="{width: metricsData.system.disk + '%'}"></div>
                            </div>
                        </div>
                    </div>
                 </div>
            </div>

            <!-- 实时警报 -->
            <div class="col-span-12 sm:col-span-6 lg:col-span-3">
                 <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-4 shadow-sm overflow-hidden h-full">
                    <div class="flex items-center justify-between mb-3">
                        <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-2">
                            <Bell class="w-3.5 h-3.5 text-rose-500" /> 实时警报
                        </h4>
                        <span class="text-[9px] bg-rose-50 text-rose-600 font-bold px-1.5 py-0.5 rounded-full border border-rose-100" v-if="metricsData.alerts">{{ metricsData.alerts.length }}</span>
                    </div>
                    <div class="space-y-2" v-if="metricsData.alerts && metricsData.alerts.length > 0">
                         <div v-for="(alert, idx) in metricsData.alerts" :key="idx" class="flex gap-2 items-start p-1.5 rounded-lg" :class="alert.level==='error'?'bg-rose-50/50 border border-rose-100/50':'bg-amber-50/50 border border-amber-100/50'">
                             <div class="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5" :class="alert.level==='error'?'bg-rose-100':'bg-amber-100'">
                                 <AlertOctagon v-if="alert.level==='error'" class="w-3 h-3 text-rose-500" />
                                 <AlertTriangle v-else class="w-3 h-3 text-amber-500" />
                             </div>
                             <div class="flex-1 min-w-0">
                                <div class="text-[11px] font-bold text-slate-800">{{ alert.title }}</div>
                                <div class="text-[9px] text-slate-400 truncate">{{ alert.desc }} · {{ alert.time }}</div>
                             </div>
                         </div>
                    </div>
                    <div v-else class="text-xs text-slate-400 text-center py-4 mt-8">
                       <CheckCircle2 class="w-6 h-6 text-emerald-400 mx-auto mb-1 opacity-50" />
                       暂无系统警报
                    </div>
                 </div>
            </div>
        </div>

        <!-- 4. 动态训练数据池追踪 (用户级测算 + 虚拟读者) -->
        <div class="grid grid-cols-12 gap-6 mt-6">
            <!-- 外部用户预测记录集 -->
            <div class="col-span-12 lg:col-span-6">
                <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm min-h-[400px]">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="font-bold text-slate-900 flex items-center gap-2">
                            <Users class="w-5 h-5 text-indigo-600" /> 用户终端干预预测留存库
                        </h3>
                        <span class="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded font-mono border border-indigo-100">AI 离线重训靶点</span>
                    </div>

                    <div v-if="loadingPoolData" class="flex items-center justify-center py-10 opacity-60">
                         <div class="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    
                    <div v-else-if="userPredictions.length > 0" class="overflow-y-auto max-h-[320px] pr-2 custom-scrollbar">
                         <div class="space-y-3">
                             <div v-for="up in userPredictions" :key="up.id" class="p-3 bg-white border border-slate-100 rounded-xl hover:border-indigo-200 transition-colors group">
                                  <div class="flex items-start justify-between">
                                      <div>
                                         <div class="font-bold text-sm text-slate-900 mb-1 group-hover:text-indigo-600 transition-colors">
                                             《{{ up.title }}》
                                             <span v-if="up.category" class="ml-2 text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">{{ up.category }}</span>
                                         </div>
                                         <div class="text-[11px] text-slate-500 flex items-center gap-3">
                                              <span class="flex items-center gap-1"><Users class="w-3 h-3 text-slate-400"/> {{ up.username || '匿名游客' }} {{ up.role === 'admin' ? '(Admin)' : '' }}</span>
                                              <span class="flex items-center gap-1"><Clock class="w-3 h-3 text-slate-400"/> {{ up.predicted_at }}</span>
                                         </div>
                                      </div>
                                      <div class="text-right flex flex-col items-end">
                                         <span class="text-lg font-bold font-mono" :class="scoreColor(up.score).split(' ')[0]">{{ up.score?.toFixed(1) || '0.0' }}</span>
                                         <span class="text-[9px] text-slate-400 uppercase">综合得分</span>
                                      </div>
                                  </div>
                             </div>
                         </div>
                    </div>
                    <div v-else class="text-sm text-slate-400 text-center py-12">暂无外部查询记录</div>
                </div>
            </div>

            <!-- 内部虚拟读者情绪交互 -->
            <div class="col-span-12 lg:col-span-6">
                 <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm min-h-[400px]">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="font-bold text-slate-900 flex items-center gap-2">
                            <BookOpen class="w-5 h-5 text-emerald-600" /> 系统虚拟读者心智衍生库
                        </h3>
                        <span class="text-xs bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded font-mono border border-emerald-100">Agentic 场景留存</span>
                    </div>

                    <div v-if="loadingPoolData" class="flex items-center justify-center py-10 opacity-60">
                         <div class="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    
                    <div v-else-if="vrComments.length > 0" class="overflow-y-auto max-h-[320px] pr-2 custom-scrollbar">
                         <div class="space-y-3">
                             <div v-for="vr in vrComments" :key="vr.id" class="p-3 bg-white border border-slate-100 rounded-xl hover:border-emerald-200 transition-colors">
                                  <div class="flex items-center justify-between mb-2">
                                      <div class="flex items-center gap-2">
                                          <div class="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-600 border border-slate-200">
                                              {{ vr.reader_name ? vr.reader_name.charAt(0) : 'R' }}
                                          </div>
                                          <span class="text-xs font-bold text-slate-700">{{ vr.reader_name || 'Agent' }}</span>
                                          <span class="px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider bg-slate-50 border border-slate-100 font-mono flex items-center gap-1"><BookOpen class="w-2.5 h-2.5" /> {{ vr.book_title || '未关联书名' }}</span>
                                      </div>
                                      <div class="flex items-center gap-2 text-[10px] font-bold">
                                         <span v-if="vr.score" class="text-amber-500">★ {{ vr.score }}</span>
                                         <span v-if="vr.emotion" class="px-1.5 py-0.5 rounded-full text-slate-500 bg-slate-100">{{ vr.emotion }}</span>
                                      </div>
                                  </div>
                                  <div class="text-sm text-slate-600 bg-slate-50/50 p-2 rounded-lg border border-slate-100/50 line-clamp-2" :title="vr.comment">
                                      "{{ vr.comment }}"
                                  </div>
                                  <div class="text-right mt-1"><span class="text-[9px] text-slate-400 font-mono">{{ vr.created_at }}</span></div>
                             </div>
                         </div>
                    </div>
                    <div v-else class="text-sm text-slate-400 text-center py-12">暂无虚拟读者行为互动日志</div>
                 </div>
            </div>
        </div>
      </div>

      <!-- ==================== TAB: USERS ==================== -->
      <div v-if="currentTab === 'users'" class="animate-fade-in">
           <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm overflow-hidden min-h-[600px]">
              <div class="flex items-center justify-between mb-6">
                 <h3 class="font-bold text-slate-900 flex items-center gap-2">
                    <Users class="w-5 h-5 text-indigo-600" />
                    用户权限管理列表
                 </h3>
                 <div class="flex gap-3">
                    <button @click="openAddUser" class="px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium shadow-lg hover:bg-indigo-700 transition-all">
                       + 新增用户
                    </button>
                 </div>
              </div>
              
              <div class="overflow-x-auto">
                 <table class="w-full text-left border-collapse">
                    <thead>
                       <tr class="border-b border-slate-100 text-xs font-bold text-slate-500 uppercase tracking-wider">
                          <th class="px-6 py-4">用户详情</th>
                          <th class="px-6 py-4">角色</th>
                          <th class="px-6 py-4 text-right">消耗 Tokens</th>
                          <th class="px-6 py-4 text-right">Token 限额</th>
                           <th class="px-6 py-4 text-center">最后操作时间</th>
                           <th class="px-6 py-4 text-center">系统状态</th>
                          <th class="px-6 py-4 text-right">操作</th>
                       </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100 relative">
                        <!-- Loading 面板 -->
                        <tr v-if="usersLoading" class="absolute inset-0 bg-white/50 backdrop-blur-sm z-10 flex items-center justify-center min-h-[100px]">
                           <td colspan="6" class="text-sm font-bold text-indigo-500 flex items-center gap-2"><div class="w-4 h-4 border-2 border-indigo-500 border-t-transparent inset-0 rounded-full animate-spin"></div>加载中...</td>
                        </tr>

                        <tr v-for="u in recentUsers" :key="u.id" class="group hover:bg-indigo-50/30 transition-colors">
                           <td class="px-6 py-4">
                              <div class="flex items-center gap-3">
                                 <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-slate-600 shadow-sm overflow-hidden"
                                      :class="u.role === 'admin' ? 'bg-gradient-to-br from-indigo-100 to-purple-100' : 'bg-slate-100'">
                                    <img v-if="u.avatar" :src="`http://localhost:5000${u.avatar}`" alt="Avatar" class="w-full h-full object-cover" />
                                    <span v-else :class="u.role === 'admin' ? 'text-indigo-700' : 'text-slate-600'">{{ u.name ? u.name.charAt(0).toUpperCase() : 'U' }}</span>
                                 </div>
                                 <div class="min-w-0 flex-1">
                                    <div class="text-sm font-bold text-slate-900 truncate flex items-center gap-2">
                                       {{ u.name || 'Unnamed' }}
                                       <!-- 借助后端的动态时间判定在线状态 -->
                                       <span v-if="u.is_online" class="flex w-2 h-2" title="当前在线">
                                          <span class="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-emerald-400 opacity-75"></span>
                                          <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                       </span>
                                       <span v-else class="flex w-2 h-2 rounded-full bg-slate-300" title="离线"></span>
                                    </div>
                                    <div class="text-xs text-slate-500 truncate">{{ u.email || '未绑定邮箱' }}</div>
                                 </div>
                              </div>
                           </td>
                           <td class="px-6 py-4">
                              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider"
                                    :class="u.role === 'admin' ? 'bg-indigo-50 text-indigo-600 border border-indigo-100' : 'bg-slate-50 text-slate-600 border border-slate-100'">
                                 {{ u.role }}
                              </span>
                           </td>
                           <td class="px-6 py-4 text-right">
                              <span class="font-mono text-xs font-bold" :class="u.token_limit > 0 && u.ai_tokens_used > u.token_limit ? 'text-rose-600' : u.ai_tokens_used > 500000 ? 'text-amber-600' : 'text-slate-600'">
                                 {{ formatNum(u.ai_tokens_used || 0) }}
                              </span>
                           </td>
                           <td class="px-6 py-4 text-right">
                              <span v-if="u.token_limit > 0" class="font-mono text-xs font-bold" :class="u.ai_tokens_used >= u.token_limit ? 'text-rose-600' : 'text-emerald-600'">
                                 {{ formatNum(u.token_limit) }}
                                 <span v-if="u.ai_tokens_used >= u.token_limit" class="text-[10px] ml-1 px-1.5 py-0.5 bg-rose-50 text-rose-600 rounded-full">已超限</span>
                              </span>
                              <span v-else class="text-xs text-slate-400">无限制</span>
                           </td>
                           <td class="px-6 py-4 text-center">
                              <span class="text-xs text-slate-500">{{ u.last_active_at || '从未登录' }}</span>
                           </td>
                           <td class="px-6 py-4 text-center">
                              <span class="text-xs font-bold flex flex-col items-center gap-0.5" 
                                    :class="u.is_active == 1 ? 'text-emerald-500' : 'text-rose-500'">
                                 <CheckCircle2 v-if="u.is_active == 1" class="w-4 h-4" />
                                 <AlertOctagon v-else class="w-4 h-4" />
                                 {{ u.is_active == 1 ? '白名单' : '封禁' }}
                              </span>
                           </td>
                           <td class="px-6 py-4 text-right">
                              <button @click="openEditUser(u)" class="text-indigo-600 hover:text-indigo-800 text-sm font-medium mr-3">编辑</button>
                              <button @click="resetUserTokens(u.id, u.name || u.username)" class="text-amber-600 hover:text-amber-800 text-sm font-medium mr-3">重置</button>
                              <button @click="deleteUser(u.id)" class="text-rose-600 hover:text-rose-800 text-sm font-medium">删除</button>
                           </td>
                        </tr>
                     </tbody>
                 </table>
              </div>
           </div>

           <!-- User Modal -->
           <div v-if="showUserModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
              <div class="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden animate-fade-in-up">
                 <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                    <h3 class="font-bold text-lg text-slate-800">{{ isEditingUser ? '编辑用户' : '新增用户' }}</h3>
                    <button @click="showUserModal = false" class="text-slate-400 hover:text-slate-600 p-1">
                       <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                    </button>
                 </div>
                 
                 <form @submit.prevent="submitUserForm" class="p-6 space-y-4">
                    <div>
                       <label class="block text-sm font-medium text-slate-700 mb-1">用户名 <span class="text-rose-500">*</span></label>
                       <input v-model="userForm.username" type="text" required class="w-full h-10 px-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white transition-all" />
                    </div>
                    <div>
                       <label class="block text-sm font-medium text-slate-700 mb-1">
                          密码 <span v-if="!isEditingUser" class="text-rose-500">*</span>
                          <span v-else class="text-slate-400 text-xs font-normal ml-1">(不修改请留空)</span>
                       </label>
                       <div class="relative">
                          <input v-model="userForm.password" :type="showPassword ? 'text' : 'password'" :required="!isEditingUser" class="w-full h-10 pl-3 pr-10 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white transition-all" />
                          <button type="button" @click="showPassword = !showPassword" class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-indigo-600 transition-colors focus:outline-none">
                             <EyeOff v-if="showPassword" class="w-4 h-4" />
                             <Eye v-else class="w-4 h-4" />
                          </button>
                       </div>
                    </div>
                    <div>
                       <label class="block text-sm font-medium text-slate-700 mb-1">邮箱</label>
                       <input v-model="userForm.email" type="email" class="w-full h-10 px-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white transition-all" />
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                       <div>
                          <label class="block text-sm font-medium text-slate-700 mb-1">系统角色</label>
                          <select v-model="userForm.role" class="w-full h-10 px-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white transition-all">
                             <option value="user">普通用户</option>
                             <option value="admin">系统管理员</option>
                          </select>
                       </div>
                       <div>
                          <label class="block text-sm font-medium text-slate-700 mb-1">状态</label>
                          <select v-model="userForm.is_active" class="w-full h-10 px-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white transition-all">
                             <option :value="1">🟢 白名单 (正常)</option>
                             <option :value="0">🔴 封禁 (禁用)</option>
                          </select>
                       </div>
                    </div>
                    <div>
                       <label class="block text-sm font-medium text-slate-700 mb-1">
                          Token 限额
                          <span class="text-slate-400 text-xs font-normal ml-1">(0 = 无限制)</span>
                       </label>
                       <input v-model.number="userForm.token_limit" type="number" min="0" step="10000" placeholder="0 表示无限制" class="w-full h-10 px-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:bg-white transition-all font-mono" />
                    </div>
                    
                    <div class="pt-4 flex items-center justify-end gap-3 border-t border-slate-100 mt-6">
                       <button type="button" @click="showUserModal = false" class="px-5 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors">
                          取消
                       </button>
                       <button type="submit" class="px-5 py-2 rounded-xl text-sm font-medium text-white bg-indigo-600 shadow-md hover:bg-indigo-700 hover:shadow-lg hover:-translate-y-0.5 transition-all active:translate-y-0">
                          保存设置
                       </button>
                    </div>
                 </form>
              </div>
           </div>
           
      </div>

       <!-- ==================== TAB: BOOKS ==================== -->
      <div v-if="currentTab === 'books'" class="animate-fade-in space-y-4">
           <!-- 筛选栏 -->
           <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-4 shadow-sm">
              <div class="flex flex-wrap items-center gap-3">
                 <!-- 搜索框 -->
                 <div class="relative flex-1 min-w-[200px] max-w-sm">
                    <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input v-model="booksSearch" @input="onSearchInput" type="text" placeholder="搜索书名或作者..."
                       class="w-full h-9 pl-9 pr-4 bg-white/70 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all" />
                 </div>
                 <!-- 平台筛选 -->
                 <select v-model="booksFilterPlatform" @change="onFilterChange"
                    class="h-9 px-3 bg-white/70 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20">
                    <option value="">全部平台</option>
                    <option value="起点">起点</option>
                    <option value="纵横">纵横</option>
                 </select>
                 <!-- 题材筛选 -->
                 <select v-model="booksFilterCategory" @change="onFilterChange"
                    class="h-9 px-3 bg-white/70 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20">
                    <option value="">全部题材</option>
                    <option v-for="cat in booksCategories" :key="cat" :value="cat">{{ cat }}</option>
                 </select>
                 <!-- 状态筛选 -->
                 <select v-model="booksFilterStatus" @change="onFilterChange"
                    class="h-9 px-3 bg-white/70 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20">
                    <option value="">全部状态</option>
                    <option value="连载">连载中</option>
                    <option value="完结">已完结</option>
                 </select>
                                   <!-- 年份筛选 -->
                  <select v-model="booksFilterYear" @change="onFilterChange"
                     class="h-9 px-3 bg-white/70 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20">
                     <option value="">全部年份</option>
                     <option v-for="y in booksYears.slice(1)" :key="y" :value="y">{{ y }}年</option>
                  </select>
                  <!-- 月份筛选 -->
                  <select v-model="booksFilterMonth" @change="onFilterChange"
                     class="h-9 px-3 bg-white/70 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20">
                     <option value="">全部月份</option>
                     <option v-for="m in booksMonths.slice(1)" :key="m" :value="m">{{ m }}月</option>
                  </select>
                  <!-- 统计 -->
                 <div class="ml-auto text-xs text-slate-500">
                    共 <span class="font-bold text-slate-800 font-mono">{{ booksTotal.toLocaleString() }}</span> 部作品
                 </div>
              </div>
           </div>

           <!-- 数据表格 -->
           <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl shadow-sm overflow-hidden">
              <!-- 加载状态 -->
              <div v-if="booksLoading" class="flex items-center justify-center py-20">
                 <div class="animate-spin w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full"></div>
                 <span class="ml-3 text-sm text-slate-500">加载中...</span>
              </div>
              <!-- 空数据 -->
              <div v-else-if="books.length === 0" class="flex flex-col items-center justify-center py-20 text-slate-400">
                 <BookOpen class="w-12 h-12 mb-3 opacity-30" />
                 <p class="text-sm">暂无匹配书籍</p>
              </div>
              <!-- 表格 -->
              <div v-else class="overflow-x-auto">
                 <table class="w-full text-left border-collapse">
                    <thead>
                       <tr class="border-b border-slate-100 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                          <th class="px-4 py-3">书名</th>
                          <th class="px-4 py-3">作者</th>
                          <th class="px-4 py-3">题材</th>
                          <th class="px-4 py-3">平台</th>
                          <th class="px-4 py-3 text-right">字数</th>
                          <th class="px-4 py-3 text-right">热度</th>
                          <th class="px-4 py-3 text-right">月票</th>
                          <th class="px-4 py-3 text-center">IP 评分</th>
                          <th class="px-4 py-3">状态</th>
                          <th class="px-4 py-3 text-right">操作</th>
                       </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-50">
                       <tr v-for="(b, idx) in books" :key="idx" class="group hover:bg-indigo-50/30 transition-colors">
                          <td class="px-4 py-3">
                             <div class="font-bold text-sm text-slate-900 max-w-[200px] truncate">{{ b.title }}</div>
                             <div class="text-[10px] text-slate-400 mt-0.5 max-w-[200px] truncate" v-if="b.latest_chapter" title="最新更新">{{ b.latest_chapter }}</div>
                          </td>
                          <td class="px-4 py-3 text-sm text-slate-600">{{ b.author }}</td>
                          <td class="px-4 py-3">
                             <span class="bg-violet-50 text-violet-600 border border-violet-100 px-2 py-0.5 rounded-md text-[11px] font-medium">{{ b.category }}</span>
                          </td>
                          <td class="px-4 py-3">
                             <span class="px-2 py-0.5 rounded-md text-[11px] font-bold"
                                :class="b.platform === 'Qidian' ? 'bg-rose-50 text-rose-600 border border-rose-100' : 'bg-sky-50 text-sky-600 border border-sky-100'">
                                {{ platformLabel(b.platform) }}
                             </span>
                          </td>
                          <td class="px-4 py-3 text-right text-sm font-mono text-slate-600">{{ formatNum(b.word_count) }}</td>
                          <td class="px-4 py-3 text-right text-sm font-mono text-slate-600">{{ formatNum(b.popularity) }}</td>
                          <td class="px-4 py-3 text-right text-sm font-mono font-bold text-amber-600">{{ formatNum(b.monthly_tickets) }}</td>
                          <td class="px-4 py-3 text-center">
                             <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-mono font-bold border"
                                :class="scoreColor(b.ip_score)">
                                {{ b.ip_score }}
                             </span>
                          </td>
                          <td class="px-4 py-3">
                             <span class="text-xs font-medium" :class="b.status === '连载' ? 'text-emerald-600' : 'text-slate-400'">{{ b.status === '连载' ? '连载中' : '已完结' }}</span>
                          </td>
                          <td class="px-4 py-3 text-right">
                             <button @click="$router.push({ path: '/admin/book/detail', query: { title: b.title, author: b.author, platform: b.platform } })" class="text-indigo-600 hover:text-indigo-800 text-xs font-medium">查看节点</button>
                          </td>
                       </tr>
                    </tbody>
                 </table>
              </div>

              <!-- 分页 -->
              <div v-if="booksTotalPages > 1" class="flex items-center justify-between px-4 py-3 border-t border-slate-100">
                 <div class="text-xs text-slate-500">
                    第 <span class="font-bold text-slate-700">{{ booksPage }}</span> / {{ booksTotalPages }} 页
                 </div>
                 <div class="flex items-center gap-1">
                    <button @click="goPage(booksPage - 1)" :disabled="booksPage <= 1"
                       class="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                       <ChevronLeft class="w-3.5 h-3.5 text-slate-600" />
                    </button>
                    <template v-for="p in Math.min(booksTotalPages, 7)" :key="p">
                       <button @click="goPage(p)" 
                          class="w-7 h-7 flex items-center justify-center rounded-md text-xs font-bold transition-all"
                          :class="p === booksPage ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50 border border-slate-200'">
                          {{ p }}
                       </button>
                    </template>
                    <span v-if="booksTotalPages > 7" class="text-xs text-slate-400 px-1">...</span>
                    <button @click="goPage(booksPage + 1)" :disabled="booksPage >= booksTotalPages"
                       class="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                       <ChevronRight class="w-3.5 h-3.5 text-slate-600" />
                    </button>
                 </div>
              </div>
           </div>
      </div>

      <div v-if="currentTab === 'monitor'" class="animate-fade-in space-y-6">
          <!-- Header Code -->
          <div class="text-center mb-8">
             <div class="text-xs font-bold tracking-[0.2em] text-slate-400 uppercase mb-2">Real-time Pipeline</div>
             <h2 class="text-3xl font-serif font-bold text-slate-900">数据采集监控</h2>
             <p class="text-slate-500 text-sm mt-2">混合爬虫策略实时采集多平台数据 · 最后采集时间 <span class="font-mono font-bold text-indigo-600">{{ pipelineExtra.last_crawl_time }}</span></p>
          </div>

          <!-- Pipeline Stats -->
          <div class="grid grid-cols-12 gap-4">
             <div v-for="stat in pipelineStats" :key="stat.label" class="col-span-6 lg:col-span-3">
                <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm flex items-center justify-between">
                   <div>
                      <div class="text-slate-500 text-xs font-bold mb-1 flex items-center gap-1">
                         <component :is="stat.icon" class="w-3 h-3" /> {{ stat.label }}
                      </div>
                      <div class="text-2xl font-serif font-bold text-slate-900">{{ stat.value }}</div>
                   </div>
                </div>
             </div>
          </div>
          
          <!-- Collection Chart -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm min-h-[280px] flex flex-col">
              <div class="flex items-center justify-between mb-6">
                 <h3 class="font-bold text-slate-900 flex items-center gap-2">
                    <Database class="w-5 h-5 text-indigo-600" />
                    采集趋势 (24h)
                 </h3>
                 <div class="flex gap-4 text-xs font-medium">
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-blue-500"></span> 起点</span>
                    <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-emerald-500"></span> 纵横</span>
                 </div>
              </div>
              <div class="flex-1 w-full relative" v-if="trafficData.length > 0" @mouseleave="chartHover = null">
                 <!-- 悬浮提示 -->
                 <div v-if="chartHover" class="absolute z-20 pointer-events-none bg-slate-800 text-white text-xs rounded-lg px-3 py-2 shadow-xl whitespace-nowrap"
                      :style="{ left: chartHover.px + '%', top: (chartHover.py - 14) + '%', transform: 'translate(-50%, -100%)' }">
                    <div class="font-bold mb-0.5">{{ chartHover.time }}</div>
                    <div class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span> 起点: {{ chartHover.qidian }}</div>
                    <div class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> 纵横: {{ chartHover.zongheng }}</div>
                 </div>
                 <svg viewBox="0 0 800 200" class="w-full h-full overflow-visible" preserveAspectRatio="none">
                    <defs>
                       <linearGradient id="qidianGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.12" />
                          <stop offset="100%" stop-color="#3b82f6" stop-opacity="0" />
                       </linearGradient>
                       <linearGradient id="zonghengGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stop-color="#10b981" stop-opacity="0.12" />
                          <stop offset="100%" stop-color="#10b981" stop-opacity="0" />
                       </linearGradient>
                    </defs>
                    <!-- Grid -->
                    <line x1="0" y1="50" x2="800" y2="50" stroke="#e2e8f0" stroke-dasharray="4" stroke-opacity="0.6" />
                    <line x1="0" y1="100" x2="800" y2="100" stroke="#e2e8f0" stroke-dasharray="4" stroke-opacity="0.6" />
                    <line x1="0" y1="150" x2="800" y2="150" stroke="#e2e8f0" stroke-dasharray="4" stroke-opacity="0.6" />
                    <!-- 起点 Area + Line -->
                    <path :d="getAreaPath(chartPoints, 'qy')" fill="url(#qidianGrad)" />
                    <path :d="getSmoothLine(chartPoints, 'qy')" fill="none" stroke="#3b82f6" stroke-width="2.5" stroke-linecap="round" />
                    <!-- 纵横 Area + Line -->
                    <path :d="getAreaPath(chartPoints, 'zy')" fill="url(#zonghengGrad)" />
                    <path :d="getSmoothLine(chartPoints, 'zy')" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" />
                    <!-- 起点 Data Dots -->
                    <circle v-for="(pt, i) in chartPoints" :key="'q'+i" :cx="pt.x" :cy="pt.qy" r="3.5"
                            fill="white" stroke="#3b82f6" stroke-width="2"
                            class="cursor-pointer transition-all duration-150"
                            :opacity="chartHover?.idx === i ? 1 : 0.7"
                            @mouseenter="chartHover = { idx: i, time: pt.time, qidian: pt.qv, zongheng: pt.zv, px: pt.x / 8, py: pt.qy / 2 }" />
                    <!-- 纵横 Data Dots -->
                    <circle v-for="(pt, i) in chartPoints" :key="'z'+i" :cx="pt.x" :cy="pt.zy" r="3.5"
                            fill="white" stroke="#10b981" stroke-width="2"
                            class="cursor-pointer transition-all duration-150"
                            :opacity="chartHover?.idx === i ? 1 : 0.7"
                            @mouseenter="chartHover = { idx: i, time: pt.time, qidian: pt.qv, zongheng: pt.zv, px: pt.x / 8, py: Math.min(pt.qy, pt.zy) / 2 }" />
                    <!-- Hover Vertical Line -->
                    <line v-if="chartHover" :x1="chartPoints[chartHover.idx]?.x" y1="0" :x2="chartPoints[chartHover.idx]?.x" y2="200" stroke="#6366f1" stroke-width="1" stroke-dasharray="3 3" opacity="0.4" />
                 </svg>
              </div>
              <div v-else class="flex-1 flex items-center justify-center text-slate-400 text-sm">
                  <Activity class="w-5 h-5 mr-2 opacity-40" /> 等待采集数据...
              </div>
          </div>

          <!-- 最近采集书籍列表 -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl shadow-sm overflow-hidden">
              <div class="px-6 pt-5 pb-4 flex items-center justify-between border-b border-slate-100/80">
                 <h3 class="font-bold text-base text-slate-900 flex items-center gap-2">
                    <BookOpen class="w-5 h-5 text-indigo-600" />
                    最近采集入库书籍
                 </h3>
                 <div class="flex items-center gap-3">
                    <!-- 日期筛选 -->
                    <div class="flex items-center gap-2">
                       <input 
                          v-model="dateFilter" 
                          type="date" 
                          @change="currentPage = 1; fetchPipelineStats()"
                          class="px-2 py-1 text-xs border border-slate-200 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          placeholder="选择日期"
                       />
                       <button v-if="dateFilter" @click="dateFilter = ''; currentPage = 1; fetchPipelineStats()"
                               class="text-xs text-slate-400 hover:text-slate-600">
                          清除
                       </button>
                    </div>
                    <!-- 去重开关 -->
                    <label class="flex items-center gap-1.5 text-xs text-slate-600 cursor-pointer select-none">
                       <input 
                          type="checkbox" 
                          v-model="dedupEnabled" 
                          @change="currentPage = 1; fetchPipelineStats()"
                          class="w-3.5 h-3.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                       />
                       <span>去重</span>
                    </label>
                    <div class="w-px h-4 bg-slate-200 mx-1"></div>
                    <!-- 平台切换按钮 -->
                    <div class="flex items-center gap-1 bg-slate-100/80 rounded-lg p-1">
                       <button @click="switchPlatform('all')" 
                               :class="platformFilter === 'all' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                               class="px-3 py-1 text-xs font-bold rounded-md transition-all">全部</button>
                       <button @click="switchPlatform('qidian')" 
                               :class="platformFilter === 'qidian' ? 'bg-blue-500 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                               class="px-3 py-1 text-xs font-bold rounded-md transition-all">起点</button>
                       <button @click="switchPlatform('zongheng')" 
                               :class="platformFilter === 'zongheng' ? 'bg-rose-500 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                               class="px-3 py-1 text-xs font-bold rounded-md transition-all">纵横</button>
                    </div>
                    <span class="text-xs text-slate-400 font-mono">共 {{ pagination.total }} 条</span>
                 </div>
              </div>
              <div v-if="recentCrawledBooks.length > 0">
                 <table class="w-full text-left">
                    <thead>
                       <tr class="text-xs font-bold text-slate-500 uppercase tracking-widest bg-slate-50/50 border-b border-slate-100">
                          <th class="px-6 py-3">#</th>
                          <th class="px-4 py-3">书名</th>
                          <th class="px-4 py-3 text-center">平台</th>
                          <th class="px-4 py-3 text-right">月票</th>
                          <th class="px-4 py-3 text-center">排名</th>
                          <th class="px-4 py-3 text-right">采集时间</th>
                       </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                       <tr v-for="(book, idx) in recentCrawledBooks" :key="idx" class="hover:bg-indigo-50/30 transition-colors group">
                          <td class="px-6 py-3 text-xs text-slate-400 font-mono">{{ (currentPage - 1) * pageSize + idx + 1 }}</td>
                          <td class="px-4 py-3">
                             <span class="font-bold text-slate-900 text-sm truncate max-w-[240px] inline-block">{{ book.title }}</span>
                          </td>
                          <td class="px-4 py-3 text-center">
                             <span class="px-2 py-0.5 inline-flex items-center justify-center rounded-md font-bold text-xs"
                                   :class="book.source === 'qidian' ? 'text-blue-700 bg-blue-100 border border-blue-200' : 'text-rose-700 bg-rose-100 border border-rose-200'">
                                {{ book.source === 'qidian' ? '起点' : '纵横' }}
                             </span>
                          </td>
                          <td class="px-4 py-3 text-right font-mono text-sm font-bold" :class="book.monthly_tickets >= 10000 ? 'text-emerald-600' : 'text-slate-700'">
                             {{ formatNum(book.monthly_tickets) }}
                          </td>
                          <td class="px-4 py-3 text-center">
                             <span class="font-mono text-xs font-bold" :class="book.rank <= 10 ? 'text-amber-600' : book.rank <= 50 ? 'text-slate-700' : 'text-slate-400'">
                                Top {{ book.rank }}
                             </span>
                          </td>
                          <td class="px-4 py-3 text-right text-xs text-slate-400 font-mono">{{ book.crawl_time }}</td>
                       </tr>
                    </tbody>
                 </table>
                 <!-- 分页控件 -->
                 <div v-if="pagination.total_pages > 1" class="px-6 py-4 flex items-center justify-between border-t border-slate-100 bg-slate-50/30">
                    <div class="text-xs text-slate-400">
                       第 {{ currentPage }} / {{ pagination.total_pages }} 页
                    </div>
                    <div class="flex items-center gap-1">
                       <button @click="goToPage(currentPage - 1)" :disabled="currentPage <= 1"
                               :class="currentPage <= 1 ? 'opacity-40 cursor-not-allowed' : 'hover:bg-slate-200'"
                               class="px-3 py-1.5 text-xs font-bold text-slate-600 bg-white rounded-md border border-slate-200 transition-all">上一页</button>
                       <div class="flex items-center gap-1 mx-2">
                          <button v-for="p in Math.min(5, pagination.total_pages)" :key="p" 
                                  @click="goToPage(p)"
                                  :class="currentPage === p ? 'bg-indigo-500 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'"
                                  class="w-7 h-7 text-xs font-bold rounded-md border border-slate-200 transition-all">{{ p }}</button>
                          <span v-if="pagination.total_pages > 5" class="text-slate-400 px-1">...</span>
                          <button v-if="pagination.total_pages > 5" @click="goToPage(pagination.total_pages)"
                                  :class="currentPage === pagination.total_pages ? 'bg-indigo-500 text-white' : 'bg-white text-slate-600 hover:bg-slate-100'"
                                  class="w-7 h-7 text-xs font-bold rounded-md border border-slate-200 transition-all">{{ pagination.total_pages }}</button>
                       </div>
                       <button @click="goToPage(currentPage + 1)" :disabled="currentPage >= pagination.total_pages"
                               :class="currentPage >= pagination.total_pages ? 'opacity-40 cursor-not-allowed' : 'hover:bg-slate-200'"
                               class="px-3 py-1.5 text-xs font-bold text-slate-600 bg-white rounded-md border border-slate-200 transition-all">下一页</button>
                    </div>
                 </div>
              </div>
              <div v-else class="text-center py-16 text-slate-400">
                 <Database class="w-10 h-10 mx-auto mb-3 opacity-15" />
                 <p class="text-sm">暂无采集记录</p>
                 <p class="text-[11px] text-slate-300 mt-1">爬虫运行后数据将在此处实时更新</p>
              </div>
          </div>

          <!-- 平台健康状态 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm flex items-center justify-between group hover:bg-white/80 transition-all">
                  <div class="flex items-center gap-4">
                     <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-xs shadow-md bg-blue-500">起</div>
                     <div>
                        <div class="font-bold text-slate-900 flex items-center gap-2">
                           起点中文网
                           <span class="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-500 rounded uppercase font-mono tracking-wider">SOURCE</span>
                        </div>
                        <div class="text-xs text-slate-500 mt-0.5">今日采集 {{ pipelineExtra.qidian_today }} 条 · 总入库 {{ formatNum(pipelineExtra.qidian_total) }}</div>
                     </div>
                  </div>
                  <div class="flex items-center gap-1.5">
                     <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                     <span class="text-xs text-emerald-600 font-bold">Online</span>
                  </div>
              </div>
              <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm flex items-center justify-between group hover:bg-white/80 transition-all">
                  <div class="flex items-center gap-4">
                     <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-xs shadow-md bg-rose-500">纵</div>
                     <div>
                        <div class="font-bold text-slate-900 flex items-center gap-2">
                           纵横中文网
                           <span class="text-[10px] px-1.5 py-0.5 bg-rose-50 text-rose-500 rounded uppercase font-mono tracking-wider">SOURCE</span>
                        </div>
                        <div class="text-xs text-slate-500 mt-0.5">今日采集 {{ pipelineExtra.zongheng_today }} 条 · 总入库 {{ formatNum(pipelineExtra.zongheng_total) }}</div>
                     </div>
                  </div>
                  <div class="flex items-center gap-1.5">
                     <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                     <span class="text-xs text-emerald-600 font-bold">Online</span>
                  </div>
              </div>
          </div>
      </div>

      <!-- ==================== TAB: AUDIT CENTER ==================== -->
      <div v-if="currentTab === 'audit'" class="animate-fade-in space-y-6">
          <!-- Gem Scan Toast -->
          <Transition name="toast">
            <div v-if="gemScanToast.show" 
                 class="fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-4 rounded-xl shadow-xl text-sm font-medium backdrop-blur-xl border"
                 :class="gemScanToast.type === 'success' 
                   ? (gemScanToast.count > 0 ? 'bg-amber-50/95 border-amber-200 text-amber-700' : 'bg-emerald-50/95 border-emerald-200 text-emerald-700')
                   : 'bg-rose-50/95 border-rose-200 text-rose-700'">
              <div class="flex items-center gap-2">
                <Sparkles v-if="gemScanToast.type === 'success' && gemScanToast.count > 0" class="w-5 h-5 text-amber-500" />
                <CheckCircle2 v-else-if="gemScanToast.type === 'success'" class="w-5 h-5 text-emerald-500" />
                <AlertOctagon v-else class="w-5 h-5 text-rose-500" />
                <span>{{ gemScanToast.message }}</span>
              </div>
            </div>
          </Transition>

          <div class="flex items-center gap-4 mb-2">
             <div class="p-3 bg-indigo-600 rounded-xl text-white shadow-lg shadow-indigo-500/30">
                <Shield class="w-6 h-6" />
             </div>
             <div>
                <h2 class="text-2xl font-serif font-bold text-slate-900">AI 决策审计中心</h2>
                <div class="text-xs text-slate-500 font-mono uppercase tracking-wide">AI Decision Audit Center · 六维多源数据融合</div>
             </div>
             <div class="ml-auto flex gap-3">
                 <button @click="triggerGemScan" :disabled="gemScanLoading" class="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 text-amber-600 rounded-lg text-sm hover:bg-amber-100 transition-colors shadow-sm font-bold disabled:opacity-50">
                    <Sparkles class="w-4 h-4" :class="{'animate-spin': gemScanLoading}" /> {{ gemScanLoading ? '扫描中...' : '挖掘潜力遗珠' }}
                 </button>
                 <button @click="fetchAuditLogs(); fetchMultiSourceOverview(); fetchAiScores()" class="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm hover:bg-slate-50 transition-colors shadow-sm">
                    <RotateCcw class="w-4 h-4 text-slate-500" :class="{'animate-spin': auditLoading}" /> 刷新
                 </button>
             </div>
          </div>

          <!-- ▸ 多源数据仪表面板 -->
          <div class="grid grid-cols-12 gap-4">
             <!-- 虚拟读者 -->
             <div class="col-span-6 lg:col-span-3 cursor-pointer" @click="showVrDetailModal = true">
                <div class="bg-gradient-to-br from-violet-50 to-purple-50 border border-violet-100 rounded-2xl p-5 shadow-sm relative overflow-hidden hover:shadow-md transition-shadow">
                   <div class="absolute -right-4 -top-4 w-16 h-16 rounded-full bg-violet-400/10"></div>
                   <div class="relative z-10">
                      <div class="flex items-center gap-2 text-violet-600 text-xs font-bold uppercase mb-3">
                         <MessageSquare class="w-4 h-4" /> 虚拟读者
                      </div>
                      <div class="text-3xl font-bold text-slate-900 mb-2">{{ multiSourceOverview.vr.total }}</div>
                      <div class="flex gap-3 text-[11px]">
                         <span class="text-emerald-600 font-bold">👍 {{ multiSourceOverview.vr.positive }}</span>
                         <span class="text-slate-500 font-medium">😐 {{ multiSourceOverview.vr.neutral }}</span>
                         <span class="text-rose-500 font-bold">👎 {{ multiSourceOverview.vr.negative }}</span>
                      </div>
                   </div>
                </div>
             </div>
             <!-- AI 评分表 -->
             <div class="col-span-6 lg:col-span-3 cursor-pointer" @click="showAiEvalModal = true">
                <div class="bg-gradient-to-br from-sky-50 to-cyan-50 border border-sky-100 rounded-2xl p-5 shadow-sm relative overflow-hidden hover:shadow-md transition-shadow">
                   <div class="absolute -right-4 -top-4 w-16 h-16 rounded-full bg-sky-400/10"></div>
                   <div class="relative z-10">
                      <div class="flex items-center gap-2 text-sky-600 text-xs font-bold uppercase mb-3">
                         <BarChart3 class="w-4 h-4" /> AI 评分表
                      </div>
                      <div class="text-3xl font-bold text-slate-900 mb-2">{{ multiSourceOverview.ai_eval.total }} <span class="text-sm font-normal text-slate-400">本</span></div>
                      <div class="text-[11px] text-slate-500">
                         均分 <span class="font-bold text-sky-600">{{ multiSourceOverview.ai_eval.avg_overall }}</span> · 
                         商业 <span class="font-bold">{{ multiSourceOverview.ai_eval.avg_commercial }}</span>
                      </div>
                   </div>
                </div>
             </div>
             <!-- 实时监控 -->
             <div class="col-span-6 lg:col-span-3 cursor-pointer" @click="showRealtimeModal = true">
                <div class="bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100 rounded-2xl p-5 shadow-sm relative overflow-hidden hover:shadow-md transition-shadow">
                   <div class="absolute -right-4 -top-4 w-16 h-16 rounded-full bg-emerald-400/10"></div>
                   <div class="relative z-10">
                      <div class="flex items-center gap-2 text-emerald-600 text-xs font-bold uppercase mb-3">
                         <Radar class="w-4 h-4" /> 实时监控
                      </div>
                      <div class="text-3xl font-bold text-slate-900 mb-2">{{ multiSourceOverview.realtime.active_books }} <span class="text-sm font-normal text-slate-400">本</span></div>
                      <div class="text-[11px] text-slate-500">
                         最新采集 <span class="font-bold text-emerald-600">{{ multiSourceOverview.realtime.last_crawl }}</span>
                      </div>
                   </div>
                </div>
             </div>
             <!-- 审计报告 -->
             <div class="col-span-6 lg:col-span-3 cursor-pointer" @click="showAuditModal = true">
                <div class="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-100 rounded-2xl p-5 shadow-sm relative overflow-hidden hover:shadow-md transition-shadow">
                   <div class="absolute -right-4 -top-4 w-16 h-16 rounded-full bg-amber-400/10"></div>
                   <div class="relative z-10">
                      <div class="flex items-center gap-2 text-amber-600 text-xs font-bold uppercase mb-3">
                         <FileText class="w-4 h-4" /> 审计报告
                      </div>
                      <div class="text-3xl font-bold text-slate-900 mb-2">{{ multiSourceOverview.audit.total }}</div>
                      <div class="flex gap-3 text-[11px]">
                         <span class="text-amber-600 font-bold">💎 {{ multiSourceOverview.audit.gems }}</span>
                         <span class="text-blue-600 font-bold">🌍 {{ multiSourceOverview.audit.global_gems }}</span>
                         <span class="text-indigo-600 font-bold">🔬 {{ multiSourceOverview.audit.deep_audits }}</span>
                      </div>
                   </div>
                </div>
             </div>
          </div>

          <!-- ▸ 深度 AI 审计 -->
          <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-sm">
             <div class="flex items-center gap-4">
                <div class="flex items-center gap-2 text-slate-700 font-bold text-sm flex-shrink-0">
                   <Scan class="w-4 h-4 text-indigo-500" /> 单本深度 AI 审计
                </div>
                <div class="flex-1 flex gap-2">
                   <input v-model="deepScanQuery" @keyup.enter="triggerDeepScan" type="text" placeholder="输入书名，发起六维数据融合深度审计..."
                          class="flex-1 h-10 px-4 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
                   <button @click="triggerDeepScan" :disabled="deepScanLoading"
                           class="flex items-center gap-2 px-5 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 transition-colors disabled:opacity-50 shadow-md shadow-indigo-500/20">
                      <Scan class="w-4 h-4" :class="{'animate-spin': deepScanLoading}" />
                      {{ deepScanLoading ? '审计中...' : '发起深度审计' }}
                   </button>
                </div>
             </div>
             
             <!-- 深度审计结果 -->
             <div v-if="deepScanResult" class="mt-4 p-5 bg-gradient-to-br from-indigo-50/50 to-violet-50/50 border border-indigo-100 rounded-xl">
                <div class="flex items-center justify-between mb-3">
                   <div class="flex items-center gap-3">
                      <span class="text-lg font-bold text-slate-900">📋 《{{ deepScanResult.title }}》</span>
                      <span class="px-2.5 py-1 bg-indigo-100 text-indigo-700 rounded-md text-xs font-bold">模型评分 {{ deepScanResult.model_score?.toFixed(1) }}</span>
                   </div>
                   <div class="flex gap-2">
                      <span v-for="(v, k) in deepScanResult.data_sources" :key="k" 
                            class="px-2 py-0.5 rounded text-[10px] font-bold"
                            :class="v ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'">
                         {{ String(k) === 'vr_comments' ? '虚拟读者' : String(k) === 'ai_eval' ? 'AI评分' : String(k) === 'global_stats' ? '出海分析' : String(k) === 'realtime_trend' ? '实时监控' : 'XGBoost' }}
                         {{ v ? '✓' : '✗' }}
                      </span>
                   </div>
                   <button @click="exportAuditReport(deepScanResult.report, deepScanResult.title, deepScanResult.model_score)"
                           class="flex items-center gap-1.5 px-3 py-1.5 bg-white/80 hover:bg-white border border-slate-200 text-slate-600 rounded-lg text-xs font-bold transition-colors ml-auto">
                      <Download class="w-3.5 h-3.5" /> 导出报告
                   </button>
                </div>
                <div class="prose prose-sm prose-slate max-w-none text-sm leading-relaxed whitespace-pre-wrap bg-white/60 rounded-lg p-4 border border-slate-100"
                     v-html="deepScanResult.report?.replace(/\n/g, '<br>')">
                </div>
             </div>
          </div>

          <!-- ▸ 审计日志列表 -->
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm min-h-[400px] flex flex-col">
             <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
                <h3 class="font-bold text-slate-900 flex items-center gap-2">
                   <Filter class="w-4 h-4 text-indigo-500" />
                   风险预警记录
                </h3>
                <!-- Filters -->
                <div class="flex items-center gap-3">
                   <select v-model="auditFilterLevel" @change="fetchAuditLogs" class="h-9 px-3 bg-white/70 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 shadow-sm">
                      <option value="">所有风险等级</option>
                      <option value="High">高风险 (High)</option>
                      <option value="Medium">中风险 (Medium)</option>
                      <option value="Low">低风险 (Low)</option>
                      <option value="Positive">正向 (Positive)</option>
                   </select>
                   <select v-model="auditFilterStatus" @change="fetchAuditLogs" class="h-9 px-3 bg-white/70 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 shadow-sm">
                      <option value="">所有状态</option>
                      <option value="Pending">待复核 (Pending)</option>
                      <option value="Resolved">已解决 (Resolved)</option>
                      <option value="Ignored">已忽略 (Ignored)</option>
                   </select>
                </div>
             </div>
             
             <!-- List content -->
             <div class="flex-1 space-y-4 pb-6 overflow-y-auto pr-2 custom-scrollbar">
                <div v-if="auditLoading && auditLogs.length === 0" class="flex items-center justify-center py-20 text-indigo-500">
                    <div class="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
                <div v-else-if="auditLogs.length === 0" class="flex flex-col items-center justify-center py-20 text-slate-400">
                   <CheckCircle2 class="w-12 h-12 text-emerald-300 mb-3 opacity-50" />
                   <div class="text-sm font-bold">暂无审计预警记录</div>
                </div>
                
                <div v-for="log in auditLogs" :key="log.id" class="group flex flex-col p-5 rounded-xl bg-white border border-slate-100 hover:border-indigo-200 hover:shadow-md transition-all">
                   <div class="flex items-center justify-between mb-3 border-b border-slate-50 pb-3">
                      <div class="flex items-center gap-3">
                         <div class="font-bold text-slate-900 text-lg">
                             《{{ log.book_title || log.book_id }}》
                         </div>
                         <span class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider"
                               :class="log.risk_level === 'High' ? 'bg-rose-50 text-rose-600 border border-rose-100' : (log.risk_level === 'Medium' ? 'bg-amber-50 text-amber-600 border border-amber-100' : (log.risk_level === 'Positive' ? 'bg-indigo-50 text-indigo-600 border border-indigo-100' : 'bg-emerald-50 text-emerald-600 border border-emerald-100'))">
                            {{ log.risk_level }} Risk
                         </span>
                         <span class="px-2 py-0.5 rounded-md text-[10px] bg-slate-100 text-slate-600 border border-slate-200">
                            {{ log.risk_type }}
                         </span>
                         
                         <span v-if="log.status === 'Resolved' || log.status === 'RESOLVED'" class="flex items-center gap-1 text-[11px] font-bold text-emerald-500 ml-2">
                            <CheckCircle2 class="w-3.5 h-3.5" /> 已解决
                         </span>
                         <span v-else-if="log.status === 'Ignored'" class="flex items-center gap-1 text-[11px] font-bold text-slate-400 ml-2">
                            <EyeOff class="w-3.5 h-3.5" /> 已忽略
                         </span>
                         <span v-else class="flex items-center gap-1 text-[11px] font-bold text-amber-500 ml-2">
                            <Clock class="w-3.5 h-3.5" /> 待复核
                         </span>
                      </div>
                      <div class="text-xs text-slate-500 font-mono">
                         {{ log.created_at }}
                      </div>
                   </div>
                   
                   <!-- Log Detail -->
                   <div class="flex gap-4">
                       <div class="flex-1 text-sm text-slate-600 bg-slate-50 rounded-lg p-3 border border-slate-100 font-mono leading-relaxed" v-if="log.content_snippet">
                          "{{ log.content_snippet }}"
                       </div>
                       
                       <div class="min-w-[200px] w-[240px] bg-slate-50 rounded-lg p-3 border border-slate-100 flex flex-col justify-between">
                          <div class="flex justify-between items-center text-xs mb-2">
                             <span class="text-slate-500">IP 综合评分</span>
                             <span class="font-mono font-bold" :class="scoreColor(log.ip_score || log.score).split(' ')[0]">{{ log.ip_score || log.score }}</span>
                          </div>
                          <div class="flex justify-between items-center text-xs mb-3">
                             <span class="text-slate-500">触发来源</span>
                             <span class="text-slate-800 font-bold truncate max-w-[120px]" :title="log.trigger_source">{{ log.trigger_source || 'AI 探测' }}</span>
                          </div>
                          
                          <!-- Actions -->
                          <div class="flex gap-2">
                              <button v-if="log.status === 'Pending' || log.status === 'PENDING'" @click="resolveAuditLog(log.id, 'resolve')" class="flex-1 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded drop-shadow-sm text-xs font-bold transition-colors">标记解决</button>
                              <button v-if="log.status === 'Pending' || log.status === 'PENDING'" @click="resolveAuditLog(log.id, 'ignore')" class="flex-1 py-1.5 px-3 bg-white border border-slate-200 hover:bg-slate-100 text-slate-500 rounded drop-shadow-sm text-xs font-bold transition-colors">忽略</button>
                              <!-- 有报告时显示展开/收起 -->
                              <button v-if="log.markdown_report && log.markdown_report.length > 100" @click="toggleLogExpand(log.id)" 
                                      class="flex-1 py-1.5 bg-violet-50 hover:bg-violet-100 text-violet-600 rounded drop-shadow-sm text-xs font-bold transition-colors flex items-center justify-center gap-1">
                                 <FileText class="w-3 h-3" /> {{ expandedLogId === log.id ? '收起报告' : '展开报告' }}
                              </button>
                              <!-- 没有报告时显示生成按钮 -->
                              <button v-else @click="toggleLogExpand(log.id)" :disabled="reportLoading"
                                      class="flex-1 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-600 rounded drop-shadow-sm text-xs font-bold transition-colors flex items-center justify-center gap-1 disabled:opacity-50">
                                 <Sparkles class="w-3 h-3" :class="{'animate-spin': reportLoading}" /> {{ reportLoading ? '生成中...' : 'AI分析' }}
                              </button>
                          </div>
                       </div>
                   </div>
                   
                   <!-- 展开的 Markdown 报告 -->
                   <div v-if="expandedLogId === log.id && log.markdown_report" 
                        class="mt-4 p-4 bg-gradient-to-br from-slate-50 to-indigo-50/30 border border-slate-200 rounded-xl transition-all">
                      <div class="flex items-center gap-2 mb-3 pb-2 border-b border-slate-200">
                         <FileText class="w-4 h-4 text-indigo-500" />
                         <span class="text-sm font-bold text-slate-700">AI 深度审计报告</span>
                         <button @click="exportAuditReport(log.markdown_report, log.book_title || 'unknown', log.ip_score || log.score)"
                                 class="ml-auto flex items-center gap-1 px-2.5 py-1 bg-white/80 hover:bg-white border border-slate-200 text-slate-500 rounded-md text-[11px] font-bold transition-colors">
                            <Download class="w-3 h-3" /> 导出
                         </button>
                      </div>
                      <div class="prose prose-sm prose-slate max-w-none text-sm leading-relaxed whitespace-pre-wrap"
                           v-html="log.markdown_report.replace(/\n/g, '<br>')">
                      </div>
                   </div>
                </div>
             </div>
             
             <!-- Pagination -->
             <div class="flex justify-between items-center pt-4 border-t border-slate-200 mt-auto">
                 <div class="text-xs text-slate-500">
                    共 <span class="font-bold text-slate-800 font-mono">{{ auditTotal }}</span> 条预警记录
                 </div>
                 <div class="flex items-center gap-2">
                    <button @click="auditPage > 1 && (auditPage--, fetchAuditLogs())" :disabled="auditPage <= 1" class="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50">上一页</button>
                    <span class="text-xs font-mono font-bold">{{ auditPage }}</span>
                    <button @click="(auditPage * auditPageSize < auditTotal) && (auditPage++, fetchAuditLogs())" :disabled="auditPage * auditPageSize >= auditTotal" class="px-2 py-1 rounded bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50">下一页</button>
                 </div>
             </div>
          </div>

          <!-- ▸ AI 评分表 Top 排行 -->
          <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm overflow-hidden">
             <div class="px-6 pt-5 pb-4 flex items-center justify-between border-b border-slate-100/80">
                <h3 class="font-bold text-base text-slate-900 flex items-center gap-2">
                   <BarChart3 class="w-5 h-5 text-sky-600" />
                   AI 六维评分排行 <span class="text-xs text-slate-400 font-normal ml-1">ip_ai_evaluation</span>
                </h3>
             </div>
             <div v-if="aiScoresLoading" class="flex items-center justify-center py-12">
                <div class="w-6 h-6 border-2 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
             </div>
             <div v-else-if="aiScores.length > 0">
                <table class="w-full text-left">
                   <thead>
                      <tr class="text-xs font-bold text-slate-500 uppercase tracking-widest bg-slate-50/50 border-b border-slate-100">
                         <th class="px-6 py-3">#</th>
                         <th class="px-4 py-3">书名</th>
                         <th class="px-4 py-3 text-center">综合分</th>
                         <th class="px-4 py-3 text-center">故事</th>
                         <th class="px-4 py-3 text-center">角色</th>
                         <th class="px-4 py-3 text-center">世界观</th>
                         <th class="px-4 py-3 text-center">商业</th>
                         <th class="px-4 py-3 text-center">改编</th>
                      </tr>
                   </thead>
                   <tbody class="divide-y divide-slate-100">
                      <tr v-for="(item, idx) in paginatedAiScores" :key="idx" class="hover:bg-sky-50/30 transition-colors">
                         <td class="px-6 py-3">
                            <span class="w-6 h-6 rounded-lg text-xs font-extrabold flex items-center justify-center shadow-sm"
                                  :class="(aiScoresPage - 1) * aiScoresPageSize + idx < 3 ? 'bg-amber-100 text-amber-700 border border-amber-200' : 'bg-slate-100 text-slate-500 border border-slate-200'">{{ (aiScoresPage - 1) * aiScoresPageSize + idx + 1 }}</span>
                         </td>
                         <td class="px-4 py-3 font-bold text-sm text-slate-900 truncate max-w-[200px]">{{ item.title }}</td>
                         <td class="px-4 py-3 text-center">
                            <span class="font-mono font-extrabold text-sm" :class="item.overall_score >= 80 ? 'text-emerald-600' : item.overall_score >= 60 ? 'text-sky-600' : 'text-slate-500'">{{ item.overall_score }}</span>
                         </td>
                         <td class="px-4 py-3 text-center font-mono text-sm text-slate-600">{{ item.story_score }}</td>
                         <td class="px-4 py-3 text-center font-mono text-sm text-slate-600">{{ item.character_score }}</td>
                         <td class="px-4 py-3 text-center font-mono text-sm text-slate-600">{{ item.world_score }}</td>
                         <td class="px-4 py-3 text-center font-mono text-sm text-slate-600">{{ item.commercial_score }}</td>
                         <td class="px-4 py-3 text-center font-mono text-sm text-slate-600">{{ item.adaptation_score || '--' }}</td>
                      </tr>
                   </tbody>
                </table>
                <!-- 分页控制 -->
                <div class="flex items-center justify-between px-6 py-4 border-t border-slate-100">
                   <div class="text-xs text-slate-500">
                      共 {{ aiScores.length }} 条，第 {{ aiScoresPage }} / {{ aiScoresTotalPages }} 页
                   </div>
                   <div class="flex items-center gap-2">
                      <button @click="aiScoresPage--" :disabled="aiScoresPage <= 1"
                              class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors"
                              :class="aiScoresPage <= 1 ? 'bg-slate-50 text-slate-300 border-slate-200 cursor-not-allowed' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'">
                         上一页
                      </button>
                      <button @click="aiScoresPage++" :disabled="aiScoresPage >= aiScoresTotalPages"
                              class="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors"
                              :class="aiScoresPage >= aiScoresTotalPages ? 'bg-slate-50 text-slate-300 border-slate-200 cursor-not-allowed' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'">
                         下一页
                      </button>
                   </div>
                </div>
             </div>
             <div v-else class="text-center py-12 text-slate-400">
                <BarChart3 class="w-10 h-10 mx-auto mb-3 opacity-15" />
                <p class="text-sm">暂无 AI 评分数据</p>
             </div>
          </div>

      </div>


      <!-- ==================== TAB: PLATFORM MONITOR ==================== -->
      <div v-if="currentTab === 'platform'" class="animate-fade-in space-y-6">

         <!-- ▸ 全局平台数据筛选器 -->
         <div class="flex items-center gap-2 bg-white/70 backdrop-blur-xl border border-white/50 rounded-xl p-1.5 w-max shadow-sm mx-auto mb-2">
            <button @click="platformFilter = 'all'" class="px-5 py-1.5 rounded-lg text-sm font-bold transition-all"
                    :class="platformFilter === 'all' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'">
               全部监控源
            </button>
            <button @click="platformFilter = 'qidian'" class="px-5 py-1.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2"
                    :class="platformFilter === 'qidian' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'">
               <span class="w-1.5 h-1.5 rounded-full" :class="platformFilter === 'qidian' ? 'bg-white' : 'bg-blue-500'"></span> 起点中文网
            </button>
            <button @click="platformFilter = 'zongheng'" class="px-5 py-1.5 rounded-lg text-sm font-bold transition-all flex items-center gap-2"
                    :class="platformFilter === 'zongheng' ? 'bg-rose-500 text-white shadow-md' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'">
               <span class="w-1.5 h-1.5 rounded-full" :class="platformFilter === 'zongheng' ? 'bg-white' : 'bg-rose-500'"></span> 纵横中文网
            </button>
         </div>

         <!-- ▸ 顶部平台概览卡片 + 调度控制 -->
         <div class="grid grid-cols-12 gap-5">
            <!-- 平台卡片 -->
            <div v-if="platformLoading" class="col-span-12 lg:col-span-8 flex items-center justify-center py-12">
               <div class="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <div v-else class="col-span-12 lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
               <div v-for="p in platformStatus" :key="p.name" 
                    class="relative rounded-2xl p-5 border border-white/50 shadow-sm overflow-hidden group hover:shadow-md transition-all"
                    :class="p.key === 'qidian' ? 'bg-gradient-to-br from-blue-50 to-indigo-50' : 'bg-gradient-to-br from-rose-50 to-orange-50'">
                  <!-- 装饰背景圆 -->
                  <div class="absolute -right-6 -top-6 w-24 h-24 rounded-full opacity-10"
                       :class="p.key === 'qidian' ? 'bg-blue-500' : 'bg-rose-500'"></div>
                  <div class="relative z-10">
                     <div class="flex items-center justify-between mb-4">
                        <div class="flex items-center gap-3">
                           <div class="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold text-white shadow-md"
                                :class="p.key === 'qidian' ? 'bg-gradient-to-br from-blue-500 to-indigo-600' : 'bg-gradient-to-br from-rose-500 to-orange-600'">
                              {{ p.name.charAt(0) }}
                           </div>
                           <div>
                              <div class="font-bold text-slate-800">{{ p.name }}</div>
                              <div class="text-[10px] font-mono text-slate-400 uppercase tracking-wider">SOURCE · {{ p.key }}</div>
                           </div>
                        </div>
                        <span class="px-2.5 py-1 rounded-full text-[10px] font-bold"
                              :class="p.status === 'Normal' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'">
                           {{ p.status === 'Normal' ? '● 正常' : '● 异常' }}
                        </span>
                     </div>
                     <div class="flex items-end justify-between">
                        <div>
                           <div class="text-3xl font-bold text-slate-900 tracking-tight">{{ formatNum(p.books) }}</div>
                           <div class="text-[11px] text-slate-500 mt-0.5">收录书籍</div>
                        </div>
                        <div class="text-right">
                           <div class="text-xs font-mono text-slate-600">{{ p.last_crawl }}</div>
                           <div class="text-[10px] text-slate-400">最后采集</div>
                        </div>
                     </div>
                  </div>
               </div>
            </div>

            <!-- 调度控制面板 -->
            <div class="col-span-12 lg:col-span-4">
               <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-sm h-full flex flex-col">
                  <div class="flex items-center justify-between mb-4">
                    <h3 class="font-bold text-sm text-slate-900 flex items-center gap-2">
                      <Clock class="w-4 h-4 text-indigo-600" />
                      定时调度
                    </h3>
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold"
                          :class="spiderSchedulerStatus.is_running ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'">
                      {{ spiderSchedulerStatus.is_running ? '● 守护中' : '○ 已停止' }}
                    </span>
                  </div>
                  
                  <div class="space-y-2.5 flex-1 text-xs">
                     <!-- 状态 -->
                     <div class="bg-slate-50/80 rounded-lg p-2.5 border border-slate-100">
                        <span class="text-slate-500">状态：</span>
                        <span class="font-medium text-slate-800">{{ spiderSchedulerStatus.status }}</span>
                     </div>
                     
                     <!-- 平台选择 -->
                     <div class="flex gap-1.5">
                        <button v-for="opt in [{key:'all',label:'全部'},{key:'qidian',label:'起点'},{key:'zongheng',label:'纵横'}]" :key="opt.key"
                                @click="spiderSchedulerStatus.target_platform = opt.key; updateSchedulerConfig()"
                                class="flex-1 px-2 py-1.5 rounded-lg text-[11px] font-bold transition-all border"
                                :class="spiderSchedulerStatus.target_platform === opt.key ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm' : 'bg-white text-slate-500 border-slate-200 hover:border-indigo-300'">
                           {{ opt.label }}
                        </button>
                     </div>
                     
                     <!-- 间隔滑块 -->
                     <div class="bg-slate-50/80 rounded-lg p-2.5 border border-slate-100">
                        <div class="flex justify-between text-[10px] text-slate-500 font-bold mb-1.5">
                           <span>间隔</span>
                           <span class="text-indigo-600">{{ spiderSchedulerStatus.interval_minutes }}min</span>
                        </div>
                        <input type="range" min="30" max="480" step="30" 
                               :value="spiderSchedulerStatus.interval_minutes"
                               @change="(e: Event) => { spiderSchedulerStatus.interval_minutes = parseInt((e.target as HTMLInputElement).value); updateSchedulerConfig() }"
                               class="w-full h-1 bg-slate-200 rounded-full appearance-none cursor-pointer accent-indigo-600" />
                     </div>
                     
                     <!-- 时间 -->
                     <div class="grid grid-cols-2 gap-2">
                        <div class="bg-slate-50/80 rounded-lg px-2.5 py-2 border border-slate-100">
                           <div class="text-[9px] text-slate-400 font-bold">上次</div>
                           <div class="text-[10px] font-mono text-slate-700 truncate">{{ spiderSchedulerStatus.last_run_time || '—' }}</div>
                        </div>
                        <div class="bg-slate-50/80 rounded-lg px-2.5 py-2 border border-slate-100">
                           <div class="text-[9px] text-slate-400 font-bold">下次</div>
                           <div class="text-[10px] font-mono text-slate-700 truncate">{{ spiderSchedulerStatus.next_run_time || '—' }}</div>
                        </div>
                     </div>
                  </div>
                  
                  <!-- 操作按钮 -->
                  <div class="mt-3 flex gap-2">
                     <button v-if="!spiderSchedulerStatus.is_running" @click="toggleSpiderScheduler('start')" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg py-2 text-[11px] font-bold transition-colors shadow-sm">
                        启动调度
                     </button>
                     <button v-else @click="toggleSpiderScheduler('stop')" class="flex-1 bg-rose-50 hover:bg-rose-100 text-rose-600 border border-rose-200 rounded-lg py-2 text-[11px] font-bold transition-colors">
                        停止
                     </button>
                     <button @click="toggleSpiderScheduler('trigger')" :disabled="spiderSchedulerStatus.status.includes('正在抓取')" class="px-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-lg py-2 text-[11px] font-bold transition-colors disabled:opacity-50">
                        立即执行
                     </button>
                  </div>
               </div>
            </div>
         </div>

         <!-- ▸ 实时日志 (实时爬取可视化) -->
         <div v-if="spiderSchedulerStatus.status.includes('正在抓取') || liveLogs.length > 0" class="bg-slate-900 rounded-2xl p-5 shadow-lg min-h-[300px] flex flex-col mb-6 border border-slate-700">
             <div class="flex items-center justify-between mb-4 border-b border-slate-700/50 pb-3">
                 <h4 class="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2 font-mono">
                    <Activity class="w-4 h-4 animate-pulse" /> 爬虫实时日志终端 (Live Scraper Output)
                 </h4>
                 <div class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono border border-slate-700">
                     {{ spiderSchedulerStatus.status }}
                 </div>
             </div>
             <div class="flex-1 overflow-y-auto space-y-1.5 pr-2 custom-scrollbar font-mono text-[11px] max-h-[400px]" id="live-logs-container">
                  <div v-for="(log, i) in liveLogs" :key="i" class="text-slate-300 leading-relaxed">
                      <span class="text-indigo-400 mr-2 select-none">></span>
                      <span :class="{'text-emerald-400 font-bold': log.includes('[√]') || log.includes('success') || log.includes('成功'), 'text-amber-400': log.includes('Timeout') || log.includes('等待'), 'text-rose-400 font-bold': log.includes('❌') || log.includes('Error') || log.includes('失败')}">{{ log }}</span>
                  </div>
                  <div v-if="spiderSchedulerStatus.status.includes('正在抓取')" class="text-slate-500 animate-pulse mt-3 text-[11px]">
                       <span class="text-indigo-400 mr-2">></span>等待输出流...
                  </div>
             </div>
         </div>

         <!-- ▸ 爬取历史记录 -->
         <div v-if="spiderSchedulerStatus.crawl_history && spiderSchedulerStatus.crawl_history.length > 0">
            <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-5 shadow-sm">
               <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Server class="w-3.5 h-3.5 text-indigo-500" /> 最近爬取记录
               </h4>
               <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                  <div v-for="(h, idx) in spiderSchedulerStatus.crawl_history.slice(0, 8)" :key="idx"
                       class="flex items-center justify-between p-3 bg-white rounded-xl border border-slate-100 text-sm"
                       :title="h.error ? `错误信息: ${h.error}` : ''">
                     <div class="flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full flex-shrink-0"
                              :class="h.status === 'success' ? 'bg-emerald-500' : h.status === 'error' ? 'bg-rose-500' : 'bg-amber-500'"></span>
                        <span class="font-mono text-[11px] text-slate-600">{{ h.platform }}</span>
                     </div>
                     <span class="text-[10px] font-bold" :class="h.status === 'success' ? 'text-emerald-600' : (h.status === 'partial' ? 'text-amber-600' : 'text-rose-500')">{{ h.books_updated }}条 · {{ h.duration_sec }}s</span>
                  </div>
               </div>
            </div>
         </div>

         <!-- ▸ 实时月票走势图（美化且支持动态选择） -->
         <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm overflow-hidden flex flex-col h-[350px]">
            <div class="px-6 pt-5 pb-3 flex items-center justify-between border-b border-slate-100/50">
               <div>
                  <h3 class="font-bold text-slate-900 text-sm flex items-center gap-2 mb-3">
                     <Activity class="w-4 h-4 text-indigo-600" />
                     专属书籍走势洞察
                  </h3>
                  <!-- 书籍搜索框 + 时间粒度切换 -->
                  <div class="flex items-center gap-2">
                      <div class="relative flex items-center shadow-sm rounded-lg">
                         <div class="relative">
                            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                            <input v-model="trendSearchQuery" @keyup.enter="searchTrendBook" placeholder="输入书名搜索走势..." class="appearance-none bg-white border border-slate-200 text-slate-700 font-bold text-sm py-1.5 pl-9 pr-4 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all w-48 sm:w-64">
                         </div>
                         <button @click="searchTrendBook" class="px-4 py-1.5 bg-indigo-600 border border-indigo-600 text-white font-bold text-sm rounded-r-lg hover:bg-indigo-700 transition-all flex items-center gap-1">
                            <Search class="w-3.5 h-3.5" /> 搜索
                         </button>
                      </div>
                      <!-- 时间粒度切换 -->
                      <div class="flex bg-slate-100 rounded-lg p-0.5">
                          <button @click="trendGranularity = 'day'" :class="trendGranularity === 'day' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-3 py-1 text-xs font-bold rounded-md transition-all">日</button>
                          <button @click="trendGranularity = 'month'" :class="trendGranularity === 'month' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-3 py-1 text-xs font-bold rounded-md transition-all">月</button>
                          <button @click="trendGranularity = 'year'" :class="trendGranularity === 'year' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'" class="px-3 py-1 text-xs font-bold rounded-md transition-all">年</button>
                      </div>
                  </div>
               </div>
               <div class="flex gap-5 text-[11px] font-medium pr-2">
                  <span class="flex items-center gap-1.5"><span class="w-3 h-1 rounded-full bg-amber-500"></span> 实际月票</span>
                  <span class="flex items-center gap-1.5"><span class="w-3 h-1 rounded-full bg-indigo-400 opacity-60"></span> 预测趋势</span>
               </div>
            </div>
            
            <div class="flex-1 relative w-full h-full">
               <div v-if="realtimeLoading" class="absolute inset-0 flex items-center justify-center">
                   <div class="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
               </div>
                   <template v-else-if="realtimeTrackingData.dates.length > 0">
                   <svg viewBox="0 0 1000 260" class="w-full h-full block absolute bottom-0 left-0 right-0" preserveAspectRatio="none">
                      <defs>
                         <linearGradient id="chartAreaGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.35" />
                            <stop offset="100%" stop-color="#3b82f6" stop-opacity="0.0" />
                         </linearGradient>
                         <linearGradient id="chartLineGradient" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0%" stop-color="#8b5cf6" />
                            <stop offset="50%" stop-color="#6366f1" />
                            <stop offset="100%" stop-color="#3b82f6" />
                         </linearGradient>
                      </defs>
                      
                      <!-- 背景网格线 -->
                      <line v-for="gy in [50, 100, 150, 200]" :key="'grid-' + gy"
                            x1="90" :y1="gy" x2="950" :y2="gy" stroke="#e2e8f0" stroke-dasharray="4 6" />
                      
                      <!-- 铺满的渐变填充区域 (统一 Max 基准) -->
                      <path :d="(() => {
                         const data = realtimeTrackingData.monthly_tickets
                         if (!data || data.length < 2) return ''
                         const rawMax = Math.max(...data, 1)
                         const predMax = Math.max(...(realtimeTrackingData.predicted_tickets || [1]))
                         const max = Math.max(rawMax, predMax)
                         const chartW = 860, chartH = 160, offsetX = 90, offsetY = 40
                         const step = chartW / (data.length - 1)
                         let d = 'M' + offsetX + ',' + (offsetY + chartH)
                         data.forEach((v: number, i: number) => { d += ' L' + (offsetX + i * step) + ',' + (offsetY + chartH - (v / max) * chartH) })
                         d += ' L' + (offsetX + (data.length - 1) * step) + ',' + (offsetY + chartH) + ' Z'
                         return d
                      })()" fill="url(#chartAreaGradient)" />
                      
                      <!-- 实际月票走势线 (统一 Max 基准) -->
                      <path :d="(() => {
                         const data = realtimeTrackingData.monthly_tickets
                         if (!data || data.length < 2) return ''
                         const rawMax = Math.max(...data, 1)
                         const predMax = Math.max(...(realtimeTrackingData.predicted_tickets || [1]))
                         const max = Math.max(rawMax, predMax)
                         const chartW = 860, chartH = 160, offsetX = 90, offsetY = 40
                         const step = chartW / (data.length - 1)
                         return 'M' + data.map((v: number, i: number) => (offsetX + i * step) + ',' + (offsetY + chartH - (v / max) * chartH)).join(' L')
                      })()" fill="none" stroke="url(#chartLineGradient)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
                      <!-- 预测期望虚线 (接入模型实算基准) -->
                      <path :d="(() => {
                         const data = realtimeTrackingData.predicted_tickets
                         if (!data || data.length < 2) return ''
                         // 必须用原始数据里的 max，否则两条线 Y 轴基准不一致
                         let max = Math.max(...realtimeTrackingData.monthly_tickets, 1)
                         // 考虑到模型预测可能会大幅度超过实际，防止出界
                         max = Math.max(max, ...data)
                         const chartW = 860, chartH = 160, offsetX = 90, offsetY = 40
                         const step = chartW / (data.length - 1)
                         return 'M' + data.map((v: number, i: number) => (offsetX + i * step) + ',' + (offsetY + chartH - (v / max) * chartH)).join(' L')
                      })()" fill="none" stroke="#818cf8" stroke-opacity="0.6" stroke-dasharray="6 4" stroke-width="1.5" stroke-linecap="round" />
                      
                       <!-- 数据点高亮及悬浮响应 (根据共同的 max 进行修正) -->
                      <circle v-for="(item, i) in realtimeTrackingData.monthly_tickets.map((v: number, idx: number) => ({v, i: idx})).filter((_: any, idx: number, arr: any[]) => {
                         const total = arr.length
                         if (total <= 20) return true
                         const step = Math.ceil(total / 15)
                         return idx % step === 0 || idx === total - 1
                      })" :key="'dot-' + item.i"
                              :cx="90 + item.i * (860 / Math.max(realtimeTrackingData.monthly_tickets.length - 1, 1))"
                              :cy="(() => {
                                 const rawMax = Math.max(...realtimeTrackingData.monthly_tickets, 1)
                                 const predMax = Math.max(...(realtimeTrackingData.predicted_tickets || [1]))
                                 const finalMax = Math.max(rawMax, predMax)
                                 return 40 + 160 - (item.v / finalMax) * 160
                              })()" r="4" 
                              fill="#ffffff" stroke="#6366f1" stroke-width="2" 
                              class="cursor-pointer hover:stroke-indigo-600 transition-all duration-300 hover:r-6 shadow-sm"
                              @mouseenter="(e) => {
                                  // 这里需要补偿 SVG viewBox 在实际 DOM 中的缩放比例，不再写死 left 像素
                                  const svgRect = (e.target as SVGCircleElement).ownerSVGElement!.getBoundingClientRect();
                                  const parentRect = (e.target as SVGCircleElement).ownerSVGElement!.parentElement!.getBoundingClientRect();
                                  const cxPercent = (90 + item.i * (860 / Math.max(realtimeTrackingData.monthly_tickets.length - 1, 1))) / 1000;
                                  const cyPercent = (() => {
                                      const rawMax = Math.max(...realtimeTrackingData.monthly_tickets, 1)
                                      const predMax = Math.max(...(realtimeTrackingData.predicted_tickets || [1]))
                                      return (40 + 160 - (item.v / Math.max(rawMax, predMax)) * 160) / 260
                                  })();
                                  hoveredPoint = {
                                      x: cxPercent * parentRect.width,
                                      y: cyPercent * parentRect.height,
                                      time: realtimeTrackingData.dates[item.i],
                                      pv: item.v,
                                      uv: realtimeTrackingData.predicted_tickets[item.i] || 0
                                  }
                              }"
                              @mouseleave="hoveredPoint = null" />
                      
                      <!-- X 轴标签（采样展示） -->
                      <text v-for="(item, i) in realtimeTrackingData.dates.map((d: string, idx: number) => ({d, i: idx})).filter((_: any, idx: number, arr: any[]) => {
                         const total = arr.length
                         if (total <= 12) return true
                         const step = Math.ceil(total / 12)
                         return idx % step === 0 || idx === total - 1
                      })" :key="'xlabel-' + item.i"
                            :x="90 + item.i * (860 / Math.max(realtimeTrackingData.dates.length - 1, 1))"
                            y="235" fill="#64748b" style="font-size: 10px; font-weight: bold; font-family: ui-sans-serif, system-ui, sans-serif;" text-anchor="middle">
                         {{ item.d }}
                      </text>

                      <!-- Y 轴标注拉到最后面渲染，永远在上层不被遮罩 -->
                      <text v-for="(gy, gi) in [50, 100, 150, 200]" :key="'ylabel-' + gy"
                            x="75" :y="gy + 4" fill="#64748b" style="font-size: 10px; font-weight: bold; font-family: ui-sans-serif, system-ui, sans-serif;" text-anchor="end">
                         {{ (() => { const max = Math.max(...realtimeTrackingData.monthly_tickets, 1); return formatNum(Math.round(max * (1 - (gi) / 4))) })() }}
                      </text>
                      
                   </svg>
                   
                    <!-- Hover Tooltip 悬浮框 (改为基于父级 flex-1 容器相对浮动，并移除硬编码 bottom) -->
                   <div v-if="hoveredPoint && hoveredPoint.pv !== undefined" 
                        class="absolute pointer-events-none z-30 transition-all duration-200 shadow-2xl"
                        :style="`left: ${hoveredPoint.x}px; top: ${(hoveredPoint.y || 150) - 70}px; transform: translateX(-50%);`">
                       <div class="bg-slate-900 border border-slate-700/50 text-white rounded-lg p-2.5 text-xs flex flex-col gap-1.5 min-w-[140px]">
                           <div class="text-slate-400 font-medium pb-1.5 border-b border-slate-700/50 flex justify-between">
                               <span>{{ selectedBookTrend || '历史数据' }}</span>
                               <span>{{ hoveredPoint.time }}</span>
                           </div>
                           <div class="flex justify-between mt-1 items-center">
                               <span class="flex items-center gap-1.5"><div class="w-2 h-2 rounded-full bg-indigo-500"></div>实际月票</span>
                               <span class="font-bold text-indigo-200">{{ formatNum(hoveredPoint.pv) }}</span>
                           </div>
                           <div class="flex justify-between mt-0.5 items-center">
                               <span class="flex items-center gap-1.5"><div class="w-2 h-2 rounded-full border border-indigo-400 bg-transparent"></div>预测基准</span>
                               <span class="font-bold text-slate-300">{{ formatNum(hoveredPoint.uv) }}</span>
                           </div>
                       </div>
                       <!-- 向下的箭头 -->
                       <div class="absolute -bottom-[5px] left-1/2 -translate-x-1/2 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-slate-900 drop-shadow-md"></div>
                   </div>
                   </template>
               <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-slate-400">
                   <Activity class="w-10 h-10 mb-3 opacity-15" />
                   <span class="text-sm">尚未有实时采集数据</span>
                   <span class="text-[11px] text-slate-300 mt-1">启动爬虫后数据将写入 novel_realtime_tracking 表</span>
               </div>
            </div>
         </div>

         <!-- ▸ 每周月票增幅 vs IP评分 -->
         <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm overflow-hidden">
            <div class="px-6 pt-5 pb-4 flex items-center justify-between border-b border-slate-100/80">
               <h3 class="font-bold text-base text-slate-900 flex items-center gap-2">
                  <TrendingUp class="w-5 h-5 text-indigo-600" />
                  月票增幅 × IP 评分对比
               </h3>
                <div class="flex items-center gap-2 text-xs">
                  <span class="px-2.5 py-1 rounded-full bg-rose-500 text-white font-bold shadow-sm">🔥 爆款</span>
                  <span class="px-2.5 py-1 rounded-full bg-purple-50 text-purple-600 border border-purple-100 font-bold">🐴 黑马</span>
                  <span class="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-100 font-bold">📈 上升</span>
                  <span class="px-2.5 py-1 rounded-full bg-slate-50 text-slate-500 border border-slate-100 font-bold">📉 走弱</span>
               </div>
            </div>
            
            <div v-if="weeklyGrowthLoading" class="flex items-center justify-center py-20">
               <div class="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <div v-else-if="weeklyGrowthData.length > 0">
               <table class="w-full text-left">
                  <thead>
                     <tr class="text-xs font-bold text-slate-500 uppercase tracking-widest bg-slate-50/50 border-b border-slate-100">
                        <th class="px-6 py-4">书名</th>
                        <th class="px-4 py-4 text-center">所属源</th>
                        <th class="px-4 py-4">月增幅 (实际 / 预测)</th>
                        <th class="px-4 py-4">增幅率 (实际 / 预测)</th>
                        <th class="px-4 py-4">总月票</th>
                        <th class="px-4 py-4 text-center">近期排名</th>
                        <th class="px-4 py-4">IP 评分</th>
                        <th class="px-4 py-4 text-center">趋势</th>
                     </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100">
                     <tr v-for="(item, idx) in weeklyGrowthData.slice(0, 20)" :key="idx" 
                         class="hover:bg-indigo-50/30 transition-colors group">
                        <td class="px-6 py-4">
                           <div class="flex items-center gap-3">
                              <span class="w-7 h-7 rounded-lg text-xs font-extrabold flex items-center justify-center flex-shrink-0 shadow-sm transition-transform group-hover:scale-110"
                                    :class="idx < 3 ? 'bg-amber-100 text-amber-700 border border-amber-200' : 'bg-slate-100 text-slate-500 border border-slate-200'">{{ idx + 1 }}</span>
                              <span class="font-extrabold text-base text-slate-900 truncate max-w-[200px]">{{ item.title }}</span>
                           </div>
                        </td>
                        <td class="px-4 py-4 text-center">
                           <span class="px-2.5 py-1 inline-flex items-center justify-center rounded-md font-bold text-xs"
                                 :class="item.source === 'qidian' ? 'text-blue-700 bg-blue-100 border border-blue-200' : 'text-rose-700 bg-rose-100 border border-rose-200'">
                              {{ item.source === 'qidian' ? '起点' : '纵横' }}
                           </span>
                        </td>
                        <td class="px-4 py-4">
                           <div class="flex flex-col gap-1">
                               <span class="font-mono text-base font-extrabold" :class="item.latest_growth > 300 ? 'text-emerald-600' : item.latest_growth > 100 ? 'text-slate-800' : 'text-slate-500'">
                                  +{{ formatNum(item.latest_growth) }}
                               </span>
                               <span class="font-mono text-xs font-medium text-indigo-400" title="模型预测增幅">
                                  估: +{{ formatNum(item.predicted_tickets - item.total_tickets + item.latest_growth || 0) }}
                               </span>
                           </div>
                        </td>
                        <td class="px-4 py-4">
                           <div class="flex flex-col gap-1">
                               <span class="font-mono text-sm font-bold" :class="item.growth_rate > 0 ? 'text-emerald-600' : 'text-rose-600'">{{ item.growth_rate > 0 ? '+' : '' }}{{ item.growth_rate }}%</span>
                               <span class="font-mono text-[11px] font-medium text-indigo-400" title="模型预测增幅率">{{ item.predicted_growth_rate > 0 ? '+' : '' }}{{ item.predicted_growth_rate || 0 }}%</span>
                           </div>
                        </td>
                        <td class="px-4 py-4 font-mono text-sm font-bold text-slate-700">{{ formatNum(item.total_tickets) }}</td>
                        <td class="px-4 py-4 text-center">
                           <span class="font-mono text-sm font-extrabold" :class="item.curr_rank <= 10 ? 'text-amber-600' : item.curr_rank <= 50 ? 'text-slate-700' : 'text-slate-400'">Top {{ item.curr_rank }}</span>
                        </td>
                        <td class="px-4 py-4">
                           <div class="flex items-center gap-2">
                              <div class="w-12 h-2 rounded-full bg-slate-200 overflow-hidden shadow-inner">
                                 <div class="h-full rounded-full transition-all" 
                                      :class="item.ip_score >= 70 ? 'bg-emerald-500' : item.ip_score >= 50 ? 'bg-amber-500' : 'bg-slate-300'"
                                      :style="{ width: item.ip_score + '%' }"></div>
                              </div>
                              <span class="font-mono font-bold text-sm" :class="item.ip_score >= 70 ? 'text-emerald-600' : item.ip_score >= 50 ? 'text-slate-800' : 'text-slate-500'">{{ item.ip_score }}</span>
                           </div>
                        </td>
                        <td class="px-4 py-4 text-center">
                           <span class="px-3 py-1 rounded-full text-xs font-bold shadow-sm" :class="trendColor(item.trend)">{{ trendLabel(item.trend) }}</span>
                        </td>
                     </tr>
                  </tbody>
               </table>
            </div>
            <div v-else class="text-center py-16 text-slate-400">
               <TrendingUp class="w-10 h-10 mx-auto mb-3 opacity-15" />
               <p class="text-sm">暂无月票追踪数据</p>
               <p class="text-[11px] text-slate-300 mt-1">启动定时爬虫后将自动采集分析</p>
            </div>
         </div>

         <!-- ▸ 实时月票排行榜 -->
         <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm overflow-hidden">
            <div class="px-6 pt-5 pb-4 flex items-center justify-between border-b border-slate-100/80">
               <h3 class="font-bold text-base text-slate-900 flex items-center gap-2">
                  <Crown class="w-5 h-5 text-amber-500" />
                  实时月票排行榜
                  <span v-if="realtimeTicketRanking.length" class="text-xs font-normal text-slate-400 ml-1">基于爬虫实时采集数据</span>
               </h3>
               <div class="flex items-center gap-3">
                  <!-- 平台切换按钮 -->
                  <div class="flex items-center gap-1 bg-slate-100 rounded-lg p-1">
                     <button @click="ticketPlatform = 'qidian'; fetchRealtimeRanking()" 
                             :class="ticketPlatform === 'qidian' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                             class="px-3 py-1 rounded-md text-xs font-medium transition-all">
                        起点
                     </button>
                     <button @click="ticketPlatform = 'zongheng'; fetchRealtimeRanking()" 
                             :class="ticketPlatform === 'zongheng' ? 'bg-white text-rose-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
                             class="px-3 py-1 rounded-md text-xs font-medium transition-all">
                        纵横
                     </button>
                  </div>
                  <button @click="fetchRealtimeRanking" class="text-xs text-indigo-600 hover:text-indigo-800 font-medium">刷新</button>
               </div>
            </div>
            <div v-if="realtimeTicketRanking.length > 0" class="divide-y divide-slate-100 max-h-[500px] overflow-y-auto">
               <div v-for="(item, idx) in realtimeTicketRanking.slice(0, 20)" :key="item.title"
                    class="flex items-center gap-3 px-6 py-3 hover:bg-amber-50/30 transition-colors">
                  <span class="w-7 h-7 rounded-lg text-xs font-extrabold flex items-center justify-center flex-shrink-0 shadow-sm"
                        :class="idx < 3 ? 'bg-gradient-to-br from-amber-100 to-amber-200 text-amber-700 border border-amber-300' : 'bg-slate-100 text-slate-500 border border-slate-200'">
                     {{ idx + 1 }}
                  </span>
                  <div class="flex-1 min-w-0">
                     <div class="text-sm font-bold text-slate-800 truncate">{{ item.title }}</div>
                     <span class="text-[10px] px-1.5 py-0.5 rounded font-bold"
                           :class="ticketPlatform === 'qidian' ? 'text-blue-600 bg-blue-50' : 'text-rose-600 bg-rose-50'">
                        {{ ticketPlatform === 'qidian' ? '起点' : '纵横' }}
                     </span>
                  </div>
                  <div class="text-right flex-shrink-0">
                     <div class="text-sm font-mono font-bold" :class="idx < 3 ? 'text-amber-600' : 'text-slate-600'">
                        {{ formatNum(item.monthly_tickets) }}
                     </div>
                     <div class="text-[10px] text-slate-400">{{ item.last_crawl }}</div>
                  </div>
               </div>
            </div>
            <div v-else class="text-center py-10 text-slate-400">
               <Crown class="w-8 h-8 mx-auto mb-2 opacity-15" />
               <p class="text-sm">暂无实时采集数据</p>
               <p class="text-[11px] text-slate-300 mt-1">启动爬虫后数据将自动写入 tracking 表</p>
            </div>
         </div>

      </div>

      <!-- ==================== TAB: SETTINGS ==================== -->
      <div v-if="currentTab === 'settings'" class="space-y-6 animate-fade-in">

        <!-- 设置页顶部 Toast -->
        <Transition name="toast">
          <div v-if="settingsToast.show" 
               class="fixed top-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-xl text-sm font-medium backdrop-blur-xl border"
               :class="settingsToast.type === 'success' ? 'bg-emerald-50/95 border-emerald-200 text-emerald-700' : 'bg-rose-50/95 border-rose-200 text-rose-700'">
            <CheckCircle2 v-if="settingsToast.type === 'success'" class="w-4 h-4" />
            <AlertOctagon v-else class="w-4 h-4" />
            {{ settingsToast.message }}
          </div>
        </Transition>

        <!-- 加载状态 -->
        <div v-if="settingsLoading" class="flex items-center justify-center py-20">
          <RefreshCw class="w-6 h-6 text-indigo-400 animate-spin" />
          <span class="ml-3 text-slate-400 text-sm">加载设置中…</span>
        </div>

        <template v-else>

        <!-- ===== 0. 个人信息 ===== -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-5">
            <div class="flex items-center gap-3">
              <div class="p-2.5 rounded-xl bg-indigo-500/10"><Users class="w-5 h-5 text-indigo-600" /></div>
              <div>
                <h3 class="font-bold text-slate-900">个人信息</h3>
                <p class="text-xs text-slate-400">修改管理员账户信息</p>
              </div>
            </div>
            <button @click="saveAdminProfile" :disabled="profileSaving"
                    class="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50">
              <Save class="w-4 h-4" /> 保存
            </button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- 头像上传 -->
            <div class="flex flex-col items-center gap-3">
              <div class="w-24 h-24 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 text-white flex items-center justify-center font-bold shadow-lg shadow-indigo-500/20 overflow-hidden">
                <img v-if="user?.avatar" :src="`http://localhost:5000${user.avatar}`" alt="Avatar" class="w-full h-full object-cover" />
                <span v-else class="text-3xl">{{ user?.username?.charAt(0).toUpperCase() || 'A' }}</span>
              </div>
              <label class="cursor-pointer">
                <input type="file" accept="image/*" @change="handleAvatarUpload" class="hidden" />
                <span class="text-xs text-indigo-600 hover:text-indigo-700 font-medium">更换头像</span>
              </label>
            </div>
            <!-- 基本信息 -->
            <div class="md:col-span-2 space-y-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-semibold text-slate-500 mb-1.5">用户名</label>
                  <input v-model="profileForm.username" type="text" placeholder="用户名"
                         class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
                </div>
                <div>
                  <label class="block text-xs font-semibold text-slate-500 mb-1.5">邮箱</label>
                  <input v-model="profileForm.email" type="email" placeholder="邮箱地址"
                         class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
                </div>
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-500 mb-1.5">新密码 <span class="text-slate-300">(留空则不修改)</span></label>
                <input v-model="profileForm.password" type="password" placeholder="输入新密码"
                       class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
              </div>
            </div>
          </div>
        </div>

        <!-- ===== 1. AI 大模型配置 ===== -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-5">
            <div class="flex items-center gap-3">
              <div class="p-2.5 rounded-xl bg-violet-500/10"><Bot class="w-5 h-5 text-violet-600" /></div>
              <div>
                <h3 class="font-bold text-slate-900">AI 大模型配置</h3>
                <p class="text-xs text-slate-400">管理推理服务接入参数</p>
              </div>
            </div>
            <button @click="saveSettings('ai')" :disabled="settingsSaving"
                    class="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50">
              <Save class="w-4 h-4" /> 保存
            </button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">Provider 服务商</label>
              <select v-model="settingsData.ai.provider" class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none">
                <option value="github">GitHub Models</option>
                <option value="deepseek">DeepSeek</option>
                <option value="gemini">Gemini (本地)</option>
                <option value="custom">自定义</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">模型名称</label>
              <input v-model="settingsData.ai.model_name" type="text" placeholder="gpt-4o / deepseek-chat" 
                     class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
            </div>
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">Base URL</label>
              <div class="flex items-center gap-2">
                <Link class="w-4 h-4 text-slate-400 flex-shrink-0" />
                <input v-model="settingsData.ai.base_url" type="text" placeholder="https://api.deepseek.com/v1" 
                       class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none font-mono" />
              </div>
            </div>
            <div class="md:col-span-2">
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">API Key</label>
              <div class="flex items-center gap-2">
                <KeyRound class="w-4 h-4 text-slate-400 flex-shrink-0" />
                <input v-model="settingsData.ai.api_key" type="text" placeholder="sk-xxxxx" 
                       class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none font-mono" />
              </div>
              <p class="text-[11px] text-slate-400 mt-1 ml-6">已脱敏显示，留空或不修改则保留原值</p>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">Temperature 温度</label>
              <input v-model.number="settingsData.ai.temperature" type="number" min="0" max="2" step="0.1" 
                     class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">Max Tokens 最大长度</label>
              <input v-model.number="settingsData.ai.max_tokens" type="number" min="256" max="16384" step="256" 
                     class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
            </div>
          </div>
        </div>

        <!-- ===== 2. 爬虫调度器配置 ===== -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-5">
            <div class="flex items-center gap-3">
              <div class="p-2.5 rounded-xl bg-emerald-500/10"><Bug class="w-5 h-5 text-emerald-600" /></div>
              <div>
                <h3 class="font-bold text-slate-900">爬虫调度器</h3>
                <p class="text-xs text-slate-400">配置自动数据采集策略</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span class="flex items-center gap-1.5 text-xs font-medium" :class="settingsData.spider.is_running ? 'text-emerald-600' : 'text-slate-400'">
                <span class="w-2 h-2 rounded-full" :class="settingsData.spider.is_running ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'"></span>
                {{ settingsData.spider.is_running ? '运行中' : '已停止' }}
              </span>
              <button @click="saveSettings('spider')" :disabled="settingsSaving" 
                      class="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50">
                <Save class="w-4 h-4" /> 保存
              </button>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">调度间隔 (分钟)</label>
              <input v-model.number="settingsData.spider.interval_minutes" type="number" min="30" max="480" step="10" 
                     class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
              <p class="text-[11px] text-slate-400 mt-1">范围 30~480 分钟 (0.5h ~ 8h)</p>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">目标平台</label>
              <select v-model="settingsData.spider.target_platform" class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none">
                <option value="all">全部平台</option>
                <option value="qidian">起点中文网</option>
                <option value="zongheng">纵横中文网</option>
              </select>
            </div>
          </div>
        </div>

        <!-- ===== 3. 数据库连接 ===== -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm">
          <div class="flex items-center gap-3 mb-5">
            <div class="p-2.5 rounded-xl bg-sky-500/10"><Database class="w-5 h-5 text-sky-600" /></div>
            <div>
              <h3 class="font-bold text-slate-900">数据库连接</h3>
              <p class="text-xs text-slate-400">查看数据源状态并测试连通性</p>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- 纵横数据库 -->
            <div class="border border-slate-100 rounded-xl p-4 bg-white/40">
              <div class="flex items-center justify-between mb-3">
                <span class="text-sm font-bold text-rose-600">纵横中文网</span>
                <button @click="testDbConnection('zongheng')" :disabled="dbTesting.zongheng" 
                        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors"
                        :class="dbTesting.zongheng ? 'bg-slate-50 text-slate-400 border-slate-200' : 'bg-white text-sky-600 border-sky-200 hover:bg-sky-50'">
                  <TestTube class="w-3.5 h-3.5" :class="dbTesting.zongheng ? 'animate-spin' : ''" />
                  {{ dbTesting.zongheng ? '测试中...' : '测试连接' }}
                </button>
              </div>
              <div class="space-y-1.5 text-xs font-mono text-slate-600">
                <div class="flex justify-between"><span class="text-slate-400">Host</span> {{ settingsData.database.zongheng.host }}:{{ settingsData.database.zongheng.port }}</div>
                <div class="flex justify-between"><span class="text-slate-400">Database</span> {{ settingsData.database.zongheng.database }}</div>
                <div class="flex justify-between"><span class="text-slate-400">User</span> {{ settingsData.database.zongheng.user }}</div>
              </div>
              <div v-if="dbTestResult.zongheng.status" class="mt-3 px-3 py-2 rounded-lg text-xs font-medium"
                   :class="dbTestResult.zongheng.status === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                {{ dbTestResult.zongheng.message }}
              </div>
            </div>
            <!-- 起点数据库 -->
            <div class="border border-slate-100 rounded-xl p-4 bg-white/40">
              <div class="flex items-center justify-between mb-3">
                <span class="text-sm font-bold text-blue-600">起点中文网</span>
                <button @click="testDbConnection('qidian')" :disabled="dbTesting.qidian" 
                        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors"
                        :class="dbTesting.qidian ? 'bg-slate-50 text-slate-400 border-slate-200' : 'bg-white text-sky-600 border-sky-200 hover:bg-sky-50'">
                  <TestTube class="w-3.5 h-3.5" :class="dbTesting.qidian ? 'animate-spin' : ''" />
                  {{ dbTesting.qidian ? '测试中...' : '测试连接' }}
                </button>
              </div>
              <div class="space-y-1.5 text-xs font-mono text-slate-600">
                <div class="flex justify-between"><span class="text-slate-400">Host</span> {{ settingsData.database.qidian.host }}:{{ settingsData.database.qidian.port }}</div>
                <div class="flex justify-between"><span class="text-slate-400">Database</span> {{ settingsData.database.qidian.database }}</div>
                <div class="flex justify-between"><span class="text-slate-400">User</span> {{ settingsData.database.qidian.user }}</div>
              </div>
              <div v-if="dbTestResult.qidian.status" class="mt-3 px-3 py-2 rounded-lg text-xs font-medium"
                   :class="dbTestResult.qidian.status === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
                {{ dbTestResult.qidian.message }}
              </div>
            </div>
          </div>
        </div>

        <!-- ===== 4. 系统参数 ===== -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-5">
            <div class="flex items-center gap-3">
              <div class="p-2.5 rounded-xl bg-amber-500/10"><Settings class="w-5 h-5 text-amber-600" /></div>
              <div>
                <h3 class="font-bold text-slate-900">系统参数</h3>
                <p class="text-xs text-slate-400">调整全局运行参数</p>
              </div>
            </div>
            <button @click="saveSettings('system')" :disabled="settingsSaving" 
                    class="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50">
              <Save class="w-4 h-4" /> 保存
            </button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">列表分页大小</label>
              <input v-model.number="settingsData.system.page_size" type="number" min="10" max="100" 
                     class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">在线认定窗口 (分钟)</label>
              <input v-model.number="settingsData.system.online_window_minutes" type="number" min="1" max="1440" 
                     class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">缓存有效期 (分钟)</label>
              <input v-model.number="settingsData.system.cache_ttl_minutes" type="number" min="5" max="1440" 
                     class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">日志级别</label>
              <select v-model="settingsData.system.log_level" class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none">
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 mb-1.5">大屏刷新间隔 (秒)</label>
              <input v-model.number="settingsData.system.data_refresh_interval" type="number" min="5" max="120" 
                     class="w-full h-10 px-3 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none" />
            </div>
          </div>
        </div>

        <!-- ===== 5. 关于系统 ===== -->
        <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-2xl p-6 shadow-sm">
          <div class="flex items-center gap-3 mb-5">
            <div class="p-2.5 rounded-xl bg-slate-500/10"><Info class="w-5 h-5 text-slate-600" /></div>
            <div>
              <h3 class="font-bold text-slate-900">关于 IP Lumina</h3>
              <p class="text-xs text-slate-400">系统版本与运行状态</p>
            </div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="border border-slate-100 rounded-xl p-4 bg-white/40 text-center">
              <div class="text-2xl font-bold text-indigo-600 mb-1">{{ settingsData.about.version }}</div>
              <div class="text-[11px] text-slate-400 font-medium">系统版本</div>
            </div>
            <div class="border border-slate-100 rounded-xl p-4 bg-white/40 text-center">
              <div class="text-2xl font-bold text-emerald-600 mb-1">{{ settingsData.about.total_books }}</div>
              <div class="text-[11px] text-slate-400 font-medium">书籍总量</div>
            </div>
            <div class="border border-slate-100 rounded-xl p-4 bg-white/40 text-center">
              <div class="text-2xl font-bold mb-1" :class="settingsData.about.model_loaded ? 'text-emerald-600' : 'text-rose-500'">{{ settingsData.about.model_loaded ? '✓' : '✗' }}</div>
              <div class="text-[11px] text-slate-400 font-medium">IP 模型状态</div>
            </div>
            <div class="border border-slate-100 rounded-xl p-4 bg-white/40 text-center">
              <div class="text-lg font-mono font-bold text-slate-700 mb-1">{{ settingsData.about.python_version }}</div>
              <div class="text-[11px] text-slate-400 font-medium">Python 版本</div>
            </div>
          </div>
          <div class="mt-4 px-4 py-3 rounded-xl bg-slate-50 border border-slate-100">
            <div class="text-xs text-slate-500">
              <span class="font-medium text-slate-700">技术栈：</span>{{ settingsData.about.tech_stack }}
            </div>
          </div>
        </div>

        </template>
      </div>

    </div>
  </main>
</div>

<!-- 虚拟读者详情弹窗 -->
<div v-if="showVrDetailModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
   <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden animate-fade-in-up">
      <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-violet-50/50">
         <div class="flex items-center gap-2">
            <MessageSquare class="w-5 h-5 text-violet-600" />
            <h3 class="font-bold text-lg text-slate-800">虚拟读者预测详情</h3>
         </div>
         <button @click="showVrDetailModal = false" class="text-slate-400 hover:text-slate-600 p-1">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
         </button>
      </div>
      <div class="p-6 overflow-y-auto max-h-[60vh]">
         <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="bg-emerald-50 rounded-xl p-4 text-center">
               <div class="text-2xl font-bold text-emerald-600">{{ multiSourceOverview.vr.positive }}</div>
               <div class="text-sm text-slate-500">正向评价 👍</div>
            </div>
            <div class="bg-slate-50 rounded-xl p-4 text-center">
               <div class="text-2xl font-bold text-slate-600">{{ multiSourceOverview.vr.neutral }}</div>
               <div class="text-sm text-slate-500">中性评价 😐</div>
            </div>
            <div class="bg-rose-50 rounded-xl p-4 text-center">
               <div class="text-2xl font-bold text-rose-600">{{ multiSourceOverview.vr.negative }}</div>
               <div class="text-sm text-slate-500">负向评价 👎</div>
            </div>
         </div>
         <div class="text-sm text-slate-600 leading-relaxed">
            <p class="mb-3">虚拟读者系统通过 AI 模拟真实读者反馈，对作品进行多维度评价。</p>
            <p class="text-slate-400 text-xs">总预测数：{{ multiSourceOverview.vr.total }} 条</p>
         </div>
      </div>
      <div class="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end">
         <button @click="showVrDetailModal = false" class="px-5 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors">
            关闭
         </button>
      </div>
   </div>
</div>

<!-- AI 评分表详情弹窗 -->
<div v-if="showAiEvalModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
   <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden animate-fade-in-up">
      <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-sky-50/50">
         <div class="flex items-center gap-2">
            <BarChart3 class="w-5 h-5 text-sky-600" />
            <h3 class="font-bold text-lg text-slate-800">AI 评分表详情</h3>
         </div>
         <button @click="showAiEvalModal = false" class="text-slate-400 hover:text-slate-600 p-1">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
         </button>
      </div>
      <div class="p-6 overflow-y-auto max-h-[60vh]">
         <div class="text-3xl font-bold text-sky-600 mb-2">{{ multiSourceOverview.ai_eval.total }} <span class="text-lg text-slate-400">本</span></div>
         <div class="grid grid-cols-2 gap-4 mb-6">
            <div class="bg-sky-50 rounded-xl p-4">
               <div class="text-sm text-slate-500 mb-1">综合均分</div>
               <div class="text-2xl font-bold text-sky-600">{{ multiSourceOverview.ai_eval.avg_overall }}</div>
            </div>
            <div class="bg-cyan-50 rounded-xl p-4">
               <div class="text-sm text-slate-500 mb-1">商业均分</div>
               <div class="text-2xl font-bold text-cyan-600">{{ multiSourceOverview.ai_eval.avg_commercial }}</div>
            </div>
         </div>
         <div class="space-y-2 text-sm">
            <div class="flex justify-between py-2 border-b border-slate-100">
               <span class="text-slate-500">故事均分</span>
               <span class="font-bold">{{ multiSourceOverview.ai_eval.avg_story || '--' }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-100">
               <span class="text-slate-500">角色均分</span>
               <span class="font-bold">{{ multiSourceOverview.ai_eval.avg_character || '--' }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-slate-100">
               <span class="text-slate-500">世界观均分</span>
               <span class="font-bold">{{ multiSourceOverview.ai_eval.avg_world || '--' }}</span>
            </div>
         </div>
      </div>
      <div class="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end">
         <button @click="showAiEvalModal = false" class="px-5 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors">
            关闭
         </button>
      </div>
   </div>
</div>

<!-- 实时监控详情弹窗 -->
<div v-if="showRealtimeModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
   <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden animate-fade-in-up">
      <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-emerald-50/50">
         <div class="flex items-center gap-2">
            <Radar class="w-5 h-5 text-emerald-600" />
            <h3 class="font-bold text-lg text-slate-800">实时监控详情</h3>
         </div>
         <button @click="showRealtimeModal = false" class="text-slate-400 hover:text-slate-600 p-1">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
         </button>
      </div>
      <div class="p-6 overflow-y-auto max-h-[60vh]">
         <div class="text-3xl font-bold text-emerald-600 mb-2">{{ multiSourceOverview.realtime.active_books }} <span class="text-lg text-slate-400">本</span></div>
         <div class="text-sm text-slate-500 mb-6">
            最新采集时间：<span class="font-bold text-emerald-600">{{ multiSourceOverview.realtime.last_crawl }}</span>
         </div>
         <div class="grid grid-cols-2 gap-4">
            <div class="bg-emerald-50 rounded-xl p-4">
               <div class="text-sm text-slate-500 mb-1">起点中文网</div>
               <div class="text-2xl font-bold text-emerald-600">{{ multiSourceOverview.realtime.qidian_count || 0 }} 本</div>
            </div>
            <div class="bg-teal-50 rounded-xl p-4">
               <div class="text-sm text-slate-500 mb-1">纵横中文网</div>
               <div class="text-2xl font-bold text-teal-600">{{ multiSourceOverview.realtime.zongheng_count || 0 }} 本</div>
            </div>
         </div>
      </div>
      <div class="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-end">
         <button @click="showRealtimeModal = false" class="px-5 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors">
            关闭
         </button>
      </div>
   </div>
</div>

<!-- 审计报告详情弹窗 -->
<div v-if="showAuditModal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm px-4">
   <div class="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[80vh] overflow-hidden animate-fade-in-up">
      <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-amber-50/50">
         <div class="flex items-center gap-2">
            <FileText class="w-5 h-5 text-amber-600" />
            <h3 class="font-bold text-lg text-slate-800">审计报告详情</h3>
         </div>
         <button @click="showAuditModal = false" class="text-slate-400 hover:text-slate-600 p-1">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
         </button>
      </div>
      <div class="p-6 overflow-y-auto max-h-[60vh] custom-scrollbar">
         <!-- 统计概览 -->
         <div class="grid grid-cols-4 gap-4 mb-6">
            <div class="bg-slate-50 rounded-xl p-4 text-center">
               <div class="text-2xl font-bold text-slate-800">{{ multiSourceOverview.audit.total }}</div>
               <div class="text-xs text-slate-500 mt-1">总报告数</div>
            </div>
            <div class="bg-amber-50 rounded-xl p-4 text-center">
               <div class="text-2xl font-bold text-amber-600">{{ multiSourceOverview.audit.gems }}</div>
               <div class="text-xs text-slate-500 mt-1">💎 潜力遗珠</div>
            </div>
            <div class="bg-blue-50 rounded-xl p-4 text-center">
               <div class="text-2xl font-bold text-blue-600">{{ multiSourceOverview.audit.global_gems }}</div>
               <div class="text-xs text-slate-500 mt-1">🌍 全球佳作</div>
            </div>
            <div class="bg-indigo-50 rounded-xl p-4 text-center">
               <div class="text-2xl font-bold text-indigo-600">{{ multiSourceOverview.audit.deep_audits }}</div>
               <div class="text-xs text-slate-500 mt-1">🔬 深度审计</div>
            </div>
         </div>
         <!-- 审计报告列表 -->
         <div v-if="auditLogs.length > 0" class="space-y-3">
            <div v-for="log in auditLogs.slice(0, 10)" :key="log.id" class="p-4 bg-slate-50 rounded-xl hover:bg-slate-100 transition-colors">
               <div class="flex items-center justify-between mb-2">
                  <div class="font-bold text-slate-800">{{ log.book_title || '未知作品' }}</div>
                  <div class="flex items-center gap-2">
                     <span :class="log.risk_level === 'High' ? 'bg-red-100 text-red-600' : log.risk_level === 'Medium' ? 'bg-amber-100 text-amber-600' : log.risk_level === 'Low' ? 'bg-blue-100 text-blue-600' : 'bg-emerald-100 text-emerald-600'" class="px-2 py-0.5 rounded text-xs font-bold">
                        {{ log.risk_level }}
                     </span>
                     <span class="px-2 py-0.5 bg-indigo-100 text-indigo-600 rounded text-xs font-bold">{{ log.risk_type }}</span>
                  </div>
               </div>
               <div class="text-sm text-slate-600 line-clamp-2">{{ log.content_snippet || '无内容摘要' }}</div>
               <div class="text-xs text-slate-400 mt-2">{{ log.created_at }}</div>
            </div>
         </div>
         <div v-else class="text-center py-10 text-slate-400">
            <CheckCircle2 class="w-12 h-12 mx-auto mb-3 opacity-50" />
            <div>暂无审计报告</div>
         </div>
      </div>
      <div class="px-6 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-between">
         <button @click="router.push({ path: '/admin', query: { tab: 'audit' } }); showAuditModal = false" class="px-4 py-2 rounded-xl text-sm font-medium text-indigo-600 hover:bg-indigo-50 transition-colors">
            查看全部审计报告 →
         </button>
         <button @click="showAuditModal = false" class="px-5 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors">
            关闭
         </button>
      </div>
   </div>
</div>

</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: #94a3b8;
}
</style>
