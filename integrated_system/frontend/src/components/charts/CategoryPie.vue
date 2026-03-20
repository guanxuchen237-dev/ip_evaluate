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

  let data: any[] = [];
  let hasError = false;

  try {
     const res = await axios.get(`${API_BASE}/charts/distribution`);
     if (res.data && Array.isArray(res.data) && res.data.length > 0) {
         data = res.data; 
     } else {
         hasError = true;
     }
  } catch (e) {
     console.warn("Category Fetch Fail", e);
     hasError = true;
  }

  if (hasError || data.length === 0) {
    // 显示空状态
    chartInstance.setOption({
      title: {
        text: '暂无数据',
        subtext: '后端服务未启动或数据为空',
        left: 'center',
        top: 'center',
        textStyle: { color: '#94a3b8', fontSize: 16 },
        subtextStyle: { color: '#cbd5e1', fontSize: 12 }
      }
    });
    return;
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
