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

  // Professional Palette
  const colors = ['#3b82f6', '#06b6d4', '#8b5cf6', '#64748b', '#94a3b8']; 
  // Blue, Cyan, Violet, Slate-Dark, Slate-Light

  let data = [
    { value: 1048, name: '都市' },
    { value: 735, name: '玄幻' },
    { value: 580, name: '科幻' },
    { value: 484, name: '仙侠' },
    { value: 300, name: '历史' }
  ];

  try {
     const res = await axios.get(`${API_BASE}/charts/distribution`);
     if (res.data && Array.isArray(res.data)) {
         data = res.data; 
     }
  } catch (e) {
     console.warn("Category Fetch Fail", e);
  }

  const option = {
    color: colors,
    tooltip: {
      trigger: 'item'
    },
    legend: {
      bottom: '0%', // Move to bottom
      left: 'center',
      textStyle: {
        color: '#64748b' 
      }
    },
    series: [
      {
        name: 'Access From',
        type: 'pie',
        radius: ['25%', '40%'], // Compact radius to maximize label space
        center: ['50%', '45%'], // Centered
        avoidLabelOverlap: true, // Ensure no overlap
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}: {d}%',
          color: '#475569', // Slate-600
          overflow: 'none', // Prevent truncation
          fontSize: 11
        },
        labelLine: {
          show: true,
          lineStyle: {
            color: '#cbd5e1' // Slate-300
          }
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: data
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
