<script setup lang="ts">
import { Shield, AlertTriangle, FileSearch, User, Copyright, Scale, CheckCircle, XCircle } from 'lucide-vue-next'

interface RiskItem {
  category: string
  categoryCn: string
  status: 'safe' | 'warning' | 'danger'
  score: number
  details: string
  icon: any
}

const riskData: RiskItem[] = [
  {
    category: 'Content Compliance',
    categoryCn: '内容合规性',
    status: 'safe',
    score: 95,
    details: '未检测到敏感内容',
    icon: Shield,
  },
  {
    category: 'Plagiarism Check',
    categoryCn: '抄袭检测',
    status: 'safe',
    score: 98,
    details: '原创度极高，相似度<2%',
    icon: FileSearch,
  },
  {
    category: 'Author Risk',
    categoryCn: '作者风险',
    status: 'warning',
    score: 72,
    details: '作者更新频率有波动',
    icon: User,
  },
  {
    category: 'Copyright Clarity',
    categoryCn: '版权清晰度',
    status: 'safe',
    score: 100,
    details: '版权归属明确，无纠纷',
    icon: Copyright,
  },
  {
    category: 'Legal Sensitivity',
    categoryCn: '法律敏感性',
    status: 'safe',
    score: 88,
    details: '不涉及敏感历史事件',
    icon: Scale,
  },
]

const overallScore = Math.round(riskData.reduce((acc, r) => acc + r.score, 0) / riskData.length)
const hasWarning = riskData.some(r => r.status === 'warning')
const hasDanger = riskData.some(r => r.status === 'danger')

const getStatusColor = (status: RiskItem['status']) => {
  switch (status) {
    case 'safe': return 'text-chart-green bg-chart-green/10'
    case 'warning': return 'text-chart-yellow bg-chart-yellow/10'
    case 'danger': return 'text-chart-red bg-chart-red/10'
  }
}

const getStatusIcon = (status: RiskItem['status']) => {
  switch (status) {
    case 'safe': return CheckCircle
    case 'warning': return AlertTriangle
    case 'danger': return XCircle
  }
}
</script>

<template>
  <div class="editorial-card rounded-3xl p-8">
    <!-- Header -->
    <div class="flex items-start justify-between mb-8">
      <div>
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-xl bg-chart-red/10 flex items-center justify-center">
            <Shield class="w-5 h-5 text-chart-red" />
          </div>
          <div>
            <h3 class="editorial-headline text-xl text-foreground">Risk Radar</h3>
            <p class="text-sm text-muted-foreground">风险"熔断"雷达</p>
          </div>
        </div>
      </div>

      <!-- Overall status -->
      <div class="text-right">
        <div :class="[
          'inline-flex items-center gap-2 px-4 py-2 rounded-full',
          hasDanger ? 'bg-chart-red/10 text-chart-red' :
          hasWarning ? 'bg-chart-yellow/10 text-chart-yellow' :
          'bg-chart-green/10 text-chart-green'
        ]">
          <component 
            :is="hasDanger ? XCircle : hasWarning ? AlertTriangle : CheckCircle"
            class="w-4 h-4"
          />
          <span class="font-medium text-sm">
            {{ hasDanger ? '高风险' : hasWarning ? '需关注' : '安全' }}
          </span>
        </div>
        <p class="text-3xl font-serif font-bold text-foreground mt-2">{{ overallScore }}</p>
        <p class="text-xs text-muted-foreground">综合安全分</p>
      </div>
    </div>

    <!-- Risk items -->
    <div class="space-y-4">
      <div 
        v-for="(risk, index) in riskData"
        :key="risk.category"
        class="flex items-center gap-4 p-4 rounded-2xl bg-white/40 backdrop-blur border border-white/30 hover:bg-white/60 transition-all group"
        :style="{ animationDelay: `${index * 100}ms` }"
      >
        <div :class="[
          'w-10 h-10 rounded-xl flex items-center justify-center',
          getStatusColor(risk.status)
        ]">
          <component :is="risk.icon" class="w-5 h-5" />
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <span class="font-medium text-foreground">{{ risk.categoryCn }}</span>
            <span class="text-xs text-muted-foreground">{{ risk.category }}</span>
          </div>
          <p class="text-sm text-muted-foreground truncate">{{ risk.details }}</p>
        </div>

        <div class="flex items-center gap-3">
          <div class="text-right">
            <p class="text-lg font-serif font-bold text-foreground">{{ risk.score }}</p>
          </div>
          <div :class="[
            'p-1.5 rounded-lg',
            getStatusColor(risk.status)
          ]">
            <component :is="getStatusIcon(risk.status)" class="w-4 h-4" />
          </div>
        </div>
      </div>
    </div>

    <!-- AI Audit note -->
    <div class="mt-6 p-4 rounded-2xl bg-gradient-to-r from-primary/5 to-accent/5 border border-primary/10">
      <p class="text-xs text-muted-foreground">
        <span class="text-primary font-medium">AI决策审计中心：</span>
        所有风险判断均已记录，支持事后审计和反馈学习
      </p>
    </div>
  </div>
</template>
