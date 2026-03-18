<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { Send, Sparkles, MessageSquare, ArrowLeft } from 'lucide-vue-next'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { parseAIError, showAIError } from '@/utils/aiErrorHandler'

const router = useRouter()

// Presets
const characters = [
  {
    id: 'klein',
    name: '克莱恩·莫雷蒂',
    title: '诡秘之主 - 愚者',
    avatar: '🎩',
    color: 'bg-indigo-900 text-indigo-100',
    persona: '你是克莱恩·莫雷蒂，也是“愚者”先生。你此时身在源堡之上，被灰雾环绕。你的语气神秘、沉稳，虽然内心戏丰富（爱吐槽），但表面上维持着不可名状的神性。你正在回应一名误入源堡的凡人的祈祷。',
    scenario: '灰雾之上的古老殿堂'
  },
  {
    id: 'shuhang',
    name: '宋书航',
    title: '修真聊天群 - 霸宋',
    avatar: '📱',
    color: 'bg-sky-500 text-white',
    persona: '你是宋书航（霸宋）。你性格随和，爱讲冷笑话，虽然拥有七个圣号，但内心还是觉得自己是个普通大学生。你现在正在“九州一号群”里水群。',
    scenario: '修真聊天群聊天界面'
  },
  {
    id: 'tangsan',
    name: '唐三',
    title: '斗罗大陆 - 海神',
    avatar: '🔱',
    color: 'bg-blue-700 text-blue-100',
    persona: '你是唐三。你性格坚毅，重情重义，说话温和有力。你时刻挂念着小舞。',
    scenario: '海神岛'
  }
]

const activeChar = ref<(typeof characters)[number] | null>(characters[0] ?? null)
const inputMsg = ref('')
const history = ref<{role: string, content: string}[]>([])
const isLoading = ref(false)
const chatContainer = ref<HTMLElement | null>(null)

// Load history from local storage key
const getHistoryKey = (charId: string) => `chat_history_${charId}`

const loadHistory = () => {
    if (!activeChar.value) {
        history.value = []
        return
    }
    const saved = window.localStorage.getItem(getHistoryKey(activeChar.value.id))
    if (saved) {
        try {
            history.value = JSON.parse(saved)
            nextTick(() => scrollToBottom())
        } catch (e) {
            console.error("Failed to load history", e)
            history.value = []
        }
    } else {
        history.value = []
    }
}

// Watch history and save
watch(history, (newVal) => {
    if (!activeChar.value) return
    window.localStorage.setItem(getHistoryKey(activeChar.value.id), JSON.stringify(newVal))
}, { deep: true })

const selectChar = (char: (typeof characters)[number]) => {
  activeChar.value = char
  loadHistory() // Load history for new char
}

const clearHistoryForActiveChar = () => {
  if (!activeChar.value) return
  history.value = []
  window.localStorage.removeItem(getHistoryKey(activeChar.value.id))
}

// Init load
loadHistory()

const sendMessage = async () => {
    if (!inputMsg.value.trim() || isLoading.value) return
    if (!activeChar.value) return
    
    const msg = inputMsg.value
    history.value.push({ role: 'user', content: msg })
    inputMsg.value = ''
    isLoading.value = true
    
    // Scroll
    await nextTick()
    scrollToBottom()
    
    try {
        const res = await axios.post('http://localhost:5000/api/ai/chat', {
            profile: {
                name: activeChar.value.name,
                persona: activeChar.value.persona,
                scenario: activeChar.value.scenario
            },
            history: history.value, // Send full history context
            message: msg
        }, {
            timeout: 120000 // 120秒超时，避免首次调用因网络冷启动而失败
        })
        
        if (res.data.response) {
            history.value.push({ role: 'assistant', content: res.data.response })
        }
    } catch (e: any) {
        console.error(e)
        const errorMsg = parseAIError(e)
        history.value.push({ role: 'assistant', content: `（错误：${errorMsg}）` })
        showAIError(e)
    } finally {
        isLoading.value = false
        await nextTick()
        scrollToBottom()
    }
}

const scrollToBottom = () => {
    if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
}
</script>

<template>
  <EditorialLayout>
     <div class="h-screen py-6 px-6 max-w-[1600px] mx-auto flex flex-col">
        <!-- Header -->
        <div class="flex items-center gap-4 mb-6">
           <button @click="router.back()" class="p-2 hover:bg-slate-100 rounded-full transition-colors">
              <ArrowLeft class="w-6 h-6 text-slate-500" />
           </button>
           <h1 class="text-2xl font-bold font-serif text-slate-900 flex items-center gap-2">
              <Sparkles class="w-6 h-6 text-purple-600" /> 
              虚拟角色对话 (Character Chat)
           </h1>
           <span class="px-3 py-1 bg-purple-100 text-purple-700 text-xs font-bold rounded-full">Powered by NVIDIA MiniMax</span>
        </div>

        <!-- Main Body -->
        <div class="flex-1 bg-white rounded-2xl border border-slate-200 shadow-xl overflow-hidden flex">
            <!-- Sidebar: Character List -->
            <div class="w-72 bg-slate-50 border-r border-slate-200 flex flex-col">
                <div class="p-4 border-b border-slate-200">
                    <h2 class="text-sm font-bold text-slate-500 uppercase tracking-wider">选择角色</h2>
                </div>
                <div class="flex-1 overflow-y-auto p-2 space-y-2">
                    <button 
                       v-for="char in characters" 
                       :key="char.id"
                       @click="selectChar(char)"
                       class="w-full text-left p-3 rounded-xl transition-all flex items-center gap-3 border"
                       :class="activeChar?.id === char.id ? 'bg-white border-indigo-200 shadow-md ring-1 ring-indigo-500/20' : 'border-transparent hover:bg-slate-200/50'"
                    >
                       <div class="w-10 h-10 rounded-full flex items-center justify-center text-xl shadow-sm" :class="char.color">
                          {{ char.avatar }}
                       </div>
                       <div>
                          <div class="font-bold text-slate-800">{{ char.name }}</div>
                          <div class="text-xs text-slate-500 truncate max-w-[140px]">{{ char.title }}</div>
                       </div>
                    </button>
                    
                    <!-- Placeholder for more -->
                    <div class="p-4 text-center text-xs text-slate-400 mt-4 border-t border-slate-200 pt-6">
                       更多角色正在接入中...
                    </div>
                </div>
            </div>

            <!-- Chat Area -->
            <div class="flex-1 flex flex-col bg-slate-50/30 relative" v-if="activeChar">
               <!-- Chat Header -->
               <div class="h-16 border-b border-slate-100 bg-white flex items-center px-6 justify-between shadow-sm z-10">
                   <div class="flex items-center gap-3">
                       <span class="text-2xl">{{ activeChar.avatar }}</span>
                       <div>
                          <h2 class="font-bold text-slate-800">{{ activeChar.name }}</h2>
                          <p class="text-xs text-slate-500">{{ activeChar.scenario }}</p>
                       </div>
                   </div>
                    <button @click="clearHistoryForActiveChar" class="text-xs text-slate-400 hover:text-red-500 transition-colors">
                     清空对话
                   </button>
               </div>
               
               <!-- Messages -->
               <div ref="chatContainer" class="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
                   <!-- Intro -->
                   <div v-if="history.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400 gap-4 opacity-50">
                       <MessageSquare class="w-12 h-12" />
                       <p>开始与 {{ activeChar.name }} 对话吧...</p>
                   </div>
                   
                   <div v-for="(msg, idx) in history" :key="idx" class="flex gap-4" :class="msg.role === 'user' ? 'flex-row-reverse' : ''">
                       <!-- Avatar -->
                       <div class="w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm text-sm font-bold"
                          :class="msg.role === 'user' ? 'bg-slate-200 text-slate-600' : activeChar.color"
                       >
                          {{ msg.role === 'user' ? 'ME' : activeChar.name[0] }}
                       </div>
                       
                       <!-- Bubble -->
                       <div class="max-w-[70%] p-4 rounded-2xl shadow-sm text-sm leading-loose whitespace-pre-wrap"
                          :class="msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-white border border-slate-100 text-slate-800 rounded-tl-none'"
                       >
                          {{ msg.content }}
                       </div>
                   </div>
                   
                   <!-- Loading Indicator -->
                   <div v-if="isLoading" class="flex gap-4">
                       <div class="w-10 h-10 rounded-full bg-slate-100 flex-shrink-0"></div>
                       <div class="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-tl-none flex gap-1">
                          <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                          <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-100"></div>
                          <div class="w-2 h-2 bg-slate-400 rounded-full animate-bounce delay-200"></div>
                       </div>
                   </div>
               </div>
               
               <!-- Input Area -->
               <div class="p-4 bg-white border-t border-slate-100">
                  <div class="relative max-w-4xl mx-auto">
                     <input 
                       v-model="inputMsg"
                       @keyup.enter="sendMessage"
                       type="text" 
                       placeholder="输入你想说的话..." 
                       class="w-full pl-6 pr-14 py-4 bg-slate-50 border border-slate-200 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-medium text-slate-700 shadow-inner"
                     >
                     <button 
                       @click="sendMessage"
                       :disabled="isLoading || !inputMsg"
                       class="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 rounded-full flex items-center justify-center text-white transition-all shadow-md hover:scale-105 active:scale-95"
                     >
                        <Send class="w-5 h-5 ml-0.5" />
                     </button>
                  </div>
               </div>
            </div>
        </div>
     </div>
  </EditorialLayout>
</template>
