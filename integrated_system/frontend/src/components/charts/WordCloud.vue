<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import * as echarts from 'echarts';
import 'echarts-wordcloud';
import axios from 'axios';

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: echarts.ECharts | null = null;
const API_BASE = 'http://localhost:5000/api';

// Neon Color Palette
const colors = ['#06b6d4', '#3b82f6', '#8b5cf6', '#d946ef', '#ec4899', '#f43f5e', '#22d3ee', '#a855f7'];

const initChart = async () => {
  if (!chartRef.value) return;
  chartInstance = echarts.init(chartRef.value);

  let data: any[] = [];
  let hasError = false;

  try {
    const res = await axios.get(`${API_BASE}/charts/wordcloud`);
    if (Array.isArray(res.data) && res.data.length > 0) {
      data = res.data.slice(0, 30).map((item: any) => ({
        name: item.name || item.word,
        value: item.value || item.count || 50
      }));
    } else {
      hasError = true;
    }
  } catch (e) {
    console.warn("WordCloud Fetch Fail", e);
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
    backgroundColor: 'transparent',
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '90%',
      height: '90%',
      sizeRange: [14, 55],
      rotationRange: [-45, 45],
      rotationStep: 15,
      gridSize: 8,
      drawOutOfBound: false,
      layoutAnimation: true,
      textStyle: {
        fontFamily: 'sans-serif',
        fontWeight: 'bold',
        color: () => colors[Math.floor(Math.random() * colors.length)]
      },
      emphasis: {
        focus: 'self',
        textStyle: {
          textShadowBlur: 10,
          textShadowColor: '#fff'
        }
      },
      data: data
    }]
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
