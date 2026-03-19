<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import axios from 'axios'
import { useAuth } from '@/composables/useAuth'
import { parseAIError, showAIError } from '@/utils/aiErrorHandler'
const { isLoggedIn } = useAuth()
import { 
    ArrowLeft, TrendingUp, TrendingDown, Sparkles, Star, Shield, Award, Globe, Crown, Send, RefreshCw, BookOpen,
    ShieldAlert, FileText, UserSquare, Copyright, Scale,
    Sun, Sparkle, Coffee, Leaf, Moon,
    DollarSign, Minus, Target, History, Clapperboard, Gamepad2, Headphones, Smartphone, CheckCircle2,
    Download
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const book = ref<any>(null)
const activeTab = ref('overview')
const synopsisExpanded = ref(false)

// 章节内容抓取与展示相关状态
const currentChapterNum = ref(1)
const chapterContent = ref<string[]>([])
const chapterTitle = ref('')
const isFetchingChapter = ref(false)

const fetchChapter = async (chapterNum: number) => {
    if (!book.value) return
    isFetchingChapter.value = true
    chapterContent.value = []
    chapterTitle.value = ''
    try {
        const params = new URLSearchParams()
        params.append('title', book.value.basic.title)
        params.append('chapter_num', chapterNum.toString())
        params.append('platform', platform.value)
        const res = await axios.get(`http://localhost:5000/api/library/chapter?${params.toString()}`)
        chapterTitle.value = res.data.chapter_title
        chapterContent.value = res.data.content || []
        currentChapterNum.value = chapterNum
    } catch (e: any) {
        chapterTitle.value = `第${chapterNum}章 取回失败`
        chapterContent.value = ['章节内容加载失败或由于网络原因超时。请稍后重试。', e.toString()]
    } finally {
        isFetchingChapter.value = false
    }
}

// 角色扮演相关状态
interface Character {
    name: string
    persona: string
    description: string
    avatar: string
}
interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
}
const characters = ref<Character[]>([])
const activeCharacter = ref<Character | null>(null)
const isExtractingChars = ref(false)
const chatHistory = ref<ChatMessage[]>([])
const inputMessage = ref('')
const isSending = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

// 提取角色
const extractCharacters = async (forceRefresh = false) => {
    if (!isLoggedIn.value) {
        router.push('/login')
        return
    }
    if (!book.value) return
    isExtractingChars.value = true
    try {
        const res = await axios.post('http://localhost:5000/api/ai/extract_characters', {
            title: book.value.basic.title,
            author: book.value.basic.author,
            platform: platform.value,
            abstract: book.value.basic.abstract,
            force_refresh: forceRefresh
        }, { timeout: 90000 })
        characters.value = res.data.characters || []
        if (characters.value.length > 0 && !activeCharacter.value) {
            activeCharacter.value = characters.value[0] || null
        }
    } catch (e: any) {
        console.error('角色提取失败:', e)
        showAIError(e)
    } finally {
        isExtractingChars.value = false
    }
}

// 生成书籍键
const getBookKey = () => {
    if (!book.value) return ''
    return `${book.value.basic.platform}|${book.value.basic.title}|${book.value.basic.author}`
}

// 加载对话历史
const loadChatHistory = async (charName: string) => {
    if (!book.value) return
    try {
        const res = await axios.get('http://localhost:5000/api/chat/history', {
            params: { book_key: getBookKey(), character: charName }
        })
        if (res.data.history) {
            chatHistory.value = res.data.history.map((h: any) => ({ role: h.role, content: h.content }))
        }
    } catch (e) {
        console.error('Failed to load history', e)
        chatHistory.value = []
    }
}

// 保存消息到数据库
const saveMessage = async (role: string, content: string) => {
    if (!activeCharacter.value || !book.value) return
    try {
        await axios.post('http://localhost:5000/api/chat/save_message', {
            book_key: getBookKey(),
            character: activeCharacter.value.name,
            role,
            content
        })
    } catch (e) {
        console.error('Failed to save message', e)
    }
}

// 清空当前角色的对话历史
const clearChatHistory = async () => {
    if (!activeCharacter.value || !book.value) return
    if (!confirm(`确定要清空与「${activeCharacter.value.name}」的对话记录吗？`)) return
    try {
        await axios.post('http://localhost:5000/api/chat/clear_history', {
            book_key: getBookKey(),
            character: activeCharacter.value.name
        })
        chatHistory.value = []
    } catch (e) {
        console.error('Failed to clear history', e)
    }
}

// 选择角色
const selectCharacter = async (char: Character) => {
    if (!isLoggedIn.value) {
        router.push('/login')
        return
    }
    activeCharacter.value = char
    chatHistory.value = []
    await loadChatHistory(char.name)
}

// 发送消息
const sendMessage = async () => {
    if (!isLoggedIn.value) {
        router.push('/login')
        return
    }
    if (!inputMessage.value.trim() || isSending.value || !activeCharacter.value || !book.value) return
    const msg = inputMessage.value.trim()
    chatHistory.value.push({ role: 'user', content: msg })
    inputMessage.value = ''
    isSending.value = true
    scrollToBottom()
    try {
        saveMessage('user', msg)
        
        const char = activeCharacter.value as any
        const profile = {
            name: activeCharacter.value.name,
            persona: activeCharacter.value.persona,
            scenario: `你是《${book.value.basic.title}》中的角色 ${activeCharacter.value.name}。${activeCharacter.value.description}`
        }
        const res = await axios.post('http://localhost:5000/api/ai/chat', {
            profile,
            history: chatHistory.value.slice(-14),
            message: msg
        }, { timeout: 90000 })
        if (res.data.response) {
            chatHistory.value.push({ role: 'assistant', content: res.data.response })
            saveMessage('assistant', res.data.response)
        }
    } catch (e: any) {
        const errorMsg = parseAIError(e)
        chatHistory.value.push({ role: 'assistant', content: `（错误：${errorMsg}）` })
        showAIError(e)
    } finally {
        isSending.value = false
        scrollToBottom()
    }
}

const scrollToBottom = () => {
    setTimeout(() => {
        if (chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }, 50)
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
        fetchTicketTrend()
        fetchRiskData() // 获取风险评估数据
        fetchHealingData() // 获取治愈指数数据
    } catch (e: any) {
        error.value = e.response?.data?.error || '加载失败'
    } finally {
        loading.value = false
    }
}

// 风险评估数据获取
const riskData = ref<any>(null)
const isFetchingRisk = ref(false)
const fetchRiskData = async () => {
    isFetchingRisk.value = true
    try {
        const params = new URLSearchParams()
        params.append('title', title.value)
        if (author.value) params.append('author', author.value)
        if (platform.value) params.append('platform', platform.value)
        const res = await axios.get(`http://localhost:5000/api/library/risk?${params.toString()}`)
        riskData.value = res.data
    } catch (e) {
        console.error('Failed to load risk data:', e)
    } finally {
        isFetchingRisk.value = false
    }
}

// 治愈系指数获取
const healingData = ref<any>(null)
const isFetchingHealing = ref(false)
const fetchHealingData = async () => {
    isFetchingHealing.value = true
    try {
        const params = new URLSearchParams()
        params.append('title', title.value)
        if (author.value) params.append('author', author.value)
        if (platform.value) params.append('platform', platform.value)
        const res = await axios.get(`http://localhost:5000/api/library/healing?${params.toString()}`)
        healingData.value = res.data
    } catch (e) {
        console.error('Failed to load healing data:', e)
    } finally {
        isFetchingHealing.value = false
    }
}

const isAuditing = ref(false)
// 简单 Markdown 解析，用于审计长文报告
const formatMarkdown = (text: string) => {
    if (!text) return ''
    return text
        .replace(/^# (.*)/gm, '<h2 class="text-2xl font-black mt-6 mb-4 text-slate-800">$1</h2>')
        .replace(/^## (.*)/gm, '<h3 class="text-lg font-black mt-6 mb-3 text-slate-800">$1</h3>')
        .replace(/^### (.*)/gm, '<h4 class="text-sm font-bold mt-4 mb-2 text-indigo-900">$1</h4>')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-slate-900">$1</strong>')
        .replace(/^- (.*)/gm, '<div class="ml-3 pl-2 border-l-2 border-current border-opacity-20 mb-1">$1</div>')
        .replace(/\n/g, '<br>')
}

const triggerBookAudit = async () => {
    if (!isLoggedIn.value) {
        router.push('/login')
        return
    }
    if (!book.value) return
    isAuditing.value = true
    
    // 初始化一个空的缓冲对象用于流式打字机效果
    latestAuditReport.value = {
        title: book.value.basic.title,
        status: 'generating',
        report: '',
        model_score: 0,
        data_sources: {}
    }
    
    try {
        const titleParam = encodeURIComponent(book.value.basic.title)
        let queryParams = `book_title=${titleParam}`
        
        // 【核心修改】将前端真实的大盘打分强行投喂给审计接口，封杀死大模型“胡乱编造极高分（99.5）”的漏洞
        if (book.value.ip_evaluation && book.value.ip_evaluation.score) {
            const ev = book.value.ip_evaluation
            queryParams += `&base_overall=${encodeURIComponent(ev.score)}`
            
            if (ev.dimensions) {
                queryParams += `&base_story=${encodeURIComponent(ev.dimensions.story || 0)}`
                queryParams += `&base_character=${encodeURIComponent(ev.dimensions.character || 0)}`
                queryParams += `&base_world=${encodeURIComponent(ev.dimensions.world || 0)}`
                queryParams += `&base_commercial=${encodeURIComponent(ev.dimensions.commercial || 0)}`
                queryParams += `&base_adaptation=${encodeURIComponent(ev.dimensions.adaptation || 0)}`
                queryParams += `&base_safety=${encodeURIComponent(ev.dimensions.safety || 0)}`
            }
        }
        
        const token = localStorage.getItem('auth_token')
        const headers: Record<string, string> = {}
        if (token) {
            headers['Authorization'] = `Bearer ${token}`
        }
        
        const response = await fetch(`http://localhost:5000/api/admin/audit/deep_scan_stream?${queryParams}`, {
            headers
        })
        
        if (!response.body) throw new Error('ReadableStream API is not supported')
        
        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let done = false
        let buffer = ''

        while (!done) {
            const { value, done: readerDone } = await reader.read()
            done = readerDone
            if (value) {
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || '' 
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6))
                            if (data.type === 'meta') {
                                latestAuditReport.value.model_score = data.score
                                latestAuditReport.value.data_sources = data.data_sources || {}
                            } else if (data.type === 'chunk') {
                                latestAuditReport.value.report += data.content
                            } else if (data.type === 'done') {
                                latestAuditReport.value.status = 'success'
                                await fetchBookAuditLogs()
                            } else if (data.type === 'error') {
                                latestAuditReport.value.report += `\n\n[警报] ${data.message}`
                            }
                        } catch (err) {
                            console.warn('JSON parse warning for stream segment', err)
                        }
                    }
                }
            }
        }
    } catch (e: any) {
        console.error('Audit failed:', e)
        // 处理fetch API的错误响应
        if (e.response) {
            e.response.json().then((data: any) => {
                showAIError({ response: { data } })
            }).catch(() => {
                showAIError(e)
            })
        } else {
            showAIError(e)
        }
    } finally {
        isAuditing.value = false
    }
}

// 最新审计报告缓存
const latestAuditReport = ref<any>(null)

// 导出审计报告为 Markdown 文件
const exportAuditReport = (report: string, bookTitle: string, score?: number) => {
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

// 审计日志获取 (用于风险评估 Tab)
const bookAuditLogs = ref<any[]>([])
const isFetchingAudit = ref(false)
const fetchBookAuditLogs = async () => {
    isFetchingAudit.value = true
    try {
        const params = new URLSearchParams()
        params.append('book_title', title.value)
        const res = await axios.get(`http://localhost:5000/api/admin/audit_logs?${params.toString()}`)
        bookAuditLogs.value = res.data.data || []
        
        // 自动加载最新的深度审计报告（缓存效果）
        if (!latestAuditReport.value && bookAuditLogs.value.length > 0) {
            const latestWithReport = bookAuditLogs.value.find((log: any) => log.markdown_report)
            if (latestWithReport) {
                latestAuditReport.value = {
                    title: latestWithReport.book_title || title.value,
                    model_score: latestWithReport.score || latestWithReport.ip_score,
                    report: latestWithReport.markdown_report,
                    data_sources: {
                        ai_eval: true,
                        realtime_trend: true,
                        xgboost: true,
                        vr_comments: latestWithReport.risk_type !== 'POTENTIAL_GEM',
                        global_stats: latestWithReport.risk_type === 'GLOBAL_GEM'
                    }
                }
            }
        }
    } catch (e) {
        console.error('Failed to load book audit logs:', e)
    } finally {
        isFetchingAudit.value = false
    }
}

// 月票趋势数据
const ticketTrend = ref<{dates: string[], tickets: number[], collections: number[]}>({dates: [], tickets: [], collections: []})
const fetchTicketTrend = async () => {
    try {
        const res = await axios.get('http://localhost:5000/api/admin/book_ticket_trend', { params: { title: title.value } })
        let data = res.data
        if (data.dates && data.dates.length === 1) {
            data.dates.push(data.dates[0] + ' (至今)')
            if (data.tickets && data.tickets.length === 1) data.tickets.push(data.tickets[0])
            if (data.collections && data.collections.length === 1) data.collections.push(data.collections[0])
        }
        ticketTrend.value = data
    } catch(e) { }
}

const isPotentialGem = computed(() => {
    return bookAuditLogs.value.some(log => log.risk_type === 'POTENTIAL_GEM')
})
const hasRisk = computed(() => {
    return bookAuditLogs.value.some(log => log.risk_level === 'High' && log.risk_type !== 'POTENTIAL_GEM')
})

// SVG 折线路径生成
const trendLinePath = computed(() => {
    const data = ticketTrend.value.tickets
    if (!data || data.length < 2) return ''
    const w = 500, h = 60
    const max = Math.max(...data, 1)
    const step = w / (data.length - 1)
    return 'M' + data.map((v, i) => `${i * step},${h - (v / max) * h}`).join(' L')
})

// 格式化大数字的辅助函数
const formatBigInt = (num: number) => {
    if (num >= 10000) return (num / 10000).toFixed(1);
    return num?.toString() || '--';
}
const formatBigIntEnglish = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num?.toString() || '--';
}

// 计算星级
const starRating = computed(() => {
    if (!book.value) return 0
    return Math.min(5, Math.max(0, book.value.ip_evaluation.score / 20))
})

// 六维评估数据
const dimensions = computed(() => {
    if (!book.value?.ip_evaluation?.dimensions) return null
    return book.value.ip_evaluation.dimensions
})

// 雷达图动态顶点坐标计算
// 六个方向（从顶部顺时针）：Story, Safety, Adaptability, Commercial, World, Character
const radarPoints = computed(() => {
    const d = dimensions.value
    if (!d) return '150,60 230,105 220,195 150,230 70,195 65,110'
    // 六个维度映射到六个方向
    const values = [d.story, d.safety, d.adaptation, d.commercial, d.world, d.character]
    const cx = 150, cy = 150, maxR = 110
    const pts = values.map((v: number, i: number) => {
        const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2
        const r = (Math.min(v, 100) / 100) * maxR
        return `${Math.round(cx + r * Math.cos(angle))},${Math.round(cy + r * Math.sin(angle))}`
    })
    return pts.join(' ')
})
const radarDots = computed(() => {
    const d = dimensions.value
    if (!d) return [{x:150,y:60},{x:230,y:105},{x:220,y:195},{x:150,y:230},{x:70,y:195},{x:65,y:110}]
    const values = [d.story, d.safety, d.adaptation, d.commercial, d.world, d.character]
    const cx = 150, cy = 150, maxR = 110
    return values.map((v: number, i: number) => {
        const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2
        const r = (Math.min(v, 100) / 100) * maxR
        return { x: Math.round(cx + r * Math.cos(angle)), y: Math.round(cy + r * Math.sin(angle)) }
    })
})

// ========== 雷达图交互 ==========
const isRadarHovered = ref(false)
const radarHoverX = ref(0)
const radarHoverY = ref(0)

const onRadarMouseMove = (event: MouseEvent) => {
    const el = event.currentTarget as HTMLElement
    const rect = el.getBoundingClientRect()
    radarHoverX.value = event.clientX - rect.left
    radarHoverY.value = event.clientY - rect.top
    isRadarHovered.value = true
}

// ========== 叙事心电图 (EKG) ==========
const ekgHover = ref<any>(null)

// 将 API 返回的 20 个张力数据点转为 SVG 坐标
const ekgSvgPoints = computed(() => {
    const data = book.value?.narrative_ekg
    if (!data || !data.length) return []
    const n = data.length
    return data.map((pt: any, i: number) => ({
        x: 10 + (i / (n - 1)) * 380,
        y: 200 - (pt.tension / 100) * 180,
        tension: pt.tension,
        segment: pt.segment,
        label: pt.label,
    }))
})

// 生成平滑的贝塞尔曲线路径
const ekgCurvePath = computed(() => {
    const pts = ekgSvgPoints.value
    if (pts.length < 2) return ''
    let d = `M${pts[0].x},${pts[0].y}`
    for (let i = 1; i < pts.length; i++) {
        const prev = pts[i - 1]
        const curr = pts[i]
        const cpx1 = prev.x + (curr.x - prev.x) * 0.4
        const cpx2 = prev.x + (curr.x - prev.x) * 0.6
        d += ` C${cpx1},${prev.y} ${cpx2},${curr.y} ${curr.x},${curr.y}`
    }
    return d
})

// 面积填充路径（曲线 + 底部闭合）
const ekgAreaPath = computed(() => {
    const pts = ekgSvgPoints.value
    if (pts.length < 2) return ''
    const curve = ekgCurvePath.value
    return `${curve} L${pts[pts.length - 1].x},200 L${pts[0].x},200 Z`
})

// 鼠标悬浮事件：找到最近的数据点并显示 tooltip
const onEkgMouseMove = (event: MouseEvent) => {
    const svg = event.currentTarget as SVGSVGElement
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const mouseX = ((event.clientX - rect.left) / rect.width) * 400

    const pts = ekgSvgPoints.value
    if (!pts.length) return

    // 找最近的点
    let closest = pts[0]
    let minDist = Math.abs(mouseX - pts[0].x)
    for (const pt of pts) {
        const dist = Math.abs(mouseX - pt.x)
        if (dist < minDist) {
            minDist = dist
            closest = pt
        }
    }

    // 计算 tooltip 在容器中的像素位置
    const tooltipX = (closest.x / 400) * rect.width + 32
    const tooltipY = (closest.y / 200) * (rect.height) - 60

    ekgHover.value = {
        ...closest,
        tooltipX: Math.max(10, Math.min(tooltipX, rect.width - 40)),
        tooltipY: Math.max(5, tooltipY),
    }
}

// 返回书库列表时携带筛选参数
const goBackToLibrary = () => {
    const q = route.query
    const libraryQuery: Record<string, string> = {}
    // 从 URL 的 f_ 前缀参数中恢复筛选状态
    if (q.f_search) libraryQuery.search = q.f_search as string
    if (q.f_category) libraryQuery.category = q.f_category as string
    if (q.f_platform) libraryQuery.platform = q.f_platform as string
    if (q.f_status) libraryQuery.status = q.f_status as string
    if (q.f_year) libraryQuery.year = q.f_year as string
    if (q.f_month) libraryQuery.month = q.f_month as string
    if (q.f_page) libraryQuery.page = q.f_page as string
    router.push({ path: '/library', query: libraryQuery })
}

// 价值估算数据
const valuationData = ref<any>(null)
const isFetchingValuation = ref(false)
const fetchValuation = async () => {
    if (!isLoggedIn.value) {
        // 允许 tab 切换，但在模板里显示登录引导
        return
    }
    if (valuationData.value) return // 已有缓存则不重复请求
    isFetchingValuation.value = true
    try {
        const params = new URLSearchParams()
        params.append('title', title.value)
        if (author.value) params.append('author', author.value)
        if (platform.value) params.append('platform', platform.value)
        const res = await axios.get(`http://localhost:5000/api/library/valuation?${params.toString()}`)
        valuationData.value = res.data
    } catch (e) {
        console.error('Failed to load valuation data:', e)
    } finally {
        isFetchingValuation.value = false
    }
}

// 全球化分析数据
const globalData = ref<any>(null)
const isFetchingGlobal = ref(false)
const fetchGlobalAnalysis = async () => {
    if (!isLoggedIn.value) return
    if (globalData.value) return // 已有缓存则不重复请求
    isFetchingGlobal.value = true
    try {
        const params = new URLSearchParams()
        params.append('title', title.value)
        if (author.value) params.append('author', author.value)
        if (platform.value) params.append('platform', platform.value)
        const res = await axios.get(`http://localhost:5000/api/library/global_analysis?${params.toString()}`)
        globalData.value = res.data
    } catch (e) {
        console.error('Failed to load global analysis data:', e)
    } finally {
        isFetchingGlobal.value = false
    }
}

// 监听 Tab 切换，按需加载估值与全球化分析数据
watch(activeTab, (newTab) => {
    if (newTab === 'valuation') {
        fetchValuation()
    } else if (newTab === 'global') {
        fetchGlobalAnalysis()
    } else if (newTab === 'risk' || newTab === 'ai-audit') {
        fetchBookAuditLogs()
    } else if (newTab === 'audit') {
        if (chapterContent.value.length === 0) fetchChapter(currentChapterNum.value)
    }
})

// 格式化估值金额的辅助函数
const formatPrice = (price: number) => {
    if (price >= 10000) return (price / 10000).toFixed(1) + '亿'
    return price.toLocaleString()
}

onMounted(() => {
    if (title.value) {
        fetchBookDetail()
        fetchBookAuditLogs()
    } else {
        error.value = '缺少书籍参数'
        loading.value = false
    }
})
</script>

<template>
    <EditorialLayout>
        <!-- 整个页面采用类似天然纸张的纹理底色 -->
        <div class="min-h-screen pb-32 pt-6 px-6 max-w-[1280px] mx-auto bg-[#faf9f6]/40">
            <!-- Back Action -->
            <button 
                @click="goBackToLibrary()"
                class="flex items-center gap-2 text-slate-500 hover:text-slate-800 mb-8 transition-colors"
            >
                <ArrowLeft class="w-4 h-4" />
                <span class="text-sm font-medium">Back to search</span>
            </button>

            <!-- Loading & Error -->
            <div v-if="loading" class="flex items-center justify-center h-96">
                <div class="animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full"></div>
            </div>
            <div v-else-if="error" class="text-center py-20">
                <p class="text-red-500 text-lg">{{ error }}</p>
                <button @click="fetchBookDetail" class="mt-4 px-6 py-2 bg-emerald-600 text-white rounded-lg">重试</button>
            </div>

            <div v-else-if="book" class="space-y-12">
                <!-- === TOP NOTIFICATION BANNER (Proactive guidance) === -->
                <transition name="fade">
                    <div v-if="isPotentialGem || hasRisk" class="relative z-50 mb-4">
                        <div 
                            class="flex items-center justify-between px-6 py-3 rounded-2xl shadow-xl border backdrop-blur-md"
                            :class="isPotentialGem ? 'bg-amber-500/10 border-amber-200 text-amber-800' : 'bg-rose-500/10 border-rose-200 text-rose-800'"
                        >
                            <div class="flex items-center gap-3">
                                <div class="p-2 rounded-xl" :class="isPotentialGem ? 'bg-amber-500 text-white' : 'bg-rose-500 text-white'">
                                    <Award v-if="isPotentialGem" class="w-5 h-5" />
                                    <ShieldAlert v-else class="w-5 h-5" />
                                </div>
                                <div>
                                    <p class="font-black text-[15px] leading-none mb-1">
                                        {{ isPotentialGem ? '系统深度发掘：该作品被判定为 S级潜力遗珠' : '系统安全审计：发现商业运营风险预警' }}
                                    </p>
                                    <p class="text-[12px] opacity-80 font-medium">详情已同步至「风险评估」栏目，请及时查阅审计报告。</p>
                                </div>
                            </div>
                            <button @click="activeTab = 'risk'" class="px-5 py-2 bg-white/60 hover:bg-white rounded-xl text-[12px] font-black transition-all border border-black/5">
                                立即查看详情 →
                            </button>
                        </div>
                    </div>
                </transition>
                <!-- ==================== HERO SECTION (结合图一图二的终极设计) ==================== -->
                <div class="flex flex-col lg:flex-row gap-12 items-start mt-4">
                    
                    <!-- Left: 封面 (来自图二的倾斜高级质感) -->
                    <div class="flex-shrink-0 mx-auto lg:mx-0 pt-4">
                        <div class="w-64 h-[340px] rounded-xl shadow-[20px_20px_40px_rgba(0,0,0,0.15)] overflow-hidden relative group rotate-[-2deg] hover:rotate-0 transition-all duration-500 border-4 border-white/80">
                            <!-- Use dynamic cover mapping if failed to load the image, otherwise unsplash placeholder -->
                            <img 
                                :src="book.basic.cover || 'https://images.unsplash.com/photo-1629198688000-71f23e745b6e?q=80&w=800&auto=format&fit=crop'" 
                                alt="Book Cover" 
                                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                            />
                            <!-- VIP Badge -->
                            <div class="absolute top-0 right-0 bg-gradient-to-br from-red-500 to-rose-600 shadow-md text-white text-[11px] font-black px-2.5 py-1 rounded-bl-xl tracking-wider">
                                VIP
                            </div>
                        </div>
                    </div>

                    <!-- Middle: 图二原版排版 (带边框标签、分隔符与横排数据) -->
                    <div class="flex-1 space-y-6 pt-2">
                        <!-- Title Row -->
                        <div class="flex items-center gap-4 flex-wrap">
                            <h1 class="text-5xl font-serif font-black text-[#1d2129] tracking-widest leading-none">{{ book.basic.title }}</h1>
                            <div class="flex items-center gap-2">
                                <div v-if="isPotentialGem" class="flex items-center gap-1 px-3 py-1 bg-gradient-to-r from-amber-400 to-orange-500 text-white rounded-full shadow-lg shadow-amber-200 animate-pulse">
                                    <Award class="w-4 h-4 fill-white" />
                                    <span class="text-[11px] font-black tracking-widest">S级潜力遗珠</span>
                                </div>
                                <div v-if="hasRisk" class="flex items-center gap-1 px-3 py-1 bg-rose-600 text-white rounded-full shadow-lg shadow-rose-200">
                                    <ShieldAlert class="w-4 h-4" />
                                    <span class="text-[11px] font-black tracking-widest">高风险预警</span>
                                </div>
                                <div class="flex items-center gap-1.5 self-start mt-1.5">
                                    <span class="bg-amber-100 p-0.5 rounded-full"><div class="w-4 h-4 rounded-full bg-amber-500 flex items-center justify-center text-white text-[9px] font-bold">V</div></span>
                                    <Crown class="w-6 h-6 text-amber-500 fill-amber-500" />
                                </div>
                            </div>
                        </div>

                        <!-- Author & Rating Row & Monthly Tickets -->
                        <div class="flex items-center gap-10 mt-4 mb-2">
                            <div class="flex items-center gap-6 text-[15px]">
                                <p class="text-[#4e5969]">by <span class="text-[#1d2129] font-medium ml-1">{{ book.basic.author }}</span></p>
                                <div class="w-px h-3.5 bg-slate-200"></div>
                                <div class="flex items-center gap-1.5 -ml-1">
                                    <Star 
                                        v-for="i in 5" 
                                        :key="i" 
                                        class="w-4 h-4"
                                        :class="i <= starRating ? 'text-amber-400 fill-amber-400' : 'text-slate-200'"
                                    />
                                    <span class="text-xl font-black text-[#1d2129] ml-2">{{ (book.ip_evaluation.score / 10).toFixed(1) }}</span>
                                    <span class="text-slate-400 text-[13px] font-medium">/10</span>
                                </div>
                            </div>
                            
                            <!-- 月票移动到这里（作者与评分行右侧） -->
                            <div class="flex items-baseline gap-1 flex-shrink-0">
                                <span class="font-black text-amber-600 text-[20px] tracking-tight whitespace-nowrap" style="font-family: 'Times New Roman', 'FangZhengShuSong', 'STSong', serif;">
                                    {{ (book.stats?.monthly_tickets || 0).toLocaleString() }}
                                </span>
                                <span class="text-amber-700/80 font-bold pl-0.5 text-[13px]">月票</span>
                            </div>
                        </div>

                        <!-- Tags Row -->
                        <div class="flex flex-wrap items-center gap-3 pt-3">
                            <span class="px-2.5 py-0.5 border border-orange-200/80 text-orange-500 rounded text-[13px] font-medium bg-white/50" v-if="book.basic.status !== '完结'">已签约</span>
                            <span 
                                class="px-2.5 py-0.5 border rounded text-[13px] font-medium bg-white/50"
                                :class="book.basic.status === '完结' ? 'border-emerald-200/80 text-emerald-500' : 'border-blue-200/80 text-blue-500'"
                            >
                                {{ book.basic.status === '完结' ? '完结' : '连载中' }}
                            </span>
                            <span class="px-2.5 py-0.5 border border-orange-200/80 text-orange-500 rounded text-[13px] font-medium bg-white/50">{{ book.basic.category || '都市' }}</span>
                            <!-- Dynamic Keywords -->
                            <span 
                                v-for="tag in book.basic.tags" 
                                :key="tag"
                                class="px-2 py-0.5 text-[#4e5969] text-[13px] font-medium"
                            >
                                {{ tag }}
                            </span>
                        </div>

                        <!-- Info Row (Compact Single Line) -->
                        <div class="flex items-center gap-5 text-[13px] text-[#4e5969] mt-6 font-medium overflow-x-auto whitespace-nowrap pb-2 scrollbar-none">
                            <div class="flex items-baseline gap-1">
                                <span class="font-black text-[#1d2129] text-[17px] tracking-tight whitespace-nowrap">{{ formatBigInt((book.stats.click_count || book.stats.heat || 13098) * 10000) }}</span>
                                <span>万总点击</span>
                            </div>
                            <div class="w-px h-3 bg-slate-200"></div>
                            <div class="flex items-baseline gap-1">
                                <span class="font-black text-[#1d2129] text-[17px] tracking-tight whitespace-nowrap">{{ formatBigInt((book.stats.recommend_count || book.stats.fans_count || 43.2) * 10000) }}</span>
                                <span>万总推荐</span>
                            </div>
                            <div class="w-px h-3 bg-slate-200"></div>
                            <div class="flex items-baseline gap-1">
                                <span class="font-black text-[#1d2129] text-[17px] tracking-tight whitespace-nowrap">{{ Math.floor((book.stats.weekly_recommend || 2705)) }}</span>
                                <span>周推荐</span>
                            </div>
                            <div class="w-px h-3 bg-slate-200"></div>
                            <div class="flex items-baseline gap-1">
                                <span class="font-black text-[#1d2129] text-[17px] tracking-tight whitespace-nowrap">{{ formatBigInt((book.stats.word_count || 4800000)) }}</span>
                                <span>万字数</span>
                            </div>
                        </div>
                        
                        <!-- 最新章节 -->
                        <div class="flex items-center gap-2 text-[13px] text-[#4e5969] pt-5 font-medium w-full">
                            <span class="flex-shrink-0">最新章节:</span>
                            <span class="bg-amber-100 p-0.5 rounded-full mt-0.5 flex-shrink-0"><div class="w-3 h-3 rounded-full bg-amber-500 flex items-center justify-center text-white text-[8px] font-bold">V</div></span>
                            <span class="text-[#1d2129] truncate max-w-[500px]">{{ book.basic.latest_chapter || '暂无更新' }}</span>
                            <span v-if="book.basic.updated_at" class="text-slate-400 font-normal ml-2 flex-shrink-0">{{ book.basic.updated_at }}</span>
                        </div>
                    </div>

                    <!-- Right: AI 综合评估卡片 (两版共通点，优化排版) -->
                    <div class="w-80 flex-shrink-0">
                        <div class="bg-white/80 backdrop-blur-xl rounded-[24px] p-7 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100/50 relative overflow-hidden group">
                           
                            <p class="text-xs font-bold text-slate-400 mb-1 relative z-10 tracking-widest uppercase">AI 综合评估</p>
                            <div class="flex items-baseline gap-2 mb-1 relative z-10">
                                <p class="text-7xl font-serif font-black text-emerald-600">{{ book.ip_evaluation.grade?.replace('+', '') || 'A' }}<span class="text-4xl text-emerald-500 align-top relative -top-3" v-if="(book.ip_evaluation.grade || '').includes('+')">+</span></p>
                            </div>
                            <p class="text-xs text-slate-500 mb-8 relative z-10 pb-4 border-b border-slate-100">Top <span class="font-bold text-slate-700">{{ (100 - (book.ip_evaluation.percentile || 50)).toFixed(1) }}%</span> in {{ book.basic.category || 'Fiction' }} Genre</p>

                            <div class="space-y-4 text-sm relative z-10 font-medium">
                                <div class="flex justify-between items-center">
                                    <span class="text-slate-600">商业价值</span>
                                    <span class="font-bold text-slate-900">{{ book.ip_evaluation.commercial_value }}</span>
                                </div>
                                <div class="flex justify-between items-center">
                                    <span class="text-slate-600">改编难度</span>
                                    <span class="font-bold text-slate-900">{{ book.ip_evaluation.adaptation_difficulty }}</span>
                                </div>
                                <div class="flex justify-between items-center">
                                    <span class="text-slate-600">风险系数</span>
                                    <span 
                                        class="font-black"
                                        :class="book.ip_evaluation.risk_factor === '低' ? 'text-emerald-500' : 'text-amber-500'"
                                    >{{ book.ip_evaluation.risk_factor }}</span>
                                </div>
                                <div class="flex justify-between items-center">
                                    <span class="text-slate-600">治愈指数</span>
                                    <span class="font-black text-purple-500">{{ book.ip_evaluation.healing_index ?? '--' }}</span>
                                </div>
                                <div class="flex justify-between items-center">
                                    <span class="text-slate-600">全球化潜力</span>
                                    <span class="font-black text-blue-500">{{ book.ip_evaluation.global_potential ?? '--' }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>


                <!-- ==================== TABS AREA ==================== -->
                <div class="flex gap-2 mb-6 mt-8 relative">
                    <!-- 背景修饰线段 -->
                    <!-- Removed for cleaner look, handled border bottom generally -->
                    <button 
                        v-for="tab in [
                            { id: 'overview', label: '概览', en: 'Overview' },
                            { id: 'roleplay', label: '角色对话', en: 'Chat' },
                            { id: 'risk', label: '风险评估', en: 'Risk' },
                            { id: 'ai-audit', label: 'AI 审计', en: 'AI Audit' },
                            { id: 'valuation', label: '价值估算', en: 'Valuation' },
                            { id: 'global', label: '全球化', en: 'Global' },
                            { id: 'audit', label: '虚拟试读', en: 'Virtual Reader' },
                        ]"
                        :key="tab.id"
                        @click="activeTab = tab.id"
                        class="px-5 py-2 text-sm font-bold transition-all rounded-full border flex items-center gap-2"
                        :class="activeTab === tab.id 
                            ? 'bg-white border-transparent shadow-[0_2px_10px_rgba(0,0,0,0.05)] text-slate-900' 
                            : 'border-transparent text-slate-500 hover:text-slate-700 bg-white/40 hover:bg-white/80'"
                    >
                        {{ tab.label }}
                        <span v-if="tab.id === 'ai-audit' && bookAuditLogs.length > 0" class="px-1.5 py-0.5 bg-amber-500 text-white text-[10px] rounded-full font-black ml-0.5 transform scale-90 origin-left">
                            {{ bookAuditLogs.length }}
                        </span>
                        <span class="text-slate-400 text-xs font-normal pl-1 border-l border-slate-100 ml-1" v-if="activeTab !== tab.id">{{ tab.en }}</span>
                    </button>
                </div>


                <!-- ==================== TAB CONTENT ==================== -->
                <div class="min-h-[400px]">
                    <!-- Overview Tab 包含了作品简介、心电图与雷达图 -->
                    <div v-if="activeTab === 'overview'" class="space-y-6">
                        
                        <!-- 融合图二：作品简介置顶于一整块的大卡片 -->
                        <div class="bg-white/90 backdrop-blur-xl rounded-[24px] p-8 border border-white shadow-[0_8px_30px_rgb(0,0,0,0.03)] flex flex-col items-center">
                            <BookOpen class="w-8 h-8 text-slate-300 mb-3" />
                            <h3 class="font-bold text-slate-900 mb-4 text-center">作品简介</h3>
                            <div class="max-w-4xl w-full text-center">
                                <p 
                                    class="text-slate-600 leading-relaxed transition-all font-medium"
                                    :class="synopsisExpanded ? '' : 'line-clamp-2'"
                                >{{ book.basic.synopsis || book.basic.abstract || '暂无作品详细内容介绍' }}</p>
                                <button 
                                    v-if="(book.basic.synopsis || book.basic.abstract || '').length > 60"
                                    @click="synopsisExpanded = !synopsisExpanded" 
                                    class="mt-4 text-emerald-600 hover:text-emerald-700 text-sm font-bold transition-colors uppercase tracking-widest mx-auto block"
                                >
                                    {{ synopsisExpanded ? 'Less △' : 'More ▽' }}
                                </button>
                            </div>
                        </div>

                        <!-- 左右两栏并排放置图表：心电图与六维评估 -->
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
                            <!-- Narrative EKG Column (动态) -->
                            <div class="bg-white/90 backdrop-blur-xl rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.03)] border border-white flex flex-col">
                                <h3 class="text-2xl font-serif font-black text-slate-900 tracking-tight mb-1">Narrative EKG</h3>
                                <p class="text-sm text-slate-500 mb-6 font-medium">叙事心电图 · 情节张力分析</p>
                                
                                <div class="flex-1 min-h-[280px] relative w-full pr-4 pb-6 mt-auto">
                                    <!-- Y Axis Labels -->
                                    <div class="absolute -left-1 top-0 h-full flex flex-col justify-between text-[11px] font-bold text-slate-300 py-3 pb-8">
                                        <span>100</span>
                                        <span>75</span>
                                        <span>50</span>
                                        <span>25</span>
                                        <span>0</span>
                                    </div>
                                    
                                    <svg 
                                        class="w-full h-full pl-8" 
                                        viewBox="0 0 400 200" 
                                        preserveAspectRatio="none"
                                        @mousemove="onEkgMouseMove($event)"
                                        @mouseleave="ekgHover = null"
                                    >
                                        <defs>
                                            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                                <stop offset="0%" style="stop-color:#3b82f6" />
                                                <stop offset="50%" style="stop-color:#e11d48" />
                                                <stop offset="100%" style="stop-color:#9333ea" />
                                            </linearGradient>
                                            <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                                <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:0.08" />
                                                <stop offset="100%" style="stop-color:#9333ea;stop-opacity:0.01" />
                                            </linearGradient>
                                        </defs>

                                        <!-- Guidelines -->
                                        <line x1="0" y1="20" x2="400" y2="20" stroke="#f1f5f9" stroke-width="1"/>
                                        <line x1="0" y1="60" x2="400" y2="60" stroke="#f1f5f9" stroke-width="1"/>
                                        <line x1="0" y1="100" x2="400" y2="100" stroke="#f1f5f9" stroke-width="1" stroke-dasharray="4"/>
                                        <line x1="0" y1="140" x2="400" y2="140" stroke="#f1f5f9" stroke-width="1"/>
                                        <line x1="0" y1="180" x2="400" y2="180" stroke="#e2e8f0" stroke-width="1.5"/>

                                        <!-- 高张力区域标识 -->
                                        <rect x="0" y="0" width="400" height="60" fill="#fef2f2" opacity="0.3" rx="2"/>

                                        <!-- 面积填充 -->
                                        <path :d="ekgAreaPath" fill="url(#areaGradient)" />

                                        <!-- 动态曲线 -->
                                        <path :d="ekgCurvePath" fill="none" stroke="url(#lineGradient)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />

                                        <!-- 数据点 -->
                                        <g v-for="(pt, idx) in ekgSvgPoints" :key="idx">
                                            <circle 
                                                :cx="pt.x" :cy="pt.y" r="4"
                                                :fill="pt.tension >= 70 ? '#ef4444' : pt.tension >= 50 ? '#f59e0b' : '#3b82f6'"
                                                stroke="#fff" stroke-width="1.5"
                                                class="cursor-pointer transition-all"
                                                :opacity="ekgHover?.segment === pt.segment ? 1 : 0.7"
                                            />
                                        </g>

                                        <!-- 悬浮指示线 -->
                                        <line v-if="ekgHover" :x1="ekgHover.x" y1="0" :x2="ekgHover.x" y2="200" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3"/>
                                    </svg>

                                    <!-- 悬浮 Tooltip -->
                                    <div 
                                        v-if="ekgHover" 
                                        class="absolute z-50 pointer-events-none bg-slate-900/90 backdrop-blur text-white px-3 py-2 rounded-lg shadow-xl text-xs min-w-[120px]"
                                        :style="{ left: ekgHover.tooltipX + 'px', top: ekgHover.tooltipY + 'px' }"
                                    >
                                        <div class="font-bold mb-1">第 {{ ekgHover.segment }} 段</div>
                                        <div class="flex justify-between gap-3">
                                            <span class="text-slate-300">张力值</span>
                                            <span class="font-bold" :class="ekgHover.tension >= 70 ? 'text-red-400' : ekgHover.tension >= 50 ? 'text-amber-400' : 'text-blue-400'">{{ ekgHover.tension }}</span>
                                        </div>
                                        <div class="flex justify-between gap-3">
                                            <span class="text-slate-300">阶段</span>
                                            <span>{{ ekgHover.label }}</span>
                                        </div>
                                    </div>

                                    <!-- X Axis Labels -->
                                    <div class="flex justify-between text-[11px] font-bold text-slate-300 px-8 absolute bottom-0 w-full left-4 pt-2">
                                        <span v-for="i in 20" :key="i">{{ i }}</span>
                                    </div>
                                </div>
                                <div class="flex justify-center gap-8 text-[10px] font-bold text-slate-500 mt-4">
                                    <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-red-500 inline-block"></span>高张力 (70+)</span>
                                    <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-amber-500 inline-block"></span>中张力 (50-70)</span>
                                    <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-blue-500 inline-block"></span>基线 (&lt;50)</span>
                                </div>
                            </div>
                            
                            <!-- Six Dimensions Column (复原图一的雷达+数值方阵) -->
                            <div class="bg-white/90 backdrop-blur-xl rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.03)] border border-white flex flex-col">
                                <h3 class="text-2xl font-serif font-black text-slate-900 tracking-tight mb-1">六维评估</h3>
                                <p class="text-sm text-slate-500 mb-8 font-medium">Dimension Analysis</p>

                                <!-- Radar Chart Area -->
                                <div class="flex-1 flex flex-col items-center justify-center relative">
                                    <div 
                                        class="flex justify-center h-[300px] items-center relative w-full mb-6"
                                        @mousemove="onRadarMouseMove"
                                        @mouseleave="isRadarHovered = false"
                                    >
                                        <!-- 悬浮 Tooltip -->
                                        <div 
                                            v-if="isRadarHovered && dimensions" 
                                            class="absolute z-50 pointer-events-none bg-white backdrop-blur-md rounded-2xl shadow-[0_10px_40px_rgba(0,0,0,0.08)] p-5 min-w-[160px] border border-slate-100 transition-all duration-75"
                                            :style="{ left: radarHoverX + 20 + 'px', top: Math.max(0, radarHoverY - 80) + 'px' }"
                                        >
                                            <p class="font-bold text-slate-800 mb-3 pb-2 border-b border-slate-100 flex items-center gap-2">
                                                <span>IP 维度分析</span>
                                            </p>
                                            <div class="space-y-2.5 text-[13px] font-medium">
                                                <div class="flex justify-between items-center gap-6">
                                                    <span class="text-slate-500">故事性</span>
                                                    <span class="text-emerald-500 font-bold">{{ dimensions?.story ?? '--' }}</span>
                                                </div>
                                                <div class="flex justify-between items-center gap-6">
                                                    <span class="text-slate-500">人物塑造</span>
                                                    <span class="text-emerald-500 font-bold">{{ dimensions?.character ?? '--' }}</span>
                                                </div>
                                                <div class="flex justify-between items-center gap-6">
                                                    <span class="text-slate-500">世界观</span>
                                                    <span class="text-emerald-500 font-bold">{{ dimensions?.world ?? '--' }}</span>
                                                </div>
                                                <div class="flex justify-between items-center gap-6">
                                                    <span class="text-slate-500">商业价值</span>
                                                    <span class="text-emerald-500 font-bold">{{ dimensions?.commercial ?? '--' }}</span>
                                                </div>
                                                <div class="flex justify-between items-center gap-6">
                                                    <span class="text-slate-500">改编潜力</span>
                                                    <span class="text-emerald-500 font-bold">{{ dimensions?.adaptation ?? '--' }}</span>
                                                </div>
                                                <div class="flex justify-between items-center gap-6">
                                                    <span class="text-slate-500">安全性</span>
                                                    <span class="text-emerald-500 font-bold">{{ dimensions?.safety ?? '--' }}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <svg class="w-[320px] h-[320px]" viewBox="-30 0 360 300" overflow="visible">
                                            <!-- Polygon Grids -->
                                            <g stroke="#cbd5e1" fill="none" class="opacity-40" stroke-width="1.5">
                                                <polygon points="150,40 245,95 245,205 150,260 55,205 55,95" />
                                                <polygon points="150,70 219,110 219,190 150,230 81,190 81,110" />
                                                <polygon points="150,100 193,125 193,175 150,200 107,175 107,125" />
                                                <polygon points="150,130 167,140 167,160 150,170 133,160 133,140" />
                                            </g>

                                            <!-- Axis Spokes -->
                                            <g stroke="#cbd5e1" stroke-width="1.5" class="opacity-40">
                                                <line x1="150" y1="150" x2="150" y2="40" />
                                                <line x1="150" y1="150" x2="245" y2="95" />
                                                <line x1="150" y1="150" x2="245" y2="205" />
                                                <line x1="150" y1="150" x2="150" y2="260" />
                                                <line x1="150" y1="150" x2="55" y2="205" />
                                                <line x1="150" y1="150" x2="55" y2="95" />
                                            </g>

                                            <!-- Data Polygon (动态) -->
                                            <polygon 
                                                :points="radarPoints" 
                                                fill="rgba(16, 185, 129, 0.15)" 
                                                stroke="#10b981" 
                                                stroke-width="2.5" 
                                                stroke-linejoin="round"
                                            />

                                            <!-- Data Vertex Dots (动态) -->
                                            <g fill="#10b981" stroke="#fff" stroke-width="1.5">
                                                <circle v-for="(dot, idx) in radarDots" :key="idx" :cx="dot.x" :cy="dot.y" r="4.5" />
                                            </g>

                                            <!-- Labels -->
                                            <g class="text-[13px] font-bold fill-slate-600">
                                                <text x="150" y="25" text-anchor="middle">故事性</text>
                                                <text x="262" y="93" text-anchor="start">安全性</text>
                                                <text x="262" y="218" text-anchor="start">改编潜力</text>
                                                <text x="150" y="285" text-anchor="middle">商业价值</text>
                                                <text x="38" y="218" text-anchor="end">世界观</text>
                                                <text x="38" y="93" text-anchor="end">人物塑造</text>
                                            </g>
                                        </svg>
                                    </div>
                                    
                                    <!-- 具体的极具高级感的六维分数看板 -->
                                    <div class="w-full grid grid-cols-3 gap-y-4 gap-x-2 mt-auto pt-6 border-t border-slate-100">
                                        <div class="flex justify-between items-center px-2">
                                            <span class="text-[13px] font-medium text-slate-800">故事性</span>
                                            <span class="text-[15px] font-black text-slate-900">{{ dimensions?.story ?? '--' }}</span>
                                        </div>
                                        <div class="flex justify-between items-center px-2">
                                            <span class="text-[13px] font-medium text-slate-800">人物塑造</span>
                                            <span class="text-[15px] font-black text-slate-900">{{ dimensions?.character ?? '--' }}</span>
                                        </div>
                                        <div class="flex justify-between items-center px-2">
                                            <span class="text-[13px] font-medium text-slate-800">世界观</span>
                                            <span class="text-[15px] font-black text-slate-900">{{ dimensions?.world ?? '--' }}</span>
                                        </div>
                                        <div class="flex justify-between items-center px-2">
                                            <span class="text-[13px] font-medium text-slate-800">商业价值</span>
                                            <span class="text-[15px] font-black text-slate-900">{{ dimensions?.commercial ?? '--' }}</span>
                                        </div>
                                        <div class="flex justify-between items-center px-2">
                                            <span class="text-[13px] font-medium text-slate-800">改编潜力</span>
                                            <span class="text-[15px] font-black text-slate-900">{{ dimensions?.adaptation ?? '--' }}</span>
                                        </div>
                                        <div class="flex justify-between items-center px-2">
                                            <span class="text-[13px] font-medium text-slate-800">安全性</span>
                                            <span class="text-[15px] font-black text-slate-900">{{ dimensions?.safety ?? '--' }}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>


                    <!-- ==================== Roleplay / Chat ==================== -->
                    <div v-if="activeTab === 'roleplay'" class="bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-[0_8px_30px_rgb(0,0,0,0.03)] overflow-hidden" style="min-height: 500px;">
                        <!-- 游客模式提示 -->
                        <div v-if="!isLoggedIn" class="p-20 text-center">
                            <div class="w-20 h-20 bg-purple-50 rounded-full flex items-center justify-center mx-auto mb-6">
                                <UserSquare class="w-10 h-10 text-purple-600" />
                            </div>
                            <h3 class="text-2xl font-bold text-slate-800 mb-3">开启角色对话</h3>
                            <p class="text-slate-500 mb-8 max-w-md mx-auto">登录后即可利用 AI 技术从书中提取灵魂角色，并与之跨次元对话，深度理解人物动机与台词风格。</p>
                            <button @click="router.push('/login')" class="px-10 py-3.5 bg-purple-600 text-white rounded-xl font-bold shadow-lg shadow-purple-200 hover:bg-purple-700 hover:-translate-y-0.5 transition-all">
                                立即登录
                            </button>
                        </div>

                        <template v-else>
                            <div v-if="characters.length === 0 && !isExtractingChars" class="p-16 text-center">
                                <Sparkles class="w-16 h-16 mx-auto mb-4 text-purple-300" />
                                <h3 class="text-xl font-bold text-slate-800 mb-2">角色扮演</h3>
                                <p class="text-slate-500 mb-6">AI 将从《{{ book.basic.title }}》中提取主要角色供你对话</p>
                                <button @click="extractCharacters()" class="px-6 py-3 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700">提取书中角色</button>
                            </div>
                            <div v-else-if="isExtractingChars" class="p-16 text-center">
                                <div class="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                                <p class="text-slate-500 font-medium">AI 正在深度分析角色属性与台词风格...</p>
                            </div>
                            <div v-else class="flex h-[600px]">
                                <div class="w-64 bg-slate-50/50 border-r border-slate-100 p-4 space-y-2 overflow-y-auto">
                                    <button v-for="char in characters" :key="char.name" @click="selectCharacter(char)" class="w-full text-left p-3 rounded-xl transition-all flex items-center gap-3" :class="activeCharacter?.name === char.name ? 'bg-white shadow-sm border border-slate-200' : 'hover:bg-slate-100/50 border border-transparent'">
                                        <span class="text-2xl">{{ char.avatar }}</span>
                                        <div class="flex-1 min-w-0"><div class="font-bold text-sm text-slate-800 truncate">{{ char.name }}</div><div class="text-[11px] text-slate-500 truncate">{{ char.description }}</div></div>
                                    </button>
                                    <button @click="extractCharacters(true)" class="w-full text-[11px] font-bold uppercase tracking-wider text-slate-400 hover:text-purple-600 pt-4 pb-2 flex items-center justify-center gap-1"><RefreshCw class="w-3 h-3" /> Retry Extraction</button>
                                </div>
                                <div class="flex-1 flex flex-col bg-slate-50/20">
                                    <div v-if="activeCharacter" class="h-[72px] border-b border-slate-100 px-6 flex items-center justify-between bg-white/50 backdrop-blur-sm">
                                        <div class="flex items-center gap-4">
                                            <span class="text-3xl">{{ activeCharacter.avatar }}</span>
                                            <div>
                                                <div class="font-black text-slate-800 tracking-tight">{{ activeCharacter.name }}</div>
                                                <div class="text-xs font-medium text-slate-500 truncate max-w-[400px]">{{ activeCharacter.persona }}</div>
                                            </div>
                                        </div>
                                        <button @click="clearChatHistory" class="text-[10px] font-bold uppercase tracking-wider text-slate-400 hover:text-red-500 px-3 py-1.5 rounded-lg border border-transparent hover:border-red-100 hover:bg-red-50 transition-colors">Clear Chat</button>
                                    </div>
                                    <div ref="chatContainer" class="flex-1 p-6 overflow-y-auto space-y-6">
                                        <div v-if="chatHistory.length === 0" class="h-full flex items-center justify-center text-slate-400 mix-blend-multiply font-medium"><p>Start a conversation with {{ activeCharacter?.name }}...</p></div>
                                        <div v-for="(msg, i) in chatHistory" :key="i" class="flex gap-4" :class="msg.role === 'user' ? 'flex-row-reverse' : ''">
                                            <div class="w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center text-lg shadow-sm" :class="msg.role === 'user' ? 'bg-slate-200' : 'bg-white border border-purple-100'">{{ msg.role === 'user' ? '我' : activeCharacter?.avatar }}</div>
                                            <div class="max-w-[70%] p-4 rounded-2xl text-[15px] leading-relaxed shadow-sm font-medium" :class="msg.role === 'user' ? 'bg-purple-600 text-white rounded-tr-none' : 'bg-white border border-slate-100 rounded-tl-none text-slate-700'">{{ msg.content }}</div>
                                        </div>
                                        <div v-if="isSending" class="flex gap-4">
                                            <div class="w-10 h-10 rounded-full bg-white border border-purple-100 flex items-center justify-center shadow-sm">{{ activeCharacter?.avatar }}</div>
                                            <div class="bg-white border px-5 py-4 rounded-2xl rounded-tl-none flex gap-1.5 shadow-sm items-center"><span class="w-2 h-2 bg-slate-300 rounded-full animate-bounce"></span><span class="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style="animation-delay:0.15s"></span><span class="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style="animation-delay:0.3s"></span></div>
                                        </div>
                                    </div>
                                    <div class="p-4 border-t border-slate-100 bg-white/50 backdrop-blur-sm">
                                        <div class="relative max-w-4xl mx-auto">
                                            <input v-model="inputMessage" @keyup.enter="sendMessage" type="text" :placeholder="`向 ${activeCharacter?.name} 提问...`" class="w-full pl-6 pr-14 py-4 bg-white border border-slate-200 shadow-sm rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500/20 text-slate-700 font-medium placeholder-slate-400" />
                                            <button @click="sendMessage" :disabled="isSending || !inputMessage.trim()" class="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-200 disabled:text-slate-400 rounded-xl flex items-center justify-center text-white transition-colors shadow-sm"><Send class="w-4 h-4 ml-0.5" /></button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </template>
                    </div>

                    <!-- Risk Assessment Tab -->
                    <div v-if="activeTab === 'risk'" class="pt-2">
                        <div v-if="(!riskData && isFetchingRisk) || (!healingData && isFetchingHealing)" class="p-16 text-center bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-sm">
                            <div class="w-12 h-12 border-4 border-slate-200 border-t-slate-800 rounded-full animate-spin mx-auto mb-4"></div>
                            <p class="text-slate-500 font-medium tracking-wide">AI 正在进行深度风险熔断与情绪治愈指数测算...</p>
                        </div>
                        <div v-else-if="riskData && healingData" class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                            <!-- Left Card: Risk Radar -->
                            <div class="bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col">
                                <!-- Header -->
                                <div class="flex justify-between items-start mb-10 pb-6 border-b border-slate-50">
                                    <div class="flex gap-4 items-start">
                                        <div class="mt-1">
                                            <ShieldAlert class="w-6 h-6 text-slate-800" stroke-width="1.5" />
                                        </div>
                                        <div>
                                            <h3 class="font-serif text-[22px] font-bold text-slate-900 tracking-tight leading-none mb-1.5">Risk Radar</h3>
                                            <p class="text-[13px] text-slate-500 font-medium">风险"熔断"雷达</p>
                                        </div>
                                    </div>
                                    <div class="flex flex-col items-end">
                                        <div class="flex items-center gap-1.5 text-slate-600 mb-2">
                                            <ShieldAlert class="w-4 h-4" :class="riskData.overall_score < 60 ? 'text-amber-500' : 'text-slate-400'" />
                                            <span class="text-[13px] font-bold">{{ riskData.overall_score < 60 ? '高危预警' : '需关注' }}</span>
                                        </div>
                                        <div class="flex items-baseline gap-1">
                                            <span class="text-[40px] font-black tracking-tighter leading-none" :class="riskData.overall_score >= 80 ? 'text-slate-900' : 'text-red-500'">{{ riskData.overall_score }}</span>
                                        </div>
                                        <span class="text-[11px] text-slate-400 font-medium mt-1">综合安全分</span>
                                    </div>
                                </div>
                                
                                <!-- Risk Dimensions List -->
                                <div class="space-y-4 mb-8">
                                    <div v-for="dim in riskData.dimensions" :key="dim.id" 
                                         class="group flex justify-between items-center p-4 rounded-2xl transition-colors hover:bg-slate-50 border border-transparent hover:border-slate-100">
                                        <div class="flex items-center gap-4">
                                            <div class="w-10 h-10 rounded-full bg-slate-50 flex items-center justify-center text-slate-500 group-hover:bg-white group-hover:shadow-sm">
                                                <Shield v-if="dim.id==='content'" class="w-5 h-5" stroke-width="1.5" />
                                                <FileText v-else-if="dim.id==='plagiarism'" class="w-5 h-5" stroke-width="1.5" />
                                                <UserSquare v-else-if="dim.id==='author'" class="w-5 h-5" stroke-width="1.5" />
                                                <Copyright v-else-if="dim.id==='copyright'" class="w-5 h-5" stroke-width="1.5" />
                                                <Scale v-else class="w-5 h-5" stroke-width="1.5" />
                                            </div>
                                            <div>
                                                <div class="flex items-baseline gap-2 mb-0.5">
                                                    <span class="text-[15px] font-bold text-slate-800">{{ dim.label }}</span>
                                                    <span class="text-[11px] text-slate-400 font-medium tracking-wide">{{ dim.en }}</span>
                                                </div>
                                                <p class="text-[13px] text-slate-500">{{ dim.desc }}</p>
                                            </div>
                                        </div>
                                        <div class="flex items-center gap-3">
                                            <span class="text-xl font-black text-slate-800">{{ dim.score }}</span>
                                            <div class="w-6 h-6 rounded-full flex items-center justify-center" :class="dim.score >= 85 ? 'bg-slate-100 text-slate-600' : 'bg-red-50 text-red-500'">
                                                <svg v-if="dim.score >= 85" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path></svg>
                                                <span v-else class="text-sm font-black">!</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="mt-auto bg-slate-50 rounded-xl p-4 text-[13px] text-slate-500 font-medium border border-slate-100">
                                    AI决策审计中心：所有风险判断均已记录，支持事后审计和反馈学习
                                </div>
                            </div>
                            
                            <!-- Right Card: Healing Index -->
                            <div class="bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col h-full">
                                <!-- Header -->
                                <div class="flex justify-between items-start mb-8">
                                    <div class="flex gap-4 items-start">
                                        <div class="mt-1">
                                            <Heart class="w-6 h-6 text-slate-800" stroke-width="1.5" />
                                        </div>
                                        <div>
                                            <h3 class="font-serif text-[22px] font-bold text-slate-900 tracking-tight leading-none mb-1.5">Healing Index</h3>
                                            <p class="text-[13px] text-slate-500 font-medium">情绪价值·治愈系指数</p>
                                        </div>
                                    </div>
                                    <div class="flex flex-col items-end">
                                        <div class="flex items-baseline gap-1 text-blue-500">
                                            <span class="text-[40px] font-black tracking-tighter leading-none">{{ healingData.overall_index }}</span>
                                        </div>
                                        <span class="text-[11px] text-slate-500 font-bold mt-1 tracking-wide">综合治愈指数</span>
                                    </div>
                                </div>
                                
                                <!-- 5 Icons Row -->
                                <div class="flex justify-between items-center px-4 mb-10 pb-8 border-b border-slate-50">
                                    <div class="flex flex-col items-center gap-4 group cursor-default">
                                        <Sun class="w-6 h-6 text-slate-400 group-hover:text-amber-500 transition-colors" stroke-width="1.5" />
                                        <div class="text-center">
                                            <div class="text-lg font-black text-slate-800">{{ healingData.dimensions.find((d:any) => d.id === 'warmth')?.score }}</div>
                                            <div class="text-[11px] text-slate-500 font-medium mt-0.5">温暖感</div>
                                        </div>
                                    </div>
                                    <div class="flex flex-col items-center gap-4 group cursor-default">
                                        <Sparkles class="w-6 h-6 text-slate-400 group-hover:text-yellow-400 transition-colors" stroke-width="1.5" />
                                        <div class="text-center">
                                            <div class="text-lg font-black text-slate-800">{{ healingData.dimensions.find((d:any) => d.id === 'hope')?.score }}</div>
                                            <div class="text-[11px] text-slate-500 font-medium mt-0.5">希望感</div>
                                        </div>
                                    </div>
                                    <div class="flex flex-col items-center gap-4 group cursor-default">
                                        <Coffee class="w-6 h-6 text-slate-400 group-hover:text-orange-400 transition-colors" stroke-width="1.5" />
                                        <div class="text-center">
                                            <div class="text-lg font-black text-slate-800">{{ healingData.dimensions.find((d:any) => d.id === 'comfort')?.score }}</div>
                                            <div class="text-[11px] text-slate-500 font-medium mt-0.5">舒适感</div>
                                        </div>
                                    </div>
                                    <div class="flex flex-col items-center gap-4 group cursor-default">
                                        <Leaf class="w-6 h-6 text-slate-400 group-hover:text-emerald-500 transition-colors" stroke-width="1.5" />
                                        <div class="text-center">
                                            <div class="text-lg font-black text-slate-800">{{ healingData.dimensions.find((d:any) => d.id === 'nature')?.score }}</div>
                                            <div class="text-[11px] text-slate-500 font-medium mt-0.5">自然感</div>
                                        </div>
                                    </div>
                                    <div class="flex flex-col items-center gap-4 group cursor-default">
                                        <Moon class="w-6 h-6 text-slate-400 group-hover:text-indigo-400 transition-colors" stroke-width="1.5" />
                                        <div class="text-center">
                                            <div class="text-lg font-black text-slate-800">{{ healingData.dimensions.find((d:any) => d.id === 'nostalgia')?.score }}</div>
                                            <div class="text-[11px] text-slate-500 font-medium mt-0.5">怀旧感</div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Dimension Details List -->
                                <div class="space-y-4 mb-8">
                                    <div class="flex items-start gap-4">
                                        <div class="w-8 h-8 flex items-center justify-center flex-shrink-0 mt-1"><Sun class="w-5 h-5 text-slate-700" stroke-width="1.5" /></div>
                                        <div>
                                            <div class="flex items-baseline gap-2 mb-1">
                                                <span class="text-[14px] font-bold text-slate-800">温暖感</span><span class="text-[11px] text-slate-400">Warmth</span>
                                            </div>
                                            <p class="text-[13px] text-slate-600">{{ healingData.dimensions.find((d:any) => d.id === 'warmth')?.desc }}</p>
                                        </div>
                                    </div>
                                    <div class="flex items-start gap-4">
                                        <div class="w-8 h-8 flex items-center justify-center flex-shrink-0 mt-1"><Sparkles class="w-5 h-5 text-slate-700" stroke-width="1.5" /></div>
                                        <div>
                                            <div class="flex items-baseline gap-2 mb-1">
                                                <span class="text-[14px] font-bold text-slate-800">希望感</span><span class="text-[11px] text-slate-400">Hope</span>
                                            </div>
                                            <p class="text-[13px] text-slate-600">{{ healingData.dimensions.find((d:any) => d.id === 'hope')?.desc }}</p>
                                        </div>
                                    </div>
                                    <div class="flex items-start gap-4">
                                        <div class="w-8 h-8 flex items-center justify-center flex-shrink-0 mt-1"><Coffee class="w-5 h-5 text-slate-700" stroke-width="1.5" /></div>
                                        <div>
                                            <div class="flex items-baseline gap-2 mb-1">
                                                <span class="text-[14px] font-bold text-slate-800">舒适感</span><span class="text-[11px] text-slate-400">Comfort</span>
                                            </div>
                                            <p class="text-[13px] text-slate-600">{{ healingData.dimensions.find((d:any) => d.id === 'comfort')?.desc }}</p>
                                        </div>
                                    </div>
                                    <div class="flex items-start gap-4">
                                        <div class="w-8 h-8 flex items-center justify-center flex-shrink-0 mt-1"><Leaf class="w-5 h-5 text-slate-700" stroke-width="1.5" /></div>
                                        <div>
                                            <div class="flex items-baseline gap-2 mb-1">
                                                <span class="text-[14px] font-bold text-slate-800">自然感</span><span class="text-[11px] text-slate-400">Nature</span>
                                            </div>
                                            <p class="text-[13px] text-slate-600">{{ healingData.dimensions.find((d:any) => d.id === 'nature')?.desc }}</p>
                                        </div>
                                    </div>
                                    <div class="flex items-start gap-4">
                                        <div class="w-8 h-8 flex items-center justify-center flex-shrink-0 mt-1"><Moon class="w-5 h-5 text-slate-700" stroke-width="1.5" /></div>
                                        <div>
                                            <div class="flex items-baseline gap-2 mb-1">
                                                <span class="text-[14px] font-bold text-slate-800">怀旧感</span><span class="text-[11px] text-slate-400">Nostalgia</span>
                                            </div>
                                            <p class="text-[13px] text-slate-600">{{ healingData.dimensions.find((d:any) => d.id === 'nostalgia')?.desc }}</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="mt-auto bg-slate-50 border border-slate-100 rounded-2xl p-5">
                                    <div class="flex items-center gap-2 mb-2">
                                        <Leaf class="w-4 h-4 text-emerald-600" />
                                        <span class="font-bold text-[13px] text-slate-800">ESG 价值观契合度</span>
                                    </div>
                                    <p class="text-[13px] text-slate-500 leading-relaxed">{{ healingData.esg_desc }}</p>
                                </div>
                            </div>
                        </div>

                        <div v-if="bookAuditLogs && bookAuditLogs.length > 0" class="mt-8 p-12 text-center bg-white/60 backdrop-blur-sm rounded-[24px] border border-dashed border-slate-200">
                             <p class="text-slate-400 font-medium text-sm">此作品已存在关联审计报告，请前往「AI 审计」频道查阅。</p>
                        </div>
                    </div>

                    <div v-if="activeTab === 'ai-audit'" class="space-y-6 pt-2">
                        <!-- 游客模式提示 -->
                        <div v-if="!isLoggedIn" class="p-20 text-center bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-sm">
                            <div class="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-6">
                                <Shield class="w-10 h-10 text-indigo-600" />
                            </div>
                            <h3 class="text-2xl font-bold text-slate-800 mb-3">开启 AI 深度审计</h3>
                            <p class="text-slate-500 mb-8 max-w-md mx-auto">登录后即可基于六维数据与 AI 大模型生成全方位的商业决策与风险排查报告。</p>
                            <button @click="router.push('/login')" class="px-10 py-3.5 bg-indigo-600 text-white rounded-xl font-bold shadow-lg shadow-indigo-200 hover:bg-indigo-700 hover:-translate-y-0.5 transition-all">
                                立即登录
                            </button>
                        </div>
                        
                        <div v-else class="flex flex-col gap-6">
                        <div class="flex items-center justify-between mb-4">
                            <div class="flex items-center gap-3">
                                <ShieldAlert class="w-8 h-8 text-slate-800" />
                                <h3 class="text-3xl font-serif font-black text-slate-900 tracking-tight">IP 商业决策审计报告</h3>
                            </div>
                            <button 
                                @click="triggerBookAudit" 
                                :disabled="isAuditing"
                                class="px-6 py-2.5 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800 transition-all flex items-center gap-2 text-sm"
                            >
                                <RefreshCw class="w-4 h-4" :class="{ 'animate-spin': isAuditing }" />
                                {{ isAuditing ? '审计中...' : '重新发起审计' }}
                            </button>
                        </div>

                        <div v-if="bookAuditLogs && bookAuditLogs.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <div 
                                v-for="log in bookAuditLogs" 
                                :key="log.id"
                                class="bg-white rounded-[28px] p-7 shadow-[0_10px_40px_rgba(0,0,0,0.04)] border transition-all hover:-translate-y-1 hover:shadow-xl relative overflow-hidden group"
                                :class="log.risk_type === 'GLOBAL_GEM' ? 'border-indigo-200 bg-gradient-to-br from-indigo-50/80 to-purple-50/50' : log.risk_type === 'POTENTIAL_GEM' ? 'border-amber-100 bg-gradient-to-br from-white to-amber-50/30' : log.risk_type === 'NORMAL' ? 'border-emerald-100 bg-gradient-to-br from-white to-emerald-50/30' : 'border-rose-100 bg-gradient-to-br from-white to-rose-50/30'"
                            >
                                <!-- Decorative BG -->
                                <div class="absolute -right-6 -bottom-6 opacity-[0.05] group-hover:opacity-[0.1] transition-opacity pointer-events-none">
                                    <Globe v-if="log.risk_type === 'GLOBAL_GEM'" class="w-32 h-32 text-indigo-700" />
                                    <Award v-else-if="log.risk_type === 'POTENTIAL_GEM'" class="w-32 h-32 text-amber-600" />
                                    <CheckCircle2 v-else-if="log.risk_type === 'NORMAL'" class="w-32 h-32 text-emerald-600" />
                                    <ShieldAlert v-else class="w-32 h-32 text-rose-900" />
                                </div>

                                <div class="flex justify-between items-start mb-4 relative z-10">
                                    <div 
                                        class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border"
                                        :class="log.risk_type === 'GLOBAL_GEM' ? 'bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-200' : log.risk_type === 'POTENTIAL_GEM' ? 'bg-amber-100 border-amber-200 text-amber-700' : log.risk_type === 'NORMAL' ? 'bg-emerald-50 border-emerald-100 text-emerald-600' : 'bg-rose-50 border-rose-100 text-rose-600'"
                                    >
                                        {{ log.risk_type === 'GLOBAL_GEM' ? '全球战略' : log.risk_type === 'POTENTIAL_GEM' ? '商业潜力' : log.risk_type === 'NORMAL' ? '健康状态' : '风险预警' }}
                                    </div>
                                    <div class="flex items-center gap-1.5" :class="log.risk_type === 'GLOBAL_GEM' ? 'text-indigo-600' : log.risk_level === 'High' ? 'text-rose-500' : log.risk_level === 'Low' ? 'text-emerald-500' : 'text-amber-500'">
                                        <div class="w-1.5 h-1.5 rounded-full bg-current animate-ping"></div>
                                        <span class="text-[11px] font-black tracking-widest">{{ log.risk_level === 'High' ? '高风险' : log.risk_level === 'Medium' ? '中风险' : log.risk_level === 'Low' ? '低风险' : log.risk_level }}</span>
                                    </div>
                                </div>

                                <h4 class="text-lg font-bold mb-3 leading-snug relative z-10" :class="log.risk_type === 'GLOBAL_GEM' ? 'text-indigo-950' : 'text-slate-800'">
                                    {{ log.risk_type === 'GLOBAL_GEM' ? '战略：S级出海潜力护航' : log.risk_type === 'POTENTIAL_GEM' ? '发掘：S级商业化潜力遗珠' : log.risk_type === 'NORMAL' ? '通报：作品运营指标健康' : '警示：检测到作品核心风险' }}
                                </h4>

                                <!-- Markdown Report display -->
                                <div v-if="log.markdown_report" class="text-[13px] leading-relaxed mb-6 relative z-10 pb-4 border-b border-black/5" 
                                     :class="log.risk_type === 'GLOBAL_GEM' ? 'text-indigo-900/80' : 'text-slate-600'"
                                     v-html="formatMarkdown(log.markdown_report)">
                                </div>
                                
                                <p v-else class="text-[13px] leading-relaxed mb-8 line-clamp-4 font-medium italic relative z-10"
                                   :class="log.risk_type === 'GLOBAL_GEM' ? 'text-indigo-800/70' : 'text-slate-500'">
                                    "{{ log.content_snippet }}"
                                </p>

                                <div class="flex items-center justify-between pt-6 border-t border-slate-50 relative z-10">
                                    <div class="flex items-center gap-3 text-[11px] font-bold text-slate-400">
                                        <div class="flex items-center gap-1"><Clock class="w-3 h-3" /> {{ log.created_at?.split('T')[0] }}</div>
                                        <div class="flex items-center gap-1"><Star class="w-3 h-3 text-amber-400" /> {{ log.score }}pts</div>
                                        <button v-if="log.markdown_report" @click.stop="exportAuditReport(log.markdown_report, book?.basic?.title || 'unknown', log.score)"
                                                class="flex items-center gap-1 text-slate-400 hover:text-indigo-600 transition-colors">
                                            <Download class="w-3 h-3" /> <span class="text-[10px] font-bold">导出</span>
                                        </button>
                                    </div>
                                    <div class="text-[11px] font-black tracking-tighter" :class="log.status === 'RESOLVED' ? 'text-emerald-500' : 'text-indigo-600'">
                                        {{ log.status === 'RESOLVED' ? 'COMPLETED' : 'PENDING REVIEW' }}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div v-else>
                            <!-- 审计中：脉冲动画 + 阶段提示 (仅前期打底阶段展示) -->
                            <div v-if="isAuditing && !latestAuditReport?.report" class="py-20 text-center bg-gradient-to-br from-indigo-50/60 to-purple-50/60 backdrop-blur-sm rounded-[40px] border border-indigo-100">
                                <div class="relative w-24 h-24 mx-auto mb-8">
                                    <div class="absolute inset-0 rounded-full border-4 border-indigo-200 animate-ping opacity-30"></div>
                                    <div class="absolute inset-2 rounded-full border-4 border-indigo-300 animate-ping opacity-20" style="animation-delay: 0.3s"></div>
                                    <div class="absolute inset-0 flex items-center justify-center">
                                        <Shield class="w-12 h-12 text-indigo-500 animate-pulse" />
                                    </div>
                                </div>
                                <h4 class="text-xl font-bold text-slate-800 mb-2">AI 深度审计进行中</h4>
                                <p class="text-indigo-600/80 text-sm font-medium mb-1">正在聚合六维数据源 → 调用 AI 大模型分析 → 生成审计报告</p>
                                <p class="text-slate-400 text-xs">实时连线推演中，请稍候...</p>
                            </div>

                            <!-- 生成中/审计完成：展示实时报告 -->
                            <div v-else-if="latestAuditReport && latestAuditReport.report" class="bg-white/90 backdrop-blur-xl rounded-[28px] p-8 border border-indigo-100 shadow-[0_8px_30px_rgba(0,0,0,0.04)]">
                                <div class="flex items-center justify-between mb-6 pb-4 border-b border-slate-100">
                                    <div class="flex items-center gap-3">
                                        <div class="p-2 bg-emerald-100 rounded-xl"><CheckCircle2 class="w-5 h-5 text-emerald-600" /></div>
                                        <div>
                                            <h4 class="text-lg font-bold text-slate-900">审计完成 · 《{{ latestAuditReport.title }}》</h4>
                                            <p class="text-xs text-slate-500">模型评分 <span class="font-bold text-indigo-600">{{ latestAuditReport.model_score?.toFixed(1) }}</span></p>
                                        </div>
                                    </div>
                                    <div class="flex gap-1.5">
                                        <span v-for="(v, k) in latestAuditReport.data_sources" :key="k"
                                              class="px-2 py-0.5 rounded text-[10px] font-bold"
                                              :class="v ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-400'">
                                            {{ String(k) === 'vr_comments' ? '虚拟读者' : String(k) === 'ai_eval' ? 'AI评分' : String(k) === 'global_stats' ? '出海' : String(k) === 'realtime_trend' ? '实时' : 'XGBoost' }}
                                            {{ v ? '✓' : '✗' }}
                                        </span>
                                    </div>
                                    <button @click="exportAuditReport(latestAuditReport.report, latestAuditReport.title, latestAuditReport.model_score)"
                                            class="flex items-center gap-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-colors ml-3">
                                        <Download class="w-3.5 h-3.5" /> 导出报告
                                    </button>
                                </div>
                                <div class="text-[13px] leading-relaxed text-slate-700" 
                                     v-html="formatMarkdown(latestAuditReport.report || '')">
                                </div>
                            </div>

                            <!-- 默认空状态 -->
                            <div v-else class="py-24 text-center bg-white/40 backdrop-blur-sm rounded-[40px] border border-dashed border-slate-200">
                                <Shield class="w-20 h-20 text-slate-200 mx-auto mb-6" stroke-width="1" />
                                <h4 class="text-xl font-bold text-slate-800 mb-2">暂无审计报告数据</h4>
                                <p class="text-slate-400 max-w-sm mx-auto mb-10">点击右上方按钮发起首次系统审计，AI 将根据该作品的当前数据进行全方位的潜力与风险评估。</p>
                                <button 
                                    @click="triggerBookAudit" 
                                    :disabled="isAuditing"
                                    class="px-10 py-4 bg-slate-900 text-white rounded-2xl font-black shadow-2xl shadow-slate-200 hover:-translate-y-1 transition-all active:translate-y-0"
                                >
                                    立即开始系统扫描
                                </button>
                            </div>
                        </div>
                        </div>
                    </div>
                    <!-- ==================== VALUATION TAB ==================== -->
                    <div v-if="activeTab === 'valuation'" class="pt-2">
                        <!-- 游客模式提示 -->
                        <div v-if="!isLoggedIn" class="p-20 text-center bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-sm">
                            <div class="w-20 h-20 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-6">
                                <DollarSign class="w-10 h-10 text-amber-600" />
                            </div>
                            <h3 class="text-2xl font-bold text-slate-800 mb-3">开启价值估算</h3>
                            <p class="text-slate-500 mb-8 max-w-md mx-auto">登录后即可查看基于 AI 算法的 IP 版权价值估算，包括最低价、建议价、最高价及全方位的商业分析报告。</p>
                            <button @click="router.push('/login')" class="px-10 py-3.5 bg-amber-600 text-white rounded-xl font-bold shadow-lg shadow-amber-200 hover:bg-amber-700 hover:-translate-y-0.5 transition-all">
                                立即登录
                            </button>
                        </div>

                        <!-- 加载中 -->
                        <div v-else-if="isFetchingValuation" class="p-16 text-center bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-sm">
                            <div class="w-12 h-12 border-4 border-amber-200 border-t-amber-600 rounded-full animate-spin mx-auto mb-4"></div>
                            <p class="text-slate-500 font-medium tracking-wide">AI 正在基于真实数据计算 IP 版权估值...</p>
                        </div>
                        
                        <div v-else-if="valuationData" class="space-y-6">
                            <!-- 顶部：三列估值卡片 -->
                            <div class="grid grid-cols-3 gap-4">
                                <!-- 最低估值 -->
                                <div class="bg-white rounded-[20px] p-6 shadow-[0_4px_20px_rgb(0,0,0,0.03)] border border-slate-100 text-center group hover:shadow-lg transition-all">
                                    <p class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">最低估值</p>
                                    <p class="text-3xl font-serif font-black text-slate-700 tracking-tight">¥{{ formatPrice(valuationData.estimated_min) }}<span class="text-lg text-slate-400 font-medium ml-0.5">万</span></p>
                                    <div class="mt-3 h-1 w-12 mx-auto rounded-full bg-slate-200"></div>
                                </div>
                                <!-- AI建议价 -->
                                <div class="bg-gradient-to-br from-amber-50 to-orange-50 rounded-[20px] p-6 shadow-[0_8px_30px_rgba(245,158,11,0.1)] border border-amber-200/50 text-center relative overflow-hidden group hover:shadow-xl transition-all">
                                    <div class="absolute -top-4 -right-4 w-20 h-20 bg-amber-200/20 rounded-full blur-xl"></div>
                                    <div class="relative z-10">
                                        <div class="flex items-center justify-center gap-1.5 mb-3">
                                            <DollarSign class="w-4 h-4 text-amber-600" />
                                            <p class="text-[11px] font-bold text-amber-700 uppercase tracking-widest">AI 建议价</p>
                                        </div>
                                        <p class="text-4xl font-serif font-black text-slate-900 tracking-tight">¥{{ formatPrice(valuationData.estimated_value) }}<span class="text-xl text-slate-500 font-medium ml-0.5">万</span></p>
                                        <p class="text-[12px] text-amber-700/80 font-bold mt-2">置信度 {{ valuationData.confidence }}%</p>
                                    </div>
                                </div>
                                <!-- 最高估值 -->
                                <div class="bg-white rounded-[20px] p-6 shadow-[0_4px_20px_rgb(0,0,0,0.03)] border border-slate-100 text-center group hover:shadow-lg transition-all">
                                    <p class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">最高估值</p>
                                    <p class="text-3xl font-serif font-black text-slate-700 tracking-tight">¥{{ formatPrice(valuationData.estimated_max) }}<span class="text-lg text-slate-400 font-medium ml-0.5">万</span></p>
                                    <div class="mt-3 h-1 w-12 mx-auto rounded-full bg-slate-200"></div>
                                </div>
                            </div>

                            <!-- 中部两栏：影响因子 + 可比案例 -->
                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                <!-- 左：价格影响因子 -->
                                <div class="bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
                                    <div class="flex items-center gap-3 mb-6">
                                        <div class="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center">
                                            <Target class="w-5 h-5 text-slate-700" stroke-width="1.5" />
                                        </div>
                                        <div>
                                            <h3 class="font-serif text-lg font-black text-slate-900 tracking-tight">价格影响因子</h3>
                                            <p class="text-[11px] text-slate-400 font-medium">Price Impact Factors</p>
                                        </div>
                                    </div>
                                    <div class="space-y-3">
                                        <div 
                                            v-for="factor in valuationData.factors" 
                                            :key="factor.name"
                                            class="flex items-center justify-between p-3.5 rounded-xl transition-colors hover:bg-slate-50 border border-transparent hover:border-slate-100 group"
                                        >
                                            <div class="flex items-center gap-3">
                                                <div class="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                                                     :class="factor.impact === 'positive' ? 'bg-emerald-50 text-emerald-600' : factor.impact === 'negative' ? 'bg-red-50 text-red-500' : 'bg-slate-50 text-slate-400'">
                                                    <TrendingUp v-if="factor.impact === 'positive'" class="w-4 h-4" />
                                                    <TrendingDown v-else-if="factor.impact === 'negative'" class="w-4 h-4" />
                                                    <Minus v-else class="w-4 h-4" />
                                                </div>
                                                <div>
                                                    <span class="text-[14px] font-bold text-slate-800 block">{{ factor.name }}</span>
                                                    <span class="text-[11px] text-slate-400">{{ factor.detail }}</span>
                                                </div>
                                            </div>
                                            <span class="text-sm font-black flex-shrink-0 ml-3"
                                                  :class="factor.impact === 'positive' ? 'text-emerald-600' : factor.impact === 'negative' ? 'text-red-500' : 'text-slate-400'">
                                                {{ factor.value }}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <!-- 右：可比交易案例 -->
                                <div class="bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
                                    <div class="flex items-center gap-3 mb-6">
                                        <div class="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center">
                                            <History class="w-5 h-5 text-slate-700" stroke-width="1.5" />
                                        </div>
                                        <div>
                                            <h3 class="font-serif text-lg font-black text-slate-900 tracking-tight">可比 IP 案例</h3>
                                            <p class="text-[11px] text-slate-400 font-medium">Comparable IP Cases</p>
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div 
                                            v-for="comp in valuationData.comparables" 
                                            :key="comp.name"
                                            class="flex items-center justify-between p-3.5 rounded-xl bg-slate-50/50 hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100"
                                        >
                                            <div class="flex-1 min-w-0">
                                                <div class="flex items-baseline gap-2">
                                                    <span class="text-[14px] font-bold text-slate-800 truncate">{{ comp.name }}</span>
                                                    <span class="text-[11px] text-slate-400 flex-shrink-0">{{ comp.category }}</span>
                                                </div>
                                                <div class="text-[11px] text-slate-400 mt-0.5">{{ comp.author }} · IP评分 {{ comp.score }}</div>
                                            </div>
                                            <div class="flex items-center gap-4 flex-shrink-0 ml-3">
                                                <div class="text-right">
                                                    <div class="text-[12px] text-slate-400">相似度</div>
                                                    <div class="text-sm font-black text-blue-600">{{ comp.similarity }}%</div>
                                                </div>
                                                <div class="text-right">
                                                    <div class="text-[12px] text-slate-400">估价</div>
                                                    <div class="text-sm font-serif font-black text-slate-800">¥{{ formatPrice(comp.estimated_price) }}万</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 底部：改编方向推荐 -->
                            <div class="bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
                                <div class="flex items-center gap-3 mb-8">
                                    <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-100 to-blue-100 flex items-center justify-center">
                                        <Clapperboard class="w-5 h-5 text-purple-700" stroke-width="1.5" />
                                    </div>
                                    <div>
                                        <h3 class="font-serif text-lg font-black text-slate-900 tracking-tight">改编方向推荐</h3>
                                        <p class="text-[11px] text-slate-400 font-medium">Adaptation Recommendations · 基于 AI 评估与市场数据</p>
                                    </div>
                                </div>
                                
                                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    <div 
                                        v-for="(rec, i) in valuationData.adaptation_recs" 
                                        :key="rec.type"
                                        class="rounded-2xl p-5 border transition-all hover:shadow-md hover:-translate-y-0.5 group relative overflow-hidden"
                                        :class="i === 0 ? 'bg-gradient-to-br from-amber-50/80 to-orange-50/80 border-amber-200/50' : 'bg-slate-50/50 border-slate-100 hover:bg-slate-50'"
                                    >
                                        <!-- 推荐排名徽章 -->
                                        <div v-if="i === 0" class="absolute top-3 right-3 bg-amber-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full">TOP</div>
                                        
                                        <div class="flex items-center gap-3 mb-4">
                                            <span class="text-2xl">{{ rec.icon }}</span>
                                            <div>
                                                <span class="text-[15px] font-black text-slate-800">{{ rec.type }}</span>
                                                <div class="flex items-center gap-2 mt-0.5">
                                                    <span class="text-[11px] font-bold" :class="rec.difficulty === '低' ? 'text-emerald-600' : rec.difficulty === '高' ? 'text-red-500' : 'text-amber-600'">{{ rec.difficulty }}难度</span>
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <!-- 匹配度进度条 -->
                                        <div class="mb-3">
                                            <div class="flex justify-between items-baseline mb-1.5">
                                                <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">匹配度</span>
                                                <span class="text-lg font-black" :class="rec.fit >= 80 ? 'text-emerald-600' : rec.fit >= 60 ? 'text-amber-600' : 'text-slate-500'">{{ rec.fit }}%</span>
                                            </div>
                                            <div class="w-full h-2 bg-slate-200/80 rounded-full overflow-hidden">
                                                <div 
                                                    class="h-full rounded-full transition-all duration-700"
                                                    :class="rec.fit >= 80 ? 'bg-gradient-to-r from-emerald-400 to-emerald-500' : rec.fit >= 60 ? 'bg-gradient-to-r from-amber-400 to-amber-500' : 'bg-slate-400'"
                                                    :style="{ width: rec.fit + '%' }"
                                                ></div>
                                            </div>
                                        </div>
                                        
                                        <p class="text-[13px] text-slate-500 leading-relaxed">{{ rec.note }}</p>
                                    </div>
                                </div>
                            </div>

                            <!-- 免责声明 -->
                            <div class="bg-slate-50 rounded-2xl p-4 border border-slate-100">
                                <p class="text-[12px] text-slate-400 text-center font-medium">
                                    📊 估值基于 XGBoost 模型评分、作品人气、月票、互动量等真实数据加权计算，结合 AI 六维评估和改编潜力分析。仅供参考，不构成商业建议。
                                </p>
                            </div>
                        </div>

                        <!-- 空态 -->
                        <div v-else class="p-16 text-center bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-sm">
                            <DollarSign class="w-16 h-16 mx-auto mb-4 text-amber-200" />
                            <h3 class="text-xl font-bold text-slate-800 mb-2">IP 版权价值估算</h3>
                            <p class="text-slate-500 mb-6">暂时无法获取估值数据，请稍后重试</p>
                            <button @click="fetchValuation()" class="px-6 py-3 bg-amber-600 text-white rounded-xl font-medium hover:bg-amber-700 transition-colors">重新估算</button>
                        </div>
                    </div>
                    
                    <!-- ==================== GLOBAL TAB ==================== -->
                    <div v-if="activeTab === 'global'" class="pt-2">
                        <!-- 游客模式提示 -->
                        <div v-if="!isLoggedIn" class="p-20 text-center bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-sm">
                            <div class="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-6">
                                <Globe class="w-10 h-10 text-blue-600" />
                            </div>
                            <h3 class="text-2xl font-bold text-slate-800 mb-3">开启全球化潜力分析</h3>
                            <p class="text-slate-500 mb-8 max-w-md mx-auto">登录后即可查看作品在不同文化语境下的受众契合度、海外市场流行潜力及多语种翻译建议。</p>
                            <button @click="router.push('/login')" class="px-10 py-3.5 bg-blue-600 text-white rounded-xl font-bold shadow-lg shadow-blue-200 hover:bg-blue-700 hover:-translate-y-0.5 transition-all">
                                立即登录
                            </button>
                        </div>
                        
                        <!-- 加载中 -->
                        <div v-else-if="isFetchingGlobal" class="p-16 text-center bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-sm">
                            <div class="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
                            <p class="text-slate-500 font-medium tracking-wide">AI 正在深度分析目标市场与文化输出价值...</p>
                        </div>
                        
                        <div v-else-if="globalData" class="space-y-6">
                            <!-- 顶部评分卡 -->
                            <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-[24px] p-8 shadow-[0_8px_30px_rgba(59,130,246,0.08)] border border-blue-100 flex items-center justify-between">
                                <div>
                                    <div class="flex items-center gap-2 mb-2">
                                        <Globe class="w-6 h-6 text-blue-600" />
                                        <h3 class="font-serif text-2xl font-black text-slate-800 tracking-tight">全球化潜力得分</h3>
                                    </div>
                                    <p class="text-sm text-slate-500 font-medium max-w-md">基于作品题材、情感共鸣与目标区域市场文化偏好计算的总和评分。</p>
                                </div>
                                <div class="flex flex-col items-end">
                                    <p class="text-6xl font-serif font-black" :class="globalData.overall_score >= 80 ? 'text-blue-600' : 'text-slate-800'">
                                        {{ globalData.overall_score }}<span class="text-2xl text-slate-400 font-medium ml-1">/100</span>
                                    </p>
                                </div>
                            </div>

                            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                                <!-- 目标区域市场偏好 -->
                                <div class="bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col min-h-[380px]">
                                    <div class="flex justify-between items-center mb-6">
                                        <h3 class="text-lg font-black text-slate-800 tracking-tight flex items-center gap-2">
                                            <Map class="w-5 h-5 text-indigo-500" /> 最具潜力海外市场
                                        </h3>
                                    </div>
                                    <div class="space-y-4 flex-1">
                                        <div v-for="(country, idx) in globalData.target_countries" :key="idx" class="p-4 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                                            <div class="flex justify-between items-center mb-2">
                                                <span class="font-bold text-[15px] text-slate-800">{{ country.country }}</span>
                                                <span class="font-black" :class="country.fit_score >= 80 ? 'text-emerald-500' : 'text-blue-500'">{{ country.fit_score }}% 契合</span>
                                            </div>
                                            <!-- 进度条 -->
                                            <div class="w-full h-1.5 bg-slate-200/80 rounded-full mb-3 overflow-hidden">
                                                <div class="h-full rounded-full" :class="country.fit_score >= 80 ? 'bg-emerald-400' : 'bg-blue-400'" :style="{ width: country.fit_score + '%' }"></div>
                                            </div>
                                            <p class="text-[13px] text-slate-500 leading-relaxed">{{ country.reason }}</p>
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="space-y-6">
                                    <!-- 传统文化特征提取 -->
                                    <div class="bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
                                        <h3 class="text-lg font-black text-slate-800 tracking-tight flex items-center gap-2 mb-6">
                                            <Sparkles class="w-5 h-5 text-amber-500" /> 出海文化亮点
                                        </h3>
                                        <div class="space-y-4">
                                            <div v-for="(elem, idx) in globalData.cultural_elements" :key="idx" class="flex gap-4 items-start">
                                                <div class="w-10 h-10 rounded-full bg-amber-50 text-amber-600 flex items-center justify-center font-bold font-serif text-lg flex-shrink-0">
                                                    {{ Number(idx) + 1 }}
                                                </div>
                                                <div>
                                                    <div class="flex items-center gap-2 mb-1">
                                                        <span class="font-bold text-slate-800">{{ elem.element }}</span>
                                                        <span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold tracking-wider">吸引力 {{ elem.impact_score }}</span>
                                                    </div>
                                                    <p class="text-[13px] text-slate-500 leading-relaxed">{{ elem.attraction }}</p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <!-- 风险与本地化建议 -->
                                    <div class="bg-white rounded-[24px] p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
                                        <h3 class="text-lg font-black text-slate-800 tracking-tight flex items-center gap-2 mb-5">
                                            <ShieldAlert class="w-5 h-5 text-red-500" /> 跨文化风险雷达
                                        </h3>
                                        <ul class="space-y-3 mb-6">
                                            <li v-for="(risk, idx) in globalData.risks" :key="idx" class="flex items-start gap-2.5 text-[13px] text-slate-600">
                                                <span class="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 flex-shrink-0"></span>
                                                <span class="leading-relaxed">{{ risk }}</span>
                                            </li>
                                        </ul>
                                        <!-- 本地化建议 -->
                                        <div class="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                            <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">本地化翻译与改编建议</div>
                                            <p class="text-[13px] text-slate-700 font-medium leading-relaxed">{{ globalData.localization_advice }}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 失败或空态 -->
                        <div v-else class="p-16 text-center bg-white/90 backdrop-blur-xl rounded-[24px] border border-white shadow-sm">
                            <Globe class="w-16 h-16 mx-auto mb-4 text-slate-200" />
                            <h3 class="text-xl font-bold text-slate-800 mb-2">AI 出海分析不可用</h3>
                            <p class="text-slate-500 mb-6">受限于服务状态或数据不完整，暂时无法生成报告。</p>
                            <button @click="fetchGlobalAnalysis()" class="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition-colors">重新分析</button>
                        </div>
                    </div>

                    <!-- ==================== AUDIT TAB (Chapter Reader) ==================== -->
                    <div v-if="activeTab === 'audit'" class="bg-[#faf9f6]/95 backdrop-blur-3xl rounded-[24px] overflow-hidden border border-slate-200/60 shadow-[0_8px_30px_rgb(0,0,0,0.04)] pb-10">
                        <!-- 游客模式提示 -->
                        <div v-if="!isLoggedIn" class="py-24 text-center">
                            <h3 class="font-bold text-slate-800 mb-2 text-xl">沉浸式阅读体验</h3>
                            <p class="text-[15px] font-medium text-slate-500 mb-8">该功能提供沉浸式的章节阅读与大模型解析体验。请登录以继续阅读。</p>
                            <button @click="router.push('/login')" class="px-10 py-3.5 bg-emerald-600 text-white rounded-xl font-bold hover:bg-emerald-700 shadow-xl shadow-emerald-200 transition-all hover:-translate-y-0.5">立即登录</button>
                        </div>
                        <template v-else>
                            <div v-if="isFetchingChapter" class="flex flex-col items-center justify-center h-[500px]">
                                <div class="animate-spin w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full mb-6 relative">
                                    <div class="absolute inset-0 rounded-full border-4 border-emerald-200/50"></div>
                                </div>
                                <p class="text-slate-500 font-bold tracking-widest text-sm uppercase">AI 正在调取或生成章节网络数据...</p>
                            </div>
                            <div v-else class="max-w-3xl mx-auto px-8 md:px-12 pt-16 pb-8">
                                <h2 class="text-3xl md:text-4xl font-serif font-black text-slate-800 tracking-tight text-center mb-16 leading-snug">{{ chapterTitle }}</h2>
                                <div class="space-y-6 text-[18px] md:text-[19px] leading-loose text-slate-800 font-[400]" style="font-family: 'Bookerly', 'Georgia', 'FangZhengShuSong', 'STSong', serif; color: #333;">
                                    <p v-for="(paragraph, idx) in chapterContent" :key="idx" class="indent-8 text-justify">
                                        {{ paragraph }}
                                    </p>
                                    <div v-if="!chapterContent || chapterContent.length === 0" class="text-center text-slate-400 font-sans text-sm">暂无内容</div>
                                </div>
                                
                                <div class="mt-24 pt-8 border-t border-slate-200/60 flex items-center justify-between font-sans">
                                    <button 
                                        @click="fetchChapter(Math.max(1, currentChapterNum - 1))"
                                        :disabled="currentChapterNum <= 1 || isFetchingChapter"
                                        class="px-7 py-3 bg-white text-slate-700 border border-slate-200 rounded-xl font-bold hover:bg-slate-50 hover:border-slate-300 hover:shadow-sm disabled:opacity-50 disabled:hover:shadow-none disabled:hover:bg-white transition-all"
                                    >
                                        上一页
                                    </button>
                                    <span class="text-sm font-bold text-slate-400 tracking-widest">目前为您展示：第 <span class="text-slate-700 mx-1">{{ currentChapterNum }}</span> 页</span>
                                    <button 
                                        @click="fetchChapter(currentChapterNum + 1)"
                                        :disabled="isFetchingChapter"
                                        class="px-7 py-3 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800 hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:shadow-none disabled:hover:translate-y-0 transition-all"
                                    >
                                        下一页
                                    </button>
                                </div>
                            </div>
                        </template>
                    </div>
            </div>
        </div>
    </div>
</EditorialLayout>
</template>

<style scoped>
/* Any additional local overrides */
</style>
