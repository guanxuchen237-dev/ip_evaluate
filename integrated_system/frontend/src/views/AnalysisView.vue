<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import NarrativeEKG from '@/components/analysis/NarrativeEKG.vue'
import DimensionRadar from '@/components/analysis/DimensionRadar.vue'
import AgentWarRoom from '@/components/analysis/AgentWarRoom.vue'
import RiskRadar from '@/components/analysis/RiskRadar.vue'
import CopyrightPricing from '@/components/analysis/CopyrightPricing.vue'
import HealingIndex from '@/components/analysis/HealingIndex.vue'
import GlobalPotential from '@/components/analysis/GlobalPotential.vue'
import DataPipeline from '@/components/analysis/DataPipeline.vue'
import AIAuditCenter from '@/components/analysis/AIAuditCenter.vue'
import { BookMarked, Flame, Users, Clock, ArrowLeft, Star } from 'lucide-vue-next'

const router = useRouter()
const activeTab = ref('overview')

const quickStats = [
  { label: 'Chapters', value: '1,432', icon: BookMarked },
  { label: 'Words', value: '4.8M', icon: Clock },
  { label: 'Followers', value: '2.1M', icon: Users },
  { label: 'Heat', value: '96.5', icon: Flame },
]

const tabs = [
  { id: 'overview', label: '概览', labelEn: 'Overview' },
  { id: 'risk', label: '风险评估', labelEn: 'Risk' },
  { id: 'value', label: '价值估算', labelEn: 'Valuation' },
  { id: 'global', label: '全球化', labelEn: 'Global' },
  { id: 'audit', label: 'AI审计', labelEn: 'Audit' },
]
</script>

<template>
  <EditorialLayout>
    <!-- Hero Header -->
    <section class="px-8 pt-12 pb-8 max-w-7xl mx-auto">
      <!-- Back button -->
      <button 
        @click="router.back()"
        class="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-8 group"
      >
        <ArrowLeft class="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
        <span class="text-sm">Back to search</span>
      </button>

      <div class="grid grid-cols-12 gap-8 items-start">
        <!-- Left - Title and info -->
        <div class="col-span-12 lg:col-span-7">
          <div class="flex items-center gap-3 mb-4">
            <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium hover:scale-105 transition-transform cursor-pointer">
              奇幻悬疑
            </span>
            <span class="px-3 py-1 rounded-full bg-green-100 text-green-600 text-sm font-medium hover:scale-105 transition-transform cursor-pointer">
              安全
            </span>
          </div>

          <h1 class="editorial-headline text-5xl md:text-7xl text-foreground mb-4">
            诡秘之主
          </h1>

          <p class="text-xl text-muted-foreground mb-6">
            by <span class="text-foreground font-medium">爱潜水的乌贼</span>
          </p>

          <!-- Rating -->
          <div class="flex items-center gap-4 mb-8">
            <div class="flex items-center gap-1">
              <Star 
                v-for="star in 5" 
                :key="star"
                class="w-5 h-5 fill-yellow-400 text-yellow-400"
              />
            </div>
            <span class="text-2xl font-serif font-bold text-foreground">9.5</span>
            <span class="text-muted-foreground">/10</span>
          </div>

          <!-- Quick stats -->
          <div class="flex flex-wrap gap-6">
            <div 
              v-for="stat in quickStats" 
              :key="stat.label"
              class="text-center cursor-pointer hover:scale-110 hover:-translate-y-1 transition-all"
            >
              <p class="text-2xl font-serif font-bold text-foreground">{{ stat.value }}</p>
              <p class="text-xs text-muted-foreground uppercase tracking-wider">{{ stat.label }}</p>
            </div>
          </div>
        </div>

        <!-- Right - Score card -->
        <div class="col-span-12 lg:col-span-5">
          <div class="editorial-card rounded-3xl p-8 hero-shadow hover:scale-102 hover:-translate-y-2 transition-all">
            <p class="text-sm text-muted-foreground mb-2">AI 综合评估</p>
            <p class="text-6xl font-serif font-bold gradient-text mb-4">A+</p>
            <p class="text-sm text-muted-foreground mb-6">
              Top 0.3% in Fantasy Genre
            </p>
            <div class="space-y-3">
              <div 
                v-for="item in [
                  { label: '商业价值', value: '极高', color: 'text-foreground' },
                  { label: '改编难度', value: '中等', color: 'text-foreground' },
                  { label: '风险系数', value: '低', color: 'text-green-600' },
                  { label: '治愈指数', value: '83', color: 'text-purple-600' },
                  { label: '全球化潜力', value: '76%', color: 'text-blue-600' },
                ]"
                :key="item.label"
                class="flex justify-between text-sm"
              >
                <span class="text-muted-foreground">{{ item.label }}</span>
                <span :class="`font-medium ${item.color}`">{{ item.value }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Tab Navigation -->
    <section class="px-8 py-4 max-w-7xl mx-auto">
      <div class="flex items-center gap-2 overflow-x-auto pb-2">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'px-6 py-3 rounded-2xl text-sm font-medium whitespace-nowrap transition-all hover:scale-105',
            activeTab === tab.id
              ? 'bg-foreground text-background'
              : 'bg-white/60 backdrop-blur border border-white/40 text-foreground hover:bg-white/80'
          ]"
        >
          {{ tab.label }}
          <span class="text-xs ml-2 opacity-60">{{ tab.labelEn }}</span>
        </button>
      </div>
    </section>

    <!-- Tab Content -->
    <div class="min-h-screen">
      <!-- Overview Tab -->
      <div v-if="activeTab === 'overview'">
        <!-- Analysis Charts - Asymmetric -->
        <section class="px-8 py-8 max-w-7xl mx-auto">
          <div class="grid grid-cols-12 gap-8">
            <!-- Narrative EKG - Wide -->
            <div class="col-span-12 lg:col-span-7">
              <div class="editorial-card rounded-3xl p-8 hover:scale-101 transition-all">
                <h2 class="editorial-headline text-2xl text-foreground mb-2">Narrative EKG</h2>
                <p class="text-muted-foreground mb-6">叙事心电图 · 情节张力分析</p>
                <NarrativeEKG />
              </div>
            </div>

            <!-- Radar - Compact -->
            <div class="col-span-12 lg:col-span-5">
              <div class="editorial-card rounded-3xl p-8 h-full hover:scale-101 transition-all">
                <h2 class="editorial-headline text-2xl text-foreground mb-2">六维评估</h2>
                <p class="text-muted-foreground mb-4">Dimension Analysis</p>
                <DimensionRadar />
              </div>
            </div>
          </div>
        </section>

        <!-- Agent War Room -->
        <section class="px-8 py-8 max-w-7xl mx-auto">
          <AgentWarRoom />
        </section>

        <!-- Key Insights -->
        <section class="px-8 py-8 max-w-7xl mx-auto">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div 
              v-for="insight in [
                { color: 'green', title: 'Strengths', content: '独特的克苏鲁+蒸汽朋克世界观，角色塑造极为出色' },
                { color: 'yellow', title: 'Opportunities', content: '影视改编潜力巨大，适合打造系列IP矩阵' },
                { color: 'blue', title: 'Recommendation', content: '优先开发动画或游戏，实拍剧集需谨慎评估' },
              ]"
              :key="insight.title"
              :class="`editorial-card rounded-3xl p-8 bg-gradient-to-br from-${insight.color}-50 to-${insight.color}-100/50 hover:scale-102 hover:-translate-y-1 transition-all`"
            >
              <p :class="`text-sm font-medium text-${insight.color}-600 mb-4 uppercase tracking-wider`">
                {{ insight.title }}
              </p>
              <p class="text-lg font-serif text-foreground leading-relaxed">
                {{ insight.content }}
              </p>
            </div>
          </div>
        </section>
      </div>

      <!-- Risk Tab -->
      <section v-if="activeTab === 'risk'" class="px-8 py-8 max-w-7xl mx-auto">
        <div class="grid grid-cols-12 gap-8">
          <div class="col-span-12 lg:col-span-7">
            <RiskRadar />
          </div>
          <div class="col-span-12 lg:col-span-5">
            <HealingIndex />
          </div>
        </div>
      </section>

      <!-- Value Tab -->
      <section v-if="activeTab === 'value'" class="px-8 py-8 max-w-7xl mx-auto">
        <CopyrightPricing />
      </section>

      <!-- Global Tab -->
      <section v-if="activeTab === 'global'" class="px-8 py-8 max-w-7xl mx-auto">
        <GlobalPotential />
      </section>

      <!-- Audit Tab -->
      <section v-if="activeTab === 'audit'" class="px-8 py-8 max-w-7xl mx-auto space-y-8">
        <DataPipeline />
        <AIAuditCenter />
      </section>
    </div>

    <!-- Bottom padding for dock -->
    <div class="h-24" />
  </EditorialLayout>
</template>
