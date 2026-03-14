<script setup lang="ts">
import { ref } from 'vue'
import { 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Eye, 
  FileText, 
  Brain,
  TrendingUp,
  Shield,
  RefreshCw
} from 'lucide-vue-next'

// 模拟AI决策审计记录
const auditRecords = [
  {
    id: 1,
    timestamp: '2026-01-14 09:23:45',
    ipName: '《星际迷途》',
    decision: '推荐收购',
    riskLevel: 'low',
    confidence: 94,
    factors: ['情感共鸣强', '改编潜力高', '作者稳定'],
    status: 'approved',
    reviewer: '系统自动',
  },
  {
    id: 2,
    timestamp: '2026-01-14 08:15:32',
    ipName: '《暗夜行者》',
    decision: '风险预警',
    riskLevel: 'high',
    confidence: 87,
    factors: ['版权争议', '作者风险', '市场饱和'],
    status: 'flagged',
    reviewer: '人工复核中',
  },
  {
    id: 3,
    timestamp: '2026-01-14 07:42:18',
    ipName: '《云端恋曲》',
    decision: '观望建议',
    riskLevel: 'medium',
    confidence: 72,
    factors: ['题材新颖', '粉丝基础弱', '改编难度大'],
    status: 'pending',
    reviewer: '待确认',
  },
  {
    id: 4,
    timestamp: '2026-01-13 16:30:00',
    ipName: '《诡秘之主》',
    decision: '强烈推荐',
    riskLevel: 'low',
    confidence: 98,
    factors: ['世界观完整', '粉丝忠诚', '全球化潜力'],
    status: 'approved',
    reviewer: '系统自动',
  },
]

// 审计统计
const auditStats = [
  { label: '今日审计', value: '47', icon: FileText, color: 'text-chart-blue' },
  { label: '高风险预警', value: '3', icon: AlertTriangle, color: 'text-chart-red' },
  { label: '自动通过', value: '38', icon: CheckCircle, color: 'text-chart-green' },
  { label: '待人工复核', value: '6', icon: Clock, color: 'text-chart-yellow' },
]

const selectedRecord = ref<number | null>(null)

const getRiskColor = (level: string) => {
  switch (level) {
    case 'low': return 'text-chart-green bg-chart-green/10'
    case 'medium': return 'text-chart-yellow bg-chart-yellow/10'
    case 'high': return 'text-chart-red bg-chart-red/10'
    default: return 'text-muted-foreground bg-muted'
  }
}

const getStatusBadge = (status: string) => {
  const badges = {
    approved: { icon: CheckCircle, text: '已通过', color: 'bg-chart-green/10 text-chart-green' },
    flagged: { icon: AlertTriangle, text: '已标记', color: 'bg-chart-red/10 text-chart-red' },
    pending: { icon: Clock, text: '待处理', color: 'bg-chart-yellow/10 text-chart-yellow' },
  }
  return badges[status as keyof typeof badges] || null
}
</script>

<template>
  <div class="editorial-card rounded-3xl p-8 bg-gradient-to-br from-chart-blue/5 to-chart-purple/5">
    <!-- Header -->
    <div class="flex items-start justify-between mb-8">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-chart-blue/20 to-chart-purple/20 flex items-center justify-center">
          <Brain class="w-6 h-6 text-chart-blue" />
        </div>
        <div>
          <h2 class="text-xl font-serif font-bold text-foreground">AI决策审计中心</h2>
          <p class="text-sm text-muted-foreground">AI Decision Audit Center</p>
        </div>
      </div>

      <button class="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/60 backdrop-blur border border-white/30 text-sm text-foreground hover:bg-white/80 transition-colors">
        <RefreshCw class="w-4 h-4" />
        刷新
      </button>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div 
        v-for="stat in auditStats" 
        :key="stat.label" 
        class="bg-white/40 backdrop-blur-sm rounded-2xl p-4 border border-white/30"
      >
        <div class="flex items-center gap-2 mb-2">
          <component :is="stat.icon" :class="`w-4 h-4 ${stat.color}`" />
          <span class="text-xs text-muted-foreground">{{ stat.label }}</span>
        </div>
        <p class="text-2xl font-bold text-foreground">{{ stat.value }}</p>
      </div>
    </div>

    <!-- Audit Records -->
    <div class="space-y-3">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-medium text-foreground">最近审计记录</h3>
        <button class="text-sm text-primary hover:underline">查看全部</button>
      </div>

      <div 
        v-for="record in auditRecords"
        :key="record.id"
        @click="selectedRecord = selectedRecord === record.id ? null : record.id"
        :class="[
          'bg-white/50 backdrop-blur-sm rounded-2xl p-4 border border-white/30 cursor-pointer transition-all hover:bg-white/70',
          selectedRecord === record.id ? 'ring-2 ring-primary/30' : ''
        ]"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-3 mb-2">
              <span class="font-medium text-foreground">{{ record.ipName }}</span>
              <span :class="['px-2 py-0.5 rounded-full text-xs font-medium', getRiskColor(record.riskLevel)]">
                {{ record.riskLevel === 'low' ? '低风险' : record.riskLevel === 'medium' ? '中风险' : '高风险' }}
              </span>
              <span 
                v-if="getStatusBadge(record.status)"
                :class="[
                  'px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1',
                  getStatusBadge(record.status)!.color
                ]"
              >
                <component :is="getStatusBadge(record.status)!.icon" class="w-3 h-3" />
                {{ getStatusBadge(record.status)!.text }}
              </span>
            </div>

            <div class="flex items-center gap-4 text-sm text-muted-foreground">
              <span class="flex items-center gap-1">
                <TrendingUp class="w-3 h-3" />
                {{ record.decision }}
              </span>
              <span class="flex items-center gap-1">
                <Shield class="w-3 h-3" />
                置信度 {{ record.confidence }}%
              </span>
              <span>{{ record.timestamp }}</span>
            </div>
          </div>

          <button class="p-2 rounded-lg hover:bg-white/50 transition-colors">
            <Eye class="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        <!-- Expanded details -->
        <div v-if="selectedRecord === record.id" class="mt-4 pt-4 border-t border-white/30">
          <p class="text-sm text-muted-foreground mb-2">决策因素:</p>
          <div class="flex flex-wrap gap-2">
            <span 
              v-for="(factor, i) in record.factors" 
              :key="i" 
              class="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs"
            >
              {{ factor }}
            </span>
          </div>
          <p class="text-sm text-muted-foreground mt-3">
            复核状态: <span class="text-foreground">{{ record.reviewer }}</span>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
