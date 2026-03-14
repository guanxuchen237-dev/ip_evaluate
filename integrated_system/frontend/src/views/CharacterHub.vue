<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onUnmounted, computed } from 'vue'
import { Send, MessageSquare, ArrowLeft, Plus, BookOpen, User } from 'lucide-vue-next'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

const router = useRouter()

interface Persona {
  id: string
  name: string
  title: string
  avatar: string
  color: string
  bio: string
  persona: string
  scenario: string
  gender: string
  age: number
  reading_age: number
  preference_tags: string[]
  toxicity_level: number
  vip_level: number
}

interface VrTaskSummary {
  task_id: string
  status: string
  progress: number
  created_at?: string
  updated_at?: string
  error?: string
}

const personas = ref<Persona[]>([])
const activePersona = ref<Persona | null>(null)
const mode = ref<'chat' | 'read'>('chat')
const showCreateModal = ref(false)

const inputMsg = ref('')
const history = ref<{ role: string; content: string }[]>([])
const isChatLoading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

const novelContent = ref('')
const readResult = ref<any>(null)
const isReadLoading = ref(false)
const readTaskId = ref('')
const readTaskStatus = ref('')
const readTaskProgress = ref(0)
const readTaskError = ref('')
const sourceTaskItems = ref<VrTaskSummary[]>([])
const sourceTaskLoading = ref(false)
const sourceTaskError = ref('')
let readPollTimer: ReturnType<typeof setInterval> | null = null

const readTaskStatusText = computed(() => {
  if (!readTaskStatus.value) return '未开始'
  const statusMap: Record<string, string> = {
    pending: '排队中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return statusMap[readTaskStatus.value] || readTaskStatus.value
})

const newPersonaForm = ref({
  name: '',
  gender: 'male',
  reading_age: 3,
  preference_tags: '',
  toxicity_level: 3,
  bio: ''
})

const loadPersonas = async () => {
  try {
    const res = await axios.get('http://localhost:5000/api/personas')
    personas.value = res.data
    if (personas.value.length > 0 && !activePersona.value) {
      const firstPersona = personas.value[0]
      if (firstPersona) {
        activePersona.value = firstPersona
        loadHistory()
      }
    }
  } catch (e) {
    console.error('Failed to load personas', e)
  }
}

const createPersona = async () => {
  const tags = newPersonaForm.value.preference_tags.split(/[，,\s]+/).filter(Boolean)
  const payload = {
    ...newPersonaForm.value,
    preference_tags: tags,
    avatar: '👤',
    color: 'bg-emerald-600 text-white',
    title: `书龄${newPersonaForm.value.reading_age}年`,
    persona: `你是一个书龄${newPersonaForm.value.reading_age}年的${newPersonaForm.value.gender === 'male' ? '男' : '女'}读者。你的人设是：${newPersonaForm.value.bio}。偏好：${tags.join(',')}`,
    scenario: '在被窝里看书'
  }

  try {
    const res = await axios.post('http://localhost:5000/api/personas', payload)
    personas.value.push(res.data)
    activePersona.value = res.data
    showCreateModal.value = false
    newPersonaForm.value = {
      name: '',
      gender: 'male',
      reading_age: 3,
      preference_tags: '',
      toxicity_level: 3,
      bio: ''
    }
  } catch (e: any) {
    alert(`创建失败: ${e?.message || e}`)
  }
}

const getHistoryKey = (charId: string) => `chat_history_${charId}`

const loadHistory = () => {
  if (!activePersona.value) return
  const saved = window.localStorage.getItem(getHistoryKey(activePersona.value.id))
  if (saved) {
    try {
      history.value = JSON.parse(saved)
      nextTick(() => scrollToBottom())
    } catch {
      history.value = []
    }
  } else {
    history.value = []
  }
}

watch(
  [history, activePersona],
  ([newHist, newPersona]) => {
    if (newPersona) {
      window.localStorage.setItem(getHistoryKey(newPersona.id), JSON.stringify(newHist))
    }
  },
  { deep: true }
)

const clearChatHistory = () => {
  if (!activePersona.value) return
  history.value = []
  window.localStorage.removeItem(getHistoryKey(activePersona.value.id))
}

const sendMessage = async () => {
  if (!inputMsg.value.trim() || isChatLoading.value || !activePersona.value) return

  const msg = inputMsg.value
  history.value.push({ role: 'user', content: msg })
  inputMsg.value = ''
  isChatLoading.value = true
  await nextTick()
  scrollToBottom()

  try {
    const res = await axios.post(
      'http://localhost:5000/api/ai/chat',
      {
        profile: activePersona.value,
        history: history.value,
        message: msg
      },
      { timeout: 60000 }
    )

    if (res.data.response) {
      history.value.push({ role: 'assistant', content: res.data.response })
    }
  } catch (e) {
    history.value.push({ role: 'assistant', content: '(连接中断...)' })
  } finally {
    isChatLoading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const stopReadPolling = () => {
  if (readPollTimer) {
    clearInterval(readPollTimer)
    readPollTimer = null
  }
}

const buildSourceMeta = () => {
  const sourceTitle = activePersona.value?.title || activePersona.value?.name || '未知小说'
  const sourceAuthor = activePersona.value?.name || '未知作者'
  const sourcePlatform = 'character_hub'
  const sourceBookKey = `${sourcePlatform}|${sourceTitle}|${sourceAuthor}`
  return { sourceTitle, sourceAuthor, sourcePlatform, sourceBookKey }
}

const loadSourceTasks = async () => {
  if (!activePersona.value) return
  const { sourceTitle, sourceAuthor, sourcePlatform } = buildSourceMeta()

  sourceTaskLoading.value = true
  sourceTaskError.value = ''
  try {
    const res = await axios.get('http://localhost:5000/api/virtual_reader/tasks', {
      params: {
        source_title: sourceTitle,
        source_author: sourceAuthor,
        source_platform: sourcePlatform,
        limit: 10,
        offset: 0
      },
      timeout: 30000
    })
    sourceTaskItems.value = res.data?.items || []
  } catch (e: any) {
    sourceTaskError.value = e?.message || String(e)
  } finally {
    sourceTaskLoading.value = false
  }
}

const fetchReadComments = async (taskId: string) => {
  const commentsRes = await axios.get('http://localhost:5000/api/virtual_reader/comments', {
    params: { task_id: taskId, limit: 1, offset: 0 },
    timeout: 30000
  })
  const items = commentsRes.data?.items || []
  if (items.length > 0) {
    readResult.value = items[0]
  }
}

const selectSourceTask = async (task: VrTaskSummary) => {
  readTaskId.value = task.task_id
  readTaskStatus.value = task.status || ''
  readTaskProgress.value = Number(task.progress || 0)
  readTaskError.value = task.error || ''
  isReadLoading.value = task.status === 'pending' || task.status === 'processing'

  await fetchReadComments(task.task_id)

  if (isReadLoading.value) {
    pollReadTask(task.task_id)
  } else {
    stopReadPolling()
  }
}

const pollReadTask = (taskId: string) => {
  stopReadPolling()
  readPollTimer = setInterval(async () => {
    try {
      const taskRes = await axios.get(`http://localhost:5000/api/virtual_reader/task/${taskId}`, {
        timeout: 30000
      })
      const task = taskRes.data || {}
      readTaskStatus.value = task.status || ''
      readTaskProgress.value = Number(task.progress || 0)

      if (task.status === 'completed') {
        await fetchReadComments(taskId)
        await loadSourceTasks()
        isReadLoading.value = false
        stopReadPolling()
        return
      }

      if (task.status === 'failed') {
        readTaskError.value = task.error || '任务失败'
        await loadSourceTasks()
        isReadLoading.value = false
        stopReadPolling()
      }
    } catch (e: any) {
      readTaskError.value = e?.message || String(e)
      isReadLoading.value = false
      stopReadPolling()
    }
  }, 2000)
}

const startReading = async () => {
  if (!novelContent.value.trim() || !activePersona.value) return

  isReadLoading.value = true
  readResult.value = null
  readTaskId.value = ''
  readTaskStatus.value = 'pending'
  readTaskProgress.value = 0
  readTaskError.value = ''

  try {
    const { sourceTitle, sourceAuthor, sourcePlatform, sourceBookKey } = buildSourceMeta()

    const res = await axios.post(
      'http://localhost:5000/api/virtual_reader/simulate_async',
      {
        persona_ids: [activePersona.value.id],
        content: novelContent.value,
        title: sourceTitle,
        chapter: '试读片段',
        source_title: sourceTitle,
        source_author: sourceAuthor,
        source_platform: sourcePlatform,
        source_book_key: sourceBookKey
      },
      { timeout: 30000 }
    )

    const taskId = res.data?.task_id
    if (!taskId) {
      throw new Error('No task_id returned')
    }

    readTaskId.value = taskId
    await loadSourceTasks()
    pollReadTask(taskId)
  } catch (e: any) {
    readTaskError.value = e?.message || String(e)
    isReadLoading.value = false
    stopReadPolling()
  }
}

watch([activePersona, mode], ([persona, currentMode]) => {
  if (persona && currentMode === 'read') {
    loadSourceTasks()
  }
})

onMounted(() => {
  loadPersonas()
})

onUnmounted(() => {
  stopReadPolling()
})
</script>

<template>
  <EditorialLayout>
     <div class="h-screen py-6 px-6 max-w-[1600px] mx-auto flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-4">
               <button @click="router.back()" class="p-2 hover:bg-slate-100 rounded-full transition-colors">
                  <ArrowLeft class="w-6 h-6 text-slate-500" />
               </button>
               <h1 class="text-2xl font-bold font-serif text-slate-900 flex items-center gap-2">
                  <User class="w-6 h-6 text-indigo-600" /> 
                  虚拟角色中心 (Character Hub)
               </h1>
            </div>
            
            <!-- Mode Switcher -->
            <div class="flex bg-slate-100 p-1 rounded-full">
                <button 
                    @click="mode = 'chat'"
                    class="px-6 py-2 rounded-full text-sm font-bold transition-all flex items-center gap-2"
                    :class="mode === 'chat' ? 'bg-white shadow-sm text-indigo-600' : 'text-slate-500 hover:text-slate-700'"
                >
                    <MessageSquare class="w-4 h-4" /> 沉浸对话
                </button>
                <button 
                    @click="mode = 'read'"
                    class="px-6 py-2 rounded-full text-sm font-bold transition-all flex items-center gap-2"
                    :class="mode === 'read' ? 'bg-white shadow-sm text-indigo-600' : 'text-slate-500 hover:text-slate-700'"
                >
                    <BookOpen class="w-4 h-4" /> 阅读模拟
                </button>
            </div>
        </div>

        <!-- Main Body -->
        <div class="flex-1 bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden flex">
            <!-- Sidebar: Character List -->
            <div class="w-72 bg-slate-50 border-r border-slate-200 flex flex-col">
                <div class="p-4 border-b border-slate-200 flex justify-between items-center">
                    <h2 class="text-sm font-bold text-slate-500 uppercase tracking-wider">我的角色</h2>
                    <button @click="showCreateModal = true" class="p-1.5 hover:bg-indigo-100 hover:text-indigo-600 rounded-lg transition-colors">
                        <Plus class="w-4 h-4" />
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto p-2 space-y-2">
                    <button 
                       v-for="p in personas" 
                       :key="p.id"
                       @click="activePersona = p; loadHistory()"
                       class="w-full text-left p-3 rounded-xl transition-all flex items-center gap-3 border"
                       :class="activePersona?.id === p.id ? 'bg-white border-indigo-200 shadow-md ring-1 ring-indigo-500/20' : 'border-transparent hover:bg-slate-200/50'"
                    >
                       <div class="w-10 h-10 rounded-full flex items-center justify-center text-xl shadow-sm" :class="p.color">
                          {{ p.avatar }}
                       </div>
                       <div>
                          <div class="font-bold text-slate-800">{{ p.name }}</div>
                          <div class="text-xs text-slate-500 truncate max-w-[140px]">{{ p.title }}</div>
                       </div>
                    </button>
                </div>
            </div>

            <!-- Content Area -->
            <div class="flex-1 flex flex-col bg-slate-50/30 relative" v-if="activePersona">
               <!-- Persona Header -->
               <div class="h-16 border-b border-slate-100 bg-white flex items-center px-6 justify-between shadow-sm z-10">
                   <div class="flex items-center gap-3">
                       <span class="text-2xl">{{ activePersona.avatar }}</span>
                       <div>
                          <h2 class="font-bold text-slate-800">{{ activePersona.name }}</h2>
                          <div class="flex gap-2 text-xs text-slate-500">
                              <span v-if="mode === 'chat'">{{ activePersona.scenario }}</span>
                              <span v-else>书龄{{ activePersona.reading_age }}年 · 毒舌{{ activePersona.toxicity_level }}级</span>
                          </div>
                       </div>
                   </div>
                    <button 
                        v-if="mode === 'chat'" 
                        @click="clearChatHistory" 
                        class="text-xs text-slate-400 hover:text-red-500 transition-colors"
                    >
                     清空对话
                   </button>
               </div>
               
               <!-- 💬 CHAT MODE -->
               <div v-show="mode === 'chat'" class="flex-1 flex flex-col h-full overflow-hidden">
                   <div ref="chatContainer" class="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
                       <div v-if="history.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400 gap-4 opacity-50">
                           <MessageSquare class="w-12 h-12" />
                           <p>开始与 {{ activePersona.name }} 对话吧...</p>
                       </div>
                       
                       <div v-for="(msg, idx) in history" :key="idx" class="flex gap-4" :class="msg.role === 'user' ? 'flex-row-reverse' : ''">
                           <div class="w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm text-sm font-bold"
                              :class="msg.role === 'user' ? 'bg-slate-200 text-slate-600' : activePersona.color">
                              {{ msg.role === 'user' ? 'ME' : activePersona.avatar }}
                           </div>
                           <div class="max-w-[70%] p-4 rounded-2xl shadow-sm text-sm leading-loose whitespace-pre-wrap"
                              :class="msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-white border border-slate-100 text-slate-800 rounded-tl-none'">
                              {{ msg.content }}
                           </div>
                       </div>
                       
                       <div v-if="isChatLoading" class="flex gap-4">
                           <div class="w-10 h-10 rounded-full bg-slate-100 flex-shrink-0"></div>
                           <div class="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-tl-none flex gap-1">
                              <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                              <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100"></div>
                              <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200"></div>
                           </div>
                       </div>
                   </div>
                   
                   <div class="p-4 bg-white border-t border-slate-100">
                      <div class="relative max-w-4xl mx-auto">
                         <input v-model="inputMsg" @keyup.enter="sendMessage" type="text" placeholder="输入你想说的话..." 
                           class="w-full pl-6 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium text-slate-700 shadow-inner">
                         <button @click="sendMessage" :disabled="isChatLoading || !inputMsg"
                           class="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 rounded-full flex items-center justify-center text-white transition-all shadow-md">
                            <Send class="w-5 h-5 ml-0.5" />
                         </button>
                      </div>
                   </div>
               </div>

               <!-- 📖 READ MODE -->
               <div v-show="mode === 'read'" class="flex-1 flex flex-col p-6 overflow-y-auto">
                   <div class="max-w-3xl mx-auto w-full space-y-6">
                       <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                           <h3 class="font-bold text-slate-700">请粘贴小说片段</h3>
                           <textarea 
                               v-model="novelContent"
                               placeholder="在此粘贴您的章节内容 (建议1000-3000字)..."
                               class="w-full h-48 p-4 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 text-sm text-slate-700 font-mono resize-none leading-relaxed"
                           ></textarea>
                           <div class="flex justify-end">
                               <button 
                                   @click="startReading" 
                                   :disabled="isReadLoading || !novelContent"
                                   class="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white rounded-lg font-bold transition-all shadow-md flex items-center gap-2"
                               >
                                   <BookOpen class="w-4 h-4" />
                                   {{ isReadLoading ? '正在阅读中...' : '开始试读' }}
                               </button>
                           </div>
                       </div>

                        <div v-if="readTaskId || isReadLoading || readTaskError" class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                            <div class="flex items-center justify-between">
                                <h4 class="font-bold text-slate-700">任务状态</h4>
                                <span
                                    class="text-xs font-bold px-2 py-1 rounded-md"
                                    :class="readTaskStatus === 'completed' ? 'bg-emerald-100 text-emerald-700' : readTaskStatus === 'failed' ? 'bg-red-100 text-red-700' : 'bg-indigo-100 text-indigo-700'"
                                >
                                    {{ readTaskStatusText }}
                                </span>
                            </div>
                            <div class="mt-2 text-xs text-slate-500 break-all">任务ID: {{ readTaskId || '-' }}</div>
                            <div class="mt-3 h-2 bg-slate-100 rounded-full overflow-hidden">
                                <div
                                    class="h-2 bg-indigo-600 transition-all duration-300"
                                    :style="{ width: `${Math.max(0, Math.min(100, readTaskProgress))}%` }"
                                ></div>
                            </div>
                            <div class="mt-2 text-xs text-slate-500">进度 {{ readTaskProgress }}%</div>
                            <div v-if="readTaskError" class="mt-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg p-2">
                                {{ readTaskError }}
                            </div>
                        </div>

                        <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
                            <div class="flex items-center justify-between">
                                <h4 class="font-bold text-slate-700">同来源任务记录</h4>
                                <button
                                    @click="loadSourceTasks"
                                    :disabled="sourceTaskLoading"
                                    class="text-xs px-2 py-1 rounded-md border border-slate-200 hover:bg-slate-50 disabled:opacity-50"
                                >
                                    {{ sourceTaskLoading ? '刷新中...' : '刷新' }}
                                </button>
                            </div>
                            <div v-if="sourceTaskError" class="mt-3 text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg p-2">
                                {{ sourceTaskError }}
                            </div>
                            <div v-else-if="sourceTaskItems.length === 0" class="mt-3 text-sm text-slate-500">
                                暂无任务记录
                            </div>
                            <div v-else class="mt-3 space-y-2">
                                <div
                                    v-for="task in sourceTaskItems"
                                    :key="task.task_id"
                                    class="p-2 rounded-lg border border-slate-100 bg-slate-50 cursor-pointer hover:border-indigo-200 hover:bg-indigo-50/30 transition-colors"
                                    @click="selectSourceTask(task)"
                                >
                                    <div class="flex items-center justify-between text-xs gap-2">
                                        <span class="font-mono text-slate-500 break-all">{{ task.task_id }}</span>
                                        <span
                                            class="font-bold"
                                            :class="task.status === 'completed' ? 'text-emerald-600' : task.status === 'failed' ? 'text-red-600' : 'text-indigo-600'"
                                        >
                                            {{ task.status }}
                                        </span>
                                    </div>
                                    <div class="mt-1 flex items-center justify-between text-xs text-slate-500">
                                        <span>进度 {{ Number(task.progress || 0) }}%</span>
                                        <span>{{ task.created_at || '-' }}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Result Display -->
                        <div v-if="readResult" class="animate-fade-in-up">
                           <div class="flex gap-4">
                               <div class="w-12 h-12 rounded-full flex-shrink-0 flex items-center justify-center shadow-md text-2xl" :class="activePersona.color">
                                  {{ activePersona.avatar }}
                               </div>
                               <div class="flex-1 bg-white p-6 rounded-2xl rounded-tl-none border border-indigo-100 shadow-lg relative">
                                   <!-- Badge -->
                                   <div class="absolute top-4 right-4 flex gap-2">
                                       <span class="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-bold rounded-md">评分: {{ readResult.score }}/5</span>
                                       <span class="px-2 py-1 bg-purple-100 text-purple-700 text-xs font-bold rounded-md uppercase">{{ readResult.emotion }}</span>
                                   </div>
                                   <h4 class="font-bold text-slate-800 mb-2">{{ activePersona.name }} 的书评</h4>
                                   <p class="text-slate-600 leading-loose whitespace-pre-wrap">{{ readResult.comment }}</p>
                                   <div class="mt-4 pt-4 border-t border-slate-100 text-xs text-slate-400 flex justify-between">
                                       <span>耗时: {{ readResult.simulated_duration }}s</span>
                                       <span>来自: 虚拟读者客户端</span>
                                   </div>
                               </div>
                           </div>
                       </div>
                   </div>
               </div>
            </div>
        </div>
     </div>

     <!-- Create Modal -->
     <div v-if="showCreateModal" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
         <div class="bg-white rounded-2xl w-full max-w-md p-6 shadow-2xl">
             <h3 class="text-xl font-bold text-slate-800 mb-4">创建新角色</h3>
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
                         <label class="block text-sm font-medium text-slate-600 mb-1">书龄 (年)</label>
                         <input v-model.number="newPersonaForm.reading_age" type="number" class="w-full p-2 border border-slate-200 rounded-lg">
                     </div>
                 </div>
                 <div>
                     <label class="block text-sm font-medium text-slate-600 mb-1">偏好标签 (用逗号分隔)</label>
                     <input v-model="newPersonaForm.preference_tags" type="text" placeholder="如: 玄幻, 甜宠, 无脑爽" class="w-full p-2 border border-slate-200 rounded-lg">
                 </div>
                 <div>
                     <label class="block text-sm font-medium text-slate-600 mb-1">毒舌指数 (1-10)</label>
                     <input v-model.number="newPersonaForm.toxicity_level" type="range" min="1" max="10" class="w-full">
                     <div class="text-right text-xs text-slate-500">{{ newPersonaForm.toxicity_level }} 级 ({{ newPersonaForm.toxicity_level > 7 ? '喷子' : '温和' }})</div>
                 </div>
                 <div>
                     <label class="block text-sm font-medium text-slate-600 mb-1">性格简述</label>
                     <textarea v-model="newPersonaForm.bio" placeholder="甚至可以写：傲娇/高冷/话痨..." class="w-full p-2 border border-slate-200 rounded-lg h-20 resize-none"></textarea>
                 </div>
             </div>
             <div class="mt-6 flex gap-3">
                 <button @click="showCreateModal = false" class="flex-1 py-2 text-slate-500 hover:bg-slate-100 rounded-lg font-medium">取消</button>
                 <button @click="createPersona" class="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold">创建</button>
             </div>
         </div>
     </div>
  </EditorialLayout>
</template>

<style scoped>
.animate-fade-in-up {
    animation: fadeInUp 0.5s ease-out;
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>

