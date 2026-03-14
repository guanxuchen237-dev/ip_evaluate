<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const chartRef = ref<HTMLDivElement>()

const dimensionData = [
  { dimension: "Story", fullMark: 100, value: 88, label: "故事性" },
  { dimension: "Character", fullMark: 100, value: 92, label: "人物塑造" },
  { dimension: "World", fullMark: 100, value: 75, label: "世界观" },
  { dimension: "Commercial", fullMark: 100, value: 85, label: "商业价值" },
  { dimension: "Adaptability", fullMark: 100, value: 78, label: "改编潜力" },
  { dimension: "Safety", fullMark: 100, value: 95, label: "安全性" },
]

onMounted(() => {
  if (!chartRef.value) return

  const chart = echarts.init(chartRef.value)

  const option: EChartsOption = {
    radar: {
      indicator: dimensionData.map(d => ({
        name: d.dimension,
        max: 100
      })),
      radius: '70%',
      axisName: {
        color: 'hsl(215, 25%, 30%)',
        fontSize: 12,
        fontWeight: 500
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(255, 255, 255, 0.1)', 'rgba(255, 255, 255, 0.2)']
        }
      },
      splitLine: {
        lineStyle: {
          color: 'hsl(210, 20%, 88%)'
        }
      }
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'rgba(255, 255, 255, 0.3)',
      borderWidth: 1,
      borderRadius: 12,
      extraCssText: 'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);',
      formatter: (params: any) => {
        let listHtml = ''
        dimensionData.forEach((dim, index) => {
           const val = params.value[index]
           listHtml += `
             <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 2px;">
               <span style="font-size: 12px; opacity: 0.8;">${dim.label}</span>
               <span style="font-size: 13px; font-weight: 600; color: hsl(160, 50%, 50%);">${val}</span>
             </div>
           `
        })
        
        return `
          <div style="padding: 8px 12px;">
            <div style="font-weight: 600; margin-bottom: 6px; border-bottom: 1px solid rgba(0,0,0,0.1); padding-bottom: 4px;">
              IP 维度分析
            </div>
            ${listHtml}
          </div>
        `
      }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: dimensionData.map(d => d.value),
            name: 'IP Score',
            lineStyle: {
              color: 'hsl(160, 50%, 50%)',
              width: 2
            },
            areaStyle: {
              color: 'hsl(160, 50%, 50%)',
              opacity: 0.25
            }
          }
        ]
      }
    ]
  }

  chart.setOption(option)

  const resizeObserver = new ResizeObserver(() => {
    chart.resize()
  })
  resizeObserver.observe(chartRef.value)
})
</script>

<template>
  <div>
    <div ref="chartRef" class="h-[280px] w-full"></div>

    <!-- Legend -->
    <div class="grid grid-cols-3 gap-2 mt-4">
      <div 
        v-for="dim in dimensionData" 
        :key="dim.dimension" 
        class="flex items-center justify-between px-3 py-2 rounded-lg bg-white/50"
      >
        <span class="text-xs text-muted-foreground">{{ dim.label }}</span>
        <span class="text-sm font-semibold text-foreground">{{ dim.value }}</span>
      </div>
    </div>
  </div>
</template>
