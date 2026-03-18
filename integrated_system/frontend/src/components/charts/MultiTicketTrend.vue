<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";
import axios from 'axios';

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const API_BASE = 'http://localhost:5000/api';

// 平台切换
const currentPlatform = ref<'all' | 'qidian' | 'zongheng'>('all');
const platforms = [
  { key: 'all', label: '全部', color: 'bg-slate-100 text-slate-700' },
  { key: 'qidian', label: '起点', color: 'bg-indigo-100 text-indigo-700' },
  { key: 'zongheng', label: '纵横', color: 'bg-blue-100 text-blue-700' }
];

const fetchData = async (platform: string) => {
  const colors = ['#6366f1', '#3b82f6', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];
  let seriesData: any[] = [];
  let xAxisData: string[] = [];
  
  try {
    const res = await axios.get(`${API_BASE}/charts/ticket_trend_multi?platform=${platform}`);
    if (res.data && res.data.dates && res.data.series) {
      xAxisData = res.data.dates || [];
      seriesData = (res.data.series || []).map((s: any, idx: number) => {
        const itemColor = s.color || colors[idx % colors.length];
        return {
          name: s.name,
          type: 'line',
          smooth: 0.4,
          symbol: 'none',
          connectNulls: true,
          lineStyle: { width: 2.5 },
          itemStyle: { color: itemColor },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: itemColor + '33' },
              { offset: 1, color: itemColor + '00' }
            ])
          },
          data: s.data
        };
      });
    }
  } catch (e) {
    console.warn("Multi-ticket trend fetch failed", e);
  }
  
  return { seriesData, xAxisData };
};

const initChart = async () => {
  if (!chartRef.value) return;
  chartInstance = echarts.init(chartRef.value);
  await updateChart();
};

const updateChart = async () => {
  if (!chartInstance) return;
  
  const { seriesData, xAxisData } = await fetchData(currentPlatform.value);
  
  // 如果没有数据，显示提示
  if (seriesData.length === 0) {
    chartInstance.setOption({
      title: {
        text: '暂无符合条件的数据',
        left: 'center',
        top: 'center',
        textStyle: { color: '#94a3b8', fontSize: 14 }
      }
    });
    return;
  }

  const option = {
    title: { show: false },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#475569', fontSize: 11 },
      padding: [8, 12],
      formatter: (params: any[]) => {
        let html = `<div class="font-bold mb-1">${params[0].axisValue}</div>`;
        params.forEach(p => {
          // 跳过null值的数据点
          if (p.value === null || p.value === undefined) return;
          const value = typeof p.value === 'number' ? p.value.toLocaleString() : p.value;
          html += `<div class="flex items-center gap-1 text-xs">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
            <span class="text-slate-500">${p.seriesName}:</span>
            <span class="font-semibold">${value}</span>
          </div>`;
        });
        return html;
      }
    },
    legend: {
      type: 'scroll',
      bottom: 0,
      left: 'center',
      itemWidth: 12,
      itemHeight: 8,
      textStyle: { fontSize: 10, color: '#64748b' },
      pageIconSize: 10,
      pageTextStyle: { fontSize: 10 }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '8%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisLine: { show: true, lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8', fontSize: 10, interval: 'auto' }
    },
    yAxis: {
      type: 'value',
      name: '月票数量',
      nameTextStyle: { color: '#94a3b8', fontSize: 10 },
      splitLine: {
        lineStyle: { color: '#f1f5f9', type: 'dashed' }
      },
      axisLabel: { 
        color: '#94a3b8', fontSize: 10,
        formatter: (value: number) => {
          if (value >= 10000) return (value / 10000).toFixed(0) + '万';
          return value.toString();
        }
      }
    },
    series: seriesData
  };

  chartInstance.setOption(option, true);
};

// 监听平台切换
watch(currentPlatform, () => {
  updateChart();
});

onMounted(() => {
  initChart();
  window.addEventListener("resize", () => chartInstance?.resize());
});

onUnmounted(() => {
  window.removeEventListener("resize", () => chartInstance?.resize());
  chartInstance?.dispose();
});
</script>

<template>
  <div class="w-full h-full flex flex-col">
    <!-- 平台切换按钮 -->
    <div class="flex justify-end gap-1 mb-1">
      <button 
        v-for="p in platforms" 
        :key="p.key"
        @click="currentPlatform = p.key as any"
        :class="[
          'px-2 py-0.5 rounded text-[10px] font-medium transition-all',
          currentPlatform === p.key ? p.color : 'bg-slate-50 text-slate-400 hover:bg-slate-100'
        ]"
      >{{ p.label }}</button>
    </div>
    <!-- 图表 -->
    <div ref="chartRef" class="flex-1 w-full" />
  </div>
</template>
