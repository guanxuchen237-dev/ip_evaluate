<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { TrendingUp, TrendingDown, AlertTriangle, Sparkles, Flame, Heart, Frown } from 'lucide-vue-next'

interface Props {
  feedData: Array<{ sentiment?: number; content: string; time: string }>
}

const props = defineProps<Props>()

// 情感统计
const stats = computed(() => {
  const posts = props.feedData || []
  if (posts.length === 0) {
    return { positiveRate: 50, controversyLevel: 0, dropRisk: 0, avgSentiment: 0 }
  }
  
  // 计算正面评论比例
  const positive = posts.filter(p => (p.sentiment ?? 0) > 0).length
  const negative = posts.filter(p => (p.sentiment ?? 0) < 0).length
  const positiveRate = Math.round((positive / posts.length) * 100)
  
  // 争议度：正负评论数量接近时争议度高
  const balance = Math.abs(positive - negative)
  const controversyLevel = Math.round(100 - (balance / posts.length) * 100)
  
  // 弃书风险：基于连续负面评论
  const recentPosts = posts.slice(0, 5)
  const recentNegative = recentPosts.filter(p => (p.sentiment ?? 0) < 0).length
  const dropRisk = Math.round((recentNegative / 5) * 100)
  
  // 平均情感
  const avgSentiment = posts.reduce((sum, p) => sum + (p.sentiment ?? 0), 0) / posts.length
  
  return { positiveRate, controversyLevel, dropRisk, avgSentiment }
})

// 当前情绪状态
const currentMood = computed(() => {
  const { positiveRate, controversyLevel, dropRisk } = stats.value
  if (controversyLevel > 70) return { label: '激烈争论', icon: Flame, color: 'text-orange-500', bg: 'bg-orange-50' }
  if (dropRisk > 60) return { label: '情绪低落', icon: Frown, color: 'text-red-500', bg: 'bg-red-50' }
  if (positiveRate > 70) return { label: '读者狂欢', icon: Sparkles, color: 'text-emerald-500', bg: 'bg-emerald-50' }
  if (positiveRate > 50) return { label: '平稳阅读', icon: Heart, color: 'text-blue-500', bg: 'bg-blue-50' }
  return { label: '观望中', icon: AlertTriangle, color: 'text-slate-500', bg: 'bg-slate-50' }
})

// 情绪历史（用于曲线图）
const sentimentHistory = ref<{ time: string; value: number }[]>([])
const maxHistoryLength = 20

watch(() => props.feedData.length, () => {
  if (props.feedData.length > 0) {
    const latest = props.feedData[0]
    if (latest) {
      sentimentHistory.value.unshift({
        time: latest.time,
        value: latest.sentiment ?? 0
      })
      if (sentimentHistory.value.length > maxHistoryLength) {
        sentimentHistory.value.pop()
      }
    }
  }
})

// 简易曲线路径
const curvePath = computed(() => {
  const data = sentimentHistory.value.slice().reverse()
  if (data.length < 2) return ''
  
  const width = 200
  const height = 40
  const padding = 4
  const stepX = (width - padding * 2) / (maxHistoryLength - 1)
  
  const points = data.map((d, i) => {
    const x = padding + i * stepX
    const y = height / 2 - d.value * (height / 2 - padding)
    return { x, y }
  })
  
  if (points.length === 0) return ''
  
  const first = points[0]
  if (!first) return ''
  let path = `M ${first.x} ${first.y}`
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1]
    const curr = points[i]
    if (prev && curr) {
      const cp1x = prev.x + stepX / 2
      const cp1y = prev.y
      const cp2x = curr.x - stepX / 2
      const cp2y = curr.y
      path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${curr.x} ${curr.y}`
    }
  }
  return path
})
</script>

<template>
  <div class="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm mb-4">
    <!-- 顶部：当前情绪状态 -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <div :class="[currentMood.bg, 'p-2 rounded-xl']">
          <component :is="currentMood.icon" :class="[currentMood.color, 'w-5 h-5']" />
        </div>
        <div>
          <p class="text-sm font-bold text-slate-800">{{ currentMood.label }}</p>
          <p class="text-[10px] text-slate-400">实时情绪状态</p>
        </div>
      </div>
      
      <!-- 迷你情绪曲线 -->
      <div class="w-[200px] h-[40px] bg-slate-50 rounded-xl overflow-hidden">
        <svg class="w-full h-full" viewBox="0 0 200 40" preserveAspectRatio="none">
          <!-- 中线 -->
          <line x1="0" y1="20" x2="200" y2="20" stroke="#e2e8f0" stroke-width="1" stroke-dasharray="4" />
          <!-- 情绪曲线 -->
          <path
            v-if="curvePath"
            :d="curvePath"
            fill="none"
            stroke="url(#sentimentGradient)"
            stroke-width="2"
            stroke-linecap="round"
          />
          <defs>
            <linearGradient id="sentimentGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#f97316" />
              <stop offset="50%" stop-color="#8b5cf6" />
              <stop offset="100%" stop-color="#10b981" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>
    
    <!-- 三个指标 -->
    <div class="grid grid-cols-3 gap-3">
      <!-- 好评率 -->
      <div class="text-center p-3 bg-gradient-to-br from-emerald-50 to-green-50 rounded-xl border border-emerald-100">
        <div class="flex items-center justify-center gap-1 mb-1">
          <TrendingUp class="w-3.5 h-3.5 text-emerald-500" />
          <span class="text-[10px] font-medium text-emerald-600">好评率</span>
        </div>
        <p class="text-2xl font-bold text-emerald-600">{{ stats.positiveRate }}%</p>
      </div>
      
      <!-- 争议度 -->
      <div class="text-center p-3 bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl border border-orange-100">
        <div class="flex items-center justify-center gap-1 mb-1">
          <Flame class="w-3.5 h-3.5 text-orange-500" />
          <span class="text-[10px] font-medium text-orange-600">争议度</span>
        </div>
        <p class="text-2xl font-bold text-orange-600">{{ stats.controversyLevel }}%</p>
      </div>
      
      <!-- 弃书风险 -->
      <div class="text-center p-3 bg-gradient-to-br from-red-50 to-rose-50 rounded-xl border border-red-100">
        <div class="flex items-center justify-center gap-1 mb-1">
          <TrendingDown class="w-3.5 h-3.5 text-red-500" />
          <span class="text-[10px] font-medium text-red-600">弃书风险</span>
        </div>
        <p class="text-2xl font-bold text-red-600">{{ stats.dropRisk }}%</p>
      </div>
    </div>
  </div>
</template>
