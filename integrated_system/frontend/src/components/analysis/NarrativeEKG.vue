<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const chartRef = ref<HTMLDivElement>()

// Simulated emotional intensity data across chapters
const narrativeData = [
  { chapter: 1, intensity: 35, event: "开篇" },
  { chapter: 2, intensity: 42, event: "" },
  { chapter: 3, intensity: 55, event: "初遇" },
  { chapter: 4, intensity: 48, event: "" },
  { chapter: 5, intensity: 72, event: "第一次冲突" },
  { chapter: 6, intensity: 58, event: "" },
  { chapter: 7, intensity: 45, event: "" },
  { chapter: 8, intensity: 38, event: "平静期" },
  { chapter: 9, intensity: 52, event: "" },
  { chapter: 10, intensity: 85, event: "重大转折" },
  { chapter: 11, intensity: 78, event: "" },
  { chapter: 12, intensity: 65, event: "" },
  { chapter: 13, intensity: 55, event: "" },
  { chapter: 14, intensity: 68, event: "真相揭晓" },
  { chapter: 15, intensity: 92, event: "高潮" },
  { chapter: 16, intensity: 75, event: "" },
  { chapter: 17, intensity: 58, event: "" },
  { chapter: 18, intensity: 45, event: "余韵" },
  { chapter: 19, intensity: 52, event: "" },
  { chapter: 20, intensity: 65, event: "结局" },
]

onMounted(() => {
  if (!chartRef.value) return

  const chart = echarts.init(chartRef.value)

  const option: EChartsOption = {
    grid: {
      top: 40,
      right: 30,
      bottom: 40,
      left: 40
    },
    xAxis: {
      type: 'category',
      data: narrativeData.map(d => d.chapter),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: 'hsl(215, 15%, 50%)',
        fontSize: 11
      },
      name: 'Chapter',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: {
        color: 'hsl(215, 15%, 50%)',
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: 'hsl(215, 15%, 50%)',
        fontSize: 11
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.3)',
      borderWidth: 1,
      extraCssText: 'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);',
      textStyle: {
        color: '#333'
      },
      formatter: (params: any) => {
        const data = Array.isArray(params) ? params[0] : params
        const dataIndex = typeof data?.dataIndex === 'number' ? data.dataIndex : -1
        const item = dataIndex >= 0 ? narrativeData[dataIndex] : undefined
        if (!item) return ''
        return `
          <div style="padding: 8px;">
            <div style="font-size: 14px; font-weight: 500;">第 ${item.chapter} 章</div>
            <div style="font-size: 16px; font-weight: 600; color: hsl(210, 70%, 55%); margin-top: 4px;">
              情感强度: ${item.intensity}
            </div>
            ${item.event ? `<div style="font-size: 12px; color: #999; margin-top: 4px;">📍 ${item.event}</div>` : ''}
          </div>
        `
      }
    },
    series: [
      {
        type: 'line',
        data: narrativeData.map(d => d.intensity),
        smooth: true,
        lineStyle: {
          width: 3,
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: 'hsl(210, 70%, 55%)' },
              { offset: 0.5, color: 'hsl(0, 70%, 55%)' },
              { offset: 1, color: 'hsl(270, 50%, 60%)' }
            ]
          }
        },
        showSymbol: false,
        emphasis: {
          itemStyle: {
            color: 'hsl(0, 70%, 55%)',
            borderColor: '#fff',
            borderWidth: 2
          }
        }
      }
    ],
    markLine: {
      silent: true,
      symbol: 'none',
      lineStyle: {
        type: 'dashed'
      },
      data: [
        {
          yAxis: 70,
          lineStyle: {
            color: 'hsl(0, 70%, 55%)',
            opacity: 0.5
          }
        },
        {
          yAxis: 50,
          lineStyle: {
            color: 'hsl(210, 70%, 55%)',
            opacity: 0.3
          }
        }
      ]
    }
  }

  chart.setOption(option)

  // Handle resize
  const resizeObserver = new ResizeObserver(() => {
    chart.resize()
  })
  resizeObserver.observe(chartRef.value)
})
</script>

<template>
  <div class="h-[280px]">
    <div ref="chartRef" class="w-full h-full"></div>

    <div class="flex items-center justify-center gap-6 mt-4 text-xs text-muted-foreground">
      <div class="flex items-center gap-2">
        <div class="w-3 h-0.5 bg-chart-red opacity-50 border-dashed"></div>
        <span>High Tension Zone (70+)</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-0.5 bg-chart-blue opacity-30 border-dashed"></div>
        <span>Baseline (50)</span>
      </div>
    </div>
  </div>
</template>
