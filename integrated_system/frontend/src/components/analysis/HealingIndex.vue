<script setup lang="ts">
import { Heart, Sparkles, Sun, Moon, Coffee, Leaf } from 'lucide-vue-next'

interface EmotionData {
  category: string
  categoryCn: string
  score: number
  description: string
  icon: any
  color: string
}

const emotionData: EmotionData[] = [
  {
    category: 'Warmth',
    categoryCn: '温暖感',
    score: 92,
    description: '情感表达细腻，治愈力强',
    icon: Sun,
    color: 'chart-yellow',
  },
  {
    category: 'Hope',
    categoryCn: '希望感',
    score: 88,
    description: '积极向上，传递正能量',
    icon: Sparkles,
    color: 'chart-cyan',
  },
  {
    category: 'Comfort',
    categoryCn: '舒适感',
    score: 85,
    description: '阅读节奏舒缓，减压效果佳',
    icon: Coffee,
    color: 'chart-purple',
  },
  {
    category: 'Nature',
    categoryCn: '自然感',
    score: 78,
    description: '场景描写贴近自然',
    icon: Leaf,
    color: 'chart-green',
  },
  {
    category: 'Nostalgia',
    categoryCn: '怀旧感',
    score: 72,
    description: '唤起美好回忆',
    icon: Moon,
    color: 'chart-blue',
  },
]

const overallScore = Math.round(emotionData.reduce((acc, e) => acc + e.score, 0) / emotionData.length)
</script>

<template>
  <div class="editorial-card rounded-3xl p-8 bg-gradient-to-br from-chart-purple/5 to-chart-cyan/5">
    <!-- Header -->
    <div class="flex items-start justify-between mb-8">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-chart-purple/20 to-chart-cyan/20 flex items-center justify-center">
          <Heart class="w-6 h-6 text-chart-purple" />
        </div>
        <div>
          <h3 class="editorial-headline text-xl text-foreground">Healing Index</h3>
          <p class="text-sm text-muted-foreground">情绪价值 · 治愈系指数</p>
        </div>
      </div>

      <div class="text-right">
        <p class="text-4xl font-serif font-bold gradient-text">{{ overallScore }}</p>
        <p class="text-xs text-muted-foreground">综合治愈指数</p>
      </div>
    </div>

    <!-- Emotion radar visualization -->
    <div class="relative mb-8">
      <div class="grid grid-cols-5 gap-4">
        <div 
          v-for="emotion in emotionData" 
          :key="emotion.category" 
          class="flex flex-col items-center"
        >
          <div class="relative h-32 w-full flex items-end justify-center mb-3">
            <div 
              :class="`w-full max-w-12 rounded-t-xl bg-gradient-to-t from-${emotion.color}/40 to-${emotion.color}/20 transition-all duration-500`"
              :style="{ height: `${(emotion.score / 100) * 120}px` }"
            >
              <div :class="`absolute -top-8 left-1/2 -translate-x-1/2 w-10 h-10 rounded-xl bg-${emotion.color}/20 flex items-center justify-center`">
                <component :is="emotion.icon" :class="`w-5 h-5 text-${emotion.color}`" />
              </div>
            </div>
          </div>
          <p class="text-sm font-medium text-foreground">{{ emotion.score }}</p>
          <p class="text-xs text-muted-foreground text-center">{{ emotion.categoryCn }}</p>
        </div>
      </div>
    </div>

    <!-- Emotion details -->
    <div class="space-y-3">
      <div 
        v-for="emotion in emotionData"
        :key="emotion.category"
        class="flex items-center gap-4 p-3 rounded-xl bg-white/40 hover:bg-white/60 transition-all"
      >
        <component :is="emotion.icon" :class="`w-5 h-5 text-${emotion.color}`" />
        <div class="flex-1">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-foreground">{{ emotion.categoryCn }}</span>
            <span class="text-xs text-muted-foreground">{{ emotion.category }}</span>
          </div>
          <p class="text-xs text-muted-foreground">{{ emotion.description }}</p>
        </div>
        <div class="w-20">
          <div class="h-2 bg-white/50 rounded-full overflow-hidden">
            <div 
              :class="`h-full rounded-full bg-gradient-to-r from-${emotion.color} to-${emotion.color}/60`"
              :style="{ width: `${emotion.score}%` }"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- ESG note -->
    <div class="mt-6 p-4 rounded-2xl bg-gradient-to-r from-chart-green/10 to-chart-cyan/10 border border-chart-green/20">
      <div class="flex items-center gap-2 mb-2">
        <Leaf class="w-4 h-4 text-chart-green" />
        <span class="text-sm font-medium text-chart-green">ESG 价值观契合度</span>
      </div>
      <p class="text-xs text-muted-foreground">
        本作品传递积极价值观，适合可持续发展品牌合作。情绪疗愈属性符合当代读者需求趋势。
      </p>
    </div>
  </div>
</template>
