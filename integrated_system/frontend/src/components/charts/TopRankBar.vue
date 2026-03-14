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

  // Mock data
  let data = [
    { name: '天下长宁', value: 90.9 },
    { name: '天启大令', value: 92.4 },
    { name: '虽然', value: 92.7 }, 
    { name: '长宁帝军', value: 92.9 },
    { name: '剑仙在此', value: 96.4 },
    { name: '深大榜神', value: 97.0 },
    { name: '我有一剑', value: 97.8 },
    { name: '剑来', value: 98.6 },
    { name: '诡秘之主', value: 99.3 },
    { name: '滚杭之王', value: 100.0 }
  ];

  try {
     const res = await axios.get(`${API_BASE}/charts/rank`);
     if (res.data && Array.isArray(res.data)) {
        data = res.data.map((item: any) => ({
             name: item.title,
             value: parseFloat((item.IP_Score || 60).toFixed(1))
        })).sort((a: any,b: any) => a.value - b.value).slice(-10); 
     }
  } catch (e) {
     console.warn("Rank Fetch Fail", e);
  }

  const option = {
    grid: {
      top: '5%',
      left: '2%',
      right: '10%',
      bottom: '2%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      splitLine: { show: false },
      axisLabel: { show: false }
    },
    yAxis: {
      type: 'category',
      data: data.map(i => i.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: '#64748b', // Slate-500
        fontSize: 12,
        fontWeight: 'bold'
      }
    },
    series: [
      {
        type: 'bar',
        data: data.map(i => i.value),
        barWidth: 10,
        itemStyle: {
          borderRadius: 5,
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#6366f1' }, // Indigo-500
            { offset: 1, color: '#3b82f6' }  // Blue-500
          ])
        },
        label: {
          show: true,
          position: 'right',
          color: '#64748b',
          formatter: '{c}'
        },
        showBackground: true,
        backgroundStyle: {
          color: '#f1f5f9', // Slate-100
          borderRadius: 5
        }
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
