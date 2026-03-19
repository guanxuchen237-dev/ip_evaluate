<template>
  <div class="heatmap-dashboard">
    <div class="heatmap-header">
      <h3>热门作品月票热力�?/h3>
      <div class="platform-tabs">
        <button 
          :class="['tab-btn', { active: activePlatform === 'qidian' }]"
          @click="activePlatform = 'qidian'"
        >
          起点
        </button>
        <button 
          :class="['tab-btn', { active: activePlatform === 'zongheng' }]"
          @click="activePlatform = 'zongheng'"
        >
          纵横
        </button>
      </div>
    </div>
    
    <div class="heatmap-container">
      <div ref="chartRef" class="chart-container"></div>
    </div>
    
    <div class="heatmap-legend">
      <span class="legend-label">低热�?/span>
      <div class="legend-gradient"></div>
      <span class="legend-label">高热�?/span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null
const activePlatform = ref<'qidian' | 'zongheng'>('qidian')
const heatmapData = ref<{qidian: any[], zongheng: any[]}>({ qidian: [], zongheng: [] })

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  renderChart()
}

const renderChart = () => {
  if (!chartInstance) return
  
  const platform = activePlatform.value
  const books = heatmapData.value[platform]
  
  if (books.length === 0) {
    chartInstance.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center' }
    })
    return
  }
  
  // 收集所有月份
  const allMonths: Set<string> = new Set()
  books.forEach(book => {
    book.dates.forEach((date: string) => allMonths.add(date))
  })
  const sortedMonths = Array.from(allMonths).sort()
  
  // 构建热力图数据 [x, y, value]
  const data: [number, number, number][] = []
  books.forEach((book, yIndex) => {
    const dateMap = new Map<string, number>()
    book.dates.forEach((date: string, i: number) => {
      dateMap.set(date, book.tickets[i] || 0)
    })
    
    sortedMonths.forEach((month: string, xIndex: number) => {
      const value = dateMap.get(month) || 0
      data.push([xIndex, yIndex, value])
    })
  })
  
  // 计算最大值用于颜色映射
  const maxValue = Math.max(...data.map(d => d[2]), 1)
  
  const option = {
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const month = sortedMonths[params.data[0]]
        const book = books[params.data[1]]
        return `${book.title}<br/>${month}: ${params.data[2].toLocaleString()} 票`
      }
    },
    grid: {
      height: '70%',
      top: '10%',
      left: '15%',
      right: '5%'
    },
    xAxis: {
      type: 'category',
      data: sortedMonths,
      splitArea: { show: true },
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        formatter: (value: string) => value.slice(2) // 显示 21-01 格式
      }
    },
    yAxis: {
      type: 'category',
      data: books.map(b => b.title),
      splitArea: { show: true },
      axisLabel: {
        fontSize: 11,
        width: 120,
        overflow: 'truncate'
      }
    },
    visualMap: {
      min: 0,
      max: maxValue,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '5%',
      inRange: {
        color: ['#f0f9ff', '#bae6fd', '#7dd3fc', '#38bdf8', '#0ea5e9', '#0284c7', '#0369a1']
      }
    },
    series: [{
      name: '月票',
      type: 'heatmap',
      data: data,
      label: {
        show: false
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }
  
  chartInstance.setOption(option, true)
}

const fetchData = async () => {
  try {
    const res = await axios.get(`${API_BASE}/charts/heatmap_data`)
    if (res.data.status === 'success') {
      heatmapData.value = res.data.data
      renderChart()
    }
  } catch (e) {
    console.error('[Heatmap] Fetch data failed:', e)
  }
}

// 监听平台切换
watch(activePlatform, renderChart)

onMounted(() => {
  initChart()
  fetchData()
  
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
})

onUnmounted(() => {
  chartInstance?.dispose()
})
</script>

<style scoped>
.heatmap-dashboard {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.heatmap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.heatmap-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.platform-tabs {
  display: flex;
  gap: 8px;
}

.tab-btn {
  padding: 6px 16px;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.tab-btn:hover {
  background: #f8fafc;
}

.tab-btn.active {
  background: #0ea5e9;
  color: white;
  border-color: #0ea5e9;
}

.heatmap-container {
  height: 500px;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e2e8f0;
}

.legend-label {
  font-size: 12px;
  color: #64748b;
}

.legend-gradient {
  width: 150px;
  height: 12px;
  background: linear-gradient(to right, #f0f9ff, #bae6fd, #7dd3fc, #38bdf8, #0ea5e9, #0284c7, #0369a1);
  border-radius: 6px;
}
</style>
