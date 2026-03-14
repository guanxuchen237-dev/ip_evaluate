<script setup lang="ts">
import { 
  Database, 
  Cpu, 
  Layers, 
  Sparkles,
  ArrowRight,
  Cloud,
  FileSearch,
  Braces,
  Bot
} from 'lucide-vue-next'

const pipelineSteps = [
  {
    id: 1,
    title: '数据采集',
    titleEn: 'Collection',
    icon: Cloud,
    description: '混合爬虫策略',
    details: ['Requests + Selenium', '突破反爬机制', '多源数据整合'],
    color: 'chart-blue',
    status: 'active',
  },
  {
    id: 2,
    title: '预处理',
    titleEn: 'Preprocessing',
    icon: FileSearch,
    description: '清洗与增强',
    details: ['冷启动填充', '异常值检测', '数据标准化'],
    color: 'chart-cyan',
    status: 'active',
  },
  {
    id: 3,
    title: '向量化',
    titleEn: 'Vectorization',
    icon: Braces,
    description: '文本向量化',
    details: ['BERT嵌入', '语义理解', '归一化处理'],
    color: 'chart-purple',
    status: 'active',
  },
  {
    id: 4,
    title: '模型推理',
    titleEn: 'Inference',
    icon: Cpu,
    description: '多模型协同',
    details: ['XGBoost估值', 'NLP情感分析', '风险检测'],
    color: 'chart-green',
    status: 'active',
  },
  {
    id: 5,
    title: '智能体',
    titleEn: 'Agents',
    icon: Bot,
    description: '代理式AI',
    details: ['任务分解', '多智能体协作', '自主决策'],
    color: 'primary',
    status: 'active',
  },
]

const realtimeStats = [
  { label: '今日处理', value: '12,847', unit: '条' },
  { label: '平均延迟', value: '234', unit: 'ms' },
  { label: '准确率', value: '94.7', unit: '%' },
  { label: '活跃Agent', value: '7', unit: '个' },
]
</script>

<template>
  <div class="editorial-card rounded-3xl p-8 bg-gradient-to-br from-chart-cyan/5 to-chart-blue/5">
    <!-- Header -->
    <div class="flex items-start justify-between mb-8">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-chart-cyan/20 to-chart-blue/20 flex items-center justify-center">
          <Layers class="w-6 h-6 text-chart-cyan" />
        </div>
        <div>
          <h2 class="text-xl font-serif font-bold text-foreground">数据处理管线</h2>
          <p class="text-sm text-muted-foreground">Data Processing Pipeline</p>
        </div>
      </div>

      <!-- Live indicator -->
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-chart-green/10 border border-chart-green/20">
        <span class="w-2 h-2 bg-chart-green rounded-full animate-pulse" />
        <span class="text-xs font-medium text-chart-green">实时运行中</span>
      </div>
    </div>

    <!-- Realtime Stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <div 
        v-for="stat in realtimeStats" 
        :key="stat.label" 
        class="bg-white/40 backdrop-blur-sm rounded-2xl p-4 border border-white/30 text-center"
      >
        <p class="text-2xl font-bold text-foreground">
          {{ stat.value }}
          <span class="text-sm font-normal text-muted-foreground ml-1">{{ stat.unit }}</span>
        </p>
        <p class="text-xs text-muted-foreground mt-1">{{ stat.label }}</p>
      </div>
    </div>

    <!-- Pipeline Visualization -->
    <div class="relative">
      <!-- Connection line -->
      <div class="absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-chart-blue/30 via-chart-purple/30 to-chart-green/30 -translate-y-1/2 hidden md:block" />

      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div 
          v-for="(step, index) in pipelineSteps" 
          :key="step.id" 
          class="relative"
        >
          <!-- Arrow between steps (mobile) -->
          <div v-if="index < pipelineSteps.length - 1" class="absolute -bottom-2 left-1/2 -translate-x-1/2 md:hidden">
            <ArrowRight class="w-4 h-4 text-muted-foreground rotate-90" />
          </div>

          <div :class="`bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-white/30 relative z-10 h-full hover:bg-white/80 transition-all hover:scale-105 cursor-pointer group`">
            <!-- Icon -->
            <div :class="`w-10 h-10 rounded-xl bg-${step.color}/20 flex items-center justify-center mb-3 mx-auto group-hover:scale-110 transition-transform`">
              <component :is="step.icon" :class="`w-5 h-5 text-${step.color}`" />
            </div>

            <!-- Title -->
            <h3 class="font-medium text-foreground text-center mb-1">{{ step.title }}</h3>
            <p class="text-xs text-muted-foreground text-center mb-3">{{ step.titleEn }}</p>

           <!-- Description -->
            <p class="text-sm text-center text-primary mb-3">{{ step.description }}</p>

            <!-- Details -->
            <div class="space-y-1">
              <p 
                v-for="(detail, i) in step.details" 
                :key="i" 
                class="text-xs text-muted-foreground text-center"
              >
                • {{ detail }}
              </p>
            </div>

            <!-- Status indicator -->
            <div class="absolute -top-1 -right-1">
              <span class="w-3 h-3 rounded-full bg-chart-green block animate-pulse" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tech Stack -->
    <div class="mt-8 pt-6 border-t border-white/20">
      <div class="flex items-center justify-center gap-8 text-xs text-muted-foreground">
        <div class="flex items-center gap-2">
          <Database class="w-4 h-4" />
          <span>PostgreSQL + Redis</span>
        </div>
        <div class="flex items-center gap-2">
          <Cpu class="w-4 h-4" />
          <span>GPU加速推理</span>
        </div>
        <div class="flex items-center gap-2">
          <Sparkles class="w-4 h-4" />
          <span>实时流处理</span>
        </div>
      </div>
    </div>
  </div>
</template>
