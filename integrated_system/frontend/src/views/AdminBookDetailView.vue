<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { parseAIError, showAIError } from '@/utils/aiErrorHandler'
import { 
    ArrowLeft, Database, Activity, Server, CheckCircle2, AlertTriangle, FileJson,
    Cpu, User, BookOpen, BarChart, Clock, Zap, Wifi, Layers, MessageSquare, ShieldCheck,
    Users, Fingerprint, Map
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const book = ref<any>(null)
const adminSynopsisExpanded = ref(false)

// 交互反馈与状态
const isPredicting = ref(false)
const isCrawling = ref(false)
const isBlacklisting = ref(false)
const isExtracting = ref(false)
const toastMessage = ref('')
const toastType = ref<'success' | 'error' | 'info'>('info')

const showToast = (msg: string, type: 'success' | 'error' | 'info' = 'info') => {
    toastMessage.value = msg
    toastType.value = type
    setTimeout(() => toastMessage.value = '', 3000)
}

const title = computed(() => route.query.title as string || '')
const author = computed(() => route.query.author as string || '')
const platform = computed(() => route.query.platform as string || '')

const fetchBookDetail = async () => {
    loading.value = true
    error.value = ''
    try {
        const params = new URLSearchParams()
        params.append('title', title.value)
        if (author.value) params.append('author', author.value)
        if (platform.value) params.append('platform', platform.value)
        const res = await axios.get(`http://localhost:5000/api/library/detail?${params.toString()}`)
        book.value = res.data
    } catch (e: any) {
        error.value = e.response?.data?.error || '节点连接失败，无法获取到底层 Payload。'
    } finally {
        loading.value = false
    }
}

// Format numbers nicely into "万" (10k) formatting for Chinese reading habits
const formatRaw = (num: number) => {
    if (!num) return '0'
    if (num >= 10000) {
        let val = (num / 10000).toFixed(1)
        return val.endsWith('.0') ? val.slice(0, -2) + ' 万' : val + ' 万'
    }
    return num.toLocaleString()
}

const getGradient = (title: string) => {
  let hash = 0
  const safeTitle = title || ''
  for (let i = 0; i < safeTitle.length; i++) {
    hash = safeTitle.charCodeAt(i) + ((hash << 5) - hash)
  }
  const color1 = `hsl(${Math.abs(hash % 360)}, 60%, 80%)`
  const color2 = `hsl(${Math.abs((hash * 2) % 360)}, 70%, 90%)`
  return `linear-gradient(135deg, ${color1} 0%, ${color2} 100%)`
}

onMounted(() => {
    if (title.value) {
        fetchBookDetail()
    } else {
        error.value = 'Missing Query Parameters.'
        loading.value = false
    }
})

// === 按钮事件处理 ===

const handleRePredict = async () => {
    if (!book.value) return
    isPredicting.value = true
    try {
        // 请求统一预测接口，使用当前书籍内容
        const payload = {
            title: book.value.basic.title,
            abstract: book.value.basic.abstract,
            category: book.value.basic.category,
            author: book.value.basic.author,
            word_count: book.value.basic.word_count,
            recent_updates: 1, // mock
            tags: book.value.basic.tags || [],
            finance: book.value.stats?.monthly_tickets || 0,
            interaction: book.value.stats?.interaction || 0,
            popularity: book.value.stats?.popularity || 0,
            fans_count: book.value.stats?.fans_count || 0
        }
        
        // 携带 Token 证明是管理员操作
        const token = localStorage.getItem('auth_token')
        const hdrs = token ? { 'Authorization': `Bearer ${token}` } : {}
        
        const res = await axios.post('http://localhost:5000/api/predict', payload, { headers: hdrs })
        showToast('IP 偏好推演已重新执行完成', 'success')
        
        // 实时将新的预测分覆盖回页面顶部概览中
        if (res.data && res.data.score) {
            if (!book.value.ip_evaluation) book.value.ip_evaluation = {}
            book.value.ip_evaluation.score = res.data.score
            if (res.data.score >= 90) book.value.ip_evaluation.grade = 'S'
            else if (res.data.score >= 80) book.value.ip_evaluation.grade = 'A'
            else if (res.data.score >= 70) book.value.ip_evaluation.grade = 'B'
            else book.value.ip_evaluation.grade = 'C'
        }
        
    } catch (e: any) {
        showAIError(e)
    } finally {
        isPredicting.value = false
    }
}

const handleTriggerSpider = async () => {
    if (!book.value) return
    isCrawling.value = true
    showToast('已下发深度探测指令至爬虫节点', 'info')
    try {
        const payload = {
            novel_id: book.value.id || '',
            platform: book.value.basic.platform
        }
        const token = localStorage.getItem('auth_token')
        const hdrs = token ? { 'Authorization': `Bearer ${token}` } : {}
        await axios.post('http://localhost:5000/api/admin/trigger_spider', payload, { headers: hdrs })
        showToast('深度节点数据抓取任务受理中...', 'success')
    } catch (e: any) {
        showToast(e.response?.data?.error || '调度指令下发失败', 'error')
    } finally {
        isCrawling.value = false
    }
}

const handleBlacklist = async () => {
    if (!book.value || !confirm(`危险操作：确定将《${book.value.basic.title}》标记为人工屏蔽/下架状态吗？`)) return
    isBlacklisting.value = true
    try {
        const payload = {
            novel_id: book.value.id || '',
            title: book.value.basic.title
        }
        const token = localStorage.getItem('auth_token')
        const hdrs = token ? { 'Authorization': `Bearer ${token}` } : {}
        await axios.post('http://localhost:5000/api/admin/blacklist', payload, { headers: hdrs })
        showToast(`操作成功，《${book.value.basic.title}》已加入系统黑名单和监控。`, 'success')
    } catch (e: any) {
         showToast(e.response?.data?.error || '加入黑名单失败', 'error')
    } finally {
        isBlacklisting.value = false
    }
}

const handleExtractCharacters = async () => {
    if (!book.value) return
    if (isExtracting.value) return
    isExtracting.value = true
    try {
        const payload = { 
            title: book.value.basic.title,
            abstract: book.value.basic.abstract,
            author: book.value.basic.author,
            platform: book.value.basic.platform
        }
        const res = await axios.post('http://localhost:5000/api/ai/extract_characters', payload)
        // 此处只做请求和 Toast, 角色提取因为当前展示为 Mock 暂时直接提示。
        console.log('提取出的人物', res.data)
        // 也可以选择将 res.data.characters 保存并更新到页面的 Mock 卡片中。
        showToast('已重新提取智能图谱实体关联', 'success')
    } catch (e: any) {
        showToast(parseAIError(e), 'error')
    } finally {
        isExtracting.value = false
    }
}
</script>

<template>
    <div class="min-h-screen bg-slate-50 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px] relative">
        <!-- Toast Notification -->
        <div v-if="toastMessage" class="fixed top-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-6 py-3 rounded-full shadow-lg border animate-fade-in-down transition-all"
             :class="{
                 'bg-emerald-50 border-emerald-200 text-emerald-700': toastType === 'success',
                 'bg-rose-50 border-rose-200 text-rose-700': toastType === 'error',
                 'bg-indigo-50 border-indigo-200 text-indigo-700': toastType === 'info'
             }">
             <CheckCircle2 v-if="toastType === 'success'" class="w-5 h-5 text-emerald-500" />
             <AlertTriangle v-if="toastType === 'error'" class="w-5 h-5 text-rose-500" />
             <span class="text-sm font-bold tracking-wide">{{ toastMessage }}</span>
        </div>
        <div class="pb-32 pt-8 px-8 max-w-7xl mx-auto font-sans">
            
            <div class="flex items-center justify-between mb-8">
                <button 
                    @click="router.push('/admin?tab=books')"
                    class="flex items-center gap-2 text-slate-500 hover:text-indigo-600 font-medium transition-colors bg-white px-4 py-2 rounded-xl border border-slate-200 shadow-sm"
                >
                    <ArrowLeft class="w-4 h-4" />
                    返回仪表盘
                </button>
                <div class="flex items-center gap-3">
                    <span class="flex items-center gap-1.5 text-xs font-bold text-indigo-600 bg-indigo-50 px-3 py-1.5 rounded-lg border border-indigo-100 uppercase tracking-wider">
                        <Database class="w-3.5 h-3.5" /> 数据库源视图 (Admin View)
                    </span>
                    <span class="flex items-center gap-1.5 text-xs font-bold text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-100">
                        <CheckCircle2 class="w-3.5 h-3.5" /> Payload 正常
                    </span>
                </div>
            </div>

            <!-- Loading -->
            <div v-if="loading" class="flex flex-col items-center justify-center py-40">
                <div class="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mb-4"></div>
                <div class="text-sm tracking-[0.2em] text-indigo-600 font-mono uppercase animate-pulse">Fetching Database Node...</div>
            </div>

            <!-- Error -->
            <div v-else-if="error" class="bg-white border border-rose-100 rounded-2xl p-12 text-center max-w-2xl mx-auto mt-20 shadow-sm">
                <AlertTriangle class="w-16 h-16 text-rose-500 mx-auto mb-6 opacity-80" />
                <h3 class="text-xl font-bold text-slate-800 mb-2 font-mono">NODE_FETCH_FAILED</h3>
                <p class="text-slate-500 mb-8 text-sm">{{ error }}</p>
                <button @click="fetchBookDetail" class="px-8 py-3 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-600 rounded-xl text-sm font-bold transition-all">
                    Retry Connection
                </button>
            </div>

            <!-- Content -->
            <div v-else-if="book" class="space-y-6">
                
                <!-- Top Header Card -->
                <div class="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm relative overflow-hidden">
                    <div class="absolute right-0 top-0 w-96 h-96 bg-indigo-50/50 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none"></div>
                    
                    <div class="relative z-10 flex flex-col md:flex-row gap-8 items-start md:items-center">
                        <div class="w-32 h-44 rounded-xl bg-slate-100 border border-slate-200 overflow-hidden flex-shrink-0 relative group shadow-md"
                             :style="!book.basic.cover ? { background: getGradient(book.basic.title) } : {}">
                            <img v-if="book.basic.cover" :src="book.basic.cover" class="w-full h-full object-cover" />
                            <div v-else class="absolute inset-0 flex items-center justify-center p-2 text-center pointer-events-none">
                                <span class="text-slate-500/30 font-serif font-black text-6xl uppercase transform -rotate-12 select-none">{{ book.basic.title.substring(0, 1) }}</span>
                            </div>
                        </div>
                        
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-3 mb-3 flex-wrap">
                                <h1 class="text-4xl font-black text-slate-800 truncate tracking-tight">{{ book.basic.title }}</h1>
                                <span class="px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-md text-[10px] font-mono text-slate-500">
                                    SYS_ID: {{ book.id || 'N/A' }}
                                </span>
                                <span class="px-2.5 py-1 bg-indigo-50 border border-indigo-200 text-indigo-600 rounded-md text-[10px] font-bold uppercase tracking-widest">
                                    {{ book.basic.platform }} Node
                                </span>
                            </div>
                            
                            <div class="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm mb-4">
                                <div class="flex items-center gap-2">
                                    <div class="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center"><User class="w-3 h-3 text-slate-500" /></div>
                                    <span class="text-slate-700 font-medium">{{ book.basic.author }}</span>
                                </div>
                                <div class="flex items-center gap-2">
                                    <div class="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center"><BookOpen class="w-3 h-3 text-slate-500" /></div>
                                    <span class="text-slate-700 font-medium">{{ book.basic.category }}</span>
                                </div>
                                <div class="flex items-center gap-2">
                                    <div class="w-6 h-6 rounded-full bg-emerald-50 flex items-center justify-center"><Activity class="w-3 h-3 text-emerald-600" /></div>
                                    <span class="text-emerald-600 font-medium">{{ book.basic.status }}</span>
                                </div>
                            </div>
                            
                            <p 
                                class="text-slate-500 text-sm leading-relaxed max-w-4xl mb-3 transition-all"
                                :class="adminSynopsisExpanded ? '' : 'line-clamp-2'"
                            >{{ book.basic.synopsis || book.basic.abstract || '暂无简介' }}</p>
                            <button 
                                v-if="(book.basic.synopsis || book.basic.abstract || '').length > 60"
                                @click="adminSynopsisExpanded = !adminSynopsisExpanded"
                                class="text-indigo-500 hover:text-indigo-700 text-xs font-bold mb-3 transition-colors"
                            >{{ adminSynopsisExpanded ? '收起 ▲' : '展开全部 ▼' }}</button>

                            <!-- 最新章节 -->
                            <div class="flex items-center gap-2 text-sm mb-4" v-if="book.basic.latest_chapter && book.basic.latest_chapter !== '暂无更新'">
                                <div class="w-6 h-6 rounded-full bg-amber-50 flex items-center justify-center flex-shrink-0">
                                    <Clock class="w-3 h-3 text-amber-600" />
                                </div>
                                <span class="text-slate-500 text-xs font-bold uppercase">最新章节</span>
                                <span class="text-slate-700 font-medium truncate">{{ book.basic.latest_chapter }}</span>
                            </div>

                            <!-- Tags -->
                            <div class="flex flex-wrap gap-2">
                                <span v-for="tag in book.basic.tags" :key="tag" class="px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-[11px] text-slate-600 font-medium">
                                    # {{ tag }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Admin Action Toolbar (New) -->
                <div class="flex flex-wrap gap-4 items-center justify-between bg-white rounded-2xl p-4 border border-slate-200 shadow-sm xl:flex-row flex-col">
                    <div class="flex flex-wrap items-center gap-3">
                        <button @click="handleRePredict" :disabled="isPredicting" class="flex items-center justify-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-600 hover:bg-indigo-100 rounded-xl text-sm font-bold transition-colors border border-indigo-100 min-w-[160px] disabled:opacity-50">
                            <div v-if="isPredicting" class="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                            <Cpu v-else class="w-4 h-4" />
                            {{ isPredicting ? '重新测算中...' : '重新运行 IP 权重预测' }}
                        </button>
                        <button @click="handleTriggerSpider" :disabled="isCrawling" class="flex items-center justify-center gap-2 px-4 py-2 bg-white text-slate-600 hover:text-emerald-600 hover:bg-emerald-50 hover:border-emerald-200 rounded-xl text-sm font-bold transition-all border border-slate-200 min-w-[160px] disabled:opacity-50">
                            <div v-if="isCrawling" class="w-4 h-4 border-2 border-slate-600 border-t-transparent rounded-full animate-spin"></div>
                            <Wifi v-else class="w-4 h-4 text-emerald-500" />
                            {{ isCrawling ? '节点调度中...' : '触发节点深度数据抓取' }}
                        </button>
                    </div>
                    
                    <div>
                        <button @click="handleBlacklist" :disabled="isBlacklisting" class="flex items-center justify-center gap-2 px-4 py-2 bg-white text-rose-500 hover:bg-rose-50 border border-rose-200 rounded-xl text-sm font-bold transition-colors group min-w-[180px] disabled:opacity-50">
                            <div v-if="isBlacklisting" class="w-4 h-4 border-2 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
                            <ShieldCheck v-else class="w-4 h-4 group-hover:hidden text-rose-400" />
                            <AlertTriangle v-if="!isBlacklisting" class="w-4 h-4 text-rose-500 hidden group-hover:block" />
                            {{ isBlacklisting ? '正在阻断...' : '加入下架管控黑名单' }}
                        </button>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    
                    <!-- Meta Metrics -->
                    <div class="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm flex flex-col">
                        <div class="flex items-center justify-between mb-6">
                            <div class="flex items-center gap-3">
                                <div class="p-2 bg-indigo-50 rounded-lg border border-indigo-100">
                                    <BarChart class="w-5 h-5 text-indigo-600" />
                                </div>
                                <h3 class="font-bold text-slate-800 tracking-wide">底层全量数据 (MySQL)</h3>
                            </div>
                        </div>
                        
                        <div class="space-y-1 flex-1">
                            <div class="group flex justify-between items-center py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-colors">
                                <span class="text-slate-500 text-xs font-bold uppercase tracking-wider group-hover:text-slate-700">总点击 (Popularity)</span>
                                <span class="font-mono text-slate-800 font-bold">{{ formatRaw(book.stats?.popularity) }}</span>
                            </div>
                            <div class="group flex justify-between items-center py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-colors">
                                <span class="text-slate-500 text-xs font-bold uppercase tracking-wider group-hover:text-slate-700">粉丝数 (Fans)</span>
                                <span class="font-mono text-slate-800 font-bold">{{ formatRaw(book.stats?.fans_count) }}</span>
                            </div>
                            <div class="group flex justify-between items-center py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-colors">
                                <span class="text-slate-500 text-xs font-bold uppercase tracking-wider group-hover:text-slate-700">交互数 (Interaction)</span>
                                <span class="font-mono text-slate-800 font-bold">{{ formatRaw(book.stats?.interaction) }}</span>
                            </div>
                            <div class="group flex justify-between items-center py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-colors">
                                <span class="text-slate-500 text-xs font-bold uppercase tracking-wider group-hover:text-amber-600">总月票 (Finance)</span>
                                <span class="font-mono text-amber-600 font-bold">{{ formatRaw(book.stats?.monthly_tickets) }}</span>
                            </div>
                            <div class="group flex justify-between items-center py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-colors">
                                <span class="text-slate-500 text-xs font-bold uppercase tracking-wider group-hover:text-indigo-600">总字数 (Words)</span>
                                <span class="font-mono text-indigo-600 font-bold">{{ formatRaw(book.stats?.word_count) }} 字</span>
                            </div>
                            <div class="group flex justify-between items-center py-2.5 px-3 rounded-lg bg-slate-50 border border-slate-100 mt-2">
                                <span class="text-slate-600 text-xs font-bold uppercase tracking-wider">采集时间批次</span>
                                <span class="font-mono text-slate-800 font-bold text-xs">{{ book.year }}年 {{ book.month }}月</span>
                            </div>
                        </div>
                    </div>

                    <!-- AI Evaluation -->
                    <div class="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm flex flex-col relative overflow-hidden">
                        
                        <div class="flex items-center justify-between mb-6 relative z-10">
                            <div class="flex items-center gap-3">
                                <div class="p-2 bg-teal-50 rounded-lg border border-teal-100">
                                    <Cpu class="w-5 h-5 text-teal-600" />
                                </div>
                                <h3 class="font-bold text-slate-800 tracking-wide">模型推断矩阵</h3>
                            </div>
                            <span class="px-2 py-0.5 rounded text-[9px] font-bold uppercase font-mono border border-slate-200 text-slate-500 bg-slate-50">Model v2.0</span>
                        </div>

                        <div class="flex-1 flex flex-col justify-center relative z-10 space-y-6">
                            <div class="text-center">
                                <div class="text-[10px] text-slate-500 font-bold uppercase tracking-[0.2em] mb-2">综合预测评分</div>
                                <div class="flex items-baseline justify-center gap-2">
                                    <span class="text-5xl font-black text-slate-800 font-serif tracking-tight">{{ book.ip_evaluation?.score || 0 }}</span>
                                    <span class="text-2xl font-bold" :class="book.ip_evaluation?.grade?.includes('A') ? 'text-teal-500' : 'text-amber-500'">{{ book.ip_evaluation?.grade }}</span>
                                </div>
                            </div>
                            
                            <div class="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                <div class="flex justify-between items-center mb-2">
                                    <span class="text-xs text-slate-500 font-bold uppercase">同类题材机读排名</span>
                                    <span class="text-xs font-mono font-bold text-indigo-500">Percentile {{ book.ip_evaluation?.percentile }}%</span>
                                </div>
                                <div class="text-sm font-bold text-slate-800">
                                    {{ book.ip_evaluation?.category_rank }}
                                </div>
                            </div>
                            
                            <div class="grid grid-cols-2 gap-3">
                                <div class="bg-slate-50 rounded-lg p-3 border border-slate-100 text-center">
                                    <div class="text-[10px] text-slate-500 uppercase font-bold mb-1">商业价值估算</div>
                                    <div class="text-sm font-bold text-slate-800">{{ book.ip_evaluation?.commercial_value }}</div>
                                </div>
                                <div class="bg-slate-50 rounded-lg p-3 border border-slate-100 text-center">
                                    <div class="text-[10px] text-slate-500 uppercase font-bold mb-1">项目风险评级</div>
                                    <div class="text-sm font-bold" :class="book.ip_evaluation?.risk_factor === '低' ? 'text-emerald-600' : 'text-amber-600'">{{ book.ip_evaluation?.risk_factor }} 风险</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Real-time Monitor (New) -->
                    <div class="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm flex flex-col">
                        <div class="flex items-center justify-between mb-6">
                            <div class="flex items-center gap-3">
                                <div class="p-2 bg-emerald-50 rounded-lg border border-emerald-100">
                                    <Wifi class="w-5 h-5 text-emerald-600" />
                                </div>
                                <h3 class="font-bold text-slate-800 tracking-wide">系统状态</h3>
                            </div>
                            <span class="flex items-center gap-1.5 text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100 uppercase">
                                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Online
                            </span>
                        </div>
                        
                        <div class="space-y-3 flex-1">
                            <div class="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                <div class="flex items-center gap-3">
                                    <ShieldCheck class="w-5 h-5 text-emerald-500" />
                                    <div>
                                        <div class="text-xs font-bold text-slate-700">API 服务正常</div>
                                        <div class="text-[10px] text-slate-500">后端节点响应正常</div>
                                    </div>
                                </div>
                            </div>
                            <div class="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                <div class="flex items-center gap-3">
                                    <Database class="w-5 h-5 text-indigo-500" />
                                    <div>
                                        <div class="text-xs font-bold text-slate-700">数据连接正常</div>
                                        <div class="text-[10px] text-slate-500">数据库连接池健康</div>
                                    </div>
                                </div>
                            </div>
                            <div class="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                <div class="flex items-center gap-3">
                                    <Server class="w-5 h-5 text-amber-500" />
                                    <div>
                                        <div class="text-xs font-bold text-slate-700">爬虫服务就绪</div>
                                        <div class="text-[10px] text-slate-500">可执行数据采集任务</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Characters Intel (New) -->
                    <div class="md:col-span-2 lg:col-span-2 bg-white rounded-3xl p-6 border border-slate-200 shadow-sm flex flex-col">
                        <div class="flex items-center justify-between mb-6">
                            <div class="flex items-center gap-3">
                                <div class="p-2 bg-amber-50 rounded-lg border border-amber-100">
                                    <Users class="w-5 h-5 text-amber-600" />
                                </div>
                                <h3 class="font-bold text-slate-800 tracking-wide">AI 角色提取</h3>
                            </div>
                            <button @click="handleExtractCharacters" :disabled="isExtracting" class="px-4 py-2 bg-indigo-50 text-indigo-600 hover:bg-indigo-100 rounded-lg text-xs font-bold transition-colors border border-indigo-100 disabled:opacity-50 flex items-center gap-2">
                                <div v-if="isExtracting" class="w-3 h-3 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                                <span v-else>+</span>
                                {{ isExtracting ? '提取中...' : '提取角色实体' }}
                            </button>
                        </div>
                        
                        <div class="bg-slate-50 rounded-2xl p-6 border border-slate-100 flex-1 flex items-center justify-center">
                            <div class="text-center">
                                <div class="w-12 h-12 bg-white rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
                                    <Fingerprint class="w-6 h-6 text-slate-400" />
                                </div>
                                <p class="text-sm text-slate-600 font-medium mb-1">点击右上角按钮提取角色</p>
                                <p class="text-xs text-slate-400">AI 将分析文本内容并提取主要角色实体信息</p>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #334155;
  border-radius: 20px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: #475569;
}
</style>
