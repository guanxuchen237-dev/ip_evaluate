<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'

const API_BASE = 'http://localhost:5000/api'
const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const platformData = ref({ qidian: 0, zongheng: 0 })

const fetchData = async () => {
  try {
    const res = await axios.get(`${API_BASE}/charts/platform`)
    if (res.data && Array.isArray(res.data)) {
      const qd = res.data.find((i: any) => i.name === '起点' || i.name === 'Qidian')?.value || 0
      const zh = res.data.find((i: any) => i.name === '纵横' || i.name === 'Zongheng')?.value || 0
      platformData.value = { qidian: qd, zongheng: zh }
      renderChart()
    }
  } catch (e) {
    console.error('获取平台数据失败', e)
  }
}

const renderChart = () => {
  if (!chartInstance) return
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = params[0]
        return `<div style="font-weight:bold">${p.name}</div>
                <div>作品数量: <span style="font-weight:bold">${p.value.toLocaleString()}</span> 本</div>`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['起点', '纵横'],
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { 
        color: '#475569',
        fontSize: 12,
        fontWeight: 'bold'
      }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (value: number) => {
          if (value >= 1000) return (value / 1000).toFixed(1) + 'k'
          return value.toString()
        }
      }
    },
    series: [{
      type: 'bar',
      barWidth: '50%',
      data: [
        {
          value: platformData.value.qidian,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#6366f1' },
              { offset: 1, color: '#4f46e5' }
            ]),
            borderRadius: [6, 6, 0, 0]
          }
        },
        {
          value: platformData.value.zongheng,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#3b82f6' },
              { offset: 1, color: '#2563eb' }
            ]),
            borderRadius: [6, 6, 0, 0]
          }
        }
      ],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0, 0, 0, 0.1)'
        }
      },
      label: {
        show: true,
        position: 'top',
        color: '#475569',
        fontSize: 11,
        fontWeight: 'bold',
        formatter: (params: any) => params.value.toLocaleString()
      }
    }]
  }
  
  chartInstance.setOption(option)
}

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  fetchData()
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chartInstance?.resize())
})
</script>

<template>
  <div ref="chartRef" class="w-full h-full"></div>
</template>
