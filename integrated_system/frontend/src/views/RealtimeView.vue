<script setup lang="ts">
import EditorialLayout from '@/components/layout/EditorialLayout.vue'
import { Activity, TrendingUp, Users, Clock, Zap, AlertCircle, Flame } from 'lucide-vue-next'

const realtimeMetrics = [
  { label: '实时访问', value: '2,847', unit: '人', icon: Users, color: 'chart-blue', trend: '+12%' },
  { label: '热度峰值', value: '98.5', unit: '/100', icon: Flame, color: 'chart-red', trend: '+5.3%' },
  { label: '评论增速', value: '1.2K', unit: '/h', icon: TrendingUp, color: 'chart-green', trend: '+8%' },
  { label: '系统延迟', value: '124', unit: 'ms', icon: Zap, color: 'chart-yellow', trend: '-3ms' },
]

const systemStatus = [
 { service: '数据采集', status: 'active', uptime: '99.9%' },
  { service: 'AI模型', status: 'active', uptime: '99.7%' },
  { service: '知识图谱', status: 'active', uptime: '100%' },
  { service: '缓存服务', status: 'warning', uptime: '98.2%' },
]
</script>

<template>
  <EditorialLayout>
    <div class="min-h-screen px-8 py-12">
      <!-- Header -->
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :enter="{ opacity: 1, y: 0 }"
        class="mb-12"
      >
        <div class="flex items-center gap-3 mb-2">
          <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-chart-red/20 to-chart-yellow/20 flex items-center justify-center">
            <Activity class="w-6 h-6 text-chart-red" />
          </div>
          <div>
            <h1 class="text-4xl font-serif font-bold text-foreground">Real-time Dashboard</h1>
            <p class="text-muted-foreground">实时数据监控 · Live Metrics</p>
          </div>
        </div>
      </div>

      <!-- Metrics Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div 
          v-for="(metric, index) in realtimeMetrics"
          :key="metric.label"
          v-motion
          :initial="{ opacity: 0, y: 20 }"
          :visible="{ opacity: 1, y: 0, transition: { delay: index * 100 } }"
          class="editorial-card rounded-3xl p-6 hover:scale-105 transition-all"
        >
          <div class="flex items-start justify-between mb-4">
            <component :is="metric.icon" :class="`w-8 h-8 text-${metric.color}`" />
            <span :class="`text-xs font-medium text-${metric.color}`">{{ metric.trend }}</span>
          </div>
          <p class="text-3xl font-bold text-foreground mb-1">
            {{ metric.value }}<span class="text-sm text-muted-foreground ml-1">{{ metric.unit }}</span>
          </p>
          <p class="text-xs text-muted-foreground">{{ metric.label }}</p>
        </div>
      </div>

      <!-- System Status -->
      <div 
        v-motion
        :initial="{ opacity: 0, y: 20 }"
        :visible="{ opacity: 1, y: 0, transition: { delay: 400 } }"
        class="editorial-card rounded-3xl p-6 mb-8"
      >
        <h2 class="text-lg font-semibold text-foreground mb-6">System Status</h2>
        <div class="space-y-3">
          <div 
            v-for="service in systemStatus"
            :key="service.service"
            class="flex items-center justify-between p-4 rounded-xl bg-white/40"
          >
            <div class="flex items-center gap-3">
              <div :class="[
                'w-2 h-2 rounded-full',
                service.status === 'active' ? 'bg-chart-green animate-pulse' : 'bg-chart-yellow'
              ]" />
              <span class="font-medium text-foreground">{{ service.service }}</span>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-sm text-muted-foreground">Uptime: {{ service.uptime }}</span>
              <span :class="[
                'px-3 py-1 rounded-full text-xs font-medium',
                service.status === 'active' 
                  ? 'bg-chart-green/10 text-chart-green'
                  : 'bg-chart-yellow/10 text-chart-yellow'
              ]">
                {{ service.status === 'active' ? '运行中' : '警告' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </EditorialLayout>
</template>
