<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { X, Sparkles, Brain, Zap, AlertTriangle, Target, TrendingUp } from 'lucide-vue-next'
import * as echarts from 'echarts'
import axios from 'axios'

const props = defineProps<{
  show: boolean
  book: any
}>()

const emit = defineEmits(['close'])

const loading = ref(true)
const report = ref<any>(null)
const chartRef = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null

const fetchReport = async () => {
    loading.value = true
    report.value = null
    try {
        const res = await axios.post('http://localhost:5000/api/ai/report', {
            title: props.book.title,
            abstract: props.book.abstract || '暂无简介'
        })
        report.value = res.data
        console.log('📊 Report data:', report.value)
        // 使用 nextTick 确保 DOM 更新后再初始化图表
        await nextTick()
        setTimeout(() => initChart(), 100) // 额外延迟确保渲染完成
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

const initChart = () => {
    if (!chartRef.value || !report.value?.radar_scores) return
    
    if (myChart) myChart.dispose()
    myChart = echarts.init(chartRef.value)
    
    const scores = report.value.radar_scores
    
    const option = {
        radar: {
            indicator: [
                { name: '创新力', max: 10 },
                { name: '故事性', max: 10 },
                { name: '人物塑造', max: 10 },
                { name: '世界观', max: 10 },
                { name: '商业价值', max: 10 }
            ],
            splitArea: {
                areaStyle: {
                    color: ['rgba(99,102,241,0.1)', 'rgba(99,102,241,0.2)']
                }
            }
        },
        series: [{
            type: 'radar',
            data: [{
                value: [
                    scores.innovation || 5,
                    scores.story || 5,
                    scores.character || 5,
                    scores.world || 5,
                    scores.commercial || 5
                ],
                name: 'AI 评分',
                areaStyle: {
                    color: 'rgba(99, 102, 241, 0.5)'
                },
                lineStyle: {
                    color: '#6366f1'
                }
            }]
        }]
    }
    myChart.setOption(option)
}

watch(() => props.show, (val) => {
    if (val && props.book) {
        fetchReport()
    }
})
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" @click="emit('close')"></div>
    
    <!-- Modal -->
    <div class="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden relative shadow-2xl flex flex-col animate-in fade-in zoom-in duration-300">
       
       <!-- Header -->
       <div class="p-6 border-b border-slate-100 flex justify-between items-center bg-gradient-to-r from-indigo-50 to-white">
          <div class="flex items-center gap-3">
             <div class="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center">
                <Sparkles class="w-6 h-6 text-indigo-600" />
             </div>
             <div>
                <h2 class="text-xl font-bold text-slate-900">智能书探报告</h2>
                <p class="text-sm text-slate-500">Target: 《{{ book?.title }}》</p>
             </div>
          </div>
          <button @click="emit('close')" class="p-2 hover:bg-slate-100 rounded-full transition-colors">
             <X class="w-5 h-5 text-slate-400" />
          </button>
       </div>

       <!-- Content -->
       <div class="flex-1 overflow-y-auto p-6 scrollbar-hide">
          
          <div v-if="loading" class="flex flex-col items-center justify-center h-64 gap-4">
             <div class="relative w-16 h-16">
                <div class="absolute inset-0 border-4 border-slate-100 rounded-full"></div>
                <div class="absolute inset-0 border-4 border-indigo-500 rounded-full border-t-transparent animate-spin"></div>
             </div>
             <p class="text-slate-500 font-medium animate-pulse">正在调用 NVIDIA GLM-4 进行深度分析...</p>
          </div>
          
          <div v-else class="flex flex-col lg:flex-row gap-8">
             <!-- Left: Scores & Chart -->
             <div class="w-full lg:w-1/3 flex flex-col gap-6">
                <div class="bg-indigo-50 rounded-xl p-4 border border-indigo-100">
                    <h3 class="text-sm font-bold text-indigo-900 mb-2 flex items-center gap-2">
                       <Brain class="w-4 h-4" /> AI 综合评分
                    </h3>
                    <div ref="chartRef" class="w-full h-64"></div>
                </div>
                
                <div class="bg-slate-50 p-4 rounded-xl border border-slate-100">
                   <h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">一句话简评</h4>
                   <p class="text-slate-800 font-medium leading-relaxed">{{ report.summary }}</p>
                </div>
             </div>

             <!-- Right: SWOT -->
             <div class="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Strengths -->
                <div class="bg-emerald-50/50 border border-emerald-100 rounded-xl p-4">
                   <h3 class="text-emerald-700 font-bold mb-3 flex items-center gap-2">
                      <Zap class="w-4 h-4" /> 核心优势 (Strengths)
                   </h3>
                   <ul class="space-y-2">
                      <li v-for="(item, i) in report.swot.strengths" :key="i" class="flex items-start gap-2 text-sm text-slate-700">
                         <span class="text-emerald-500 mt-0.5">✔</span> {{ item }}
                      </li>
                   </ul>
                </div>

                <!-- Weaknesses -->
                <div class="bg-rose-50/50 border border-rose-100 rounded-xl p-4">
                   <h3 class="text-rose-700 font-bold mb-3 flex items-center gap-2">
                      <AlertTriangle class="w-4 h-4" /> 潜在劣势 (Weaknesses)
                   </h3>
                   <ul class="space-y-2">
                       <li v-for="(item, i) in report.swot.weaknesses" :key="i" class="flex items-start gap-2 text-sm text-slate-700">
                         <span class="text-rose-400 mt-0.5">●</span> {{ item }}
                      </li>
                   </ul>
                </div>

                <!-- Opportunities -->
                <div class="bg-blue-50/50 border border-blue-100 rounded-xl p-4">
                   <h3 class="text-blue-700 font-bold mb-3 flex items-center gap-2">
                      <TrendingUp class="w-4 h-4" /> 市场机会 (Opportunities)
                   </h3>
                   <ul class="space-y-2">
                       <li v-for="(item, i) in report.swot.opportunities" :key="i" class="flex items-start gap-2 text-sm text-slate-700">
                         <span class="text-blue-400 mt-0.5">↗</span> {{ item }}
                      </li>
                   </ul>
                </div>

                <!-- Threats -->
                <div class="bg-amber-50/50 border border-amber-100 rounded-xl p-4">
                   <h3 class="text-amber-700 font-bold mb-3 flex items-center gap-2">
                      <Target class="w-4 h-4" /> 挑战与风险 (Threats)
                   </h3>
                    <ul class="space-y-2">
                       <li v-for="(item, i) in report.swot.threats" :key="i" class="flex items-start gap-2 text-sm text-slate-700">
                         <span class="text-amber-400 mt-0.5">!</span> {{ item }}
                      </li>
                   </ul>
                </div>
             </div>
          </div>
       </div>
    </div>
  </div>
</template>
