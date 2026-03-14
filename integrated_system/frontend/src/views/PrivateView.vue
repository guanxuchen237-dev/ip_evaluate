<script setup lang="ts">
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import { Crown, TrendingUp, Shield, Star, Users, Sparkles } from 'lucide-vue-next'

const vipFeatures = [
  { title: '专属顾问', desc: '1对1投资咨询服务', icon: Users, color: 'chart-blue' },
  { title: '优先访问', desc: '提前获取新增IP数据', icon: Star, color: 'chart-yellow' },
  { title: '深度报告', desc: '定制化行业分析报告', icon: TrendingUp, color: 'chart-green' },
  { title: '风险预警', desc: '实时市场风险提醒', icon: Shield, color: 'chart-red' },
]

const benefits = [
  '无限次AI分析查询',
  '完整历史数据访问',
  '自定义数据导出',
  '线下活动邀请',
  '行业人脉对接',
  '投资机会推荐',
]
</script>

<template>
  <EditorialLayout>
    <!-- Hero Section -->
    <section class="px-8 py-20 max-w-5xl mx-auto text-center">
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0 }"
        class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-yellow-500/10 to-orange-500/10 border border-yellow-500/20 mb-8"
      >
        <Crown class="w-4 h-4 text-yellow-600" />
        <span class="text-sm text-yellow-700 font-medium">VIP Executive Board</span>
      </div>

      <h1 
        v-motion
        :initial="{ opacity: 0, y: 30 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 100 } }"
        class="editorial-headline text-6xl mb-6"
      >
        私董会<br>
        <span class="gradient-text">专属服务</span>
      </h1>

      <p 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0, transition: { delay: 200 } }"
        class="text-xl text-muted-foreground mb-12"
      >
        为高端投资人提供定制化IP评估与咨询服务
      </p>
    </section>

    <!-- Features Grid -->
    <section class="px-8 py-12 max-w-6xl mx-auto">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div 
          v-for="(feature, index) in vipFeatures"
          :key="feature.title"
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :visible="{ opacity: 1, y: 0, transition: { delay: index * 100 } }"
          class="editorial-card rounded-3xl p-6 hover:scale-105 transition-all"
        >
          <div :class="`w-14 h-14 rounded-2xl bg-${feature.color}/10 flex items-center justify-center mb-4`">
            <component :is="feature.icon" :class="`w-7 h-7 text-${feature.color}`" />
          </div>
          <h3 class="font-semibold text-foreground mb-2">{{ feature.title }}</h3>
          <p class="text-sm text-muted-foreground">{{ feature.desc }}</p>
        </div>
      </div>
    </section>

    <!-- Benefits List -->
    <section class="px-8 py-12 max-w-4xl mx-auto">
      <h2 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :visible="{ opacity: 1, y: 0 }"
        class="text-3xl font-serif font-bold text-center mb-12"
      >
        VIP会员权益
      </h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div 
          v-for="(benefit, index) in benefits"
          :key="benefit"
          v-motion
          :initial="{ opacity: 0, x: -20 }"
          :visible="{ opacity: 1, x: 0, transition: { delay: index * 80 } }"
          class="flex items-center gap-4 p-4 rounded-2xl bg-white/40"
        >
          <Sparkles class="w-5 h-5 text-primary flex-shrink-0" />
          <span class="text-foreground">{{ benefit }}</span>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="px-8 py-20 text-center">
      <button class="px-8 py-4 rounded-2xl bg-gradient-to-r from-yellow-500 to-orange-500 text-white font-semibold text-lg hover:scale-105 transition-all shadow-xl">
        申请加入私董会
      </button>
      <p class="text-sm text-muted-foreground mt-4">
        年费 ¥50,000 · 限额100名
      </p>
    </section>
  </EditorialLayout>
</template>
