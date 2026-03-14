<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import * as echarts from "echarts";
import axios from 'axios';

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const API_BASE = 'http://localhost:5000/api';

const initChart = async () => {
  if (!chartRef.value) return;
  chartInstance = echarts.init(chartRef.value);

  // Default Data
  let xAxisData = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  let seriesData = [820, 932, 901, 934, 1290, 1330, 1320, 1000, 1200, 1100, 1050, 900];

  try {
     const res = await axios.get(`${API_BASE}/charts/trend`);
     // Assume data structure { x: [], y: [] } or similar
     if (res.data && res.data.dates && res.data.values) {
         xAxisData = res.data.dates;
         seriesData = res.data.values;
     }
  } catch (e) {
     console.warn("Trend Fetch Fail", e);
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#475569' }
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
      boundaryGap: false,
      data: xAxisData,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#94a3b8' } // Slate-400
    },
    yAxis: {
      type: 'value',
      splitLine: {
        lineStyle: {
           color: '#f1f5f9', // Slate-100
           type: 'dashed'
        }
      },
      axisLabel: { 
        color: '#94a3b8',
        formatter: (value: number) => {
          if (value >= 10000) return (value / 10000).toFixed(0) + ' 万';
          return value.toString();
        } 
      }
    },
    series: [
      {
        name: 'Interaction Index',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: '#3b82f6', // Blue-500
          width: 3
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.2)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.0)' }
          ])
        },
        data: seriesData
      }
    ]
  };

  chartInstance.setOption(option);
};

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
  <div ref="chartRef" class="w-full h-full" />
</template>
