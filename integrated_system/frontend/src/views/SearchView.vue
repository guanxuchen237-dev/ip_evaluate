<script setup lang="ts">
import { ref } from 'vue'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import { Sparkles, Send, Zap, Shield, Heart, TrendingUp, Flame, BookOpen, ArrowRight } from 'lucide-vue-next'

const query = ref('')
const selectedTags = ref<string[]>([])

const suggestedTags = [
  { label: 'Low Risk', labelCn: '低风险', icon: Shield, color: 'from-chart-green/20 to-chart-green/5' },
  { label: 'High Adaptation', labelCn: '强改编', icon: TrendingUp, color: 'from-chart-blue/20 to-chart-blue/5' },
  { label: 'Gen Z Favorite', labelCn: 'Z世代', icon: Flame, color: 'from-chart-red/20 to-chart-red/5' },
  { label: 'Healing', labelCn: '治愈系', icon: Heart, color: 'from-chart-purple/20 to-chart-purple/5' },
  { label: 'Fast-paced', labelCn: '快节奏', icon: Zap, color: 'from-chart-yellow/20 to-chart-yellow/5' },
]

const exampleQueries = [
  {
    title: '赛博朋克 × 治愈',
    desc: '高科技背景下的温情故事',
    gradient: 'from-chart-cyan/30 to-chart-blue/10'
  },
  {
    title: '都市异能 × 喜剧',
    desc: '轻松幽默的现代奇幻',
    gradient: 'from-chart-yellow/30 to-chart-red/10'
  },
  {
    title: '古风仙侠 × 大女主',
    desc: '权谋与浪漫的交织',
    gradient: 'from-chart-purple/30 to-primary/10'
  },
]

const toggleTag = (tag: string) => {
  selectedTags.value = selectedTags.value.includes(tag)
    ? selectedTags.value.filter(t => t !== tag)
    : [...selectedTags.value, tag]
}
</script>

<template>
  <EditorialLayout>
    <!-- Hero Section -->
    <section class="min-h-[60vh] flex flex-col items-center justify-center px-8 py-20">
      <!-- Decorative elements -->
      <div class="absolute top-32 left-1/4 w-64 h-64 bg-gradient-to-br from-primary/10 to-accent/5 rounded-full blur-3xl" />
      <div class="absolute top-48 right-1/4 w-48 h-48 bg-gradient-to-br from-chart-purple/10 to-chart-cyan/5 rounded-full blur-3xl" />

      <div class="relative z-10 text-center max-w-4xl mx-auto">
        <div 
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0 }"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/60 backdrop-blur border border-white/40 mb-8"
        >
          <Sparkles class="w-4 h-4 text-primary" />
          <span class="text-sm text-muted-foreground">AI Agent Search</span>
        </div>

        <h1 
          v-motion
          :initial="{ opacity: 0, y: 30 }"
          :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 100 } }"
          class="editorial-headline text-5xl md:text-7xl text-foreground mb-6"
        >
          用想象力<br>
          <span class="gradient-text">发现故事</span>
        </h1>

        <p 
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 200 } }"
          class="text-lg text-muted-foreground mb-12"
        >
          描述你理想中的故事，AI将从数据库中为你匹配
        </p>
      </div>

      <!-- Search Input -->
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 300 } }"
        class="relative z-10 w-full max-w-3xl mx-auto"
      >
        <div class="editorial-card rounded-3xl p-3 hero-shadow">
          <div class="relative">
            <textarea
              v-model="query"
              placeholder="描述你想要寻找的故事类型..."
              class="w-full min-h-[140px] p-6 pr-16 rounded-2xl bg-background/50 border-0 resize-none text-lg text-foreground placeholder:text-muted-foreground/50 focus:outline-none transition-all"
            />
            <button 
              :disabled="!query.trim()"
              class="absolute bottom-4 right-4 w-12 h-12 rounded-2xl bg-foreground text-background flex items-center justify-center hover:bg-foreground/90 transition-all hover:scale-105 disabled:opacity-50"
            >
              <Send class="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Tags -->
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 400 } }"
        class="relative z-10 flex flex-wrap items-center justify-center gap-3 mt-8 max-w-3xl"
      >
        <button
          v-for="tag in suggestedTags"
          :key="tag.label"
          @click="toggleTag(tag.label)"
          :class="[
            'flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium transition-all duration-300',
            selectedTags.includes(tag.label)
              ? 'bg-foreground text-background scale-105'
              : `bg-gradient-to-r ${tag.color} backdrop-blur border border-white/40 text-foreground hover:scale-105`
          ]"
        >
          <component :is="tag.icon" class="w-4 h-4" />
          <span>{{ tag.labelCn }}</span>
        </button>
      </div>
    </section>

    <!-- Example Queries -->
    <section class="px-8 py-20 max-w-6xl mx-auto">
      <p 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :visible="{ opacity: 1, y: 0 }"
        class="text-sm uppercase tracking-[0.2em] text-muted-foreground text-center mb-12"
      >
        Popular Combinations
      </p>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <button
          v-for="(example, index) in exampleQueries"
          :key="index"
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :visible="{ opacity: 1, y: 0, transition: { delay: (index + 1) * 100 } }"
          @click="query = example.title + ' - ' + example.desc"
          class="group text-left"
        >
          <div :class="`editorial-card rounded-3xl p-8 h-full bg-gradient-to-br ${example.gradient} hover:scale-[1.02] transition-all duration-300`">
            <BookOpen class="w-8 h-8 text-foreground/40 mb-6 group-hover:scale-110 transition-transform" />
            <h3 class="text-2xl font-serif font-semibold text-foreground mb-2">
              {{ example.title }}
            </h3>
            <p class="text-muted-foreground mb-6">{{ example.desc }}</p>
            <div class="flex items-center gap-2 text-primary">
              <span class="text-sm font-medium">试试这个</span>
              <ArrowRight class="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </button>
      </div>
    </section>

    <!-- Bottom hint -->
    <section class="px-8 pb-32 text-center">
      <p class="text-sm text-muted-foreground">
        AI will analyze your requirements and recommend matching IPs from our database of 50,000+ novels
      </p>
    </section>
  </EditorialLayout>
</template>
