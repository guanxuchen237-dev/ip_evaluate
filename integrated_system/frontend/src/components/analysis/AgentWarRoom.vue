<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { Briefcase, BookOpen, Shield, MessageSquare, Sparkles } from 'lucide-vue-next'

interface AgentMessage {
  agent: 'market' | 'content' | 'risk'
  message: string
  timestamp: string
  sentiment: 'positive' | 'warning' | 'neutral'
}

const agentProfiles = {
  market: {
    name: 'Market Agent',
    icon: Briefcase,
    color: 'from-emerald-500 to-teal-500',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    textColor: 'text-emerald-700',
  },
  content: {
    name: 'Content Agent',
    icon: BookOpen,
    color: 'from-blue-500 to-indigo-500',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    textColor: 'text-blue-700',
  },
  risk: {
    name: 'Risk Agent',
    icon: Shield,
    color: 'from-amber-500 to-orange-500',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    textColor: 'text-amber-700',
  },
}

const conversationScript: AgentMessage[] = [
  {
    agent: 'market',
    message: '《诡秘之主》的改编潜力极高。从市场数据看，克苏鲁+蒸汽朋克题材在18-35岁用户中热度持续上升，预估首播可达2亿+播放量。',
    timestamp: '10:32:15',
    sentiment: 'positive',
  },
  {
    agent: 'content',
    message: '同意市场判断。作品世界观完整度评分9.2/10，序列体系具有极强的可视化潜力。但需注意：前50章节奏较慢，改编时建议压缩。',
    timestamp: '10:32:28',
    sentiment: 'neutral',
  },
  {
    agent: 'risk',
    message: '⚠️ 需要关注：原著涉及部分宗教元素和恐怖描写，海外发行可能面临分级问题。建议提前准备多版本剧本。',
    timestamp: '10:32:41',
    sentiment: 'warning',
  },
  {
    agent: 'market',
    message: '风险可控。参考《三体》案例，合规改编后市场表现更优。且该IP已有成熟粉丝基础，可降低营销成本约40%。',
    timestamp: '10:32:55',
    sentiment: 'positive',
  },
  {
    agent: 'content',
    message: '补充：原著作者配合度高，已公开表示愿意参与改编。这将大幅提升内容质量和粉丝接受度。',
    timestamp: '10:33:08',
    sentiment: 'positive',
  },
  {
    agent: 'risk',
    message: '综合评估：投资安全系数 7.8/10。建议优先开发动画形式，降低特效成本风险。实拍剧需追加30%预算做技术储备。',
    timestamp: '10:33:22',
    sentiment: 'neutral',
  },
]

const messages = ref<AgentMessage[]>([])
const isTyping = ref(false)
const currentAgent = ref<'market' | 'content' | 'risk' | null>(null)
let currentIndex = 0
let timeoutId: number | null = null

const getSentimentStyle = (sentiment: string) => {
  switch (sentiment) {
    case 'positive': return 'bg-green-50 border-green-200'
    case 'warning': return 'bg-amber-50 border-amber-200'
    default: return 'bg-slate-50 border-slate-200'
  }
}

const addMessage = () => {
  if (currentIndex >= conversationScript.length) return

  const currentMessage = conversationScript[currentIndex]
  if (!currentMessage) return

  isTyping.value = true
  currentAgent.value = currentMessage.agent

  timeoutId = window.setTimeout(() => {
    messages.value.push(currentMessage)
    isTyping.value = false
    currentAgent.value = null
    currentIndex++

    if (currentIndex < conversationScript.length) {
      timeoutId = window.setTimeout(addMessage, 1500)
    }
  }, 1200)
}

onMounted(() => {
  timeoutId = window.setTimeout(addMessage, 500)
})

onUnmounted(() => {
  if (timeoutId) clearTimeout(timeoutId)
})

const isConversationComplete = computed(() => messages.value.length >= conversationScript.length)
</script>

<template>
  <div class="glass-card rounded-2xl p-6 float-shadow animate-fade-up opacity-0" style="animation-delay: 400ms; animation-fill-mode: forwards;">
    <div class="flex items-center gap-2 mb-6">
      <MessageSquare class="w-5 h-5 text-primary" />
      <h3 class="text-lg font-semibold text-foreground">Agent War Room · 多智能体评估会议</h3>
      <div class="ml-auto flex items-center gap-2">
        <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
        <span class="text-xs text-muted-foreground">Live Discussion</span>
      </div>
    </div>

    <!-- Agent Cards -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div 
        v-for="(agent, key) in agentProfiles"
        :key="key"
        :class="[
          'relative p-4 rounded-xl border-2 transition-all duration-300',
          currentAgent === key 
            ? `${agent.borderColor} ${agent.bgColor} scale-105 shadow-lg`
            : 'border-border/50 bg-white/50'
        ]"
      >
        <div v-if="currentAgent === key" class="absolute -top-1 -right-1">
          <div class="w-3 h-3 rounded-full bg-green-500 animate-ping"></div>
          <div class="absolute inset-0 w-3 h-3 rounded-full bg-green-500"></div>
        </div>

        <div :class="`w-12 h-12 rounded-xl bg-gradient-to-br ${agent.color} flex items-center justify-center mb-3`">
          <component :is="agent.icon" class="w-6 h-6 text-white" />
        </div>
        <h4 class="font-semibold text-foreground text-sm">{{ agent.name }}</h4>
        <p class="text-xs text-muted-foreground mt-1">
          {{ key === 'market' ? '市场分析 & ROI预测' : 
             key === 'content' ? '内容质量 & 改编建议' : 
             '风险评估 & 合规审查' }}
        </p>
      </div>
    </div>

    <!-- Chat Log -->
    <div class="border border-border/50 rounded-xl bg-white/30 p-4 h-80 overflow-y-auto space-y-4">
      <div 
        v-for="(msg, index) in messages"
        :key="index"
        :class="[
          'flex gap-3 p-3 rounded-xl border transition-all animate-fade-up',
          getSentimentStyle(msg.sentiment)
        ]"
        style="animation-duration: 0.3s;"
      >
        <div :class="`w-8 h-8 rounded-lg bg-gradient-to-br ${agentProfiles[msg.agent].color} flex items-center justify-center flex-shrink-0`">
          <component :is="agentProfiles[msg.agent].icon" class="w-4 h-4 text-white" />
        </div>
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span :class="`font-medium text-sm ${agentProfiles[msg.agent].textColor}`">{{ agentProfiles[msg.agent].name }}</span>
            <span class="text-xs text-muted-foreground">{{ msg.timestamp }}</span>
          </div>
          <p class="text-sm text-foreground/90 leading-relaxed">{{ msg.message }}</p>
        </div>
      </div>

      <!-- Typing indicator -->
      <div v-if="isTyping && currentAgent" class="flex items-center gap-2 text-muted-foreground">
        <Sparkles class="w-4 h-4 animate-pulse" />
        <span class="text-xs">{{ agentProfiles[currentAgent].name }} is analyzing...</span>
        <div class="flex gap-1">
          <div class="w-1.5 h-1.5 rounded-full bg-primary/50 animate-bounce" style="animation-delay: 0ms;"></div>
          <div class="w-1.5 h-1.5 rounded-full bg-primary/50 animate-bounce" style="animation-delay: 150ms;"></div>
          <div class="w-1.5 h-1.5 rounded-full bg-primary/50 animate-bounce" style="animation-delay: 300ms;"></div>
        </div>
      </div>
    </div>

    <!-- Summary -->
    <div v-if="isConversationComplete" class="mt-4 p-4 rounded-xl bg-gradient-to-r from-primary/5 to-accent/5 border border-primary/20 animate-fade-up">
      <div class="flex items-center gap-2 mb-2">
        <Sparkles class="w-4 h-4 text-primary" />
        <span class="font-medium text-sm text-foreground">会议结论</span>
      </div>
      <p class="text-sm text-muted-foreground">
        经多智能体综合评估，《诡秘之主》IP价值评级：<span class="font-semibold text-primary">A+</span>。
        建议优先开发动画形式，同步筹备海外分级版本剧本。
      </p>
    </div>
  </div>
</template>
