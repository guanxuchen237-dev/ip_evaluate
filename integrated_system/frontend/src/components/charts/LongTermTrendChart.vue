<template>
  <div class="h-full w-full flex flex-col p-4 bg-white/60 rounded-xl border border-white/40 backdrop-blur-xl shadow-sm hover:shadow-md transition-all group">
    <div class="flex items-center justify-between z-10 flex-shrink-0">
      <div class="flex items-center">
        <div class="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center mr-3 shadow-sm border border-indigo-100">
          <TrendingUp class="w-4 h-4 text-indigo-500" />
        </div>
        <div>
          <h3 class="text-slate-700 text-sm font-bold tracking-wide">{{ title }}</h3>
          <p class="text-[10px] text-slate-400 mt-0.5">2020-2025 历史月票互动走势</p>
        </div>
      </div>
    </div>
    
    <div class="flex-1 w-full relative mt-1 z-10">
      <div ref="chartRef" class="absolute inset-0 w-full h-full"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';
import axios from 'axios';
import { TrendingUp } from 'lucide-vue-next';

const props = defineProps<{
  platform: 'qidian' | 'zongheng';
  title: string;
}>();

const chartRef = ref<HTMLElement | null>(null);
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';
let chartInstance: echarts.ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

const qidianColors = ['#F59E0B', '#3B82F6', '#10B981', '#EF4444', '#8B5CF6'];
const zonghengColors = ['#06b6d4', '#ec4899', '#f97316', '#6366f1', '#84cc16'];

const initChart = async () => {
  if (!chartRef.value) return;
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }
  
  chartInstance.showLoading({
    text: '',
    color: '#6366f1',
    maskColor: 'rgba(255, 255, 255, 0)'
  });

  try {
    const res = await axios.get(`${API_BASE}/charts/long_term_trend?platform=${props.platform}`);
    const data = res.data;
    
    const colors = props.platform === 'qidian' ? qidianColors : zonghengColors;

    if (data && data.dates && data.series) {
      const option = {
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          borderColor: '#e2e8f0',
          borderWidth: 1,
          padding: [8, 12],
          textStyle: { color: '#334155', fontSize: 12 },
          axisPointer: {
            type: 'line',
            lineStyle: { color: '#cbd5e1', width: 1, type: 'dashed' }
          }
        },
        legend: {
          data: data.series.map((s: any) => s.name),
          textStyle: { color: '#64748b', fontSize: 11 },
          itemWidth: 12, itemHeight: 8,
          icon: 'roundRect',
          bottom: 0,
          type: 'scroll'
        },
        grid: {
          top: '8%',
          left: '2%',
          right: '5%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: data.dates,
          axisLine: { lineStyle: { color: '#cbd5e1' } },
          axisLabel: { color: '#64748b', fontSize: 10 },
          splitLine: { show: false }
        },
        yAxis: {
          type: 'value',
          axisLine: { show: false },
          axisLabel: {
            color: '#64748b',
            fontSize: 10,
            formatter: (value: number) => {
              if (value >= 10000) return (value / 10000).toFixed(0) + 'w';
              return value;
            }
          },
          splitLine: {
            lineStyle: { color: '#f1f5f9', type: 'dashed' }
          }
        },
        series: data.series.map((s: any, idx: number) => ({
          name: s.name,
          type: 'line',
          smooth: 0.4,
          symbol: 'circle',
          symbolSize: 0, 
          showSymbol: false,
          lineStyle: {
            width: 2.5,
            color: colors[idx % colors.length]
          },
          itemStyle: {
            color: colors[idx % colors.length]
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: colors[idx % colors.length] + '30' },
              { offset: 1, color: colors[idx % colors.length] + '00' }
            ])
          },
          emphasis: {
            focus: 'series',
            itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' }
          },
          data: s.data
        }))
      };
      chartInstance.setOption(option, true);
    }
  } catch (err) {
    console.error(`Failed to load long term trend for ${props.platform}`, err);
  } finally {
    chartInstance.hideLoading();
  }
};

onMounted(() => {
  initChart();
  if (chartRef.value) {
    resizeObserver = new ResizeObserver(() => {
      chartInstance?.resize();
    });
    resizeObserver.observe(chartRef.value);
  } else {
    window.addEventListener('resize', () => chartInstance?.resize());
  }
});

watch(() => props.platform, () => {
  initChart();
});

onUnmounted(() => {
  if (resizeObserver && chartRef.value) {
    resizeObserver.disconnect();
  } else {
    window.removeEventListener('resize', () => chartInstance?.resize());
  }
  chartInstance?.dispose();
});
</script>
