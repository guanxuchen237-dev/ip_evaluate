<script setup lang="ts">
import { DollarSign, TrendingUp, TrendingDown, Minus, History, Target } from 'lucide-vue-next'

interface PriceRange {
  min: number
  max: number
  estimated: number
  confidence: number
}

interface ComparableIP {
  name: string
  transactionYear: number
  price: number
  similarity: number
}

const priceData: PriceRange = {
  min: 8000,
  max: 15000,
  estimated: 12000,
  confidence: 87,
}

const comparables: ComparableIP[] = [
  { name: '斗罗大陆', transactionYear: 2020, price: 12000, similarity: 85 },
  { name: '斗破苍穹', transactionYear: 2019, price: 10000, similarity: 78 },
  { name: '凡人修仙传', transactionYear: 2021, price: 8500, similarity: 72 },
  { name: '雪中悍刀行', transactionYear: 2022, price: 15000, similarity: 68 },
]

const factors = [
  { name: '粉丝基数', impact: 'positive', value: '+15%' },
  { name: '改编难度', impact: 'negative', value: '-8%' },
  { name: '市场热度', impact: 'positive', value: '+12%' },
  { name: '原创性', impact: 'positive', value: '+20%' },
  { name: '作者配合度', impact: 'neutral', value: '0%' },
]

const getImpactIcon = (impact: string) => {
  switch (impact) {
    case 'positive': return TrendingUp
    case 'negative': return TrendingDown
    default: return Minus
  }
}

const getImpactColor = (impact: string) => {
  switch (impact) {
    case 'positive': return 'text-chart-green'
    case 'negative': return 'text-chart-red'
    default: return 'text-muted-foreground'
  }
}
</script>

<template>
  <div class="editorial-card rounded-3xl p-8">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-8">
      <div class="w-10 h-10 rounded-xl bg-chart-yellow/10 flex items-center justify-center">
        <DollarSign class="w-5 h-5 text-chart-yellow" />
      </div>
      <div>
        <h3 class="editorial-headline text-xl text-foreground">Copyright Valuation</h3>
        <p class="text-sm text-muted-foreground">智能版权估值系统 · XGBoost驱动</p>
      </div>
    </div>

    <!-- Price estimate -->
    <div class="grid grid-cols-3 gap-6 mb-8">
      <div class="text-center p-4 rounded-2xl bg-white/40 border border-white/30">
        <p class="text-xs text-muted-foreground mb-1">最低估值</p>
        <p class="text-2xl font-serif font-bold text-foreground">¥{{ priceData.min.toLocaleString() }}万</p>
      </div>
      <div class="text-center p-6 rounded-2xl bg-gradient-to-br from-chart-yellow/20 to-chart-yellow/5 border border-chart-yellow/20">
        <p class="text-xs text-chart-yellow font-medium mb-1">AI建议价</p>
        <p class="text-3xl font-serif font-bold text-foreground">¥{{ priceData.estimated.toLocaleString() }}万</p>
        <p class="text-xs text-muted-foreground mt-1">置信度 {{ priceData.confidence }}%</p>
      </div>
      <div class="text-center p-4 rounded-2xl bg-white/40 border border-white/30">
        <p class="text-xs text-muted-foreground mb-1">最高估值</p>
        <p class="text-2xl font-serif font-bold text-foreground">¥{{ priceData.max.toLocaleString() }}万</p>
      </div>
    </div>

    <!-- Comparable transactions -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-4">
        <History class="w-4 h-4 text-muted-foreground" />
        <span class="text-sm font-medium text-foreground">可比交易案例</span>
      </div>
      <div class="space-y-2">
        <div 
          v-for="comp in comparables"
          :key="comp.name"
          class="flex items-center justify-between p-3 rounded-xl bg-white/30 hover:bg-white/50 transition-all"
        >
          <div class="flex items-center gap-3">
            <span class="text-sm font-medium text-foreground">{{ comp.name }}</span>
            <span class="text-xs text-muted-foreground">{{ comp.transactionYear }}</span>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-sm text-muted-foreground">相似度 {{ comp.similarity }}%</span>
            <span class="text-sm font-serif font-bold text-foreground">¥{{ comp.price.toLocaleString() }}万</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Price factors -->
    <div>
      <div class="flex items-center gap-2 mb-4">
        <Target class="w-4 h-4 text-muted-foreground" />
        <span class="text-sm font-medium text-foreground">价格影响因子</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <div 
          v-for="factor in factors"
          :key="factor.name"
          class="flex items-center gap-2 px-3 py-2 rounded-full bg-white/40 border border-white/30"
        >
          <component :is="getImpactIcon(factor.impact)" class="w-4 h-4" :class="getImpactColor(factor.impact)" />
          <span class="text-sm text-foreground">{{ factor.name }}</span>
          <span class="text-xs font-medium" :class="getImpactColor(factor.impact)">{{ factor.value }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
