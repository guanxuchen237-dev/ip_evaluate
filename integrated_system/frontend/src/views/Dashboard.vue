<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from "vue";
import * as echarts from 'echarts'
import { useRouter } from "vue-router";
import { 
  BookOpen, Zap, TrendingUp, Sparkles, Brain, ArrowRight, MessageCircle, 
  Globe, Users, BarChart3, MapPin, Crown, Award,
  Radar, Cloud, Grid3X3, FileText, LineChart, PieChart
} from "lucide-vue-next";
import EditorialLayout from "@/components/layout/EditorialLayout.vue";
import CategoryPie from "@/components/charts/CategoryPie.vue";
import WordCloud from "@/components/charts/WordCloud.vue";
import RadarChart from "@/components/charts/RadarChart.vue";
import AuthorPyramid from "@/components/charts/AuthorPyramid.vue";
import GeoMap from "@/components/charts/GeoMap.vue";
import CorrelationHeatmap from "@/components/charts/CorrelationHeatmap.vue";
import ScoreDistribution from "@/components/charts/ScoreDistribution.vue";
import MultiTicketTrend from "@/components/charts/MultiTicketTrend.vue";
import PlatformBarChart from "@/components/charts/PlatformBarChart.vue";
import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';
const router = useRouter();

// 统计数据
const stats = ref([
  { title: "书库总量", value: "-", unit: "本", icon: BookOpen, color: "from-blue-500 to-indigo-600" },
  { title: "平均IP指数", value: "-", unit: "分", icon: Zap, color: "from-amber-500 to-orange-600" },
  { title: "收录作者", value: "-", unit: "位", icon: Users, color: "from-emerald-500 to-teal-600" },
  { title: "评论总量", value: "-", unit: "条", icon: MessageCircle, color: "from-rose-500 to-pink-600" },
]);

// ==================== 专业可视化分析面板数据 ====================

// 六维度雷达图数据
const radarData = ref<any>({
  dimension_names: ['内容质量', '商业价值', '读者粘性', '更新稳定性', '市场潜力', 'IP延展性'],
  qidian: { total_books: 0, dimensions: [0, 0, 0, 0, 0, 0] },
  zongheng: { total_books: 0, dimensions: [0, 0, 0, 0, 0, 0] },
  top_books: []
})
const radarLoading = ref(false)
const radarChartRef = ref<HTMLElement | null>(null)
let radarChart: any = null

// jieba词云数据
const wordcloudData = ref<any[]>([])
const wordcloudLoading = ref(false)

// 维度相关性热力图数据
const correlationData = ref<any>({
  dimension_names: ['内容质量', '商业价值', '读者粘性', '更新稳定性', '市场潜力', 'IP延展性'],
  matrix: [[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0], [0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 1, 0], [0, 0, 0, 0, 0, 1]],
  sample_size: 0
})
const correlationLoading = ref(false)

// 平台类型分布数据
const categoryData = ref<any[]>([])
const categoryLoading = ref(false)
const platformTotals = ref({ qidian: 0, zongheng: 0 })

// 实时月票排名
const realtimeTicketRanking = ref<any[]>([])
const realtimeRankingLoading = ref(false)
const ticketPlatform = ref<'qidian' | 'zongheng'>('qidian')

// 切换月票平台
const switchTicketPlatform = async (platform: 'qidian' | 'zongheng') => {
  ticketPlatform.value = platform
  realtimeRankingLoading.value = true
  try {
    const resTicket = await axios.get(`${API_BASE}/charts/ticket_top?limit=10&platform=${platform}`)
    if (resTicket.data && Array.isArray(resTicket.data)) {
      realtimeTicketRanking.value = resTicket.data
    }
  } finally {
    realtimeRankingLoading.value = false
  }
}

// 平台数据
const platformData = ref({ qidian: { value: 0, percent: 10 }, zongheng: { value: 0, percent: 10 } });

// 格式化大数字（精确版）
const formatNum = (n: number) => {
  if (n >= 10000) return (n / 10000).toFixed(2) + '万';
  return n.toLocaleString();
};

const fetchData = async () => {
  try {
    // 1. 总览统计
    const resStats = await axios.get(`${API_BASE}/stats/overview`);
    if (resStats.data) {
      stats.value[0]!.value = (resStats.data.total_novels || 0).toLocaleString();
      stats.value[1]!.value = (resStats.data.avg_ip_score || 0).toString();
      stats.value[2]!.value = (resStats.data.total_authors || 0).toLocaleString();
      stats.value[3]!.value = '11万+'; // 评论数据来自纵横，约11万条
    }

    // 2. 平台分布
    const resPlat = await axios.get(`${API_BASE}/charts/platform`);
    if (resPlat.data && Array.isArray(resPlat.data)) {
      const qd = resPlat.data.find((i: any) => i.name === '起点' || i.name === 'Qidian')?.value || 0;
      const zh = resPlat.data.find((i: any) => i.name === '纵横' || i.name === 'Zongheng')?.value || 0;
      const max = Math.max(qd, zh, 1);
      platformData.value = {
        qidian: { value: qd, percent: Math.max((qd / max) * 85, 10) },
        zongheng: { value: zh, percent: Math.max((zh / max) * 85, 10) }
      };
    }

    // 3. 月票排行 - 使用实时排名数据
    realtimeRankingLoading.value = true;
    try {
      const resTicket = await axios.get(`${API_BASE}/charts/ticket_top?limit=10&platform=${ticketPlatform.value}`);
      if (resTicket.data && Array.isArray(resTicket.data)) {
        realtimeTicketRanking.value = resTicket.data;
      }
    } finally {
      realtimeRankingLoading.value = false;
    }
  } catch (e) {
    console.error("Dashboard Data Fetch Error", e);
  }
};

onMounted(() => {
  fetchData();
  fetchAllAnalytics();
});

// ==================== 数据获取函数 ====================

// 获取六维度雷达图数据
async function fetchRadarData() {
  radarLoading.value = true
  try {
    const res = await axios.get(`${API_BASE}/admin/six_dimensions_radar`)
    console.log('雷达图API返回:', res.data)
    if (res.data && res.data.status === 'success') {
      radarData.value = res.data
      console.log('雷达图数据已更新:', radarData.value)
    } else {
      console.warn('雷达图API返回异常:', res.data)
    }
  } catch (e) { 
    console.error('获取雷达图数据失败', e) 
  }
  finally { 
    radarLoading.value = false 
    // DOM更新后再初始化图表
    await nextTick()
    initRadarChart()
  }
}

// 初始化雷达图
function initRadarChart() {
  if (!radarChartRef.value) {
    console.warn('雷达图DOM元素不存在')
    return
  }
  
  if (radarChart) {
    radarChart.dispose()
  }
  
  radarChart = echarts.init(radarChartRef.value)
  
  const option = {
    tooltip: {
      trigger: 'item',
      formatter: function(params: any) {
        const dims = radarData.value.dimension_names
        const values = params.value
        let html = `<div style="font-weight:bold;margin-bottom:5px">${params.name}</div>`
        dims.forEach((dim: string, idx: number) => {
          html += `<div style="display:flex;justify-content:space-between;gap:15px">
            <span>${dim}:</span>
            <span style="font-weight:bold">${values[idx]}</span>
          </div>`
        })
        return html
      }
    },
    legend: {
      data: ['起点', '纵横'],
      bottom: 0,
      textStyle: { fontSize: 11 }
    },
    radar: {
      indicator: radarData.value.dimension_names.map((name: string) => ({
        name,
        max: 100
      })),
      radius: '65%',
      center: ['50%', '45%'],
      splitNumber: 4,
      axisName: {
        fontSize: 10,
        color: '#64748b'
      },
      splitLine: {
        lineStyle: { color: '#e2e8f0' }
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(248,250,252,0.5)', 'rgba(241,245,249,0.3)']
        }
      },
      axisLine: {
        lineStyle: { color: '#e2e8f0' }
      }
    },
    series: [{
      type: 'radar',
      data: [
        {
          value: radarData.value.qidian?.dimensions || [0,0,0,0,0,0],
          name: '起点',
          areaStyle: { color: 'rgba(99, 102, 241, 0.2)' },
          lineStyle: { color: '#6366f1', width: 2 },
          itemStyle: { color: '#6366f1' }
        },
        {
          value: radarData.value.zongheng?.dimensions || [0,0,0,0,0,0],
          name: '纵横',
          areaStyle: { color: 'rgba(59, 130, 246, 0.2)' },
          lineStyle: { color: '#3b82f6', width: 2 },
          itemStyle: { color: '#3b82f6' }
        }
      ]
    }]
  }
  
  radarChart.setOption(option)
  
  // 响应式
  window.addEventListener('resize', () => {
    radarChart?.resize()
  })
}

// 获取jieba词云数据
async function fetchWordcloudData() {
  wordcloudLoading.value = true
  try {
    const res = await axios.get(`${API_BASE}/admin/wordcloud_jieba`)
    console.log('词云API返回:', res.data)
    if (res.data && res.data.status === 'success') {
      wordcloudData.value = res.data.words || []
      console.log('词云数据已更新, 词数:', wordcloudData.value.length)
    } else {
      console.warn('词云API返回异常:', res.data)
    }
  } catch (e) { 
    console.error('获取词云数据失败', e) 
  }
  finally { wordcloudLoading.value = false }
}

// 获取维度相关性热力图数据
async function fetchCorrelationData() {
  correlationLoading.value = true
  try {
    const res = await axios.get(`${API_BASE}/admin/dimension_correlation`)
    if (res.data && res.data.status === 'success') {
      correlationData.value = res.data
    }
  } catch (e) { console.error('获取相关性数据失败', e) }
  finally { correlationLoading.value = false }
}

// 获取平台类型分布数据
async function fetchCategoryData() {
  categoryLoading.value = true
  try {
    const res = await axios.get(`${API_BASE}/admin/platform_category`)
    console.log('类型分布API返回:', res.data)
    if (res.data && res.data.status === 'success') {
      categoryData.value = res.data.categories || []
      platformTotals.value = {
        qidian: res.data.total_qidian || 0,
        zongheng: res.data.total_zongheng || 0
      }
      console.log('类型分布数据已更新, 类别数:', categoryData.value.length)
      console.log('平台总数量:', platformTotals.value)
    } else {
      console.warn('类型分布API返回异常:', res.data)
    }
  } catch (e) { 
    console.error('获取类型分布数据失败', e) 
  }
  finally { categoryLoading.value = false }
}

// 刷新所有可视化数据
async function fetchAllAnalytics() {
  await Promise.all([
    fetchRadarData(),
    fetchWordcloudData(),
    fetchCorrelationData(),
    fetchCategoryData()
  ])
}

// ==================== 工具函数 ====================

// 生成雷达图路径
const getRadarPath = (dimensions: number[], maxVal: number = 100) => {
  if (!dimensions || dimensions.length !== 6) return ''
  const centerX = 100
  const centerY = 100
  const radius = 80
  const angleStep = (Math.PI * 2) / 6

  const points = dimensions.map((val, i) => {
    const angle = i * angleStep - Math.PI / 2
    const r = (val / maxVal) * radius
    const x = centerX + r * Math.cos(angle)
    const y = centerY + r * Math.sin(angle)
    return `${x},${y}`
  })

  return 'M' + points.join(' L') + ' Z'
}

// 获取热力图颜色
const getHeatmapColor = (value: number) => {
  // value范围 -1 到 1，转换为颜色
  if (value >= 0.8) return '#dc2626' // 深红
  if (value >= 0.6) return '#ef4444' // 红
  if (value >= 0.4) return '#f87171' // 浅红
  if (value >= 0.2) return '#fca5a5' // 淡红
  if (value >= 0) return '#fecaca' // 很淡红
  if (value >= -0.2) return '#bfdbfe' // 淡蓝
  if (value >= -0.4) return '#93c5fd' // 浅蓝
  if (value >= -0.6) return '#60a5fa' // 蓝
  if (value >= -0.8) return '#3b82f6' // 深蓝
  return '#2563eb' // 很深蓝
}

// 柱状图悬停状态和提示框位置
const hoveredCategory = ref<any>(null)
const hoveredTooltipPos = ref({ left: 0, top: 0 })

// 处理分类悬停事件
const onCategoryHover = (cat: any, event: MouseEvent) => {
  hoveredCategory.value = cat
  const rect = (event.currentTarget as SVGGElement)?.getBoundingClientRect()
  if (rect) {
    // 使用fixed定位，基于屏幕坐标
    hoveredTooltipPos.value = {
      left: rect.left + rect.width / 2,
      top: rect.top - 10
    }
  }
}

// 计算柱状图最大值（用于Y轴刻度）
const maxCategoryCount = computed(() => {
  if (!categoryData.value.length) return 100
  return Math.max(
    ...categoryData.value.map(c => Math.max(c.qidian_count || 0, c.zongheng_count || 0))
  )
})

// 计算柱状图高度（百分比）
const getCategoryBarHeight = (count: number, platform: 'qidian' | 'zongheng') => {
  if (!categoryData.value.length) return 0
  
  // 获取该平台下所有分类的最大值
  const maxCount = platform === 'qidian' 
    ? Math.max(...categoryData.value.map(c => c.qidian_count))
    : Math.max(...categoryData.value.map(c => c.zongheng_count))
  
  if (maxCount === 0) return 0
  return Math.max((count / maxCount) * 100, 5) // 最小5%高度
}

// Top3 奖牌颜色
const medalColor = (idx: number) => {
  if (idx === 0) return 'from-amber-400 to-yellow-500 shadow-amber-200/50';
  if (idx === 1) return 'from-slate-300 to-slate-400 shadow-slate-200/50';
  if (idx === 2) return 'from-orange-400 to-amber-600 shadow-orange-200/50';
  return 'from-slate-100 to-slate-200';
};
</script>

<template>
  <EditorialLayout :showDock="true">
    <div class="min-h-screen p-5 pb-20 text-slate-900 relative z-10">

      <!-- 大屏标题 -->
      <header class="text-center mb-5 relative">
        <div class="text-[10px] font-bold tracking-[0.3em] text-slate-400 uppercase mb-1">IP Lumina · Data Visualization</div>
        <h1 class="font-serif text-3xl font-bold tracking-wider text-slate-900">
          核心数据概览大屏
        </h1>
        <div class="w-48 h-0.5 bg-gradient-to-r from-transparent via-indigo-400 to-transparent mx-auto mt-2"></div>
      </header>

      <!-- 统计卡片 (跨度 12) -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <div v-for="stat in stats" :key="stat.title" class="relative group">
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm hover:shadow-md transition-all p-4 flex items-center gap-3 h-[80px]">
            <div class="w-10 h-10 rounded-lg bg-gradient-to-br flex items-center justify-center text-white shadow-md flex-shrink-0" :class="stat.color">
              <component :is="stat.icon" class="w-5 h-5" />
            </div>
            <div>
              <p class="text-[11px] text-slate-500 mb-0.5 font-bold">{{ stat.title }}</p>
              <div class="text-2xl font-sans font-bold text-slate-900 leading-tight">{{ stat.value }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== Row 2: 月票排名 + 月票趋势 + 平台对比 ==================== -->
      <div class="grid grid-cols-12 gap-4 mb-5">
        <!-- 左侧：实时月票总榜 TOP 10 -->
        <div class="col-span-12 lg:col-span-3">
          <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm p-4 h-[380px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <Crown class="w-4 h-4 text-amber-500" />
                {{ ticketPlatform === 'qidian' ? '起点月票榜' : '纵横月票榜' }} TOP 10
              </h3>
              <!-- 平台切换按钮 -->
              <div class="flex gap-1">
                <button 
                  @click="switchTicketPlatform('qidian')"
                  class="px-2 py-0.5 rounded text-[10px] font-medium transition-colors"
                  :class="ticketPlatform === 'qidian' ? 'bg-orange-500 text-white' : 'bg-orange-50 text-orange-600 hover:bg-orange-100'"
                >起点</button>
                <button 
                  @click="switchTicketPlatform('zongheng')"
                  class="px-2 py-0.5 rounded text-[10px] font-medium transition-colors"
                  :class="ticketPlatform === 'zongheng' ? 'bg-blue-500 text-white' : 'bg-blue-50 text-blue-600 hover:bg-blue-100'"
                >纵横</button>
              </div>
            </div>
            <!-- 加载状态 -->
            <div v-if="realtimeRankingLoading" class="flex-1 flex items-center justify-center">
              <div class="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <!-- 排名列表 -->
            <div v-else class="flex-1 overflow-y-auto custom-scrollbar space-y-1 pr-1">
              <div v-if="realtimeTicketRanking.length === 0" class="h-full flex items-center justify-center text-slate-400 text-sm">暂无月票数据</div>
              <div 
                v-for="(item, idx) in realtimeTicketRanking.slice(0, 10)" 
                :key="idx"
                class="flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all hover:bg-slate-50/80 group cursor-pointer"
                :class="idx < 3 ? 'bg-gradient-to-r from-amber-50/60 to-transparent' : ''"
              >
                <!-- 排名序号 -->
                <div 
                  class="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-black flex-shrink-0 shadow-sm"
                  :class="idx === 0 ? 'bg-gradient-to-br from-amber-400 to-yellow-500 text-white' : idx === 1 ? 'bg-gradient-to-br from-slate-300 to-slate-400 text-white' : idx === 2 ? 'bg-gradient-to-br from-orange-400 to-amber-600 text-white' : 'bg-slate-100 text-slate-500'"
                >
                  {{ idx + 1 }}
                </div>
                <!-- 书名 + 平台 -->
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-bold text-slate-800 truncate leading-tight group-hover:text-indigo-700 transition-colors">{{ item.title }}</div>
                  <span 
                    class="inline-block mt-0.5 px-1.5 py-0.5 rounded text-[9px] font-bold"
                    :class="item.platform === '起点' ? 'bg-orange-100 text-orange-600' : 'bg-blue-100 text-blue-600'"
                  >{{ item.platform }}</span>
                </div>
                <!-- 月票数 -->
                <div class="text-right flex-shrink-0">
                  <span 
                    class="font-black tabular-nums"
                    :class="idx < 3 ? 'text-lg text-amber-600' : 'text-sm text-slate-600'"
                  >{{ formatNum(item.monthly_tickets) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 中间：全站阅读热度趋势 (多线) -->
        <div class="col-span-12 lg:col-span-6">
          <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm p-4 h-[380px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <TrendingUp class="w-4 h-4 text-blue-500" />
                全站阅读热度趋势
              </h3>
              <span class="text-[10px] text-slate-400">起点与纵横热门作品月票趋势对比</span>
            </div>
            <div class="text-center mb-1">
              <span class="text-base font-bold text-slate-800">起点与纵横热门作品月票趋势对比</span>
              <div class="text-[10px] text-slate-400 mt-0.5">各平台热度最高且延续最长的前5名作品</div>
            </div>
            <div class="flex-1 relative" style="min-height: 0;">
              <MultiTicketTrend />
            </div>
          </div>
        </div>

        <!-- 右侧：平台书本数量对比 -->
        <div class="col-span-12 lg:col-span-3">
          <div class="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl shadow-sm p-4 h-[380px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <BarChart3 class="w-4 h-4 text-indigo-500" />
                平台书库规模对比
              </h3>
            </div>
            <div class="flex-1 relative" style="min-height: 0;">
              <PlatformBarChart />
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== Row 3: 六维度雷达图 + 相关性热力图 + 评级分布 ==================== -->
      <div class="grid grid-cols-12 gap-4 mb-5">
        
        <!-- 全站跨维综合指标雷达图 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[320px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <Radar class="w-4 h-4 text-violet-500" />
                全站跨维综合指标雷达图
              </h3>
            </div>
            <div class="flex-1 w-full relative" v-if="!radarLoading">
              <div ref="radarChartRef" class="w-full h-full"></div>
            </div>
            <div v-else class="flex-1 flex items-center justify-center">
              <div class="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          </div>
        </div>

        <!-- 维度相关性热力图 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[320px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <Grid3X3 class="w-4 h-4 text-indigo-500" />
                IP 六大维度相关性分析
              </h3>
            </div>
            <div class="flex-1 relative" style="min-height: 0;">
              <CorrelationHeatmap />
            </div>
          </div>
        </div>

        <!-- IP评级/等级分布 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[320px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <BarChart3 class="w-4 h-4 text-emerald-500" />
                全站作品 IP 评级分布
              </h3>
            </div>
            <div class="flex-1 relative" style="min-height: 0;">
              <ScoreDistribution />
            </div>
          </div>
        </div>

      </div>

      <!-- ==================== Row 4: 读者地域分布 + 平台题材配比 + 热门词云 ==================== -->
      <div class="grid grid-cols-12 gap-4">
        
        <!-- 读者地域热度分布 (地图) -->
        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[360px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <MapPin class="w-4 h-4 text-sky-500" />
                核心读者地域热度分布
              </h3>
              <span class="text-[10px] text-slate-400 font-mono">平台 IP 属地</span>
            </div>
            <div class="flex-1 relative" style="min-height: 0;">
              <GeoMap />
            </div>
          </div>
        </div>

        <!-- 平台作品资源类别配比 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[360px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <PieChart class="w-4 h-4 text-pink-500" />
                平台作品题材资源配比
              </h3>
              <span class="text-[10px] text-slate-400">分类词频统计</span>
            </div>
            <div class="flex-1 relative" style="min-height: 0;">
              <CategoryPie />
            </div>
          </div>
        </div>

        <!-- 热门畅销作者或标签词云 -->
        <div class="col-span-12 lg:col-span-4 flex flex-col">
          <div class="bg-white/60 backdrop-blur-xl border border-white/40 rounded-xl shadow-sm p-4 h-[360px] flex flex-col">
            <div class="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 class="text-sm font-bold text-slate-700 flex items-center gap-2">
                <Cloud class="w-4 h-4 text-teal-500" />
                热门畅销主题聚焦词云
              </h3>
              <span class="text-[10px] text-slate-400">高频词汇提取</span>
            </div>
            <div class="flex-1 relative" style="min-height: 0;">
              <WordCloud />
            </div>
          </div>
        </div>

      </div>
    </div>
    
    <!-- 全局悬停提示框（fixed定位，避免被裁剪） -->
    <Teleport to="body">
      <div 
        v-if="hoveredCategory"
        class="fixed z-[9999] bg-slate-800 text-white px-3 py-2 rounded-lg shadow-xl pointer-events-none text-center"
        :style="{ 
          left: hoveredTooltipPos.left + 'px', 
          top: hoveredTooltipPos.top + 'px',
          transform: 'translate(-50%, -100%)'
        }"
      >
        <div class="text-[10px] text-slate-400 mb-0.5">{{ hoveredCategory.category }}</div>
        <div class="flex items-center gap-3 text-[11px]">
          <span class="text-indigo-300 font-semibold">起点: {{ hoveredCategory.qidian_count.toLocaleString() }}</span>
          <span class="text-blue-300 font-semibold">纵横: {{ hoveredCategory.zongheng_count.toLocaleString() }}</span>
        </div>
        <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800"></div>
      </div>
    </Teleport>
  </EditorialLayout>
</template>

<style scoped>
/* Custom scrollbar for small areas like the top10 list */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 4px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: #94a3b8;
}
</style>
