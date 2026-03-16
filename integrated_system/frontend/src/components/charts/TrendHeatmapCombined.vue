<template>
  <div class="trend-heatmap-combined">
    <div class="section-header">
      <h3>
        <span class="icon">🔥</span>
        热门作品长期趋势分析
      </h3>
      <div class="platform-tabs">
        <button 
          :class="['tab-btn', { active: activePlatform === 'qidian' }]"
          @click="switchPlatform('qidian')"
        >
          起点
        </button>
        <button 
          :class="['tab-btn', { active: activePlatform === 'zongheng' }]"
          @click="switchPlatform('zongheng')"
        >
          纵横
        </button>
      </div>
    </div>

    <!-- 热力图区�?-->
    <div class="heatmap-section">
      <div class="section-title">月票热力分布</div>
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>加载�?..</span>
      </div>
      <div v-else-if="!hasData" class="empty-state">
        <span class="empty-icon">📊</span>
        <span>暂无数据</span>
      </div>
      <div v-else ref="heatmapRef" class="heatmap-chart"></div>
    </div>

    <!-- 趋势图区�?-->
    <div class="trend-section">
      <div class="section-title">月度走势对比</div>
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>加载�?..</span>
      </div>
      <div v-else-if="!hasData" class="empty-state">
        <span class="empty-icon">📈</span>
        <span>暂无数据</span>
      </div>
      <div v-else ref="trendRef" class="trend-chart"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

const heatmapRef = ref<HTMLDivElement>()
const trendRef = ref<HTMLDivElement>()
let heatmapChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null

const activePlatform = ref<'qidian' | 'zongheng'>('qidian')
const heatmapData = ref<{qidian: any[], zongheng: any[]}>({ qidian: [], zongheng: [] })
const loading = ref(true)

const hasData = computed(() => {
  const books = heatmapData.value[activePlatform.value]
  return books && books.length > 0
})

const switchPlatform = (platform: 'qidian' | 'zongheng') => {
  activePlatform.value = platform
  renderCharts()
}

const initCharts = () => {
  if (heatmapRef.value) heatmapChart = echarts.init(heatmapRef.value)
  if (trendRef.value) trendChart = echarts.init(trendRef.value)
}

const renderCharts = () => {
  console.log('[TrendHeatmap] renderCharts called, heatmapChart:', !!heatmapChart, 'trendChart:', !!trendChart)
  
  if (!heatmapChart || !trendChart) {
    console.log('[TrendHeatmap] Charts not initialized, returning')
    return
  }
  
  const platform = activePlatform.value
  const books = heatmapData.value[platform]
  
  console.log('[TrendHeatmap] Rendering for platform:', platform, 'books count:', books?.length || 0)
  
  if (!books || books.length === 0) {
    console.log('[TrendHeatmap] No books data, returning')
    return
  }
  
  // 收集所有月�?  const allMonths = new Set<string>()
  books.forEach((book: any) => {
    book.dates.forEach((date: string) => allMonths.add(date))
  })
  const sortedMonths = Array.from(allMonths).sort()
  
  // ========== 热力�?==========
  const heatmapDataArr: [number, number, number][] = []
  books.forEach((book: any, yIndex: number) => {
    const dateMap = new Map<string, number>()
    book.dates.forEach((date: string, i: number) => {
      dateMap.set(date, book.tickets[i] || 0)
    })
    
    sortedMonths.forEach((month: string, xIndex: number) => {
      const value = dateMap.get(month) || 0
      heatmapDataArr.push([xIndex, yIndex, value])
    })
  })
  
  const maxValue = Math.max(...heatmapDataArr.map(d => d[2]))
  
  heatmapChart.setOption({
    tooltip: {
      position: 'top',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#1e293b' },
      formatter: (params: any) => {
        const month = sortedMonths[params.data[0]]
        const book = books[params.data[1]]
        return `<div style="font-weight:600">${book.title}</div>
                <div style="color:#64748b;font-size:12px">${month}</div>
                <div style="color:#0ea5e9;font-weight:600">${params.data[2].toLocaleString()} �?/div>`
      }
    },
    grid: {
      height: '75%',
      top: '5%',
      left: '18%',
      right: '3%'
    },
    xAxis: {
      type: 'category',
      data: sortedMonths,
      splitArea: { show: true },
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: '#64748b',
        formatter: (value: string) => value.slice(2)
      },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'category',
      data: books.map((b: any) => b.title),
      splitArea: { show: true },
      axisLabel: {
        fontSize: 11,
        width: 140,
        overflow: 'truncate',
        color: '#334155'
      },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    visualMap: {
      min: 0,
      max: maxValue,
      show: false,
      inRange: {
        color: ['#f0f9ff', '#bae6fd', '#7dd3fc', '#38bdf8', '#0ea5e9', '#0284c7', '#0369a1']
      }
    },
    series: [{
      type: 'heatmap',
      data: heatmapDataArr,
      label: { show: false },
      emphasis: {
        itemStyle: {
          shadowBlur: 8,
          shadowColor: 'rgba(14, 165, 233, 0.5)'
        }
      }
    }]
  }, true)
  
  // ========== 趋势�?==========
  const series = books.map((book: any, index: number) => ({
    name: book.title,
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 4,
    data: sortedMonths.map((month: string) => {
      const idx = book.dates.indexOf(month)
      return idx >= 0 ? book.tickets[idx] : null
    }),
    lineStyle: { width: 2 },
    emphasis: { focus: 'series' }
  }))
  
  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#1e293b' }
    },
    legend: {
      type: 'scroll',
      top: 0,
      textStyle: { fontSize: 11, color: '#64748b' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: sortedMonths,
      axisLabel: {
        fontSize: 10,
        color: '#64748b',
        formatter: (value: string) => value.slice(2)
      },
      axisLine: { lineStyle: { color: '#e2e8f0' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 10,
        color: '#64748b',
        formatter: (value: number) => value >= 10000 ? (value/10000).toFixed(1) + 'w' : value
      },
      splitLine: { lineStyle: { color: '#f1f5f9' } }
    },
    series
  }, true)
}

const fetchData = async () => {
  loading.value = true
  try {
    console.log('[TrendHeatmap] Fetching data from:', `${API_BASE}/charts/top_books_monthly_trend`)
    const res = await axios.get(`${API_BASE}/charts/top_books_monthly_trend`)
    console.log('[TrendHeatmap] API response:', res.data)
    if (res.data.status === 'success') {
      heatmapData.value = res.data.data
      console.log('[TrendHeatmap] Data loaded:', {
        qidian: heatmapData.value.qidian?.length || 0,
        zongheng: heatmapData.value.zongheng?.length || 0
      })
      // 等待DOM更新后再初始化图�?      await nextTick()
      // 确保图表已初始化再渲�?      if (!heatmapChart && heatmapRef.value) {
        heatmapChart = echarts.init(heatmapRef.value)
      }
      if (!trendChart && trendRef.value) {
        trendChart = echarts.init(trendRef.value)
      }
      renderCharts()
    }
  } catch (e: any) {
    console.error('[TrendHeatmap] Fetch failed:', e.message || e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  initCharts()
  fetchData()
  
  const handleResize = () => {
    heatmapChart?.resize()
    trendChart?.resize()
  }
  window.addEventListener('resize', handleResize)
  
  onUnmounted(() => {
    window.removeEventListener('resize', handleResize)
    heatmapChart?.dispose()
    trendChart?.dispose()
  })
})
</script>

<style scoped>
.trend-heatmap-combined {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon {
  font-size: 20px;
}

.platform-tabs {
  display: flex;
  gap: 6px;
  background: #f8fafc;
  padding: 4px;
  border-radius: 8px;
}

.tab-btn {
  padding: 6px 16px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #334155;
}

.tab-btn.active {
  background: white;
  color: #0ea5e9;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.section-title {
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid #0ea5e9;
}

.heatmap-section {
  margin-bottom: 24px;
}

.heatmap-chart {
  height: 320px;
  background: #fafafa;
  border-radius: 12px;
}

.trend-section {
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
}

.trend-chart {
  height: 260px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #94a3b8;
  gap: 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #0ea5e9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 32px;
  opacity: 0.5;
}
</style>
