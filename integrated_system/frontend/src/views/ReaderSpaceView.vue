<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import GraphPanel from '@/components/graph/GraphPanel.vue'
import AISettingsModal from '@/components/common/AISettingsModal.vue'
import SentimentPanel from '@/components/reader/SentimentPanel.vue'
import TypewriterText from '@/components/reader/TypewriterText.vue'
import EffectsLayer from '@/components/reader/EffectsLayer.vue'
import { mockReaderProfiles, mockGraphDataMap, mockBooks } from '@/api/mock_simulation'
import { Users, Play, Pause, RefreshCw, MessageCircle, Settings, Search, Send, BookOpen, CornerDownRight } from 'lucide-vue-next'
import axios from 'axios'

interface Persona {
  id: string
  name: string
  avatar?: string
  region?: string
  preference_tags?: string[]
  toxicity_level?: number
}

interface FeedPost {
  id: string
  agentId: string | number
  agentName?: string
  agentAvatar?: string
  content: string
  time: string
  sentiment?: number  // -1 到 1 的情感值
  replyTo?: string    // 回复的评论 ID
  replyToName?: string // 回复的用户名
}

type DedupMode = 'strict' | 'balanced' | 'lenient'

const route = useRoute()
const currentBookId = ref(1)
const displayTitle = ref(route.query.bookTitle?.toString() || mockBooks.find((b: any) => b.id === 1)?.title || '未知书籍')

const isSimulating = ref(false)
const isRoundRunning = ref(false)
const feed = ref<FeedPost[]>([])
const searchQuery = ref('')
const globalEventInput = ref('')
const feedContainer = ref<HTMLElement | null>(null)
const showCreateModal = ref(false)
const showSettingsModal = ref(false)
const createPersonaError = ref('')
const activeEffect = ref<'rain' | 'fire' | 'storm' | null>(null)
const currentEventMessage = ref('')
const processedEventCount = ref(0) // Track number of processed events to avoid replay

const currentTaskId = ref('')
const taskStatus = ref('idle')
const taskError = ref('')
const nextEventHint = ref('')
let taskPollTimer: ReturnType<typeof setInterval> | null = null
const taskCommentOffsets: Record<string, number> = {}
const feedDedupKeys = new Set<string>()
const feedGlobalDedupKeys = new Set<string>()
const dedupMode = ref<DedupMode>('balanced')

const dedupModeOptions: Array<{ value: DedupMode; label: string }> = [
  { value: 'strict', label: '严格' },
  { value: 'balanced', label: '平衡' },
  { value: 'lenient', label: '宽松' },
]

const setDedupMode = (mode: DedupMode) => {
  if (dedupMode.value === mode) return
  dedupMode.value = mode
}

// ========== 书籍搜索与图谱生成 ==========
interface SearchResult {
  id: number
  title: string
  author: string
  abstract: string
  platform: string
  cover: string
}

const bookSearchQuery = ref('')
const bookSearchResults = ref<SearchResult[]>([])
const isSearching = ref(false)
const showSearchResults = ref(false)
const selectedBook = ref<SearchResult | null>(null)
const isGeneratingGraph = ref(false)
const aiGeneratedGraph = ref<{ nodes: any[], edges: any[] } | null>(null)
const manualInputMode = ref(false)
const manualBookForm = ref({
  title: '',
  author: '',
  abstract: ''
})

// 搜索书籍
const searchBooks = async () => {
  if (!bookSearchQuery.value.trim()) {
    bookSearchResults.value = []
    showSearchResults.value = false
    return
  }
  isSearching.value = true
  try {
    const res = await axios.get('http://localhost:5000/api/virtual_reader/search_novel', {
      params: { q: bookSearchQuery.value.trim(), limit: 8 }
    })
    bookSearchResults.value = res.data?.items || []
    showSearchResults.value = bookSearchResults.value.length > 0
  } catch (e) {
    console.error('搜索失败:', e)
    bookSearchResults.value = []
  } finally {
    isSearching.value = false
  }
}

// 选择书籍
const selectBook = (book: SearchResult) => {
  selectedBook.value = book
  displayTitle.value = book.title
  bookSearchQuery.value = book.title
  showSearchResults.value = false
  manualInputMode.value = false
  // 选择后自动生成图谱
  generateGraph()
}

// 手动输入书籍
const submitManualBook = () => {
  if (!manualBookForm.value.title.trim()) return
  selectedBook.value = {
    id: 0,
    title: manualBookForm.value.title,
    author: manualBookForm.value.author,
    abstract: manualBookForm.value.abstract,
    platform: 'manual',
    cover: ''
  }
  displayTitle.value = manualBookForm.value.title
  bookSearchQuery.value = manualBookForm.value.title
  manualInputMode.value = false
  generateGraph()
}

// AI 生成图谱
const generateGraph = async () => {
  if (!selectedBook.value && !manualBookForm.value.title) return
  isGeneratingGraph.value = true
  try {
    const title = selectedBook.value?.title || manualBookForm.value.title
    const abstract = selectedBook.value?.abstract || manualBookForm.value.abstract
    const res = await axios.post('http://localhost:5000/api/virtual_reader/generate_graph', {
      title,
      abstract
    })
    if (res.data?.success && res.data?.graph) {
      aiGeneratedGraph.value = res.data.graph
    }
  } catch (e) {
    console.error('图谱生成失败:', e)
  } finally {
    isGeneratingGraph.value = false
  }
}

// 使用 AI 生成的图谱或 mock 数据
const currentGraphData = computed(() => {
  if (aiGeneratedGraph.value && aiGeneratedGraph.value.nodes?.length > 0) {
    return aiGeneratedGraph.value
  }
  return mockGraphDataMap[currentBookId.value] || mockGraphDataMap[1]
})
const taskStatusLabel = computed(() => {
  if (!isSimulating.value) return '已暂停'
  switch (taskStatus.value) {
    case 'pending':
      return '排队中'
    case 'running':
      return '运行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return '准备中'
  }
})

const taskStatusClass = computed(() => {
  if (taskStatus.value === 'failed') return 'bg-red-50 text-red-700 border-red-200'
  if (isSimulating.value) return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  return 'bg-slate-100 text-slate-600 border-slate-200'
})

const realPersonas = ref<Persona[]>([])
const allProfiles = computed(() => {
  const mappedReal = realPersonas.value.map((p) => ({
    id: p.id,
    name: p.name,
    username: 'user_' + String(p.id).substring(0, 6),
    avatar: p.avatar || '👤',
    tags: p.preference_tags || [],
    sentiment: (p.toxicity_level || 0) > 7 ? -5 : 5,
    activity_level: 0.8,
    region: p.region || '',
  }))
  return [...mappedReal, ...mockReaderProfiles]
})

const newPersonaForm = ref({
  name: '',
  gender: 'male',
  region: '',
  reading_age: 3,
  preference_tags: '',
  toxicity_level: 3,
  bio: '',
})

const getFeedAvatar = (post: FeedPost) => {
  if (post.agentAvatar) return post.agentAvatar
  const mock = mockReaderProfiles.find((p: any) => String(p.id) === String(post.agentId))
  return mock?.avatar || '👤'
}

const getFeedName = (post: FeedPost) => {
  if (post.agentName) return post.agentName
  const mock = mockReaderProfiles.find((p: any) => String(p.id) === String(post.agentId))
  return mock?.name || `Reader ${post.agentId}`
}

const fetchPersonas = async () => {
  try {
    const res = await axios.get('http://localhost:5000/api/personas')
    realPersonas.value = res.data || []
  } catch (e) {
    console.error('Failed to load personas', e)
  }
}

const createPersona = async () => {
  const name = newPersonaForm.value.name.trim()
  if (!name) {
    createPersonaError.value = '请填写读者昵称。'
    return
  }

  if (newPersonaForm.value.reading_age < 1 || newPersonaForm.value.reading_age > 40) {
    createPersonaError.value = '书龄请填写 1-40 之间的整数。'
    return
  }

  if (newPersonaForm.value.toxicity_level < 1 || newPersonaForm.value.toxicity_level > 10) {
    createPersonaError.value = '毒舌指数应在 1-10 之间。'
    return
  }

  const tags = newPersonaForm.value.preference_tags.split(/[，,\s]+/).filter(Boolean)
  if (!tags.length) {
    createPersonaError.value = '请至少填写一个偏好标签。'
    return
  }

  createPersonaError.value = ''
  const payload = {
    ...newPersonaForm.value,
    name,
    preference_tags: tags,
    avatar: '👤',
    color: 'bg-indigo-600 text-white',
    title: `书龄${newPersonaForm.value.reading_age}年`,
    persona: `你是一个书龄${newPersonaForm.value.reading_age}年的${newPersonaForm.value.gender === 'male' ? '男' : '女'}读者。你来自${newPersonaForm.value.region || '未知地区'}。你的性格${newPersonaForm.value.bio}。偏好：${tags.join(',')}。`,
    scenario: '虚拟空间',
  }

  try {
    await axios.post('http://localhost:5000/api/personas', payload)
    await fetchPersonas()
    showCreateModal.value = false
    createPersonaError.value = ''
    newPersonaForm.value = { name: '', gender: 'male', region: '', reading_age: 3, preference_tags: '', toxicity_level: 3, bio: '' }
  } catch (e: any) {
    createPersonaError.value =
      e?.response?.data?.error ||
      e?.response?.data?.message ||
      e?.message ||
      String(e)
  }
}

const filteredProfiles = computed(() => {
  if (!searchQuery.value) return allProfiles.value
  const query = searchQuery.value.toLowerCase()
  return allProfiles.value.filter((p) =>
    p.name.toLowerCase().includes(query) ||
    p.username.toLowerCase().includes(query) ||
    p.tags.some((t: string) => t.toLowerCase().includes(query))
  )
})

const getActivePersonaIds = () => {
  return realPersonas.value.slice(0, 8).map((p) => p.id)
}

const buildFeedDedupKey = (agentId: string | number, content: string) => {
  const normalized = String(content || '').replace(/\s+/g, ' ').trim()
  return `${String(agentId)}|${normalized}`
}

const buildGlobalFeedDedupKey = (content: string) => {
  return normalizeForSimilarity(String(content || ''))
}

const buildAgentKey = (readerId: unknown, readerName: unknown, fallback: string) => {
  const idText = String(readerId || '').trim()
  if (idText) return idText
  const nameText = String(readerName || '').trim().toLowerCase()
  if (nameText) return `name:${nameText}`
  return fallback
}

const feedDedupThresholdMap: Record<DedupMode, number> = {
  strict: 0.74,
  balanced: 0.82,
  lenient: 0.9,
}

const feedGlobalDedupThresholdMap: Record<DedupMode, number> = {
  strict: 0.68,
  balanced: 0.75,
  lenient: 0.84,
}

const normalizeForSimilarity = (text: string) => String(text || '').replace(/\s+/g, '').toLowerCase()

const buildTextUnits = (text: string) => {
  const value = normalizeForSimilarity(text)
  const units = new Set<string>()
  const latin = value.match(/[a-z0-9]{2,}/g) || []
  for (const token of latin) units.add(token)
  const zhTokens = value.match(/[\u4e00-\u9fff]+/g) || []
  for (const token of zhTokens) {
    if (token.length <= 1) continue
    if (token.length === 2) {
      units.add(token)
      continue
    }
    for (let i = 0; i < token.length - 1; i++) {
      units.add(token.slice(i, i + 2))
    }
  }
  return units
}

const semanticSimilarity = (a: string, b: string) => {
  const setA = buildTextUnits(a)
  const setB = buildTextUnits(b)
  if (!setA.size || !setB.size) return 0
  let inter = 0
  for (const item of setA) {
    if (setB.has(item)) inter += 1
  }
  const union = setA.size + setB.size - inter
  return union > 0 ? inter / union : 0
}

const isNearDuplicateFeedPost = (candidate: FeedPost) => {
  const threshold = feedDedupThresholdMap[dedupMode.value]
  const agentId = String(candidate.agentId)
  const content = String(candidate.content || '')
  for (const existing of feed.value) {
    if (String(existing.agentId) !== agentId) continue
    const score = semanticSimilarity(content, String(existing.content || ''))
    if (score >= threshold) return true
  }
  return false
}

const isGlobalNearDuplicateFeedPost = (candidate: FeedPost) => {
  const threshold = feedGlobalDedupThresholdMap[dedupMode.value]
  const content = String(candidate.content || '')
  for (const existing of feed.value) {
    const score = semanticSimilarity(content, String(existing.content || ''))
    if (score >= threshold) return true
  }
  return false
}

const clearFeed = () => {
  feed.value = []
  feedDedupKeys.clear()
  feedGlobalDedupKeys.clear()
}

const buildSimulationContent = () => {
  const hint = nextEventHint.value.trim()
  nextEventHint.value = ''
  
  // 随机剧情库，避免每次都是单调的“模拟中”
  const plots = [
      `最新章节：主角在绝境中强行突破境界，引动天劫降临，却反而利用天雷淬炼肉身，震惊全场。`,
      `最新章节：反派竟然是主角失散多年的亲兄弟，这一波反转太突然了，而且前面的伏笔终于回收了。`,
      `最新章节：主角和女主角终于发糖了！虽然只有短短几句对话，但那个眼神拉丝的感觉写得太好了。`,
      `最新章节：配角为了掩护主角撤退，独自一人挡在千军万马前，那句“虽千万人吾往矣”太燃了，也太刀了。`,
      `最新章节：宗门大比开始，主角作为一个不起眼的外门弟子，竟然一招击败了夺冠热门，全场鸦雀无声。`,
      `最新章节：主角发现了世界的真相，原来他们一直生活在一个巨大的阵法之中，所有人的命运都是被安排好的。`,
      `最新章节：日常过渡回，主角在山下小镇上闲逛，遇到几个奇怪的路人，感觉暴风雨前的宁静。`
  ]
  const randomPlot = plots[Math.floor(Math.random() * plots.length)]

  const base = `请假设你正在阅读作品《${displayTitle.value}》的最新更新。\n剧情梗概：${randomPlot}\n请基于你的人设，对这段剧情发表简短、口语化的读后感。`
  return hint ? `${base}\n附加事件：${hint}` : base
}

const fetchTaskComments = async (taskId: string) => {
  const offset = taskCommentOffsets[taskId] || 0
  const res = await axios.get('http://localhost:5000/api/virtual_reader/comments', {
    params: { task_id: taskId, limit: 100, offset },
    timeout: 30000,
  })
  const allItems = res.data?.items || []
  const fetchedCount = allItems.length
  if (!fetchedCount) return
  const items = allItems.filter((item: any) => {
    const text = String(item?.comment || '').trim()
    if (!text) return false
    const readerName = String(item?.reader_name || '').trim().toLowerCase()
    // Defensive filter for stale system records from old UI versions.
    if (/任务\s*已提交|已暂停\s*模拟|^\s*system\s*$/i.test(text)) return false
    if (readerName === 'system') return false
    return true
  })
  const mapped: FeedPost[] = items.map((item: any, idx: number) => ({
    id: `${taskId}-${offset + idx}`,
    agentId: buildAgentKey(item.reader_id, item.reader_name, `reader-${offset + idx}`),
    agentName: item.reader_name,
    content: item.comment || '',
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    sentiment: item.sentiment ?? 0,  // 从后端传递情感值
    replyToName: item.reply_to_name,
  }))

  for (let i = mapped.length - 1; i >= 0; i--) {
    const item = mapped[i]
    if (!item) continue
    const dedupKey = buildFeedDedupKey(item.agentId, item.content)
    const globalDedupKey = buildGlobalFeedDedupKey(item.content)
    if (feedDedupKeys.has(dedupKey)) continue
    if (feedGlobalDedupKeys.has(globalDedupKey)) continue
    if (isNearDuplicateFeedPost(item)) continue
    if (isGlobalNearDuplicateFeedPost(item)) continue
    feedDedupKeys.add(dedupKey)
    feedGlobalDedupKeys.add(globalDedupKey)
    feed.value.unshift(item)
  }
  // Offset must advance by raw fetched rows to avoid re-reading filtered records.
  taskCommentOffsets[taskId] = offset + fetchedCount
}

const clearTaskPoll = () => {
  if (taskPollTimer) {
    clearInterval(taskPollTimer)
    taskPollTimer = null
  }
}

const closeCreateModal = () => {
  showCreateModal.value = false
  createPersonaError.value = ''
}

const openCreateModal = () => {
  createPersonaError.value = ''
  showCreateModal.value = true
}

const triggerEffect = (type: string, message: string) => {
  if (['rain', 'fire', 'storm'].includes(type)) {
    activeEffect.value = type as 'rain' | 'fire' | 'storm'
    currentEventMessage.value = message
    setTimeout(() => {
      activeEffect.value = null
      currentEventMessage.value = ''
    }, 8000)
  }
}

const startRound = async () => {
  console.log('[VR Simulation] startRound called, isSimulating:', isSimulating.value, 'isRoundRunning:', isRoundRunning.value)
  if (!isSimulating.value || isRoundRunning.value) return

  const personaIds = getActivePersonaIds()
  console.log('[VR Simulation] personaIds:', personaIds)
  if (!personaIds.length) {
    taskError.value = '没有可用真实读者，请先创建角色。'
    isSimulating.value = false
    console.warn('[VR Simulation] No personas available')
    return
  }

  isRoundRunning.value = true
  taskError.value = ''

  try {
    const sourceTitle = displayTitle.value || '未知书籍'
    const sourceAuthor = 'reader_space'
    const sourcePlatform = 'reader_space'
    const sourceBookKey = `${sourcePlatform}|${sourceTitle}|${sourceAuthor}`

    const submitRes = await axios.post(
      'http://localhost:5000/api/virtual_reader/simulate_async',
      {
        persona_ids: personaIds,
        title: sourceTitle,
        chapter: '实时模拟片段',
        content: buildSimulationContent(),
        source_title: sourceTitle,
        source_author: sourceAuthor,
        source_platform: sourcePlatform,
        source_book_key: sourceBookKey,
        dedup_mode: dedupMode.value,
        use_story_context: true,
        force_refresh_story_context: false,
        use_web_search: false,
      },
      { timeout: 30000 }
    )

    const taskId = submitRes.data?.task_id
    if (!taskId) throw new Error('No task_id returned')

    currentTaskId.value = taskId
    taskStatus.value = 'pending'
    taskCommentOffsets[taskId] = 0

    clearTaskPoll()
    taskPollTimer = setInterval(async () => {
      try {
        const taskRes = await axios.get(`http://localhost:5000/api/virtual_reader/task/${taskId}`, { timeout: 30000 })
        const task = taskRes.data || {}
        taskStatus.value = task.status || 'unknown'
        
        // Check for new events
        const events = task.events || []
        if (events.length > processedEventCount.value) {
            const newEvents = events.slice(processedEventCount.value)
            const now = Date.now() / 1000
            for (const ev of newEvents) {
                // Only trigger if event is recent (within 60 seconds) to avoid spam on refresh
                if (ev.timestamp && now - ev.timestamp < 60) {
                    triggerEffect(ev.type, ev.message)
                }
            }
            processedEventCount.value = events.length
        }

        await fetchTaskComments(taskId)

        if (task.status === 'completed') {
          clearTaskPoll()
          isRoundRunning.value = false
          if (isSimulating.value) {
            setTimeout(() => {
              startRound()
            }, 1200)
          }
        } else if (task.status === 'failed') {
          clearTaskPoll()
          isRoundRunning.value = false
          taskError.value = task.error || '任务失败'
        }
      } catch (e: any) {
        clearTaskPoll()
        isRoundRunning.value = false
        taskError.value =
          e?.response?.data?.error ||
          e?.response?.data?.message ||
          e?.message ||
          String(e)
      }
    }, 2000)
  } catch (e: any) {
    isRoundRunning.value = false
    taskError.value =
      e?.response?.data?.error ||
      e?.response?.data?.message ||
      e?.message ||
      String(e)
  }
}

const toggleSimulation = () => {
  console.log('[VR Simulation] toggleSimulation called, current isSimulating:', isSimulating.value)
  if (isSimulating.value) {
    isSimulating.value = false
    clearTaskPoll()
    isRoundRunning.value = false
    return
  }
  console.log('[VR Simulation] Starting simulation, realPersonas count:', realPersonas.value.length)
  isSimulating.value = true
  startRound()
}

const injectGlobalEvent = () => {
  if (!globalEventInput.value.trim()) return
  const eventText = globalEventInput.value.trim()
  nextEventHint.value = eventText

  if (isSimulating.value && !isRoundRunning.value) {
    startRound()
  }
  globalEventInput.value = ''
}

// 根据情感值返回气泡样式类
const getSentimentBubbleClass = (sentiment?: number) => {
  const s = sentiment ?? 0
  if (s >= 0.5) return 'bg-emerald-50 border-emerald-200 text-emerald-800'
  if (s >= 0.2) return 'bg-green-50 border-green-200 text-green-800'
  if (s >= -0.2) return 'bg-white border-slate-100 text-slate-700'
  if (s >= -0.5) return 'bg-amber-50 border-amber-200 text-amber-800'
  return 'bg-red-50 border-red-200 text-red-800'
}

// 根据情感值返回边框样式类
const getSentimentBorderClass = (sentiment?: number) => {
  const s = sentiment ?? 0
  if (s >= 0.5) return 'border-emerald-200'
  if (s >= 0.2) return 'border-green-200'
  if (s >= -0.2) return 'border-slate-100'
  if (s >= -0.5) return 'border-amber-200'
  return 'border-red-200'
}

// ========== 动态统计 ==========
// 实时统计数据
const liveStats = computed(() => {
  const posts = feed.value
  const count = posts.length
  
  // 活跃Agent数量（去重的发言者）
  const activeAgents = filteredProfiles.value.length
  
  // 好评/差评统计
  const positive = posts.filter(p => (p.sentiment ?? 0) > 0.2).length
  const negative = posts.filter(p => (p.sentiment ?? 0) < -0.2).length
  
  // 参与度评级
  let engagement = '观望'
  if (count >= 20) engagement = '极高'
  else if (count >= 10) engagement = '活跃'
  else if (count >= 5) engagement = '一般'
  
  // 阅读速度（模拟）
  const readingSpeed = (2.0 + Math.random() * 1.5).toFixed(1)
  
  return {
    activeAgents: activeAgents || mockReaderProfiles.length,
    engagement,
    readingSpeed,
    positive,
    negative,
    total: count
  }
})

// 热门话题词
const hotKeywords = computed(() => {
  const posts = feed.value.slice(0, 20)
  const wordCount: Record<string, number> = {}
  
  const stopWords = new Set(['的', '是', '在', '了', '和', '有', '这', '就', '不', '也', '都', '一', '个', '这个', '那个', '什么', '怎么', '为什么'])
  
  posts.forEach(p => {
    // 简单分词（中文按字符，检测2-4字词组）
    const text = p.content
    for (let len = 2; len <= 4; len++) {
      for (let i = 0; i <= text.length - len; i++) {
        const word = text.substring(i, i + len)
        if (!stopWords.has(word) && /^[\u4e00-\u9fa5]+$/.test(word)) {
          wordCount[word] = (wordCount[word] || 0) + 1
        }
      }
    }
  })
  
  return Object.entries(wordCount)
    .filter(([_, count]) => count >= 2)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([word]) => word)
})

watch(
  () => feed.value.length,
  async () => {
    await nextTick()
    if (feedContainer.value) {
      feedContainer.value.scrollTop = 0
    }
  }
)

watch(dedupMode, () => {
  // Rebuild in-memory exact-key cache under a new mode; keep existing feed visible.
  feedDedupKeys.clear()
  feedGlobalDedupKeys.clear()
  for (const post of feed.value) {
    const key = buildFeedDedupKey(post.agentId, post.content)
    const globalKey = buildGlobalFeedDedupKey(post.content)
    feedDedupKeys.add(key)
    feedGlobalDedupKeys.add(globalKey)
  }
})

onMounted(() => {
  fetchPersonas()
})

onUnmounted(() => {
  clearTaskPoll()
})
</script>

<template>
  <EditorialLayout>
    <EffectsLayer :effect="activeEffect" />
    
    <!-- Event Toast -->
    <Transition name="fade">
      <div v-if="currentEventMessage" class="fixed top-24 left-1/2 -translate-x-1/2 z-[60] px-6 py-3 bg-slate-900/90 text-white rounded-full shadow-xl backdrop-blur-md border border-white/10 flex items-center gap-3">
        <span class="text-xl">
           {{ activeEffect === 'fire' ? '🔥' : activeEffect === 'rain' ? '🌧️' : activeEffect === 'storm' ? '⚡' : '📢' }}
        </span>
        <span class="font-bold tracking-wide">{{ currentEventMessage }}</span>
      </div>
    </Transition>

    <div class="h-screen flex flex-col pt-6 px-6 pb-24 max-w-[1920px] mx-auto gap-6 transition-all">
      
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div class="flex-1">
          <h1 class="text-3xl font-serif font-bold text-slate-900 tracking-tight flex items-center gap-3">
             <span>虚拟读者实验室</span>
             <span class="text-slate-300">/</span>
             <span class="text-indigo-600">{{ displayTitle }}</span>
          </h1>
          <p class="text-slate-500 mt-1">全息模拟读者反应，深度解析受众参与模式</p>
          
          <!-- Debug Tools -->
          <div class="flex gap-2 mt-2">
             <button @click="triggerEffect('rain', 'Debug: 强制触发雨天')" class="text-[10px] px-2 py-0.5 bg-slate-100 rounded text-slate-500 hover:bg-slate-200">Test Rain</button>
             <button @click="triggerEffect('fire', 'Debug: 强制触发火灾')" class="text-[10px] px-2 py-0.5 bg-slate-100 rounded text-slate-500 hover:bg-slate-200">Test Fire</button>
             <button @click="triggerEffect('storm', 'Debug: 强制触发风暴')" class="text-[10px] px-2 py-0.5 bg-slate-100 rounded text-slate-500 hover:bg-slate-200">Test Storm</button>
          </div>
          
          <!-- 书籍搜索 -->
          <div class="mt-3 flex items-center gap-2">
            <div class="relative flex-1 max-w-md">
              <input
                v-model="bookSearchQuery"
                @input="searchBooks"
                @focus="showSearchResults = bookSearchResults.length > 0"
                @blur="showSearchResults = false"
                type="text"
                placeholder="搜索书名或作者..."
                class="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm placeholder:text-slate-400 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
              />
              <Search class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <span v-if="isSearching" class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">搜索中...</span>
              
              <!-- 搜索结果下拉 -->
              <div
                v-if="showSearchResults && bookSearchResults.length > 0"
                class="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-lg z-50 max-h-64 overflow-y-auto"
              >
                <div
                  v-for="book in bookSearchResults"
                  :key="book.id"
                  @mousedown.prevent="selectBook(book)"
                  class="px-4 py-3 hover:bg-slate-50 cursor-pointer border-b border-slate-100 last:border-0"
                >
                  <div class="font-medium text-slate-800">{{ book.title }}</div>
                  <div class="text-xs text-slate-500">{{ book.author }} · {{ book.platform }}</div>
                </div>
              </div>
            </div>
            
            <button
              @click="manualInputMode = !manualInputMode"
              class="px-3 py-2 text-sm text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
            >
              {{ manualInputMode ? '取消' : '手动输入' }}
            </button>
            
            <button
              v-if="selectedBook && !isGeneratingGraph"
              @click="generateGraph"
              class="px-3 py-2 text-sm bg-indigo-100 text-indigo-700 rounded-lg hover:bg-indigo-200 transition-colors"
            >
              重新生成图谱
            </button>
            <span v-if="isGeneratingGraph" class="text-sm text-indigo-600">生成图谱中...</span>
          </div>
          
          <!-- 手动输入表单 -->
          <div v-if="manualInputMode" class="mt-3 p-4 bg-slate-50 rounded-xl max-w-lg">
            <div class="grid gap-3">
              <input
                v-model="manualBookForm.title"
                type="text"
                placeholder="书名（必填）"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-indigo-400"
              />
              <input
                v-model="manualBookForm.author"
                type="text"
                placeholder="作者"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-indigo-400"
              />
              <textarea
                v-model="manualBookForm.abstract"
                placeholder="简介（AI 将根据简介生成关系图谱）"
                rows="3"
                class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-indigo-400 resize-none"
              ></textarea>
              <button
                @click="submitManualBook"
                :disabled="!manualBookForm.title.trim()"
                class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                确认并生成图谱
              </button>
            </div>
          </div>
        </div>
        
        <div class="flex items-center gap-3">
          <button 
            @click="showSettingsModal = true"
            class="p-2 text-slate-400 hover:text-slate-600 transition-colors bg-white hover:bg-slate-50 border border-transparent hover:border-slate-200 rounded-lg">
            <Settings class="w-5 h-5" />
          </button>
          <div class="h-8 w-px bg-slate-200 mx-1"></div>
          <button 
            @click="toggleSimulation"
            class="flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium transition-all active:scale-95 shadow-sm group"
            :class="isSimulating ? 'bg-amber-50 text-amber-600 border border-amber-200 hover:bg-amber-100' : 'bg-slate-900 text-white hover:bg-slate-800 border border-transparent'"
          >
            <component :is="isSimulating ? Pause : Play" class="w-4 h-4 fill-current group-hover:scale-110 transition-transform" />
            {{ isSimulating ? '暂停模拟' : '开始模拟' }}
          </button>
        </div>
      </div>

      <!-- Main Content Grid -->
      <div class="flex-1 grid grid-cols-12 gap-6 min-h-0">
        
        <!-- Left Sidebar (Reader Profiles) -->
        <div class="col-span-12 lg:col-span-3 flex flex-col gap-4 min-h-0">
          <div class="flex items-center justify-between mb-1 px-1">
            <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
              <Users class="w-4 h-4 text-indigo-500" />
              读者画像
            </h2>
            <div class="flex items-center gap-2">
                <button @click="openCreateModal" class="text-xs font-bold text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 px-2 py-1 rounded transition-colors">+ 新建</button>
                <span class="px-2.5 py-1 bg-indigo-50 text-indigo-600 rounded-lg text-xs font-bold border border-indigo-100">{{ filteredProfiles.length }} 活跃</span>
            </div>
          </div>
          
          <div class="relative group">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors" />
            <input 
              v-model="searchQuery"
              type="text" 
              placeholder="搜索读者..." 
              class="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-400 shadow-sm"
            >
          </div>

          <div class="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar p-1">
            <TransitionGroup name="list">
              <div 
                v-for="profile in filteredProfiles" 
                :key="profile.id"
                class="bg-white border border-slate-200 hover:border-indigo-300 rounded-2xl p-4 transition-all hover:shadow-md cursor-pointer group relative overflow-hidden"
              >
                <div v-if="profile.persona" class="absolute top-0 right-0 px-2.5 py-1 bg-indigo-50/80 backdrop-blur-sm rounded-bl-xl text-[10px] font-bold text-indigo-600 z-10 border-b border-l border-indigo-100">
                  {{ profile.persona }}
                </div>

                <div class="flex items-start gap-4 relative z-10">
                  <div class="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center text-2xl shadow-sm group-hover:scale-105 transition-transform">
                    {{ profile.avatar }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between">
                      <h3 class="font-bold text-slate-900 truncate group-hover:text-indigo-700 transition-colors" :title="profile.name">{{ profile.name }}</h3>
                      <span class="text-xs font-mono text-slate-400" :title="profile.id">#{{ String(profile.id).slice(0, 6) }}</span>
                    </div>
                    <p class="text-xs text-slate-500 mb-2 font-medium">@{{ profile.username }}</p>
                    <p v-if="profile.region" class="text-[11px] text-slate-400 mb-2">{{ profile.region }}</p>
                    <p class="text-xs text-slate-600 mb-2.5 line-clamp-2 italic opacity-80" :title="profile.bio">{{ profile.bio }}</p>
                    
                    <div class="flex flex-wrap gap-1.5 ">
                      <span 
                        v-for="tag in profile.tags.slice(0, 2)" 
                        :key="tag"
                        class="px-2 py-0.5 bg-slate-100 text-slate-600 border border-slate-200 rounded-md text-[10px] font-medium group-hover:bg-indigo-50 group-hover:text-indigo-600 group-hover:border-indigo-200 transition-colors"
                      >
                        {{ tag }}
                      </span>
                      <span v-if="profile.tags.length > 2" class="px-1.5 py-0.5 text-[10px] text-slate-400 font-medium bg-slate-50 rounded-md border border-transparent">
                        +{{ profile.tags.length - 2 }}
                      </span>
                    </div>
                  </div>
                </div>
                <div class="mt-3 pt-3 border-t border-slate-100 flex justify-between items-center text-xs opacity-80 group-hover:opacity-100 transition-opacity">
                   <div class="flex items-center gap-1">
                      <span class="text-slate-400">情感倾向:</span>
                      <span class="font-bold" :class="profile.sentiment > 0 ? 'text-emerald-500' : 'text-red-500'">{{ profile.sentiment > 0 ? '+' : ''}}{{ profile.sentiment }}</span>
                   </div>
                   <div class="flex items-center gap-1">
                      <span class="text-slate-400">活跃度</span>
                      <div class="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div class="h-full bg-indigo-500 rounded-full" :style="{ width: (profile.activity_level * 100) + '%' }"></div>
                      </div>
                   </div>
                </div>
              </div>
            </TransitionGroup>
          </div>
        </div>

        <!-- Center (Simulation View) -->
        <div class="col-span-12 lg:col-span-6 flex flex-col min-h-0">
          <div class="flex items-center justify-between mb-4 px-1">
             <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
               <RefreshCw class="w-4 h-4 text-emerald-500" :class="{ 'animate-spin': isSimulating }" />
               实时模拟
             </h2>
              <div class="flex items-center gap-2">
                 <span class="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border shadow-sm" :class="taskStatusClass">
                   <span class="relative flex h-2 w-2">
                     <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" v-if="isSimulating"></span>
                     <span class="relative inline-flex rounded-full h-2 w-2" :class="isSimulating ? 'bg-emerald-500' : 'bg-slate-400'"></span>
                   </span>
                   {{ taskStatusLabel }}
                 </span>
                 <span class="px-3 py-1 bg-slate-50 text-slate-500 rounded-full text-xs font-medium border border-slate-200 shadow-sm" v-if="currentTaskId">
                   Task: {{ currentTaskId.slice(0, 8) }}...
                 </span>
              </div>
           </div>

          <div class="mb-3 px-1" v-if="taskError">
            <div class="px-3 py-2 rounded-xl border border-red-200 bg-red-50 text-red-700 text-xs">
              {{ taskError }}
            </div>
          </div>
          
          <div class="flex-1 rounded-3xl border border-slate-200 bg-white shadow-sm overflow-hidden relative group">
             <div class="absolute inset-0 bg-[url('@/assets/grid.svg')] opacity-[0.03] pointer-events-none"></div>
             
             <!-- Dynamic Data Passing -->
             <GraphPanel :data="currentGraphData" />
             
             <div class="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-6 px-6 py-3 bg-white/95 backdrop-blur-xl border border-slate-200/60 rounded-2xl shadow-lg">
                <div class="flex items-center gap-2">
                   <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                     <span class="text-slate-600 text-sm">💬</span>
                   </div>
                   <div>
                     <p class="text-[10px] text-slate-400 font-medium">评论</p>
                     <p class="text-lg font-bold text-slate-800">{{ liveStats.total }}</p>
                   </div>
                </div>
                <div class="w-px h-8 bg-slate-200"></div>
                <div class="flex items-center gap-2">
                   <div class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                     <span class="text-indigo-600 text-sm">👥</span>
                   </div>
                   <div>
                     <p class="text-[10px] text-slate-400 font-medium">Agent</p>
                     <p class="text-lg font-bold text-indigo-600">{{ liveStats.activeAgents }}</p>
                   </div>
                </div>
                <div class="w-px h-8 bg-slate-200"></div>
                <div class="flex items-center gap-3">
                   <div class="flex items-center gap-1">
                     <span class="text-emerald-500">👍</span>
                     <span class="text-sm font-bold text-emerald-600">{{ liveStats.positive }}</span>
                   </div>
                   <div class="flex items-center gap-1">
                     <span class="text-red-400">👎</span>
                     <span class="text-sm font-bold text-red-500">{{ liveStats.negative }}</span>
                   </div>
                </div>
             </div>
          </div>
        </div>

        <!-- Right (Feed) -->
        <div class="col-span-12 lg:col-span-3 flex flex-col min-h-0">
          <div class="flex items-center justify-between mb-4 px-1">
             <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
               <MessageCircle class="w-4 h-4 text-amber-500" />
               实时反馈流
             </h2>
             <button @click="clearFeed" class="text-xs font-medium text-slate-400 hover:text-slate-600 transition-colors px-2 py-1 rounded bg-slate-50 hover:bg-slate-100">清除</button>
          </div>

          <!-- 情感可视化面板 -->
          <SentimentPanel :feedData="feed" />
          <div class="mb-3 px-1 relative z-10">
            <div class="mb-1 text-[11px] font-medium text-slate-500">去重模式（当前轮次即时生效）</div>
            <div class="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm pointer-events-auto">
              <button
                v-for="mode in dedupModeOptions"
                :key="mode.value"
                type="button"
                @click.stop.prevent="setDedupMode(mode.value)"
                class="px-2.5 py-1 rounded-lg text-xs font-medium transition-colors"
                :class="dedupMode === mode.value ? 'bg-slate-900 text-white' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'"
                :aria-pressed="dedupMode === mode.value"
              >
                {{ mode.label }}
              </button>
            </div>
          </div>
          
          <div class="flex-1 bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
             <div ref="feedContainer" class="flex-1 overflow-y-auto px-4 py-4 space-y-4 custom-scrollbar bg-slate-50/30">
                <TransitionGroup name="list">
                  <div 
                    v-for="post in feed" 
                    :key="post.id" 
                    class="flex gap-3 items-start group"
                  >
                     <div class="w-9 h-9 rounded-full bg-white border border-slate-100 flex items-center justify-center text-sm shadow-sm flex-shrink-0 group-hover:scale-110 transition-transform">
                        {{ getFeedAvatar(post) }}
                     </div>
                     <div class="flex-1">
                        <div class="flex items-baseline justify-between mb-1">
                           <div class="flex items-center gap-2">
                             <span class="text-xs font-bold text-slate-800">
                               {{ getFeedName(post) }}
                             </span>
                             <span v-if="post.replyToName" class="text-[10px] text-slate-400 flex items-center gap-0.5">
                               <CornerDownRight class="w-3 h-3 text-slate-300" />
                               回复 <span class="text-indigo-600 font-medium">@{{ post.replyToName }}</span>
                             </span>
                           </div>
                           <span class="text-[10px] text-slate-400 font-mono">{{ post.time }}</span>
                        </div>
                        <div 
                          class="p-3 border shadow-sm text-sm leading-relaxed relative rounded-2xl rounded-tl-none transition-all"
                          :class="getSentimentBubbleClass(post.sentiment)"
                        >
                           <TypewriterText 
                             :text="post.content" 
                             :sentiment="post.sentiment ?? 0"
                             :speed="25"
                             :delay="100"
                           />
                            <div class="absolute -left-1.5 top-0 w-3 h-3 border-t border-l bg-inherit transform -rotate-45" :class="getSentimentBorderClass(post.sentiment)"></div>
                        </div>
                     </div>
                  </div>
                </TransitionGroup>
             </div>
             
             <div class="p-3 border-t border-slate-100 bg-white">
                <div class="relative group">
                   <input 
                     v-model="globalEventInput"
                     @keyup.enter="injectGlobalEvent"
                     type="text" 
                     placeholder="注入突发事件 (例如: 作者断更...)" 
                     class="w-full pl-4 pr-10 py-3 bg-slate-50 border border-slate-200 focus:bg-white rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
                   >
                   <button 
                     @click="injectGlobalEvent"
                     class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-indigo-600 text-white rounded-lg shadow-md hover:bg-indigo-700 hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:scale-100"
                     :disabled="!globalEventInput.trim()"
                   >
                      <Send class="w-3.5 h-3.5" />
                   </button>
                </div>
             </div>
          </div>
        </div>
      </div>
    </div>

     <!-- Create Modal -->
     <div v-if="showCreateModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
         <div class="bg-white rounded-2xl w-full max-w-md p-6 shadow-2xl">
             <h3 class="text-xl font-bold text-slate-800 mb-4">创建新读者</h3>
             <div class="space-y-4">
                 <div>
                     <label class="block text-sm font-medium text-slate-600 mb-1">昵称</label>
                     <input v-model="newPersonaForm.name" type="text" class="w-full p-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20">
                 </div>
                 <div class="grid grid-cols-2 gap-4">
                     <div>
                         <label class="block text-sm font-medium text-slate-600 mb-1">性别</label>
                         <select v-model="newPersonaForm.gender" class="w-full p-2 border border-slate-200 rounded-lg">
                             <option value="male">男</option>
                             <option value="female">女</option>
                         </select>
                     </div>
                     <div>
                         <label class="block text-sm font-medium text-slate-600 mb-1">地区</label>
                         <input v-model="newPersonaForm.region" type="text" placeholder="如：广东" class="w-full p-2 border border-slate-200 rounded-lg">
                     </div>
                 </div>
                 <div class="grid grid-cols-2 gap-4">
                     <div>
                         <label class="block text-sm font-medium text-slate-600 mb-1">书龄 (年)</label>
                         <input v-model.number="newPersonaForm.reading_age" type="number" class="w-full p-2 border border-slate-200 rounded-lg">
                     </div>
                     <div class="flex items-end">
                         <div class="text-xs text-slate-400">地区字段会用于联动真实评论样本。</div>
                     </div>
                 </div>
                 <div>
                     <label class="block text-sm font-medium text-slate-600 mb-1">偏好标签 (逗号分隔)</label>
                     <input v-model="newPersonaForm.preference_tags" type="text" placeholder="如: 玄幻, 甜宠, 轻松" class="w-full p-2 border border-slate-200 rounded-lg">
                 </div>
                 <div>
                     <label class="block text-sm font-medium text-slate-600 mb-1">毒舌指数 (1-10)</label>
                     <input v-model.number="newPersonaForm.toxicity_level" type="range" min="1" max="10" class="w-full">
                     <div class="text-right text-xs text-slate-500">{{ newPersonaForm.toxicity_level }} 级 ({{ newPersonaForm.toxicity_level > 7 ? '偏激' : '温和' }})</div>
                 </div>
                 <div>
                     <label class="block text-sm font-medium text-slate-600 mb-1">性格简述</label>
                     <textarea v-model="newPersonaForm.bio" placeholder="例如：理性、吐槽型、感性..." class="w-full p-2 border border-slate-200 rounded-lg h-20 resize-none"></textarea>
                 </div>
              </div>
              <p v-if="createPersonaError" class="mt-3 text-xs text-red-600">{{ createPersonaError }}</p>
              <div class="mt-6 flex gap-3">
                  <button @click="closeCreateModal" class="flex-1 py-2 text-slate-500 hover:bg-slate-100 rounded-lg font-medium">取消</button>
                 <button @click="createPersona" class="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold">创建</button>
             </div>
         </div>
     </div>
     
     <!-- Settings Modal -->
     <AISettingsModal v-if="showSettingsModal" @close="showSettingsModal = false" />
  </EditorialLayout>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.2);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.4);
}

.list-enter-active,
.list-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.95);
}
</style>
